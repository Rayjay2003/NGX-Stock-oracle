"""
NGX Oracle Keeper - Main Service
=================================
Runs 24/7, fetches NGX stock prices, and updates the on-chain oracle

Features:
- Fetches all 343+ NGX stocks every 15 minutes
- Only updates stocks with significant price changes (>0.5%)
- Batch updates for gas efficiency
- Automatic error handling and retries
- Detailed logging
"""

import sys
import time
import logging
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from keeper.config import Config
from keeper.blockchain_interface import OracleContract

# Import your existing NGX fetcher
# Make sure ngx_fetcher.py is in the keeper/ directory
from ngx_fetcher import UnifiedNGXFetcher

# Setup logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('oracle_keeper.log') if Config.SAVE_LOGS_TO_FILE else logging.NullHandler()
    ]
)

logger = logging.getLogger(__name__)


class NGXOracleKeeper:
    """Main keeper service that orchestrates price updates"""
    
    def __init__(self):
        """Initialize the keeper"""
        logger.info("="*60)
        logger.info("NGX ORACLE KEEPER STARTING")
        logger.info("="*60)
        
        # Validate configuration
        try:
            Config.validate()
            Config.print_config()
        except ValueError as e:
            logger.error(f"Configuration error: {e}")
            sys.exit(1)
        
        # Initialize blockchain interface
        self.contract = OracleContract(
            rpc_url=Config.RPC_URL,
            private_key=Config.PRIVATE_KEY,
            contract_address=Config.CONTRACT_ADDRESS,
            abi_path=Config.CONTRACT_ABI_PATH
        )
        
        # Initialize NGX data fetcher
        self.fetcher = UnifiedNGXFetcher(prefer_mock=Config.USE_MOCK_DATA)
        
        # Store last known prices for comparison
        self.last_prices = {}
        
        # Statistics
        self.stats = {
            'total_updates': 0,
            'successful_updates': 0,
            'failed_updates': 0,
            'total_stocks_updated': 0,
            'start_time': datetime.now()
        }
        
        logger.info("✅ Keeper initialized successfully")
        
        # Show network info
        network_info = self.contract.get_network_info()
        logger.info(f"Chain ID: {network_info['chain_id']}")
        logger.info(f"Current Block: {network_info['block_number']}")
        logger.info(f"Gas Price: {network_info['gas_price_gwei']:.2f} Gwei")
        logger.info(f"Wallet Balance: {network_info['balance_eth']:.6f} ETH")
        
        if network_info['balance_eth'] < 0.01:
            logger.warning("⚠️ Low ETH balance! Get more from https://sepoliafaucet.com")
    
    def should_update_price(self, symbol, new_price):
        """
        Determine if a stock price should be updated
        
        Only update if:
        1. Stock doesn't exist in contract yet
        2. Price changed by more than MIN_PRICE_CHANGE_PERCENT
        """
        if symbol not in self.last_prices:
            return True
        
        old_price = self.last_prices[symbol]
        
        if old_price == 0:
            return True
        
        price_change_pct = abs((new_price - old_price) / old_price * 100)
        
        if price_change_pct >= Config.MIN_PRICE_CHANGE_PERCENT:
            logger.debug(f"{symbol}: {old_price:.2f} → {new_price:.2f} ({price_change_pct:+.2f}%)")
            return True
        
        return False
    
    def update_prices(self):
        """
        Main update function - fetches NGX prices and updates on-chain
        """
        logger.info("="*60)
        logger.info(f"PRICE UPDATE CYCLE - {datetime.now()}")
        logger.info("="*60)
        
        try:
            # Step 1: Fetch all NGX stock prices
            logger.info("📊 Fetching NGX stock prices...")
            start_time = time.time()
            
            all_stocks = self.fetcher.scraper.fetch_ngx_data()
            
            if not all_stocks:
                logger.warning("⚠️ No stock data fetched - using mock data")
                # Fallback to mock for key stocks
                mock_symbols = ['DANGCEM', 'GTCO', 'BUACEMENT', 'MTNN', 'ACCESSCORP']
                all_stocks = [self.fetcher.mock.get_stock_price(s) for s in mock_symbols]
            
            fetch_time = time.time() - start_time
            logger.info(f"✅ Fetched {len(all_stocks)} stocks in {fetch_time:.2f}s")
            
            # Step 2: Filter stocks that need updating
            stocks_to_update = []
            
            for stock in all_stocks:
                symbol = stock['symbol']
                price = stock['price']
                
                if self.should_update_price(symbol, price):
                    stocks_to_update.append((symbol, price))
            
            logger.info(f"📝 {len(stocks_to_update)} stocks need updating (>{Config.MIN_PRICE_CHANGE_PERCENT}% change)")
            
            if not stocks_to_update:
                logger.info("✅ All prices up to date - no updates needed")
                return True
            
            # Step 3: Batch update stocks (split into chunks)
            batch_size = Config.BATCH_SIZE
            total_batches = (len(stocks_to_update) + batch_size - 1) // batch_size
            
            logger.info(f"🚀 Updating in {total_batches} batches of {batch_size} stocks")
            
            for i in range(0, len(stocks_to_update), batch_size):
                batch = stocks_to_update[i:i+batch_size]
                batch_num = (i // batch_size) + 1
                
                logger.info(f"\nBatch {batch_num}/{total_batches}: Updating {len(batch)} stocks...")
                
                # Update batch on-chain
                receipt = self.contract.batch_update_prices(
                    batch,
                    max_gas_price_gwei=Config.MAX_GAS_PRICE_GWEI
                )
                
                if receipt:
                    # Update last known prices
                    for symbol, price in batch:
                        self.last_prices[symbol] = price
                    
                    self.stats['successful_updates'] += 1
                    self.stats['total_stocks_updated'] += len(batch)
                else:
                    logger.error(f"❌ Batch {batch_num} failed")
                    self.stats['failed_updates'] += 1
                
                # Small delay between batches to avoid rate limiting
                if i + batch_size < len(stocks_to_update):
                    time.sleep(2)
            
            self.stats['total_updates'] += 1
            
            logger.info("="*60)
            logger.info("✅ UPDATE CYCLE COMPLETE")
            logger.info("="*60)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error in update cycle: {e}", exc_info=True)
            self.stats['failed_updates'] += 1
            return False
    
    def print_stats(self):
        """Print keeper statistics"""
        uptime = datetime.now() - self.stats['start_time']
        
        logger.info("="*60)
        logger.info("KEEPER STATISTICS")
        logger.info("="*60)
        logger.info(f"Uptime: {uptime}")
        logger.info(f"Total Updates: {self.stats['total_updates']}")
        logger.info(f"Successful: {self.stats['successful_updates']}")
        logger.info(f"Failed: {self.stats['failed_updates']}")
        logger.info(f"Total Stocks Updated: {self.stats['total_stocks_updated']}")
        
        network_info = self.contract.get_network_info()
        logger.info(f"Current Block: {network_info['block_number']}")
        logger.info(f"Wallet Balance: {network_info['balance_eth']:.6f} ETH")
        logger.info("="*60)
    
    def run_once(self):
        """Run one update cycle (useful for testing)"""
        self.update_prices()
        self.print_stats()
    
    def run_forever(self):
        """Main loop - runs forever, updating every N minutes"""
        logger.info(f"🚀 Starting continuous updates every {Config.UPDATE_INTERVAL_MINUTES} minutes")
        logger.info("Press Ctrl+C to stop\n")
        
        try:
            while True:
                # Run update
                self.update_prices()
                
                # Print stats every 10 updates
                if self.stats['total_updates'] % 10 == 0:
                    self.print_stats()
                
                # Wait for next update
                next_update = datetime.now().timestamp() + (Config.UPDATE_INTERVAL_MINUTES * 60)
                logger.info(f"\n⏰ Next update at {datetime.fromtimestamp(next_update).strftime('%H:%M:%S')}")
                logger.info(f"Sleeping for {Config.UPDATE_INTERVAL_MINUTES} minutes...\n")
                
                time.sleep(Config.UPDATE_INTERVAL_MINUTES * 60)
                
        except KeyboardInterrupt:
            logger.info("\n\n⏹️ Keeper stopped by user")
            self.print_stats()
            sys.exit(0)
        except Exception as e:
            logger.error(f"❌ Fatal error: {e}", exc_info=True)
            sys.exit(1)


def main():
    """Entry point"""
    keeper = NGXOracleKeeper()
    
    # Check command line args
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        logger.info("Running in single-update mode")
        keeper.run_once()
    else:
        keeper.run_forever()


if __name__ == "__main__":
    main()