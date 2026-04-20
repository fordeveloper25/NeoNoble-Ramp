// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface ICompliance {
    event TransferApproved(address indexed from, address indexed to, uint256 amount);
    event TransferRejected(address indexed from, address indexed to, uint256 amount, string reason);
    event CountryRestrictionSet(uint16 country, bool allowed);
    event MaxHoldersSet(uint256 max);
    event LockupSet(uint40 until);

    /**
     * Pre-transfer hook. Reverts with reason string if transfer is not allowed.
     * Called by the token on every transfer (including mint with from=0x0, burn with to=0x0).
     */
    function canTransfer(address from, address to, uint256 amount) external view returns (bool);

    /**
     * Called by the token AFTER a successful transfer to let the compliance
     * module update its own state (e.g. holder counter).
     */
    function transferred(address from, address to, uint256 amount) external;
    function created(address to, uint256 amount) external;   // mint
    function destroyed(address from, uint256 amount) external; // burn
}
