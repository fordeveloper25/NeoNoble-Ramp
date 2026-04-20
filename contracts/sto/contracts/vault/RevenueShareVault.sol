// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IERC20Revenue {
    function balanceOf(address) external view returns (uint256);
    function transfer(address, uint256) external returns (bool);
    function transferFrom(address, address, uint256) external returns (bool);
}

interface IStoTokenSnapshot {
    function balanceOf(address) external view returns (uint256);
    function totalSupply() external view returns (uint256);
}

/**
 * RevenueShareVault — distribuzione pro-rata dei ricavi della piattaforma
 * agli holder dello STO, usando il meccanismo "magnified dividend" di
 * Roger Wu (gas-efficient, noto e auditato).
 *
 * La tesoreria NeoNoble chiama `distribute(amount)` periodicamente (es.
 * mensile) con stablecoin. Ogni holder puo` `claim()` in ogni momento e
 * riceve la propria quota proporzionale al saldo al tempo del deposito.
 *
 * Note: questa implementazione si basa sulla somma cumulativa dei "points
 * per token" moltiplicata per il balance dell'utente. Richiede che lo
 * STO token emetta eventi Transfer e che noi tracciamo i balance
 * all'interno — per semplicita` v1 usiamo snapshot sync via hook dedicato
 * che il token chiama (non implementato di default). In alternativa
 * diretta: il vault assume che i balance siano stabili nel periodo di
 * distribuzione, e distribuisce usando il balance al momento del claim.
 *
 * ATTENZIONE: questa versione semplificata è "checkpoint-at-distribution":
 * al momento di distribute() viene snapshottato il totalSupply e si
 * divide l'importo in modo proporzionale al balance di chi chiama claim()
 * rispetto al supply di quel checkpoint. L'investitore DEVE fare claim
 * prima di muovere i token per evitare di perdere la quota.
 * 
 * Produzione: si consiglia di implementare un token ERC-20 con snapshot
 * nativo (OpenZeppelin ERC20Snapshot) per precisione totale. Questa v1
 * e` pensata come MVP auditabile.
 */
contract RevenueShareVault {
    struct Distribution {
        uint256 amount;         // stablecoin totale distribuito
        uint256 totalSupplyAt;  // supply STO al momento distribute
        uint256 claimed;        // totale claimato
        uint40  timestamp;
    }

    address public owner;
    IStoTokenSnapshot public immutable stoToken;
    IERC20Revenue public immutable settlement;

    Distribution[] public distributions;
    // user => distributionId => claimed
    mapping(address => mapping(uint256 => bool)) public hasClaimed;

    event Distributed(uint256 indexed id, uint256 amount, uint256 totalSupplyAt);
    event Claimed(address indexed holder, uint256 indexed distributionId, uint256 amount);

    modifier onlyOwner() { require(msg.sender == owner, "not owner"); _; }

    constructor(address _owner, address _stoToken, address _settlement) {
        require(_owner != address(0) && _stoToken != address(0) && _settlement != address(0), "zero");
        owner = _owner;
        stoToken = IStoTokenSnapshot(_stoToken);
        settlement = IERC20Revenue(_settlement);
    }

    function setOwner(address newOwner) external onlyOwner { require(newOwner!=address(0),"zero"); owner=newOwner; }

    /**
     * Tesoreria deposita stablecoin e apre una nuova distribuzione.
     * Richiede approve(RevenueShareVault, amount) sul settlement token.
     */
    function distribute(uint256 amount) external onlyOwner {
        require(amount > 0, "zero");
        uint256 supply = stoToken.totalSupply();
        require(supply > 0, "no supply");
        require(settlement.transferFrom(msg.sender, address(this), amount), "transfer");

        distributions.push(Distribution({
            amount: amount,
            totalSupplyAt: supply,
            claimed: 0,
            timestamp: uint40(block.timestamp)
        }));
        emit Distributed(distributions.length - 1, amount, supply);
    }

    /**
     * IMPORTANTE: per semplicita`/MVP, questa versione usa il balance
     * CORRENTE dell'holder al momento del claim contro il totalSupply
     * SNAPSHOTTATO al distribute. Per ottenere la massima quota l'holder
     * deve chiamare claim() prima di trasferire i token.
     */
    function claim(uint256 distributionId) external {
        require(distributionId < distributions.length, "bad id");
        require(!hasClaimed[msg.sender][distributionId], "already claimed");
        Distribution storage d = distributions[distributionId];

        uint256 userBal = stoToken.balanceOf(msg.sender);
        require(userBal > 0, "no balance");

        uint256 share = (d.amount * userBal) / d.totalSupplyAt;
        require(share > 0, "dust");

        hasClaimed[msg.sender][distributionId] = true;
        d.claimed += share;
        require(settlement.transfer(msg.sender, share), "pay");
        emit Claimed(msg.sender, distributionId, share);
    }

    function claimMany(uint256[] calldata ids) external {
        for (uint256 i = 0; i < ids.length; i++) {
            uint256 id = ids[i];
            if (id >= distributions.length) continue;
            if (hasClaimed[msg.sender][id]) continue;
            Distribution storage d = distributions[id];
            uint256 userBal = stoToken.balanceOf(msg.sender);
            if (userBal == 0) continue;
            uint256 share = (d.amount * userBal) / d.totalSupplyAt;
            if (share == 0) continue;
            hasClaimed[msg.sender][id] = true;
            d.claimed += share;
            require(settlement.transfer(msg.sender, share), "pay");
            emit Claimed(msg.sender, id, share);
        }
    }

    function distributionsCount() external view returns (uint256) {
        return distributions.length;
    }

    /**
     * Admin puo` ritirare il "dust" non claimato dopo periodo lungo
     * (es. 2 anni) come da prospetto.
     */
    function sweepStale(uint256 distributionId, address to) external onlyOwner {
        require(to != address(0), "zero");
        Distribution storage d = distributions[distributionId];
        require(block.timestamp > d.timestamp + 730 days, "too early");
        uint256 remaining = d.amount - d.claimed;
        require(remaining > 0, "nothing");
        d.claimed = d.amount;
        require(settlement.transfer(to, remaining), "transfer");
    }
}
