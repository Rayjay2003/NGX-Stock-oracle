// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;
import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

contract FakeUSDC is ERC20 {
    constructor() ERC20("Fake USDC", "fUSDC") {
        _mint(msg.sender, 1_000_000 * 1e6); // 1 million fake USDC
    }
    function decimals() public pure override returns (uint8) { return 6; }
}