"""
NGX Stock Data Parser - Working Implementation
===============================================
This scraper parses the actual NGX data format found on their website.

Data Format Discovered:
BUACEMENT N168.600.00 % AIRTELAFRI N2310.500.00 % DANGCEM N450.500.00 %

The format is: SYMBOL N[PRICE][CHANGE]%

This script includes:
1. Parser for NGX's actual data format
2. Mock data generator for testing
3. Unified interface
"""

import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json
import time
import random


class NGXDataParser:
    """
    Parses NGX data from the actual format found on their website
    """
    
    @staticmethod
    def parse_ngx_string(data_string):
        """
        Parse NGX data string format:
        "BUACEMENT N168.600.00 % AIRTELAFRI N2310.500.00 %"
        
        Returns list of dicts: [{'symbol': 'BUACEMENT', 'price': 168.60, ...}, ...]
        """
        stocks = []
        
        # Pattern: SYMBOL N[PRICE][CHANGE]%
        # Example: BUACEMENT N168.600.00 % or AIRTELAFRI N2310.500.00 %
        pattern = r'([A-Z0-9]+)\s+N([\d,]+\.?\d*)([\d\.\-\+]+)?\s*%'
        
        matches = re.findall(pattern, data_string)
        
        for match in matches:
            symbol = match[0]
            price_str = match[1].replace(',', '')
            change_str = match[2] if len(match) > 2 else '0'
            
            try:
                price = float(price_str)
                change = float(change_str) if change_str else 0.0
                
                # Skip if price is suspiciously high (like N100.000.00 = N100k bonds)
                if price > 50000:
                    continue
                
                stocks.append({
                    'symbol': symbol,
                    'price': price,
                    'change': change,
                    'timestamp': datetime.now().isoformat(),
                    'source': 'NGX Website (30min delayed)'
                })
            
            except (ValueError, IndexError):
                continue
        
        return stocks
    
    @staticmethod
    def extract_from_html(html_content):
        """
        Extract NGX data from HTML content
        The data is often embedded in the page as text
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Look for the data string (usually starts with "30 MINUTES DELAYED DATA:")
        # It could be in a <span>, <div>, or script tag
        
        # Try to find the delayed data text
        text = soup.get_text()
        
        # Look for the pattern of stock data
        if 'DELAYED DATA' in text:
            # Extract everything after "DELAYED DATA:"
            start_idx = text.find('DELAYED DATA:')
            if start_idx != -1:
                data_section = text[start_idx:start_idx + 10000]  # Get next 10k chars
                return NGXDataParser.parse_ngx_string(data_section)
        
        # Alternative: look for price patterns directly
        return NGXDataParser.parse_ngx_string(text)


class NGXWebsiteScraper:
    """
    Scrapes NGX official website for 30-minute delayed prices
    """
    
    URLS_TO_TRY = [
        'https://ngxgroup.com/exchange/data/',
        'https://ngxgroup.com/exchange/data/equities-price-list/',
        'https://ngxgroup.com/exchange/data/data-library/',
    ]
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        })
        self.parser = NGXDataParser()
    
    def fetch_ngx_data(self):
        """
        Try multiple NGX URLs to get stock data
        """
        for url in self.URLS_TO_TRY:
            try:
                print(f"🔍 Trying {url}...")
                response = self.session.get(url, timeout=30)
                
                if response.status_code == 200:
                    stocks = self.parser.extract_from_html(response.text)
                    
                    if stocks:
                        print(f"✅ Found {len(stocks)} stocks from {url}")
                        return stocks
                    else:
                        print(f"⚠ Page loaded but no stock data found")
                
                time.sleep(1)  # Be nice to the server
            
            except Exception as e:
                print(f"⚠ Error with {url}: {e}")
                continue
        
        print("❌ Could not fetch data from any NGX URL")
        return []
    
    def get_stock_price(self, symbol):
        """Get price for a specific stock"""
        all_stocks = self.fetch_ngx_data()
        
        for stock in all_stocks:
            if stock['symbol'].upper() == symbol.upper():
                return stock
        
        return None
    
    def get_multiple_stocks(self, symbols):
        """Get prices for multiple stocks"""
        all_stocks = self.fetch_ngx_data()
        
        # Create lookup dict
        stock_dict = {s['symbol'].upper(): s for s in all_stocks}
        
        result = {}
        for symbol in symbols:
            result[symbol] = stock_dict.get(symbol.upper())
        
        return result


class MockNGXData:
    """
    High-quality mock data for testing
    Uses realistic NGX stock prices and behavior
    """
    
    # Real NGX stocks with realistic base prices (as of Nov 2024)
    STOCKS = {
        'DANGCEM': 450.50,      # Dangote Cement
        'GTCO': 48.75,          # GT Holding Company
        'BUACEMENT': 168.60,    # BUA Cement
        'MTNN': 285.00,         # MTN Nigeria
        'AIRTELAFRI': 2310.50,  # Airtel Africa
        'ZENITHBANK': 42.30,    # Zenith Bank
        'FBNH': 28.95,          # FBN Holdings
        'SEPLAT': 4520.00,      # Seplat Energy
        'ACCESSCORP': 27.65,    # Access Holdings
        'BUAFOODS': 588.00,     # BUA Foods
        'TRANSCORP': 14.50,     # Transcorp
        'OANDO': 95.00,         # Oando
        'STANBIC': 68.50,       # Stanbic IBTC
        'UBA': 32.50,           # United Bank for Africa
        'NESTLE': 1250.00,      # Nestle Nigeria
    }
    
    def __init__(self, volatility=0.02):
        """
        volatility: How much prices fluctuate (0.02 = 2% variance)
        """
        self.volatility = volatility
        self.last_prices = {}
    
    def get_stock_price(self, symbol):
        """
        Generate realistic price with momentum
        (prices don't jump randomly, they trend)
        """
        symbol_upper = symbol.upper()
        
        if symbol_upper not in self.STOCKS:
            return None
        
        base_price = self.STOCKS[symbol_upper]
        
        # Use last price if we have it (creates momentum)
        if symbol_upper in self.last_prices:
            current_price = self.last_prices[symbol_upper]
        else:
            current_price = base_price
        
        # Small random walk
        change_pct = random.uniform(-self.volatility, self.volatility)
        new_price = current_price * (1 + change_pct)
        
        # Mean reversion (slowly drift back to base price)
        new_price = new_price * 0.95 + base_price * 0.05
        
        # Store for next time
        self.last_prices[symbol_upper] = new_price
        
        # Calculate change from base
        change = new_price - base_price
        change_pct = (change / base_price) * 100
        
        return {
            'symbol': symbol,
            'price': round(new_price, 2),
            'change': round(change, 2),
            'change_pct': round(change_pct, 2),
            'timestamp': datetime.now().isoformat(),
            'source': 'MOCK DATA (for testing)',
            'note': '⚠ Simulated data - replace with real source for production'
        }
    
    def get_all_stocks(self):
        """Get all stock prices"""
        return [self.get_stock_price(symbol) for symbol in self.STOCKS.keys()]
    
    def get_multiple_stocks(self, symbols):
        """Get prices for multiple stocks"""
        return {symbol: self.get_stock_price(symbol) for symbol in symbols}


class UnifiedNGXFetcher:
    """
    Unified interface that tries scraping first, falls back to mock
    """
    
    def __init__(self, prefer_mock=False):
        """
        prefer_mock: If True, use mock data immediately (faster for testing)
        """
        self.prefer_mock = prefer_mock
        self.scraper = NGXWebsiteScraper()
        self.mock = MockNGXData()
    
    def get_stock_price(self, symbol):
        """Get price with automatic fallback"""
        
        if self.prefer_mock:
            print(f"🎭 Using mock data for {symbol}")
            return self.mock.get_stock_price(symbol)
        
        # Try scraping first
        print(f"🔍 Attempting to scrape {symbol} from NGX website...")
        result = self.scraper.get_stock_price(symbol)
        
        if result:
            print(f"✅ Got real data: ₦{result['price']:.2f}")
            return result
        
        # Fall back to mock
        print(f"⚠ Scraping failed, using mock data for {symbol}")
        return self.mock.get_stock_price(symbol)
    
    def get_multiple_stocks(self, symbols):
        """Get multiple stocks with fallback"""
        
        if self.prefer_mock:
            print(f"🎭 Using mock data for all stocks")
            return self.mock.get_multiple_stocks(symbols)
        
        # Try scraping
        print(f"🔍 Attempting to scrape from NGX website...")
        results = self.scraper.get_multiple_stocks(symbols)
        
        # Check if we got data
        real_data_count = sum(1 for v in results.values() if v is not None)
        
        if real_data_count > 0:
            print(f"✅ Got real data for {real_data_count}/{len(symbols)} stocks")
            
            # Fill missing stocks with mock data
            for symbol in symbols:
                if results[symbol] is None:
                    print(f"⚠ Using mock data for {symbol}")
                    results[symbol] = self.mock.get_stock_price(symbol)
            
            return results
        
        # All scraping failed, use mock
        print(f"⚠ Scraping failed, using mock data for all stocks")
        return self.mock.get_multiple_stocks(symbols)
    
    def get_oracle_format(self, symbols):
        """
        Get data in oracle-ready format (scaled to 10^18)
        """
        stocks = self.get_multiple_stocks(symbols)
        
        oracle_data = []
        for symbol, data in stocks.items():
            if data:
                # Scale to 18 decimals for Solidity
                price_scaled = int(data['price'] * 10**18)
                
                oracle_data.append({
                    'symbol': symbol,
                    'price': data['price'],
                    'price_scaled': price_scaled,
                    'price_hex': hex(price_scaled),
                    'timestamp': data['timestamp'],
                    'source': data['source']
                })
        
        return oracle_data


# ==================== USAGE EXAMPLES ====================

def test_mock_data():
    """Test mock data generator"""
    print("="*70)
    print("MOCK DATA TEST")
    print("="*70)
    
    mock = MockNGXData()
    
    # Get data multiple times to see price evolution
    for i in range(3):
        print(f"\n--- Update {i+1} ---")
        stocks = ['DANGCEM', 'GTCO', 'BUACEMENT']
        
        for symbol in stocks:
            data = mock.get_stock_price(symbol)
            print(f"{data['symbol']:12} | ₦{data['price']:>10.2f} | Change: {data['change']:>+7.2f} ({data['change_pct']:>+6.2f}%)")
        
        time.sleep(1)


def test_scraper():
    """Test web scraper"""
    print("="*70)
    print("NGX WEBSITE SCRAPER TEST")
    print("="*70)
    
    scraper = NGXWebsiteScraper()
    stocks = scraper.fetch_ngx_data()
    
    if stocks:
        print(f"\n✅ Found {len(stocks)} stocks")
        print("\nSample (first 10):")
        for stock in stocks[:10]:
            print(f"{stock['symbol']:12} | ₦{stock['price']:>10.2f}")
    else:
        print("\n❌ No data found")


def test_unified():
    """Test unified fetcher"""
    print("="*70)
    print("UNIFIED FETCHER TEST (Scrape with Mock Fallback)")
    print("="*70)
    
    # Try scraping first, fall back to mock if it fails
    fetcher = UnifiedNGXFetcher(prefer_mock=False)
    
    symbols = ['DANGCEM', 'GTCO', 'BUACEMENT', 'MTNN']
    
    results = fetcher.get_multiple_stocks(symbols)
    
    print("\n📊 RESULTS:")
    print("="*70)
    for symbol, data in results.items():
        if data:
            print(f"✅ {symbol:12} | ₦{data['price']:>10.2f} | {data['source']}")
        else:
            print(f"❌ {symbol:12} | NOT FOUND")


def test_oracle_format():
    """Test oracle-ready output"""
    print("="*70)
    print("ORACLE-READY FORMAT TEST")
    print("="*70)
    
    # Use mock for reliable testing
    fetcher = UnifiedNGXFetcher(prefer_mock=True)
    
    symbols = ['DANGCEM', 'GTCO', 'BUACEMENT']
    
    oracle_data = fetcher.get_oracle_format(symbols)
    
    print("\n🔗 DATA READY FOR SMART CONTRACT:")
    print(json.dumps(oracle_data, indent=2))
    
    print("\n💡 Usage in your Python keeper:")
    print("```python")
    for item in oracle_data:
        print(f"contract.updatePrice('{item['symbol']}', {item['price_scaled']})")
    print("```")


if __name__ == "__main__":
    print("NGX Data Fetcher - Choose test:")
    print("1. Mock Data (always works)")
    print("2. Web Scraper (may fail)")
    print("3. Unified (tries scraping, falls back to mock)")
    print("4. Oracle Format (ready for blockchain)")
    
    choice = input("\nEnter choice (1-4): ").strip()
    
    if choice == "1":
        test_mock_data()
    elif choice == "2":
        test_scraper()
    elif choice == "3":
        test_unified()
    elif choice == "4":
        test_oracle_format()
    else:
        print("Running unified test...")
        test_unified()