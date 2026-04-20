// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/*
 * NeoNoble Launchpad — BondingCurveToken
 *
 * Modello: virtual constant-product AMM (stile Pump.fun).
 *
 *   k = virtualBnbReserve * virtualTokenReserve   (invariante)
 *
 * Le reserve sono "virtuali" nel senso che bootstrapano la curva con un
 * prezzo iniziale ragionevole senza che nessuno debba depositare capitale
 * upfront. Il creator del token NON deposita nulla: paga solo la fee di
 * deploy al factory.
 *
 * Liquidita` reale: arriva esclusivamente dagli acquisti degli utenti
 * (realBnbReserve). Quando realBnbReserve >= GRADUATION_BNB la curva si
 * chiude e i fondi+token residui vengono emessi in un evento che il
 * backend off-chain puo` usare per migrare su PancakeSwap V3 (v2+).
 *
 * Fee: 1% su ogni buy/sell (in BNB) va a `platformFeeRecipient`.
 *
 * Security notes:
 *  - reentrancy guard su buy/sell (transferimenti in ETH)
 *  - no owner backdoor, no mint unbounded, no admin pause
 *  - mint totale max = TOKENS_ON_CURVE + TOKENS_FOR_LP
 */

interface IERC20 {
    function totalSupply() external view returns (uint256);
    function balanceOf(address account) external view returns (uint256);
    function transfer(address to, uint256 amount) external returns (bool);
    function allowance(address owner, address spender) external view returns (uint256);
    function approve(address spender, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);
}

