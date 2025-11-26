"""
Blockchain interface for interacting with the SimpleStockOracle contract
Handles all Web3.py operations - OPTIMIZED 2025 VERSION
"""

from web3 import Web3
from web3.gas_strategies.time_based import medium_gas_price_strategy
from web3.middleware import geth_poa_middleware
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Configure logging for better visibility
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class OracleContract:
    """Wrapper for SimpleStockOracle contract interactions"""
    
    def __init__(self, rpc_url, private_key, contract_address, abi_path):
        """
        Initialize connection to the oracle contract
        """
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))

        # === MODERN 2025 MIDDLEWARE SETUP (WORKS ON SEPOLIA) ===
        # 1. Set reasonable dynamic gas price strategy (replaces old gasprice_strategy_middleware)
        self.w3.eth.set_gas_price_strategy(medium_gas_price_strategy)

        # 2. Add PoA middleware ONLY for legacy PoA chains (Sepolia is NOT PoA anymore)
        # Sepolia chain ID = 11155111 → NOT included here
        legacy_poa_chains = [5, 42, 100, 11155420]  # Goerli (dead), Kovan (dead), xDai, Optimism Sepolia (rare)
        if self.w3.eth.chain_id in legacy_poa_chains:
            self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
            logger.info(f"Added geth_poa_middleware for legacy chain ID {self.w3.eth.chain_id}")

        # Check connection
        if not self.w3.is_connected():
            logger.error(f"Failed to connect to RPC: {rpc_url}")
            raise ConnectionError(f"Failed to connect to RPC: {rpc_url}")
        
        logger.info(f"Connected to network: Chain ID {self.w3.eth.chain_id}")

        # Load account
        self.account = self.w3.eth.account.from_key(private_key)
        self.address = self.account.address
        
        # Load contract ABI
        try:
            with open(abi_path, 'r') as f:
                contract_data = json.load(f)
                abi = contract_data['abi']
        except FileNotFoundError:
            logger.error(f"Contract ABI file not found at {abi_path}")
            raise
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in ABI file at {abi_path}")
            raise
        
        self.contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(contract_address),
            abi=abi
        )
        
        logger.info(f"Oracle contract loaded at {contract_address}")
        logger.info(f"Using account: {self.address}")
        logger.info(f"Current gas price: {self.w3.from_wei(self.w3.eth.gas_price, 'gwei'):.2f} Gwei")
    
    def _send_transaction(self, transaction, private_key, action_name="Transaction"):
        """Helper to sign and send a transaction, and wait for receipt."""
        try:
            signed_tx = self.w3.eth.account.sign_transaction(transaction, private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            logger.info(f"Sent {action_name} | Tx: {tx_hash.hex()}")
            
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
            
            if receipt['status'] == 1:
                logger.info(f"✅ {action_name} SUCCESS | Block: {receipt['blockNumber']} | Gas used: {receipt['gasUsed']:,}")
                return receipt
            else:
                logger.error(f"❌ {action_name} FAILED | Receipt: {receipt}")
                return None
        except Exception as e:
            logger.error(f"Transaction error ({action_name}): {e}")
            return None

    def get_balance(self):
        """Get wallet balance in ETH"""
        try:
            balance_wei = self.w3.eth.get_balance(self.address)
            return float(self.w3.from_wei(balance_wei, 'ether'))
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            return 0.0
    
    def string_to_bytes32(self, text):
        """Convert string to bytes32 (matches Solidity function)"""
        try:
            return self.contract.functions.stringToBytes32(text).call()
        except Exception as e:
            logger.error(f"Error converting '{text}' to bytes32: {e}")
            return None
    
    def get_price(self, symbol):
        """Get current price for a stock"""
        try:
            price_wei, timestamp = self.contract.functions.getPrice(symbol).call()
            price_ngn = float(self.w3.from_wei(price_wei, 'ether'))
            
            return {
                'symbol': symbol,
                'price': price_ngn,
                'timestamp': timestamp,
                'exists': True
            }
        except Exception as e:
            logger.debug(f"Stock {symbol} not found: {e}")
            return {
                'symbol': symbol,
                'price': None,
                'timestamp': None,
                'exists': False
            }
    
    def stock_exists(self, symbol):
        try:
            return self.contract.functions.stockExists(symbol).call()
        except Exception as e:
            logger.error(f"Error checking stock {symbol}: {e}")
            return False
    
    def get_stock_count(self):
        try:
            return self.contract.functions.getStockCount().call()
        except Exception as e:
            logger.error(f"Error getting stock count: {e}")
            return 0
    
    def update_price(self, symbol, price_ngn, max_gas_price_gwei=50):
        """Update price for a single stock"""
        try:
            price_wei = self.w3.to_wei(price_ngn, 'ether')
            current_gas = self.w3.from_wei(self.w3.eth.gas_price, 'gwei')
            
            if current_gas > max_gas_price_gwei:
                logger.warning(f"Gas too high: {current_gas:.2f} > {max_gas_price_gwei} Gwei. Skipping {symbol}")
                return None
            
            nonce = self.w3.eth.get_transaction_count(self.address)
            
            tx = self.contract.functions.updatePrice(symbol, price_wei).build_transaction({
                'from': self.address,
                'nonce': nonce,
                'gas': 200000,
                'gasPrice': self.w3.eth.gas_price
            })
            
            return self._send_transaction(tx, self.account.key, f"Update {symbol}")
                
        except Exception as e:
            logger.error(f"Error updating {symbol}: {e}")
            return None
    
    def batch_update_prices(self, symbol_price_pairs, max_gas_price_gwei=50):
        """
        Update multiple stocks in one transaction
        OPTIMIZED: Better gas estimation to prevent out-of-gas failures
        """
        if not symbol_price_pairs:
            logger.warning("No prices to update")
            return None
        
        try:
            symbols = [p[0] for p in symbol_price_pairs]
            prices_ngn = [p[1] for p in symbol_price_pairs]
            prices_wei = [self.w3.to_wei(p, 'ether') for p in prices_ngn]
            
            # Check gas price
            current_gas = self.w3.from_wei(self.w3.eth.gas_price, 'gwei')
            
            if current_gas > max_gas_price_gwei:
                logger.warning(f"Gas too high ({current_gas:.2f} Gwei > {max_gas_price_gwei} Gwei). Skipping batch update.")
                return None
            
            # Get nonce
            nonce = self.w3.eth.get_transaction_count(self.address)
            
            # IMPROVED GAS ESTIMATION
            # More conservative calculation to prevent out-of-gas errors
            base_gas = 200000  # Base transaction overhead
            gas_per_stock = 150000  # Gas per stock update (increased from 50000)
            gas_estimate = base_gas + (len(symbols) * gas_per_stock)
            
            # Cap at block gas limit minus safety margin
            max_gas = 8000000  # Most networks have ~30M block limit, be conservative
            gas_estimate = min(gas_estimate, max_gas)
            
            logger.info(f"Batch size: {len(symbols)} stocks | Estimated gas: {gas_estimate:,}")
            
            # Build transaction
            tx = self.contract.functions.updatePrices(symbols, prices_wei).build_transaction({
                'from': self.address,
                'nonce': nonce,
                'gas': gas_estimate,
                'gasPrice': self.w3.eth.gas_price
            })
            
            # Send transaction
            receipt = self._send_transaction(tx, self.account.key, f"Batch update {len(symbols)} stocks")
            
            # Log cost if successful
            if receipt and receipt['status'] == 1:
                gas_used = receipt['gasUsed']
                cost_eth = self.w3.from_wei(gas_used * self.w3.eth.gas_price, 'ether')
                cost_per_stock = cost_eth / len(symbols)
                
                logger.info(f"💰 Total cost: {cost_eth:.6f} ETH ({cost_per_stock:.6f} ETH per stock)")
                logger.info(f"📊 Gas efficiency: {gas_used:,} / {gas_estimate:,} ({gas_used/gas_estimate*100:.1f}% used)")
            
            return receipt
                
        except Exception as e:
            logger.error(f"Batch update failed: {e}")
            # If error contains gas info, log it
            if "gas" in str(e).lower():
                logger.error(f"💡 Hint: Try reducing BATCH_SIZE in .env file")
            return None
    
    def estimate_batch_gas(self, symbol_price_pairs):
        """
        Estimate gas for a batch update without sending transaction
        Useful for testing optimal batch sizes
        """
        try:
            symbols = [p[0] for p in symbol_price_pairs]
            prices_ngn = [p[1] for p in symbol_price_pairs]
            prices_wei = [self.w3.to_wei(p, 'ether') for p in prices_ngn]
            
            # Simulate transaction to estimate gas
            gas_estimate = self.contract.functions.updatePrices(
                symbols, prices_wei
            ).estimate_gas({'from': self.address})
            
            logger.info(f"Gas estimate for {len(symbols)} stocks: {gas_estimate:,}")
            return gas_estimate
            
        except Exception as e:
            logger.error(f"Gas estimation failed: {e}")
            return None
    
    def get_network_info(self):
        """Get current network stats"""
        try:
            return {
                'chain_id': self.w3.eth.chain_id,
                'block_number': self.w3.eth.block_number,
                'gas_price_gwei': round(float(self.w3.from_wei(self.w3.eth.gas_price, 'gwei')), 2),
                'balance_eth': round(self.get_balance(), 6)
            }
        except Exception as e:
            logger.error(f"Network info error: {e}")
            return {}