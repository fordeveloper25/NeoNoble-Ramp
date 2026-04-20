// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "../interfaces/IIdentityRegistry.sol";
import "../interfaces/ICompliance.sol";

/**
 * NenoSecurityToken — ERC-20 + ERC-3643-style transfer restrictions.
 *
 * Struttura:
 *   - `owner` (emittente / NeoNoble Ramp S.r.l.) puo` nominare "agent" che
 *     chiamano mint (subscription) / burn (post-redemption).
 *   - `compliance` e` consultato prima di OGNI movimento (canTransfer)
 *     e notificato dopo.
 *   - `registry` e` la whitelist KYC on-chain.
 *   - `paused`: blocco globale (richiesto da MiCA art. 91 in caso di
 *      market abuse / ordine CONSOB).
 *   - `forcedTransfer`: backdoor amministrativa legalmente richiesta
 *     (es. perdita chiavi investitore, ordine giudiziario, correzione
 *      errore). DEVE essere documentata nel prospetto.
 *   - `setLost`: marca un wallet come "lost" bloccandone i trasferimenti
 *     prima della sostituzione via forcedTransfer.
 *
 * DECIMALI: 18 (standard). Il NAV ha decimali = settlementToken.decimals().
 */
contract NenoSecurityToken {
    // ---------- ERC20 ----------
    string  public name;
    string  public symbol;
    uint8   public constant decimals = 18;
    uint256 private _totalSupply;
    mapping(address => uint256) private _balances;
    mapping(address => mapping(address => uint256)) private _allowances;

    // ---------- governance ----------
    address public owner;
    mapping(address => bool) public agents;           // mint/burn/forcedTransfer
    bool public paused;
    mapping(address => bool) public lost;             // wallet compromessi, blocco

    IIdentityRegistry public registry;
    ICompliance public compliance;

    // ---------- events ----------
    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);
    event OwnerChanged(address indexed newOwner);
    event AgentSet(address indexed agent, bool enabled);
    event Paused(address indexed by);
    event Unpaused(address indexed by);
    event WalletLost(address indexed wallet);
    event WalletRecovered(address indexed lostWallet, address indexed recoveryWallet);
    event ComplianceChanged(address indexed newCompliance);
    event RegistryChanged(address indexed newRegistry);
    event ForcedTransfer(address indexed from, address indexed to, uint256 amount, string reason);

    modifier onlyOwner()  { require(msg.sender == owner, "not owner"); _; }
    modifier onlyAgent()  { require(agents[msg.sender] || msg.sender == owner, "not agent"); _; }
    modifier notPaused()  { require(!paused, "paused"); _; }

    constructor(
        string memory _name,
        string memory _symbol,
        address _owner,
        address _registry,
        address _compliance
    ) {
        require(_owner != address(0), "owner=0");
        require(_registry != address(0) && _compliance != address(0), "zero");
        name = _name;
        symbol = _symbol;
        owner = _owner;
        registry = IIdentityRegistry(_registry);
        compliance = ICompliance(_compliance);
    }

    // ---------- governance setters ----------
    function setOwner(address newOwner) external onlyOwner {
        require(newOwner != address(0), "zero");
        owner = newOwner;
        emit OwnerChanged(newOwner);
    }
    function setAgent(address a, bool enabled) external onlyOwner {
        agents[a] = enabled;
        emit AgentSet(a, enabled);
    }
    function pause()   external onlyOwner { paused = true;  emit Paused(msg.sender); }
    function unpause() external onlyOwner { paused = false; emit Unpaused(msg.sender); }
    function setRegistry(address r) external onlyOwner {
        require(r != address(0), "zero"); registry = IIdentityRegistry(r); emit RegistryChanged(r);
    }
    function setCompliance(address c) external onlyOwner {
        require(c != address(0), "zero"); compliance = ICompliance(c); emit ComplianceChanged(c);
    }
    function setLost(address wallet, bool isLost) external onlyAgent {
        lost[wallet] = isLost;
        if (isLost) emit WalletLost(wallet);
    }

    // ---------- ERC20 ----------
    function totalSupply() external view returns (uint256) { return _totalSupply; }
    function balanceOf(address a) external view returns (uint256) { return _balances[a]; }
    function allowance(address o, address s) external view returns (uint256) { return _allowances[o][s]; }

    function approve(address spender, uint256 amount) external returns (bool) {
        _allowances[msg.sender][spender] = amount;
        emit Approval(msg.sender, spender, amount);
        return true;
    }

    function transfer(address to, uint256 amount) external notPaused returns (bool) {
        _transfer(msg.sender, to, amount);
        return true;
    }

    function transferFrom(address from, address to, uint256 amount) external notPaused returns (bool) {
        uint256 a = _allowances[from][msg.sender];
        require(a >= amount, "allowance");
        if (a != type(uint256).max) _allowances[from][msg.sender] = a - amount;
        _transfer(from, to, amount);
        return true;
    }

    function _transfer(address from, address to, uint256 amount) internal {
        require(to != address(0), "to=0");
        require(!lost[from], "from lost");
        require(compliance.canTransfer(from, to, amount), "compliance");
        uint256 b = _balances[from];
        require(b >= amount, "balance");
        unchecked { _balances[from] = b - amount; }
        _balances[to] += amount;
        compliance.transferred(from, to, amount);
        emit Transfer(from, to, amount);
    }

    // ---------- mint / burn (subscription & redemption) ----------

    function mint(address to, uint256 amount) external onlyAgent notPaused {
        require(to != address(0), "to=0");
        require(compliance.canTransfer(address(0), to, amount), "compliance");
        _totalSupply += amount;
        _balances[to] += amount;
        compliance.created(to, amount);
        emit Transfer(address(0), to, amount);
    }

    function burn(address from, uint256 amount) external onlyAgent {
        uint256 b = _balances[from];
        require(b >= amount, "balance");
        unchecked {
            _balances[from] = b - amount;
            _totalSupply -= amount;
        }
        compliance.destroyed(from, amount);
        emit Transfer(from, address(0), amount);
    }

    // ---------- forced transfer (regulatory backdoor — logged) ----------

    function forcedTransfer(
        address from,
        address to,
        uint256 amount,
        string calldata reason
    ) external onlyAgent {
        require(to != address(0), "to=0");
        require(bytes(reason).length > 0, "reason required");
        // compliance e` comunque rispettata perche` il destinatario DEVE
        // essere KYC-verificato (qualunque sia il motivo del forced transfer).
        require(compliance.canTransfer(from, to, amount), "compliance");
        uint256 b = _balances[from];
        require(b >= amount, "balance");
        unchecked { _balances[from] = b - amount; }
        _balances[to] += amount;
        compliance.transferred(from, to, amount);
        if (lost[from]) emit WalletRecovered(from, to);
        emit ForcedTransfer(from, to, amount, reason);
        emit Transfer(from, to, amount);
    }
}
