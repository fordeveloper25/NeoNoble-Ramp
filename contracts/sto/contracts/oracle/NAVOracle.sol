// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "../interfaces/INAVOracle.sol";

/**
 * NAVOracle — NAV per token pubblicato dall'operatore (es. NeoNoble tesoreria
 * dopo la certificazione del revisore esterno).
 *
 * Ogni aggiornamento include un `reportHash` (IPFS/keccak) del report NAV
 * firmato, che e` auditabile pubblicamente. La redemption usa SEMPRE il NAV
 * all'istante della richiesta, non quello corrente al claim — vedi
 * RedemptionVault.requestRedemption().
 *
 * `effectiveFrom` consente di annunciare in anticipo il prossimo NAV e
 * dare 24-48h di notice agli investitori prima che diventi attivo.
 */
contract NAVOracle is INAVOracle {
    address public owner;
    mapping(address => bool) public operators;

    uint256 private _navPerToken;
    uint40  private _effectiveFrom;
    bytes32 private _reportHash;

    address public immutable settlementTokenAddress;

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }
    modifier onlyOperator() {
        require(operators[msg.sender] || msg.sender == owner, "not operator");
        _;
    }

    constructor(address _owner, address _settlementToken, uint256 _initialNav) {
        require(_owner != address(0) && _settlementToken != address(0), "zero");
        owner = _owner;
        settlementTokenAddress = _settlementToken;
        _navPerToken = _initialNav;
        _effectiveFrom = uint40(block.timestamp);
    }

    function setOwner(address newOwner) external onlyOwner {
        require(newOwner != address(0), "zero");
        owner = newOwner;
    }

    function setOperator(address op, bool enabled) external onlyOwner {
        operators[op] = enabled;
    }

    function updateNAV(
        uint256 newNavPerToken,
        uint40 newEffectiveFrom,
        bytes32 newReportHash
    ) external onlyOperator {
        require(newNavPerToken > 0, "nav=0");
        require(newEffectiveFrom >= uint40(block.timestamp), "past");
        _navPerToken = newNavPerToken;
        _effectiveFrom = newEffectiveFrom;
        _reportHash = newReportHash;
        emit NAVUpdated(newNavPerToken, newEffectiveFrom, newReportHash);
    }

    function navPerToken() external view returns (uint256) {
        return _navPerToken;
    }
    function effectiveFrom() external view returns (uint40) {
        return _effectiveFrom;
    }
    function reportHash() external view returns (bytes32) {
        return _reportHash;
    }
    function settlementToken() external view returns (address) {
        return settlementTokenAddress;
    }
}
