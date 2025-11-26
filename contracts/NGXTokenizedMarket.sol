// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

interface IStockOracle {
    function getPrice(string memory symbol) external view returns (uint256 price, uint256 timestamp);
}

contract NGXTokenizedMarket is Ownable {
    IStockOracle public immutable oracle;
    mapping(string => address) public stockTokens;
    mapping(string => uint256) public lastPrices;

    event StockCreated(string indexed symbol, address token);
    event Bought(string indexed symbol, address buyer, uint256 usdcAmount, uint256 tokens);

    constructor(address _oracle) Ownable(msg.sender) {
        oracle = IStockOracle(_oracle);
    }

    // DEMO MODE: Create any stock instantly (even if not in oracle yet)
    function createStockDemo(string memory symbol, uint256 fakePriceWei) external onlyOwner {
        require(stockTokens[symbol] == address(0), "Exists");
        address token = address(new TokenizedStock(symbol, fakePriceWei, block.timestamp, address(this)));
        stockTokens[symbol] = token;
        lastPrices[symbol] = fakePriceWei;
        emit StockCreated(symbol, token);
    }

    // Normal path (use when keeper has updated the stock)
    function createStock(string memory symbol) external {
        require(stockTokens[symbol] == address(0), "Exists");
        (uint256 price, ) = oracle.getPrice(symbol);
        require(price > 0, "Not in oracle");
        address token = address(new TokenizedStock(symbol, price, block.timestamp, address(this)));
        stockTokens[symbol] = token;
        lastPrices[symbol] = price;
        emit StockCreated(symbol, token);
    }

    function buy(string memory symbol, uint256 usdcAmount) external {
        address token = stockTokens[symbol];
        require(token != address(0), "Not created");
        TokenizedStock(token).buy(msg.sender, usdcAmount, lastPrices[symbol]);
    }

    function demoMint(string memory symbol, address to, uint256 amount) external onlyOwner {
        TokenizedStock(stockTokens[symbol]).demoMint(to, amount);
    }
}

contract TokenizedStock is ERC20 {
    uint256 public price;
    address public market;

    constructor(string memory symbol, uint256 _price, uint256, address _market)
        ERC20(string(abi.encodePacked("t", symbol)), string(abi.encodePacked("t", symbol)))
    {
        price = _price;
        market = _market;
    }

    function buy(address to, uint256 usdcAmount, uint256 currentPrice) external {
        require(msg.sender == market);
        uint256 tokens = (usdcAmount * 1e18) / currentPrice;
        _mint(to, tokens);
    }

    function demoMint(address to, uint256 amount) external {
        require(msg.sender == market);
        _mint(to, amount);
    }
}