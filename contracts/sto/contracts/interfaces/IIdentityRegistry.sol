// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IIdentityRegistry {
    struct Identity {
        bool verified;
        uint16 country;      // ISO 3166-1 numeric (380=IT, 276=DE, 840=US, ...)
        uint40 verifiedAt;
        uint40 expiresAt;
        bytes32 kycProvider; // hash of provider id (Sumsub, internal, etc.)
    }

    event IdentityRegistered(address indexed investor, uint16 country, uint40 expiresAt, bytes32 kycProvider);
    event IdentityUpdated(address indexed investor, uint16 country, uint40 expiresAt);
    event IdentityRemoved(address indexed investor);
    event AgentAdded(address indexed agent);
    event AgentRemoved(address indexed agent);

    function registerIdentity(
        address investor,
        uint16 country,
        uint40 expiresAt,
        bytes32 kycProvider
    ) external;

    function removeIdentity(address investor) external;

    function isVerified(address investor) external view returns (bool);

    function identityOf(address investor) external view returns (Identity memory);

    function addAgent(address agent) external;
    function removeAgent(address agent) external;
    function isAgent(address agent) external view returns (bool);
}
