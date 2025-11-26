// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title SimpleStockOracle
 * @dev Stores NGX stock prices on-chain with 18 decimal precision
 * 
 * Supports all 343+ NGX stocks dynamically - no hardcoded symbols
 * Only owner can update prices, anyone can read
 */
contract SimpleStockOracle {
    
    address public owner;
    
    struct StockPrice {
        uint256 price;          // Price scaled to 18 decimals
        uint256 timestamp;      // Last update time
        bool exists;            // Whether stock has been initialized
    }
    
    // symbol (as bytes32) => StockPrice
    mapping(bytes32 => StockPrice) private stockPrices;
    
    // Track all symbols that have been added
    bytes32[] private symbolList;
    mapping(bytes32 => uint256) private symbolIndex;
    
    // Events
    event PriceUpdated(
        string symbol,
        bytes32 indexed symbolBytes,
        uint256 price,
        uint256 timestamp
    );
    
    event BatchUpdateCompleted(
        uint256 count,
        uint256 timestamp
    );
    
    event OwnershipTransferred(
        address indexed previousOwner,
        address indexed newOwner
    );
    
    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can call this");
        _;
    }
    
    constructor() {
        owner = msg.sender;
        emit OwnershipTransferred(address(0), owner);
    }
    
    /**
     * @dev Convert string to bytes32 (Solidity doesn't support string keys in mappings)
     */
    function stringToBytes32(string memory source) public pure returns (bytes32 result) {
        bytes memory tempBytes = bytes(source);
        if (tempBytes.length == 0) {
            return 0x0;
        }
        assembly {
            result := mload(add(source, 32))
        }
    }
    
    /**
     * @dev Update price for a single stock
     * @param symbol Stock symbol (e.g., "DANGCEM")
     * @param price Price scaled to 18 decimals (e.g., 450.50 = 450500000000000000000)
     */
    function updatePrice(string memory symbol, uint256 price) public onlyOwner {
        require(bytes(symbol).length > 0, "Symbol cannot be empty");
        require(price > 0, "Price must be greater than 0");
        
        bytes32 symbolBytes = stringToBytes32(symbol);
        
        // If this is a new symbol, add it to the list
        if (!stockPrices[symbolBytes].exists) {
            symbolList.push(symbolBytes);
            symbolIndex[symbolBytes] = symbolList.length - 1;
            stockPrices[symbolBytes].exists = true;
        }
        
        stockPrices[symbolBytes].price = price;
        stockPrices[symbolBytes].timestamp = block.timestamp;
        
        emit PriceUpdated(symbol, symbolBytes, price, block.timestamp);
    }
    
    /**
     * @dev Batch update multiple stocks in one transaction (gas efficient)
     * @param symbols Array of stock symbols
     * @param prices Array of prices (must match symbols length)
     */
    function updatePrices(
        string[] memory symbols,
        uint256[] memory prices
    ) public onlyOwner {
        require(symbols.length == prices.length, "Arrays must have equal length");
        require(symbols.length > 0, "Arrays cannot be empty");
        require(symbols.length <= 50, "Cannot update more than 50 stocks at once");
        
        for (uint256 i = 0; i < symbols.length; i++) {
            require(bytes(symbols[i]).length > 0, "Symbol cannot be empty");
            require(prices[i] > 0, "Price must be greater than 0");
            
            bytes32 symbolBytes = stringToBytes32(symbols[i]);
            
            // Add new symbol to list if needed
            if (!stockPrices[symbolBytes].exists) {
                symbolList.push(symbolBytes);
                symbolIndex[symbolBytes] = symbolList.length - 1;
                stockPrices[symbolBytes].exists = true;
            }
            
            stockPrices[symbolBytes].price = prices[i];
            stockPrices[symbolBytes].timestamp = block.timestamp;
            
            emit PriceUpdated(symbols[i], symbolBytes, prices[i], block.timestamp);
        }
        
        emit BatchUpdateCompleted(symbols.length, block.timestamp);
    }
    
    /**
     * @dev Get current price for a stock
     * @param symbol Stock symbol
     * @return price Current price (18 decimals)
     * @return timestamp When price was last updated
     */
    function getPrice(string memory symbol) public view returns (
        uint256 price,
        uint256 timestamp
    ) {
        bytes32 symbolBytes = stringToBytes32(symbol);
        require(stockPrices[symbolBytes].exists, "Stock not found");
        
        return (
            stockPrices[symbolBytes].price,
            stockPrices[symbolBytes].timestamp
        );
    }
    
    /**
     * @dev Check if a stock exists in the oracle
     */
    function stockExists(string memory symbol) public view returns (bool) {
        bytes32 symbolBytes = stringToBytes32(symbol);
        return stockPrices[symbolBytes].exists;
    }
    
    /**
     * @dev Get total number of stocks tracked
     */
    function getStockCount() public view returns (uint256) {
        return symbolList.length;
    }
    
    /**
     * @dev Get symbol at specific index (for enumeration)
     */
    function getSymbolAtIndex(uint256 index) public view returns (bytes32) {
        require(index < symbolList.length, "Index out of bounds");
        return symbolList[index];
    }
    
    /**
     * @dev Get multiple prices in one call (gas efficient for front-ends)
     * @param symbols Array of stock symbols to query
     * @return prices Array of prices
     * @return timestamps Array of timestamps
     * @return exists Array indicating if stock exists
     */
    function getPrices(string[] memory symbols) public view returns (
        uint256[] memory prices,
        uint256[] memory timestamps,
        bool[] memory exists
    ) {
        prices = new uint256[](symbols.length);
        timestamps = new uint256[](symbols.length);
        exists = new bool[](symbols.length);
        
        for (uint256 i = 0; i < symbols.length; i++) {
            bytes32 symbolBytes = stringToBytes32(symbols[i]);
            
            if (stockPrices[symbolBytes].exists) {
                prices[i] = stockPrices[symbolBytes].price;
                timestamps[i] = stockPrices[symbolBytes].timestamp;
                exists[i] = true;
            } else {
                prices[i] = 0;
                timestamps[i] = 0;
                exists[i] = false;
            }
        }
        
        return (prices, timestamps, exists);
    }
    
    /**
     * @dev Transfer ownership to new address
     */
    function transferOwnership(address newOwner) public onlyOwner {
        require(newOwner != address(0), "New owner cannot be zero address");
        
        address oldOwner = owner;
        owner = newOwner;
        
        emit OwnershipTransferred(oldOwner, newOwner);
    }
    
    /**
     * @dev Emergency function to remove a stock (rarely needed)
     */
    function removeStock(string memory symbol) public onlyOwner {
        bytes32 symbolBytes = stringToBytes32(symbol);
        require(stockPrices[symbolBytes].exists, "Stock does not exist");
        
        // Mark as non-existent
        stockPrices[symbolBytes].exists = false;
        stockPrices[symbolBytes].price = 0;
        stockPrices[symbolBytes].timestamp = 0;
        
        // Remove from symbol list (swap with last element and pop)
        uint256 indexToRemove = symbolIndex[symbolBytes];
        uint256 lastIndex = symbolList.length - 1;
        
        if (indexToRemove != lastIndex) {
            bytes32 lastSymbol = symbolList[lastIndex];
            symbolList[indexToRemove] = lastSymbol;
            symbolIndex[lastSymbol] = indexToRemove;
        }
        
        symbolList.pop();
        delete symbolIndex[symbolBytes];
    }
}