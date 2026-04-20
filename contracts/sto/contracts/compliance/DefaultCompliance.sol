// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "../interfaces/ICompliance.sol";
import "../interfaces/IIdentityRegistry.sol";

/**
 * DefaultCompliance — regole MiCA / TUF 100-bis base
 *
 * - Tutti i transfer (mint/burn/transfer/transferFrom) DEVONO avere
 *   entrambe le parti (from,to) KYC-verificate; eccezioni: mint da 0x0
 *   (solo destinatario verificato) e burn verso 0x0 (solo mittente).
 * - Lock-up globale fino a `lockupUntil` (per adempiere vesting
 *   regolamentari post-issuance, es. 12 mesi).
 * - Max holder (per restare sotto soglie prospetto): se raggiunto,
 *   nuovi holder bloccati (trasferimenti verso holder esistenti sempre ok).
 * - Country allowlist: se non vuota, country del destinatario deve esservi.
 *
 * Token e` autorizzato a chiamare `transferred/created/destroyed` per
 * aggiornare il contatore holder.
 */
contract DefaultCompliance is ICompliance {
    address public owner;
    address public token;                 // autorizzato a chiamare i hook state-mutating
    IIdentityRegistry public registry;

    uint40 public lockupUntil;            // 0 = disabilitato
    uint256 public maxHolders;            // 0 = illimitato
    uint256 public holdersCount;

    mapping(address => uint256) public balancesCache; // helper per tracking holder count
    mapping(uint16 => bool) public allowedCountries;  // se nessun country e` abilitato => allowlist disabilitata
    bool public countryAllowlistActive;
    mapping(address => bool) public exempt;           // vault / escrow / treasury — non contano come holders, bypass country

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }
    modifier onlyToken() {
        require(msg.sender == token, "not token");
        _;
    }

    constructor(address _owner, address _registry) {
        require(_owner != address(0) && _registry != address(0), "zero");
        owner = _owner;
        registry = IIdentityRegistry(_registry);
    }

    function setOwner(address newOwner) external onlyOwner {
        require(newOwner != address(0), "zero");
        owner = newOwner;
    }

    function setToken(address newToken) external onlyOwner {
        require(newToken != address(0), "zero");
        token = newToken;
    }

    function setLockup(uint40 until) external onlyOwner {
        lockupUntil = until;
        emit LockupSet(until);
    }

    function setMaxHolders(uint256 max) external onlyOwner {
        maxHolders = max;
        emit MaxHoldersSet(max);
    }

    function setCountryAllowed(uint16 country, bool allowed) external onlyOwner {
        allowedCountries[country] = allowed;
        countryAllowlistActive = true;
        emit CountryRestrictionSet(country, allowed);
    }

    function disableCountryAllowlist() external onlyOwner {
        countryAllowlistActive = false;
    }

    function setExempt(address addr, bool isExempt) external onlyOwner {
        exempt[addr] = isExempt;
    }

    // --- Hook views ---

    function canTransfer(address from, address to, uint256 amount) external view returns (bool) {
        // Lockup globale (non blocca mint ne` burn; non blocca movimenti con exempt endpoint)
        if (from != address(0) && to != address(0) && !exempt[from] && !exempt[to]) {
            if (lockupUntil != 0 && block.timestamp < lockupUntil) return false;
        }

        // KYC richiesto sempre (tranne per l'indirizzo 0x0 mint/burn e tranne per exempt technical addresses)
        if (from != address(0) && !exempt[from] && !registry.isVerified(from)) return false;
        if (to   != address(0) && !exempt[to]   && !registry.isVerified(to))   return false;

        // Country allowlist sul destinatario (exempt bypassa)
        if (to != address(0) && !exempt[to] && countryAllowlistActive) {
            uint16 cTo = registry.identityOf(to).country;
            if (!allowedCountries[cTo]) return false;
        }

        // Max holders: se il destinatario non e` gia` holder e non e` exempt, controllo soglia.
        if (maxHolders > 0 && to != address(0) && !exempt[to] && balancesCache[to] == 0 && amount > 0) {
            if (holdersCount >= maxHolders) return false;
        }

        return true;
    }

    // --- Hook state-mutating (chiamati dal token dopo il transfer) ---

    function _applyDelta(address from, address to, uint256 amount) internal {
        if (from != address(0) && !exempt[from]) {
            uint256 newFrom = balancesCache[from] - amount;
            balancesCache[from] = newFrom;
            if (newFrom == 0 && holdersCount > 0) holdersCount -= 1;
        } else if (from != address(0)) {
            balancesCache[from] -= amount; // exempt: traccia balance per symmetry ma non tocca counter
        }
        if (to != address(0) && !exempt[to]) {
            uint256 prevTo = balancesCache[to];
            balancesCache[to] = prevTo + amount;
            if (prevTo == 0 && amount > 0) holdersCount += 1;
        } else if (to != address(0)) {
            balancesCache[to] += amount;
        }
    }

    function transferred(address from, address to, uint256 amount) external onlyToken {
        _applyDelta(from, to, amount);
        emit TransferApproved(from, to, amount);
    }

    function created(address to, uint256 amount) external onlyToken {
        _applyDelta(address(0), to, amount);
    }

    function destroyed(address from, uint256 amount) external onlyToken {
        _applyDelta(from, address(0), amount);
    }
}
