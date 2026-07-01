"""
Main Trading System Integration
Combines data collection, backtesting, and real-time simulation
"""

import pandas as pd
from data_collector import NiftyOptionsDataCollector
from backtester import NiftyBacktester
from realtime_simulator import RealTimeSimulator
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NiftyTradingSystem:
    """Complete integrated trading system"""
    
    def __init__(self, db_path: str = "nifty_options_5years.db"):
        """Initialize system"""
        self.db_path = db_path
        self.collector = NiftyOptionsDataCollector(db_path)
        self.backtester = NiftyBacktester(db_path)
        self.simulator = RealTimeSimulator(db_path)
        self.system_status = "INITIALIZED"
    
    def setup_historical_data(self):
        """Setup historical data collection"""
        print("\n" + "="*70)
        print("STEP 1: DATA COLLECTION & STORAGE")
        print("="*70)
        
        # Clear old database if it exists and has no data or is corrupt
        import os
        print("\n[1.0] Checking database...")
        if os.path.exists(self.db_path):
            # Check if database has data
            import sqlite3
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM spot_data")
                count = cursor.fetchone()[0]
                conn.close()
                if count == 0:
                    print("   Database exists but is empty. Rebuilding...")
                    os.remove(self.db_path)
                    print("   ✅ Old empty database removed")
            except Exception as e:
                print(f"   Database is corrupt ({e}). Rebuilding...")
                os.remove(self.db_path)
                print("   ✅ Old corrupt database removed")
        
        print("\n[1.1] Fetching 5 years of Nifty 50 spot data...")
        spot_df = self.collector.fetch_spot_data_yfinance(
            start_date='2019-07-01',
            end_date=datetime.now().strftime('%Y-%m-%d')
        )
        
        if len(spot_df) == 0:
            print("⚠️  Could not fetch from yfinance, using synthetic data")
            from datetime import timedelta
            import numpy as np
            dates = pd.date_range(
                start=datetime.now() - timedelta(days=5*365),
                end=datetime.now(),
                freq='D'
            )
            prices = 20000 + np.cumsum(np.random.randn(len(dates)) * 50)
            spot_df = pd.DataFrame({
                'date': dates.strftime('%Y-%m-%d'),
                'open_price': prices * (1 + np.random.uniform(-0.01, 0.01, len(dates))),
                'high_price': prices * (1 + np.random.uniform(0, 0.02, len(dates))),
                'low_price': prices * (1 + np.random.uniform(-0.02, 0, len(dates))),
                'close_price': prices,
                'volume': np.random.randint(1000000, 5000000, len(dates))
            })
        
        self.collector.store_spot_data(spot_df)
        print(f"✅ Stored {len(spot_df)} spot price records")
        print(f"   Date range: {spot_df['date'].min()} to {spot_df['date'].max()}")
        
        print("\n[1.2] Generating synthetic options data...")
        options_df = self.collector.generate_synthetic_options_data(spot_df)
        self.collector.store_options_data(options_df)
        print(f"✅ Generated {len(options_df)} options records")
        
        # Summary
        print("\n[1.3] Data Summary:")
        summary = self.collector.get_data_summary()
        for key, value in summary.items():
            print(f"   {key}: {value}")
    
    def run_backtest(self):
        """Run strategy backtest"""
        print("\n" + "="*70)
        print("STEP 2: HISTORICAL BACKTESTING")
        print("="*70)
        
        # Get date range
        db_start, db_end = self.backtester.get_dates_range()
        backtest_start = (datetime.strptime(db_start, '%Y-%m-%d') + pd.Timedelta(days=365)).strftime('%Y-%m-%d')
        backtest_end = db_end
        
        print(f"\n[2.1] Running backtest from {backtest_start} to {backtest_end}...")
        results = self.backtester.backtest(
            start_date=backtest_start,
            end_date=backtest_end,
            max_risk_per_trade=2000
        )
        
        print("\n[2.2] Backtest Results:")
        for key, value in results.items():
            print(f"   {key}: {value}")
        
        # Trade summary
        if len(self.backtester.trades) > 0:
            print("\n[2.3] Sample Trades:")
            summary_df = self.backtester.get_trade_summary()
            print(summary_df.head(10).to_string())
            
            # Performance by strategy
            print("\n[2.4] Performance by Strategy:")
            strategy_perf = summary_df.groupby('strategy').agg({
                'pnl': ['count', 'sum', 'mean'],
                'status': lambda x: (x == 'TARGET_HIT').sum()
            })
            print(strategy_perf)
        
        return results
    
    def run_realtime_simulation(self):
        """Run real-time simulation and forecasting"""
        print("\n" + "="*70)
        print("STEP 3: REAL-TIME SIMULATION & FORECASTING")
        print("="*70)
        
        # Get current market status
        print("\n[3.1] Current Market Status:")
        gap_info = self.simulator.detect_current_gap()
        print(f"   Gap: {gap_info['gap_percent']:.2f}% ({gap_info['direction']})")
        print(f"   Current Spot: {gap_info['current_spot']:.2f}")
        
        # IV Analysis
        print("\n[3.2] Volatility Analysis:")
        iv_rank = self.simulator.get_current_iv_rank()
        print(f"   IV Rank: {iv_rank:.1f}%")
        iv_class = "HIGH" if iv_rank > 75 else "NORMAL" if iv_rank > 25 else "LOW"
        print(f"   Classification: {iv_class}")
        
        # Forecast
        print("\n[3.3] 7-Day Price Forecast:")
        forecast = self.simulator.generate_forecast(days_ahead=7)
        if 'error' not in forecast:
            print(f"   Current Price: {forecast['current_price']:.2f}")
            print(f"   Forecast Average: {forecast['avg_forecast']:.2f}")
            print(f"   Expected Range: {forecast['forecast_range']['low']:.2f} - {forecast['forecast_range']['high']:.2f}")
            print(f"   Probability UP: {forecast['probability_up']*100:.1f}%")
            print(f"   Probability DOWN: {forecast['probability_down']*100:.1f}%")
        
        # Trade Recommendation
        print("\n[3.4] TODAY'S TRADE RECOMMENDATION:")
        print("   " + "-"*60)
        rec = self.simulator.get_trade_recommendation()
        print(f"   Strategy: {rec['suggested_strategy']}")
        print(f"   Rationale: {rec['rationale']}")
        
        if 'setup' in rec and rec['suggested_strategy'] != "NO_TRADE":
            print(f"\n   Setup Details:")
            for key, value in rec['setup'].items():
                print(f"      {key}: {value}")
        
        # Intraday simulation
        print("\n[3.5] Intraday Simulation (Next 4 Hours):")
        intraday = self.simulator.simulate_intraday_moves(hours_ahead=4)
        if 'error' not in intraday:
            print(f"   Current Price: {intraday['current_price']:.2f}")
            print(f"   Expected High: {intraday['expected_high']:.2f}")
            print(f"   Expected Low: {intraday['expected_low']:.2f}")
            print(f"   Expected Close: {intraday['expected_close']:.2f}")
            print(f"   Expected Move: {intraday['expected_move']:+.2f}%")
    
    def generate_report(self, output_file: str = "trading_report.txt"):
        """Generate comprehensive trading report"""
        print("\n" + "="*70)
        print("STEP 4: GENERATING REPORT")
        print("="*70)
        
        with open(output_file, 'w') as f:
            f.write("="*70 + "\n")
            f.write("NIFTY OPTIONS ADAPTIVE TRADING SYSTEM - REPORT\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*70 + "\n\n")
            
            # Data Summary
            f.write("SECTION 1: DATA SUMMARY\n")
            f.write("-"*70 + "\n")
            summary = self.collector.get_data_summary()
            for key, value in summary.items():
                f.write(f"{key}: {value}\n")
            f.write("\n")
            
            # Backtest Results
            if len(self.backtester.trades) > 0:
                f.write("SECTION 2: BACKTEST RESULTS\n")
                f.write("-"*70 + "\n")
                summary_df = self.backtester.get_trade_summary()
                f.write(summary_df.to_string())
                f.write("\n\n")
            
            # Current Market Status
            f.write("SECTION 3: CURRENT MARKET STATUS\n")
            f.write("-"*70 + "\n")
            gap_info = self.simulator.detect_current_gap()
            f.write(f"Gap: {gap_info['gap_percent']:.2f}%\n")
            f.write(f"Direction: {gap_info['direction']}\n")
            f.write(f"Current Spot: {gap_info['current_spot']:.2f}\n")
            f.write("\n")
            
            # IV Analysis
            f.write("SECTION 4: IV ANALYSIS\n")
            f.write("-"*70 + "\n")
            iv_rank = self.simulator.get_current_iv_rank()
            f.write(f"IV Rank: {iv_rank:.1f}%\n")
            f.write("\n")
            
            # Recommendation
            f.write("SECTION 5: TODAY'S RECOMMENDATION\n")
            f.write("-"*70 + "\n")
            rec = self.simulator.get_trade_recommendation()
            f.write(f"Strategy: {rec['suggested_strategy']}\n")
            f.write(f"Rationale: {rec['rationale']}\n")
            f.write("\n")
        
        print(f"✅ Report saved to {output_file}")
    
    def run_full_system(self):
        """Run complete system: Data → Backtest → Real-time Sim → Report"""
        print("\n" + "█"*70)
        print("█" + " "*68 + "█")
        print("█" + "  NIFTY ADAPTIVE OPTIONS TRADING SYSTEM (FULL SETUP)".center(68) + "█")
        print("█" + " "*68 + "█")
        print("█"*70)
        
        try:
            # Step 1: Setup historical data
            self.setup_historical_data()
            
            # Step 2: Run backtest
            backtest_results = self.run_backtest()
            
            # Step 3: Run real-time simulation
            self.run_realtime_simulation()
            
            # Step 4: Generate report
            self.generate_report(output_file="NIFTY_TRADING_REPORT.txt")
            
            print("\n" + "="*70)
            print("✅ SYSTEM SETUP COMPLETE!")
            print("="*70)
            print("\nNext Steps:")
            print("1. Review NIFTY_TRADING_REPORT.txt")
            print("2. Check database: nifty_options_5years.db")
            print("3. Run: python -c 'from data_collector import *; print(\"Ready for live trading!\")'")
            print("="*70 + "\n")
            
            self.system_status = "READY"
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
            self.system_status = "ERROR"


# ==================== MAIN EXECUTION ====================

if __name__ == "__main__":
    system = NiftyTradingSystem(db_path="nifty_options_5years.db")
    system.run_full_system()
