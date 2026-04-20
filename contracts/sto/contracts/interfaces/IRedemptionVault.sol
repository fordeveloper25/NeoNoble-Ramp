// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IRedemptionVault {
    event RedemptionRequested(
        uint256 indexed requestId,
        address indexed investor,
        uint256 tokenAmount,
        uint256 navSnapshot,
        uint40 requestedAt
    );
    event RedemptionApproved(uint256 indexed requestId, address indexed operator);
    event RedemptionRejected(uint256 indexed requestId, address indexed operator, string reason);
    event RedemptionClaimed(uint256 indexed requestId, address indexed investor, uint256 stablecoinAmount);

    function requestRedemption(uint256 tokenAmount) external returns (uint256 requestId);
    function approve(uint256 requestId) external;
    function reject(uint256 requestId, string calldata reason) external;
    function claim(uint256 requestId) external;
    function fund(uint256 stablecoinAmount) external;
}
