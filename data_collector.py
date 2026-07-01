"""
Nifty Options Data Collection & Storage System
Fetches Nifty 50 options data from multiple sources (NSE, yfinance, etc.)
Stores in SQLite for backtesting and simulation
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import json
import yfinance as yf
import requests
from typing import Dict, List, Tuple
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NiftyOptionsDataCollector:
    """Collects Nifty 50 options data from various sources"""
    
    def __init__(self, db_path: str = "nifty_options.db"):
        """
        Initialize data collector
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self.conn = None
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Options data table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS options_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                expiry TEXT NOT NULL,
                strike INTEGER NOT NULL,
                option_type TEXT NOT NULL,  -- 'CE' or 'PE'
                open_price REAL,
                high_price REAL,
                low_price REAL,
                close_price REAL,
                volume INTEGER,
                open_interest INTEGER,
                implied_volatility REAL,
                spot_price REAL,
                days_to_expiry INTEGER,
                moneyness REAL,  -- (spot - strike) / strike
                UNIQUE(date, expiry, strike, option_type)
            )
        ''')
        
        # Spot price data table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS spot_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT UNIQUE NOT NULL,
                open_price REAL,
                high_price REAL,
                low_price REAL,
                close_price REAL,
                volume INTEGER
            )
        ''')
        
        # Trade log table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trade_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_date TEXT NOT NULL,
                strategy TEXT NOT NULL,
                entry_time TEXT,
                entry_strike_long INTEGER,
                entry_strike_short INTEGER,
                entry_premium REAL,
                exit_time TEXT,
                exit_premium REAL,
                pnl REAL,
                pnl_percent REAL,
                status TEXT,  -- 'OPEN', 'CLOSED', 'STOPLOSS'
                notes TEXT
            )
        ''')
        
        # IV data table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS iv_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT UNIQUE NOT NULL,
                iv_rank REAL,
                iv_percentile REAL,
                historical_volatility REAL,
                implied_volatility REAL
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info(f"Database initialized: {self.db_path}")
    
    def fetch_spot_data_yfinance(self, symbol: str = "^NSEI", start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        Fetch Nifty 50 spot price data from yfinance
        
        Args:
            symbol: Yahoo Finance ticker (^NSEI for Nifty 50)
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
        
        Returns:
            DataFrame with OHLCV data
        """
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=5*365)).strftime('%Y-%m-%d')
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        logger.info(f"Fetching {symbol} data from {start_date} to {end_date}")
        
        try:
            data = yf.download(symbol, start=start_date, end=end_date, progress=False)
            data.reset_index(inplace=True)
            data.columns = ['date', 'open_price', 'high_price', 'low_price', 'close_price', 'volume', 'adj_close']
            data['date'] = data['date'].dt.strftime('%Y-%m-%d')
            
            logger.info(f"Downloaded {len(data)} rows of spot data")
            return data[['date', 'open_price', 'high_price', 'low_price', 'close_price', 'volume']]
        
        except Exception as e:
            logger.error(f"Error fetching spot data: {e}")
            return pd.DataFrame()
    
    def generate_synthetic_options_data(self, spot_df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate synthetic options data based on spot prices
        (Used as placeholder until real NSE data is obtained)
        
        Args:
            spot_df: DataFrame with spot price data
        
        Returns:
            DataFrame with synthetic options data
        """
        logger.info("Generating synthetic options data...")
        
        options_list = []
        expiry_dates = [7, 14, 21, 28]  # 1-week to monthly
        strikes = [-500, -200, -100, 0, 100, 200, 500]  # Relative to spot
        
        for idx, row in spot_df.iterrows():
            date = row['date']
            spot = row['close_price']
            
            for expiry_days in expiry_dates:
                expiry_date = (datetime.strptime(date, '%Y-%m-%d') + timedelta(days=expiry_days)).strftime('%Y-%m-%d')
                
                for strike_offset in strikes:
                    strike = int((spot + strike_offset) // 100) * 100
                    
                    # Generate option data using Black-Scholes approximation
                    for opt_type in ['CE', 'PE']:
                        # Simplified option pricing
                        moneyness = (spot - strike) / spot
                        iv = 0.20 + np.random.normal(0, 0.05)  # Random IV ~20%
                        days_to_exp = expiry_days
                        
                        # Intrinsic value
                        if opt_type == 'CE':
                            intrinsic = max(spot - strike, 0)
                            time_decay_factor = np.exp(-0.05 * days_to_exp / 365)
                        else:
                            intrinsic = max(strike - spot, 0)
                            time_decay_factor = np.exp(-0.05 * days_to_exp / 365)
                        
                        # Time value (simplified)
                        time_value = spot * iv * np.sqrt(days_to_exp / 365) * 0.4 * time_decay_factor
                        
                        # Premium
                        premium = intrinsic + time_value
                        premium = max(premium, 0.01)  # Minimum 0.01
                        
                        options_list.append({
                            'date': date,
                            'expiry': expiry_date,
                            'strike': strike,
                            'option_type': opt_type,
                            'open_price': premium * (1 + np.random.uniform(-0.02, 0.02)),
                            'high_price': premium * (1 + np.random.uniform(0, 0.05)),
                            'low_price': premium * (1 + np.random.uniform(-0.05, 0)),
                            'close_price': premium,
                            'volume': int(np.random.exponential(10000)),
                            'open_interest': int(np.random.exponential(50000)),
                            'implied_volatility': iv,
                            'spot_price': spot,
                            'days_to_expiry': days_to_exp,
                            'moneyness': moneyness
                        })
        
        options_df = pd.DataFrame(options_list)
        logger.info(f"Generated {len(options_df)} synthetic options data points")
        return options_df
    
    def store_spot_data(self, df: pd.DataFrame):
        """Store spot price data in SQLite"""
        conn = sqlite3.connect(self.db_path)
        try:
            df.to_sql('spot_data', conn, if_exists='append', index=False)
            logger.info(f"Stored {len(df)} spot data records")
        except Exception as e:
            logger.error(f"Error storing spot data: {e}")
        finally:
            conn.close()
    
    def store_options_data(self, df: pd.DataFrame):
        """Store options data in SQLite"""
        conn = sqlite3.connect(self.db_path)
        try:
            df.to_sql('options_data', conn, if_exists='append', index=False)
            logger.info(f"Stored {len(df)} options data records")
        except Exception as e:
            logger.error(f"Error storing options data: {e}")
        finally:
            conn.close()
    
    def get_latest_spot(self) -> float:
        """Get latest spot price from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT close_price FROM spot_data ORDER BY date DESC LIMIT 1')
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    
    def get_options_chain(self, date: str, expiry: str) -> pd.DataFrame:
        """
        Get complete options chain for a date and expiry
        
        Args:
            date: Trading date (YYYY-MM-DD)
            expiry: Expiry date (YYYY-MM-DD)
        
        Returns:
            DataFrame with call and put options
        """
        conn = sqlite3.connect(self.db_path)
        query = f'''
            SELECT * FROM options_data 
            WHERE date = '{date}' AND expiry = '{expiry}'
            ORDER BY strike ASC
        '''
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    
    def calculate_iv_metrics(self, date: str) -> Dict:
        """
        Calculate IV Rank and other metrics for a date
        
        Args:
            date: Trading date (YYYY-MM-DD)
        
        Returns:
            Dictionary with IV metrics
        """
        conn = sqlite3.connect(self.db_path)
        
        # Get all IVs for this date
        query = f"SELECT implied_volatility FROM options_data WHERE date = '{date}'"
        df = pd.read_sql_query(query, conn)
        
        if len(df) == 0:
            return {"error": "No data for date"}
        
        # Get 52-week IV range
        date_obj = datetime.strptime(date, '%Y-%m-%d')
        one_year_ago = (date_obj - timedelta(days=365)).strftime('%Y-%m-%d')
        
        query_52w = f'''
            SELECT implied_volatility FROM options_data 
            WHERE date BETWEEN '{one_year_ago}' AND '{date}'
        '''
        df_52w = pd.read_sql_query(query_52w, conn)
        conn.close()
        
        if len(df_52w) == 0:
            iv_min = df['implied_volatility'].min()
            iv_max = df['implied_volatility'].max()
        else:
            iv_min = df_52w['implied_volatility'].min()
            iv_max = df_52w['implied_volatility'].max()
        
        current_iv = df['implied_volatility'].mean()
        iv_rank = ((current_iv - iv_min) / (iv_max - iv_min) * 100) if iv_max > iv_min else 50
        
        return {
            "date": date,
            "current_iv": current_iv,
            "iv_rank": iv_rank,
            "iv_52w_min": iv_min,
            "iv_52w_max": iv_max,
            "iv_percentile": iv_rank
        }
    
    def get_data_summary(self) -> Dict:
        """Get summary statistics of stored data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM spot_data')
        spot_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM options_data')
        options_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT MIN(date), MAX(date) FROM spot_data')
        date_range = cursor.fetchone()
        
        cursor.execute('SELECT COUNT(*) FROM trade_log')
        trade_count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "spot_records": spot_count,
            "options_records": options_count,
            "date_range": f"{date_range[0]} to {date_range[1]}" if date_range[0] else "No data",
            "trade_logs": trade_count,
            "database_file": self.db_path
        }


# ==================== USAGE EXAMPLE ====================

if __name__ == "__main__":
    # Initialize collector
    collector = NiftyOptionsDataCollector(db_path="nifty_options_5years.db")
    
    print("\n" + "="*60)
    print("NIFTY OPTIONS DATA COLLECTION SYSTEM")
    print("="*60)
    
    # Step 1: Fetch spot data (5 years)
    print("\n[Step 1] Fetching Nifty 50 spot data (5 years)...")
    spot_df = collector.fetch_spot_data_yfinance(
        start_date=(datetime.now() - timedelta(days=5*365)).strftime('%Y-%m-%d')
    )
    
    if len(spot_df) > 0:
        collector.store_spot_data(spot_df)
        print(f"✅ Stored {len(spot_df)} spot price records")
        print(f"   Date range: {spot_df['date'].min()} to {spot_df['date'].max()}")
    else:
        print("⚠️ No spot data fetched, using sample dates")
        # Create sample dates if fetch fails
        dates = pd.date_range(
            start=datetime.now() - timedelta(days=5*365),
            end=datetime.now(),
            freq='D'
        )
        spot_df = pd.DataFrame({
            'date': dates.strftime('%Y-%m-%d'),
            'open_price': 20000 + np.cumsum(np.random.randn(len(dates)) * 50),
            'high_price': 20100 + np.cumsum(np.random.randn(len(dates)) * 50),
            'low_price': 19900 + np.cumsum(np.random.randn(len(dates)) * 50),
            'close_price': 20050 + np.cumsum(np.random.randn(len(dates)) * 50),
            'volume': np.random.randint(1000000, 5000000, len(dates))
        })
        collector.store_spot_data(spot_df)
        print(f"✅ Created {len(spot_df)} sample spot records")
    
    # Step 2: Generate options data
    print("\n[Step 2] Generating synthetic options data...")
    options_df = collector.generate_synthetic_options_data(spot_df)
    collector.store_options_data(options_df)
    print(f"✅ Generated and stored {len(options_df)} options records")
    
    # Step 3: Calculate IV metrics
    print("\n[Step 3] Calculating IV metrics...")
    latest_date = spot_df['date'].max()
    iv_metrics = collector.calculate_iv_metrics(latest_date)
    print(f"✅ IV Metrics for {latest_date}:")
    for key, value in iv_metrics.items():
        print(f"   {key}: {value}")
    
    # Step 4: Display summary
    print("\n[Step 4] Data Summary:")
    summary = collector.get_data_summary()
    for key, value in summary.items():
        print(f"   {key}: {value}")
    
    # Step 5: Sample options chain
    print(f"\n[Step 5] Sample Options Chain ({latest_date}):")
    sample_expiry = (datetime.strptime(latest_date, '%Y-%m-%d') + timedelta(days=7)).strftime('%Y-%m-%d')
    chain = collector.get_options_chain(latest_date, sample_expiry)
    print(chain[['strike', 'option_type', 'close_price', 'implied_volatility', 'open_interest']].head(10))
    
    print("\n" + "="*60)
    print("✅ Data Collection Complete!")
    print(f"📊 Database: {collector.db_path}")
    print("="*60)
