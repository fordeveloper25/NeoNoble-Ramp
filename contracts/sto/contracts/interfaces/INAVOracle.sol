// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface INAVOracle {
    event NAVUpdated(uint256 navPerToken, uint40 effectiveFrom, bytes32 reportHash);

    /**
     * NAV per token in stablecoin units (6 decimals for USDC, 18 for DAI).
     * Se il token STO vale nominalmente 250 EUR e 1 USDC = 1 EUR, navPerToken = 250e6.
     */
    function navPerToken() external view returns (uint256);

    /**
     * Timestamp a partire dal quale il NAV corrente e` efficace (per redemption).
     */
    function effectiveFrom() external view returns (uint40);

    /**
     * Hash (ipfs/keccak) del report NAV pubblicato (auditable).
     */
    function reportHash() external view returns (bytes32);

    /**
     * Settlement stablecoin (es. USDC su Polygon).
     */
    function settlementToken() external view returns (address);
}
