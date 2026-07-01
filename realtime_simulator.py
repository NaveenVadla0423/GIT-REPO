"""
Real-Time Trading Simulator
Simulates live trading on real-time market data and forecasts next moves
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RealTimeSimulator:
    """Simulates real-time trading and forecasting"""
    
    def __init__(self, db_path: str = "nifty_options_5years.db"):
        """Initialize simulator"""
        self.db_path = db_path
        self.active_trades = {}
        self.today_trades = []
        self.forecast_data = {}
    
    def get_today_data(self) -> Optional[Dict]:
        """Get today's market data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get today's date
        today = datetime.now().strftime('%Y-%m-%d')
        
        cursor.execute(f"SELECT * FROM spot_data WHERE date = '{today}'")
        spot_result = cursor.fetchone()
        
        conn.close()
        
        if spot_result is None:
            # If today's data not available, use latest available
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM spot_data ORDER BY date DESC LIMIT 1")
            spot_result = cursor.fetchone()
            conn.close()
        
        if spot_result is None:
            return None
        
        return {
            "date": spot_result[1],
            "open": spot_result[2],
            "high": spot_result[3],
            "low": spot_result[4],
            "close": spot_result[5],
            "volume": spot_result[6]
        }
    
    def detect_current_gap(self) -> Dict:
        """Detect today's gap"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        cursor.execute(f"SELECT close_price FROM spot_data WHERE date = '{today}'")
        today_result = cursor.fetchone()
        
        if today_result is None:
            # Use latest data
            cursor.execute("SELECT close_price FROM spot_data ORDER BY date DESC LIMIT 2")
            results = cursor.fetchall()
            if len(results) < 2:
                conn.close()
                return {"gap_percent": 0}
            today_close = results[0][0]
            prev_close = results[1][0]
        else:
            today_close = today_result[0]
            cursor.execute(f"SELECT close_price FROM spot_data WHERE date < '{today}' ORDER BY date DESC LIMIT 1")
            prev_result = cursor.fetchone()
            prev_close = prev_result[0] if prev_result else today_close
        
        conn.close()
        
        gap_percent = ((today_close - prev_close) / prev_close) * 100 if prev_close != 0 else 0
        
        return {
            "gap_percent": gap_percent,
            "direction": "UP" if gap_percent > 0.5 else "DOWN" if gap_percent < -0.5 else "NEUTRAL",
            "current_spot": today_close
        }
    
    def get_current_iv_rank(self) -> float:
        """Calculate current IV Rank"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Get today's IVs
        cursor.execute(f"SELECT implied_volatility FROM options_data WHERE date = '{today}'")
        today_results = cursor.fetchall()
        
        if not today_results:
            # Use latest available date
            cursor.execute("SELECT implied_volatility FROM options_data ORDER BY date DESC LIMIT 100")
            today_results = cursor.fetchall()
        
        if not today_results:
            conn.close()
            return 50.0
        
        current_iv = np.mean([r[0] for r in today_results])
        
        # Get 52-week range
        one_year_ago = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        cursor.execute(f"SELECT implied_volatility FROM options_data WHERE date >= '{one_year_ago}'")
        year_results = cursor.fetchall()
        
        conn.close()
        
        if not year_results:
            return 50.0
        
        iv_min = min([r[0] for r in year_results])
        iv_max = max([r[0] for r in year_results])
        
        iv_rank = ((current_iv - iv_min) / (iv_max - iv_min) * 100) if iv_max > iv_min else 50
        
        return iv_rank
    
    def generate_forecast(self, days_ahead: int = 5) -> Dict:
        """
        Generate price forecast for next N days
        
        Args:
            days_ahead: Number of days to forecast
        
        Returns:
            Forecast data with probability of up/down
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get last 30 days of price data
        today = datetime.now().strftime('%Y-%m-%d')
        thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        cursor.execute(f'''
            SELECT date, close_price FROM spot_data 
            WHERE date BETWEEN '{thirty_days_ago}' AND '{today}'
            ORDER BY date ASC
        ''')
        
        results = cursor.fetchall()
        conn.close()
        
        if len(results) < 10:
            return {"error": "Insufficient data for forecast"}
        
        prices = np.array([r[1] for r in results])
        returns = np.diff(prices) / prices[:-1]
        
        # Calculate statistics
        avg_return = np.mean(returns)
        volatility = np.std(returns)
        current_price = prices[-1]
        
        # Generate forecast using Monte Carlo
        forecast_prices = []
        for day in range(days_ahead):
            random_shock = np.random.normal(avg_return, volatility)
            forecast_price = current_price * (1 + random_shock)
            forecast_prices.append(forecast_price)
            current_price = forecast_price
        
        # Calculate probability of up/down
        final_forecast = forecast_prices[-1]
        prob_up = 0.5 + (final_forecast - prices[-1]) / (abs(final_forecast - prices[-1]) + 0.01) * 0.3
        prob_up = min(max(prob_up, 0.1), 0.9)
        
        return {
            "current_price": prices[-1],
            "forecast_prices": forecast_prices,
            "avg_forecast": np.mean(forecast_prices),
            "volatility": volatility,
            "days_ahead": days_ahead,
            "probability_up": prob_up,
            "probability_down": 1 - prob_up,
            "forecast_range": {
                "high": np.max(forecast_prices),
                "low": np.min(forecast_prices)
            }
        }
    
    def get_trade_recommendation(self) -> Dict:
        """Get today's trade recommendation"""
        gap_info = self.detect_current_gap()
        iv_rank = self.get_current_iv_rank()
        forecast = self.generate_forecast(days_ahead=7)
        today_data = self.get_today_data()
        
        if today_data is None:
            return {"error": "No market data available"}
        
        current_spot = today_data['close']
        
        # Decision logic
        recommendation = {
            "date": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "current_spot": current_spot,
            "gap_info": gap_info,
            "iv_rank": iv_rank,
            "forecast": forecast
        }
        
        # Strategy selection
        if gap_info['gap_percent'] > 1 and iv_rank > 60:
            recommendation['suggested_strategy'] = "BUY_CALL_SPREAD"
            recommendation['rationale'] = f"Gap-up ({gap_info['gap_percent']:.2f}%) with high IV ({iv_rank:.1f}%). Expect pullback."
            recommendation['setup'] = {
                "long_strike": int((current_spot // 100) * 100),
                "short_strike": int((current_spot // 100) * 100) + 300,
                "entry_premium": "Check live bid-ask",
                "max_profit_target": f"₹{300 * 0.75 * 25:.0f}",
                "max_loss_stop": f"₹{200 * 25:.0f}"
            }
        
        elif gap_info['gap_percent'] < -1 and iv_rank > 60:
            recommendation['suggested_strategy'] = "BUY_PUT_SPREAD"
            recommendation['rationale'] = f"Gap-down ({gap_info['gap_percent']:.2f}%) with high IV ({iv_rank:.1f}%). Expect bounce."
            recommendation['setup'] = {
                "long_strike": int((current_spot // 100) * 100),
                "short_strike": int((current_spot // 100) * 100) - 300,
                "entry_premium": "Check live bid-ask",
                "max_profit_target": f"₹{300 * 0.75 * 25:.0f}",
                "max_loss_stop": f"₹{200 * 25:.0f}"
            }
        
        elif abs(gap_info['gap_percent']) < 0.5 and 25 < iv_rank < 75:
            recommendation['suggested_strategy'] = "IRON_BUTTERFLY"
            recommendation['rationale'] = f"Neutral gap ({gap_info['gap_percent']:.2f}%) with normal IV ({iv_rank:.1f}%). Stable market."
            recommendation['setup'] = {
                "call_sell": int((current_spot // 100) * 100),
                "call_buy": int((current_spot // 100) * 100) + 200,
                "put_sell": int((current_spot // 100) * 100),
                "put_buy": int((current_spot // 100) * 100) - 200,
                "entry_credit": "Check live bid-ask",
                "max_profit_target": "50% of credit",
                "max_loss_stop": "Max width - credit"
            }
        
        else:
            recommendation['suggested_strategy'] = "NO_TRADE"
            recommendation['rationale'] = "Market conditions not suitable for high-probability setup."
        
        return recommendation
    
    def simulate_intraday_moves(self, hours_ahead: int = 4) -> Dict:
        """
        Simulate intraday price movements
        
        Args:
            hours_ahead: Number of hours to simulate
        
        Returns:
            Simulated intraday data
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get today's opening data
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute(f"SELECT open_price, close_price FROM spot_data WHERE date = '{today}' LIMIT 1")
        today_result = cursor.fetchone()
        
        if today_result is None:
            # Use latest available
            cursor.execute("SELECT open_price, close_price FROM spot_data ORDER BY date DESC LIMIT 1")
            today_result = cursor.fetchone()
        
        conn.close()
        
        if today_result is None:
            return {"error": "No data available"}
        
        current_price = today_result[1]
        
        # Simulate hourly movements
        simulated_prices = [current_price]
        for hour in range(hours_ahead):
            # Random walk with slight upward/downward bias
            volatility = 0.002  # 0.2% per hour
            drift = np.random.uniform(-0.001, 0.001)
            
            random_shock = np.random.normal(drift, volatility)
            next_price = current_price * (1 + random_shock)
            simulated_prices.append(next_price)
            current_price = next_price
        
        # Get current time
        current_time = datetime.now()
        
        return {
            "current_time": current_time.strftime('%H:%M:%S'),
            "current_price": simulated_prices[0],
            "simulated_hours": hours_ahead,
            "hourly_prices": simulated_prices,
            "expected_high": np.max(simulated_prices),
            "expected_low": np.min(simulated_prices),
            "expected_close": simulated_prices[-1],
            "expected_move": ((simulated_prices[-1] - simulated_prices[0]) / simulated_prices[0] * 100)
        }


# ==================== EXAMPLE USAGE ====================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("REAL-TIME TRADING SIMULATOR")
    print("="*60)
    
    simulator = RealTimeSimulator(db_path="nifty_options_5years.db")
    
    # 1. Get current market status
    print("\n[1] Current Market Status:")
    gap_info = simulator.detect_current_gap()
    print(f"    Gap: {gap_info['gap_percent']:.2f}% ({gap_info['direction']})")
    print(f"    Current Spot: {gap_info['current_spot']:.2f}")
    
    # 2. Get IV Rank
    print("\n[2] Volatility Analysis:")
    iv_rank = simulator.get_current_iv_rank()
    print(f"    IV Rank: {iv_rank:.1f}%")
    print(f"    Classification: {'HIGH' if iv_rank > 75 else 'NORMAL' if iv_rank > 25 else 'LOW'}")
    
    # 3. Generate forecast
    print("\n[3] Price Forecast (7 days):")
    forecast = simulator.generate_forecast(days_ahead=7)
    if 'error' not in forecast:
        print(f"    Current: {forecast['current_price']:.2f}")
        print(f"    Average Forecast: {forecast['avg_forecast']:.2f}")
        print(f"    Range: {forecast['forecast_range']['low']:.2f} - {forecast['forecast_range']['high']:.2f}")
        print(f"    Prob Up: {forecast['probability_up']*100:.1f}%")
        print(f"    Prob Down: {forecast['probability_down']*100:.1f}%")
    else:
        print(f"    {forecast['error']}")
    
    # 4. Get trade recommendation
    print("\n[4] Today's Trade Recommendation:")
    rec = simulator.get_trade_recommendation()
    print(f"    Strategy: {rec['suggested_strategy']}")
    print(f"    Rationale: {rec['rationale']}")
    if 'setup' in rec:
        print(f"    Setup: {rec['setup']}")
    
    # 5. Simulate intraday moves
    print("\n[5] Intraday Simulation (4 hours):")
    intraday = simulator.simulate_intraday_moves(hours_ahead=4)
    if 'error' not in intraday:
        print(f"    Current: {intraday['current_price']:.2f}")
        print(f"    Expected High: {intraday['expected_high']:.2f}")
        print(f"    Expected Low: {intraday['expected_low']:.2f}")
        print(f"    Expected Move: {intraday['expected_move']:.2f}%")
    else:
        print(f"    {intraday['error']}")
    
    print("\n" + "="*60)
