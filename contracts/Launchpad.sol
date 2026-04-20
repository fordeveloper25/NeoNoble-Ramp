// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./BondingCurveToken.sol";

/*
 * NeoNoble Launchpad Factory
 *
 * Deploy dei token bonding-curve. Chi crea un token paga una fee
 * fissa in BNB (es. 0.05 BNB ~ 25 EUR ai prezzi correnti).
 * NESSUN collateral richiesto al creator oltre la fee.
 *
 * Admin:
 *  - puo` aggiornare `deployFee` e `platformFeeRecipient`
 *  - non puo` toccare i token gia` deployati
 */

contract Launchpad {
    address public owner;
    address public platformFeeRecipient;
    uint256 public deployFee = 0.05 ether;

    address[] public allTokens;
    mapping(address => address[]) public tokensByCreator;

    event TokenCreated(
        address indexed token,
        address indexed creator,
        string name,
        string symbol,
        string metadataURI,
        uint256 timestamp
    );
    event DeployFeeChanged(uint256 newFee);
    event OwnerChanged(address newOwner);
    event FeeRecipientChanged(address newRecipient);

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    constructor(address _platformFeeRecipient) {
        require(_platformFeeRecipient != address(0), "feeRcp=0");
        owner = msg.sender;
        platformFeeRecipient = _platformFeeRecipient;
    }

    function setDeployFee(uint256 newFee) external onlyOwner {
        deployFee = newFee;
        emit DeployFeeChanged(newFee);
    }

    function setPlatformFeeRecipient(address newRecipient) external onlyOwner {
        require(newRecipient != address(0), "zero");
        platformFeeRecipient = newRecipient;
        emit FeeRecipientChanged(newRecipient);
    }

    function setOwner(address newOwner) external onlyOwner {
        require(newOwner != address(0), "zero");
        owner = newOwner;
        emit OwnerChanged(newOwner);
    }

    function createToken(
        string calldata name,
        string calldata symbol,
        string calldata metadataURI
    ) external payable returns (address tokenAddr) {
        require(msg.value >= deployFee, "insufficient fee");
        require(bytes(name).length > 0 && bytes(name).length <= 50, "bad name");
        require(bytes(symbol).length > 0 && bytes(symbol).length <= 12, "bad symbol");

        BondingCurveToken token = new BondingCurveToken(
            name,
            symbol,
            metadataURI,
            msg.sender,
            platformFeeRecipient
        );
        tokenAddr = address(token);
        allTokens.push(tokenAddr);
        tokensByCreator[msg.sender].push(tokenAddr);

        // inoltra la fee di deploy al platform recipient
        (bool ok, ) = payable(platformFeeRecipient).call{value: msg.value}("");
        require(ok, "fee transfer");

        emit TokenCreated(tokenAddr, msg.sender, name, symbol, metadataURI, block.timestamp);
    }

    function allTokensLength() external view returns (uint256) {
        return allTokens.length;
    }

    function getTokensByCreator(address creator) external view returns (address[] memory) {
        return tokensByCreator[creator];
    }
}