contract BondingCurveToken is IERC20 {
    // --- ERC20 standard ---
    string public name;
    string public symbol;
    uint8 public constant decimals = 18;
    uint256 private _totalSupply;
    mapping(address => uint256) private _balances;
    mapping(address => mapping(address => uint256)) private _allowances;

    // --- Bonding curve ---
    uint256 public constant TOKENS_ON_CURVE = 800_000_000 * 1e18; // 800M per bonding curve
    uint256 public constant TOKENS_FOR_LP   = 200_000_000 * 1e18; // 200M riservati per LP PancakeSwap post-graduation
    uint256 public constant INITIAL_VIRTUAL_BNB   = 30 ether;
    uint256 public constant INITIAL_VIRTUAL_TOKEN = 1_073_000_000 * 1e18; // Pump.fun-style
    uint256 public constant GRADUATION_BNB = 85 ether; // quando si raggiunge, curva chiusa

    uint256 public virtualBnbReserve;
    uint256 public virtualTokenReserve;
    uint256 public realBnbReserve;   // BNB depositati da buyer reali
    uint256 public realTokenReserve; // tokens gia` venduti ai buyer
    bool public graduated;

    uint256 public constant PLATFORM_FEE_BPS = 100; // 1%
    uint256 public constant CREATOR_FEE_BPS  = 100; // 1% al creator come incentivo

    address public immutable creator;
    address public immutable platformFeeRecipient;
    address public immutable factory;
    string public metadataURI; // IPFS / URL descrittivo (logo, descrizione)

    bool private _locked;
    modifier nonReentrant() {
        require(!_locked, "reentrancy");
        _locked = true;
        _;
        _locked = false;
    }

    event Buy(address indexed buyer, uint256 bnbIn, uint256 tokensOut, uint256 priceAfter);
    event Sell(address indexed seller, uint256 tokensIn, uint256 bnbOut, uint256 priceAfter);
    event Graduated(uint256 bnbCollected, uint256 tokensForLp);

    constructor(
        string memory _name,
        string memory _symbol,
        string memory _metadataURI,
        address _creator,
        address _platformFeeRecipient
    ) {
        require(_creator != address(0), "creator=0");
        require(_platformFeeRecipient != address(0), "feeRcp=0");
        name = _name;
        symbol = _symbol;
        metadataURI = _metadataURI;
        creator = _creator;
        platformFeeRecipient = _platformFeeRecipient;
        factory = msg.sender;
        virtualBnbReserve = INITIAL_VIRTUAL_BNB;
        virtualTokenReserve = INITIAL_VIRTUAL_TOKEN;
    }

    // --- ERC20 minimal ---
    function totalSupply() external view returns (uint256) { return _totalSupply; }
    function balanceOf(address a) external view returns (uint256) { return _balances[a]; }
    function allowance(address o, address s) external view returns (uint256) { return _allowances[o][s]; }

    function transfer(address to, uint256 amount) external returns (bool) {
        _transfer(msg.sender, to, amount);
        return true;
    }
    function approve(address spender, uint256 amount) external returns (bool) {
        _allowances[msg.sender][spender] = amount;
        emit Approval(msg.sender, spender, amount);
        return true;
    }
    function transferFrom(address from, address to, uint256 amount) external returns (bool) {
        uint256 a = _allowances[from][msg.sender];
        require(a >= amount, "allowance");
        if (a != type(uint256).max) _allowances[from][msg.sender] = a - amount;
        _transfer(from, to, amount);
        return true;
    }
    function _transfer(address from, address to, uint256 amount) internal {
        require(to != address(0), "to=0");
        uint256 b = _balances[from];
        require(b >= amount, "balance");
        unchecked { _balances[from] = b - amount; }
        _balances[to] += amount;
        emit Transfer(from, to, amount);
    }
    function _mint(address to, uint256 amount) internal {
        _totalSupply += amount;
        _balances[to] += amount;
        emit Transfer(address(0), to, amount);
    }
    function _burn(address from, uint256 amount) internal {
        uint256 b = _balances[from];
        require(b >= amount, "balance");
        unchecked { _balances[from] = b - amount; _totalSupply -= amount; }
        emit Transfer(from, address(0), amount);
    }

    // --- Curva ---

    /**
     * Quota `bnbIn` -> `tokensOut` (view, senza fee applicate).
     * Usata dal frontend per mostrare il quote live.
     */
    function getTokensOut(uint256 bnbInGross) external view returns (uint256 tokensOut, uint256 bnbAfterFees) {
        uint256 fees = (bnbInGross * (PLATFORM_FEE_BPS + CREATOR_FEE_BPS)) / 10000;
        bnbAfterFees = bnbInGross - fees;
        uint256 k = virtualBnbReserve * virtualTokenReserve;
        uint256 newBnb = virtualBnbReserve + bnbAfterFees;
        uint256 newTok = k / newBnb;
        tokensOut = virtualTokenReserve - newTok;
    }

    /**
     * Quota `tokensIn` -> `bnbOut`.
     */
    function getBnbOut(uint256 tokensIn) external view returns (uint256 bnbOut, uint256 userReceives) {
        uint256 k = virtualBnbReserve * virtualTokenReserve;
        uint256 newTok = virtualTokenReserve + tokensIn;
        uint256 newBnb = k / newTok;
        bnbOut = virtualBnbReserve - newBnb;
        uint256 fees = (bnbOut * (PLATFORM_FEE_BPS + CREATOR_FEE_BPS)) / 10000;
        userReceives = bnbOut - fees;
    }

    /**
     * Prezzo "spot" in BNB per 1 token (1e18).
     */
    function currentPriceWei() external view returns (uint256) {
        // price = virtualBnb / virtualToken per 1 token unit (1e18)
        return (virtualBnbReserve * 1e18) / virtualTokenReserve;
    }

    /**
     * Market cap implicita in BNB: price * (TOKENS_ON_CURVE) (approssimazione).
     */
    function marketCapWei() external view returns (uint256) {
        return (virtualBnbReserve * TOKENS_ON_CURVE) / virtualTokenReserve;
    }

    function buy(uint256 minTokensOut) external payable nonReentrant {
        require(!graduated, "graduated");
        require(msg.value > 0, "zero");

        uint256 platformFee = (msg.value * PLATFORM_FEE_BPS) / 10000;
        uint256 creatorFee  = (msg.value * CREATOR_FEE_BPS)  / 10000;
        uint256 bnbIn = msg.value - platformFee - creatorFee;

        uint256 k = virtualBnbReserve * virtualTokenReserve;
        uint256 newBnb = virtualBnbReserve + bnbIn;
        uint256 newTok = k / newBnb;
        uint256 tokensOut = virtualTokenReserve - newTok;

        require(tokensOut >= minTokensOut, "slippage");
        require(realTokenReserve + tokensOut <= TOKENS_ON_CURVE, "curve exhausted");

        virtualBnbReserve = newBnb;
        virtualTokenReserve = newTok;
        realBnbReserve += bnbIn;
        realTokenReserve += tokensOut;

        _mint(msg.sender, tokensOut);

        // fees
        (bool okP, ) = payable(platformFeeRecipient).call{value: platformFee}("");
        require(okP, "fee-platform");
        (bool okC, ) = payable(creator).call{value: creatorFee}("");
        require(okC, "fee-creator");

        emit Buy(msg.sender, msg.value, tokensOut, this.currentPriceWei());

        if (realBnbReserve >= GRADUATION_BNB) {
            graduated = true;
            // mint 200M LP tokens al factory per migrazione PancakeSwap v2+
            _mint(factory, TOKENS_FOR_LP);
            emit Graduated(realBnbReserve, TOKENS_FOR_LP);
        }
    }

    function sell(uint256 tokensIn, uint256 minBnbOut) external nonReentrant {
        require(!graduated, "graduated");
        require(tokensIn > 0, "zero");
        require(_balances[msg.sender] >= tokensIn, "balance");

        uint256 k = virtualBnbReserve * virtualTokenReserve;
        uint256 newTok = virtualTokenReserve + tokensIn;
        uint256 newBnb = k / newTok;
        uint256 bnbOut = virtualBnbReserve - newBnb;

        // Safety: non possiamo pagare piu` del realBnbReserve effettivamente depositato
        require(bnbOut <= realBnbReserve, "liquidity");

        uint256 platformFee = (bnbOut * PLATFORM_FEE_BPS) / 10000;
        uint256 creatorFee  = (bnbOut * CREATOR_FEE_BPS)  / 10000;
        uint256 userReceives = bnbOut - platformFee - creatorFee;

        require(userReceives >= minBnbOut, "slippage");

        virtualBnbReserve = newBnb;
        virtualTokenReserve = newTok;
        realBnbReserve -= bnbOut;
        realTokenReserve -= tokensIn;

        _burn(msg.sender, tokensIn);

        (bool okU, ) = payable(msg.sender).call{value: userReceives}("");
        require(okU, "pay-user");
        (bool okP, ) = payable(platformFeeRecipient).call{value: platformFee}("");
        require(okP, "fee-platform");
        (bool okC, ) = payable(creator).call{value: creatorFee}("");
        require(okC, "fee-creator");

        emit Sell(msg.sender, tokensIn, userReceives, this.currentPriceWei());
    }

    // Fallback: reject accidental sends
    receive() external payable {
        revert("use buy()");
    }
}
