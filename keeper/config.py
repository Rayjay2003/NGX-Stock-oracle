"""
Configuration module for NGX Oracle Keeper
Loads environment variables and provides centralized settings
"""

import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env file from project root
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

class Config:
    """Centralized configuration for the oracle keeper"""
    
    # ========== BLOCKCHAIN SETTINGS ==========
    RPC_URL = os.getenv('RPC_URL')
    PRIVATE_KEY = os.getenv('PRIVATE_KEY')
    CONTRACT_ADDRESS = os.getenv('ORACLE_CONTRACT_ADDRESS')
    
    # ========== ORACLE SETTINGS ==========
    UPDATE_INTERVAL_MINUTES = int(os.getenv('UPDATE_INTERVAL_MINUTES', '15'))
    MIN_PRICE_CHANGE_PERCENT = float(os.getenv('MIN_PRICE_CHANGE_PERCENT', '0.5'))
    BATCH_SIZE = int(os.getenv('BATCH_SIZE', '20'))
    MAX_GAS_PRICE_GWEI = int(os.getenv('MAX_GAS_PRICE_GWEI', '50'))
    
    # ========== DATA SOURCE SETTINGS ==========
    USE_MOCK_DATA = os.getenv('USE_MOCK_DATA', 'false').lower() == 'true'
    NGX_API_KEY = os.getenv('NGX_API_KEY', '')
    
    # ========== LOGGING SETTINGS ==========
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    SAVE_LOGS_TO_FILE = os.getenv('SAVE_LOGS_TO_FILE', 'true').lower() == 'true'
    
    # ========== CONTRACT ABI PATH ==========
    CONTRACT_ABI_PATH = Path(__file__).parent.parent / 'artifacts' / 'contracts' / 'SimpleStockOracle.sol' / 'SimpleStockOracle.json'
    
    @classmethod
    def validate(cls):
        """Validate that all required config is present"""
        errors = []
        
        if not cls.RPC_URL:
            errors.append("RPC_URL not set in .env file")
        
        if not cls.PRIVATE_KEY:
            errors.append("PRIVATE_KEY not set in .env file")
        
        if not cls.CONTRACT_ADDRESS:
            errors.append("ORACLE_CONTRACT_ADDRESS not set in .env file (deploy contract first)")
        
        if not cls.CONTRACT_ABI_PATH.exists():
            errors.append(f"Contract ABI not found at {cls.CONTRACT_ABI_PATH} (run 'npm run compile' first)")
        
        if errors:
            raise ValueError("Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors))
        
        return True
    
    @classmethod
    def print_config(cls):
        """Print current configuration (for debugging)"""
        print("=" * 60)
        print("NGX ORACLE KEEPER CONFIGURATION")
        print("=" * 60)
        print(f"RPC URL: {cls.RPC_URL[:50]}...")
        print(f"Contract: {cls.CONTRACT_ADDRESS}")
        print(f"Update Interval: {cls.UPDATE_INTERVAL_MINUTES} minutes")
        print(f"Min Price Change: {cls.MIN_PRICE_CHANGE_PERCENT}%")
        print(f"Batch Size: {cls.BATCH_SIZE} stocks")
        print(f"Max Gas Price: {cls.MAX_GAS_PRICE_GWEI} Gwei")
        print(f"Use Mock Data: {cls.USE_MOCK_DATA}")
        print(f"Log Level: {cls.LOG_LEVEL}")
        print("=" * 60)