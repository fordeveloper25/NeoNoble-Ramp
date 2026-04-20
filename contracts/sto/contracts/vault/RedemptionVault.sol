// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "../interfaces/IRedemptionVault.sol";
import "../interfaces/INAVOracle.sol";

interface IERC20Minimal {
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
    function decimals() external view returns (uint8);
}

interface ISecurityToken {
    function burn(address from, uint256 amount) external;
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
}

/**
 * RedemptionVault — redemption a NAV con riserva dedicata
 *
 * Flow:
 *   1. Investitore chiama requestRedemption(amount). I suoi token
 *      vengono trasferiti al vault + NAV corrente e` snapshottato.
 *   2. Operator controlla la request (compliance, limiti quote) e la
 *      approva (approve) oppure la rifiuta (reject → token restituiti).
 *   3. Se approvata, il VAULT DEVE avere riserva stablecoin sufficiente
 *      (fund() da parte della tesoreria).
 *   4. Investitore chiama claim(requestId): vault brucia i token via
 *      ISecurityToken.burn() e paga l'investitore in stablecoin.
 *
 * Questo schema garantisce che:
 *   - il NAV usato e` quello all'istante della RICHIESTA (no front-run)
 *   - la tesoreria ha tempo per alimentare la riserva
 *   - in caso di pausa/blocco regolamentare, le richieste restano
 *     congelate senza perdita di fondi
 */
contract RedemptionVault is IRedemptionVault {
    enum Status { None, Pending, Approved, Rejected, Claimed }

    struct Request {
        address investor;
        uint256 tokenAmount;     // token 18dec
        uint256 navSnapshot;     // NAV per 1 token (in settlement decimals)
        uint256 stableAmount;    // = tokenAmount * nav / 1e18, precomputed
        uint40  requestedAt;
        Status  status;
    }

    address public owner;
    mapping(address => bool) public operators;

    ISecurityToken public immutable stoToken;
    INAVOracle public navOracle;
    IERC20Minimal public immutable settlement;

    uint256 public nextRequestId;
    mapping(uint256 => Request) public requests;

    // riserva dedicata (conteggio contabile, non lock hard)
    uint256 public reserveFunded;
    uint256 public reserveLocked; // = somma stableAmount delle Approved non ancora Claimed

    modifier onlyOwner()    { require(msg.sender == owner, "not owner"); _; }
    modifier onlyOperator() { require(operators[msg.sender] || msg.sender == owner, "not operator"); _; }

    constructor(address _owner, address _stoToken, address _navOracle, address _settlement) {
        require(_owner != address(0) && _stoToken != address(0) && _navOracle != address(0) && _settlement != address(0), "zero");
        owner = _owner;
        stoToken = ISecurityToken(_stoToken);
        navOracle = INAVOracle(_navOracle);
        settlement = IERC20Minimal(_settlement);
        require(navOracle.settlementToken() == _settlement, "oracle mismatch");
    }

    function setOwner(address newOwner) external onlyOwner { require(newOwner != address(0),"zero"); owner = newOwner; }
    function setOperator(address op, bool enabled) external onlyOwner { operators[op] = enabled; }
    function setNavOracle(address newOracle) external onlyOwner {
        require(newOracle != address(0), "zero");
        require(INAVOracle(newOracle).settlementToken() == address(settlement), "mismatch");
        navOracle = INAVOracle(newOracle);
    }

    /**
     * Investitore trasferisce i suoi token al vault e snapshott il NAV.
     * Richiede approve(RedemptionVault, amount) sullo STO token prima.
     */
    function requestRedemption(uint256 tokenAmount) external returns (uint256 requestId) {
        require(tokenAmount > 0, "zero");
        // preleva token dall'investitore (richiede approve sullo STO token)
        require(stoToken.transferFrom(msg.sender, address(this), tokenAmount), "transfer");

        uint256 nav = navOracle.navPerToken();
        uint256 stableAmount = (tokenAmount * nav) / 1e18;

        requestId = ++nextRequestId;
        requests[requestId] = Request({
            investor: msg.sender,
            tokenAmount: tokenAmount,
            navSnapshot: nav,
            stableAmount: stableAmount,
            requestedAt: uint40(block.timestamp),
            status: Status.Pending
        });

        emit RedemptionRequested(requestId, msg.sender, tokenAmount, nav, uint40(block.timestamp));
    }

    function approve(uint256 requestId) external onlyOperator {
        Request storage r = requests[requestId];
        require(r.status == Status.Pending, "not pending");
        uint256 available = reserveFunded - reserveLocked;
        require(available >= r.stableAmount, "reserve insufficient");
        reserveLocked += r.stableAmount;
        r.status = Status.Approved;
        emit RedemptionApproved(requestId, msg.sender);
    }

    function reject(uint256 requestId, string calldata reason) external onlyOperator {
        Request storage r = requests[requestId];
        require(r.status == Status.Pending, "not pending");
        r.status = Status.Rejected;
        // restituisce i token all'investitore (brutti o compliance)
        require(stoToken.transfer(r.investor, r.tokenAmount), "refund");
        emit RedemptionRejected(requestId, msg.sender, reason);
    }

    function claim(uint256 requestId) external {
        Request storage r = requests[requestId];
        require(r.status == Status.Approved, "not approved");
        require(msg.sender == r.investor, "not investor");
        r.status = Status.Claimed;

        reserveLocked -= r.stableAmount;
        reserveFunded -= r.stableAmount;

        // brucia i token parcheggiati nel vault (il vault deve essere agent sullo STO token)
        stoToken.burn(address(this), r.tokenAmount);

        // paga l'investitore
        require(settlement.transfer(r.investor, r.stableAmount), "pay");
        emit RedemptionClaimed(requestId, r.investor, r.stableAmount);
    }

    /**
     * Tesoreria NeoNoble alimenta la riserva dedicata.
     * Richiede approve(RedemptionVault, amount) sul settlement token.
     */
    function fund(uint256 stablecoinAmount) external {
        require(stablecoinAmount > 0, "zero");
        require(settlement.transferFrom(msg.sender, address(this), stablecoinAmount), "transfer");
        reserveFunded += stablecoinAmount;
    }

    /**
     * Tesoreria puo` ritirare riserva non locked (es. fine-trimestre,
     * ribilanciamento verso investimenti).
     */
    function withdrawUnlocked(uint256 amount, address to) external onlyOwner {
        require(to != address(0), "zero");
        uint256 available = reserveFunded - reserveLocked;
        require(amount <= available, "locked");
        reserveFunded -= amount;
        require(settlement.transfer(to, amount), "transfer");
    }

    function reserveAvailable() external view returns (uint256) {
        return reserveFunded - reserveLocked;
    }
}
