// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "../interfaces/IIdentityRegistry.sol";

/**
 * IdentityRegistry — on-chain KYC whitelist
 *
 * Solo gli "agent" (es. backoffice NeoNoble + studio legale) possono
 * registrare/rimuovere identita`. L'owner nomina gli agent.
 *
 * L'investitore passa KYC off-chain (Sumsub / manual review) e l'agent
 * pubblica on-chain lo stato. L'ID è l'indirizzo wallet dell'investitore.
 *
 * `kycProvider` permette di revocare in blocco tutti gli utenti verificati
 * da un certo provider se quest'ultimo viene compromesso.
 */
contract IdentityRegistry is IIdentityRegistry {
    address public owner;
    mapping(address => bool) public agents;
    mapping(address => Identity) private _identities;

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    modifier onlyAgent() {
        require(agents[msg.sender] || msg.sender == owner, "not agent");
        _;
    }

    constructor(address _owner) {
        require(_owner != address(0), "owner=0");
        owner = _owner;
    }

    function setOwner(address newOwner) external onlyOwner {
        require(newOwner != address(0), "zero");
        owner = newOwner;
    }

    function addAgent(address agent) external onlyOwner {
        require(agent != address(0), "zero");
        agents[agent] = true;
        emit AgentAdded(agent);
    }

    function removeAgent(address agent) external onlyOwner {
        agents[agent] = false;
        emit AgentRemoved(agent);
    }

    function isAgent(address agent) external view returns (bool) {
        return agents[agent];
    }

    function registerIdentity(
        address investor,
        uint16 country,
        uint40 expiresAt,
        bytes32 kycProvider
    ) external onlyAgent {
        require(investor != address(0), "zero");
        require(expiresAt > uint40(block.timestamp), "already expired");
        _identities[investor] = Identity({
            verified: true,
            country: country,
            verifiedAt: uint40(block.timestamp),
            expiresAt: expiresAt,
            kycProvider: kycProvider
        });
        emit IdentityRegistered(investor, country, expiresAt, kycProvider);
    }

    function removeIdentity(address investor) external onlyAgent {
        delete _identities[investor];
        emit IdentityRemoved(investor);
    }

    function isVerified(address investor) public view returns (bool) {
        Identity memory id = _identities[investor];
        if (!id.verified) return false;
        if (id.expiresAt <= block.timestamp) return false;
        return true;
    }

    function identityOf(address investor) external view returns (Identity memory) {
        return _identities[investor];
    }
}
