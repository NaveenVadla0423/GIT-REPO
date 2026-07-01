"""
Nifty Options Backtesting Engine
Simulates the corrected adaptive strategy on historical options data
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import logging
from dataclasses import dataclass
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TradeStatus(Enum):
    OPEN = "OPEN"
    TARGET_HIT = "TARGET_HIT"
    STOPLOSS_HIT = "STOPLOSS_HIT"
    TIME_EXIT = "TIME_EXIT"
    CLOSED = "CLOSED"


@dataclass
class Trade:
    """Single trade representation"""
    trade_id: str
    date: str
    strategy: str
    entry_strike_long: int
    entry_strike_short: int
    entry_premium: float
    expiry: str
    lot_size: int = 1
    max_profit: float = 0
    max_loss: float = 0
    status: TradeStatus = TradeStatus.OPEN
    pnl: float = 0
    exit_date: str = None
    exit_premium: float = None
    days_held: int = 0
    
    def calculate_exit_pnl(self, exit_premium: float, exit_date: str = None):
        """Calculate P&L on exit"""
        self.exit_premium = exit_premium
        if exit_date:
            self.exit_date = exit_date
            self.days_held = (datetime.strptime(exit_date, '%Y-%m-%d') - 
                            datetime.strptime(self.date, '%Y-%m-%d')).days
        
        # For buy spreads: profit if premium decreases
        profit_per_share = (self.entry_premium - exit_premium)
        self.pnl = profit_per_share * self.lot_size * 25  # 25 = multiplier


class NiftyBacktester:
    """Backtesting engine for Nifty options strategies"""
    
    def __init__(self, db_path: str = "nifty_options_5years.db"):
        """Initialize backtester with database"""
        self.db_path = db_path
        self.trades = []
        self.daily_results = []
    
    def get_options_data(self, date: str, expiry: str) -> pd.DataFrame:
        """Fetch options chain from database"""
        conn = sqlite3.connect(self.db_path)
        query = f'''
            SELECT * FROM options_data 
            WHERE date = '{date}' AND expiry = '{expiry}'
            ORDER BY strike ASC
        '''
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    
    def get_spot_price(self, date: str) -> float:
        """Get spot price for a date"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(f"SELECT close_price FROM spot_data WHERE date = '{date}'")
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    
    def get_dates_range(self) -> Tuple[str, str]:
        """Get date range from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT MIN(date), MAX(date) FROM spot_data")
        dates = cursor.fetchone()
        conn.close()
        return dates[0], dates[1]
    
    def get_next_trading_date(self, date: str) -> str:
        """Get next trading date after given date"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        date_obj = datetime.strptime(date, '%Y-%m-%d')
        next_date = date_obj + timedelta(days=1)
        
        cursor.execute(f"SELECT date FROM spot_data WHERE date >= '{next_date.strftime('%Y-%m-%d')}' LIMIT 1")
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    
    def detect_gap(self, date: str) -> Dict:
        """Detect gap for a date"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get previous close
        prev_date_query = "SELECT date FROM spot_data WHERE date < ? ORDER BY date DESC LIMIT 1"
        cursor.execute(prev_date_query, (date,))
        prev_result = cursor.fetchone()
        
        if not prev_result:
            conn.close()
            return {"gap_percent": 0, "direction": "NONE"}
        
        prev_date = prev_result[0]
        cursor.execute(f"SELECT close_price FROM spot_data WHERE date = '{prev_date}'")
        prev_close = cursor.fetchone()[0]
        
        cursor.execute(f"SELECT close_price FROM spot_data WHERE date = '{date}'")
        open_result = cursor.fetchone()
        conn.close()
        
        if not open_result:
            return {"gap_percent": 0, "direction": "NONE"}
        
        open_price = open_result[0]
        gap_percent = ((open_price - prev_close) / prev_close) * 100
        
        return {
            "gap_percent": gap_percent,
            "direction": "UP" if gap_percent > 1 else "DOWN" if gap_percent < -1 else "NONE",
            "magnitude": "STRONG" if abs(gap_percent) > 1 else "MODERATE" if abs(gap_percent) > 0.5 else "NONE"
        }
    
    def decide_strategy(self, gap_info: Dict, iv_rank: float) -> str:
        """Decide which strategy to use"""
        gap_percent = gap_info["gap_percent"]
        
        if gap_percent > 1 and iv_rank > 60:
            return "BUY_CALL_SPREAD"
        elif gap_percent < -1 and iv_rank > 60:
            return "BUY_PUT_SPREAD"
        elif abs(gap_percent) < 0.5 and 25 < iv_rank < 75:
            return "IRON_BUTTERFLY"
        else:
            return "NO_TRADE"
    
    def build_trade(self, date: str, spot: float, strategy: str, iv_rank: float, lot_size: int = 1) -> Trade:
        """Build a trade based on strategy"""
        round_spot = int((spot // 100) * 100)
        
        # Get 7-day expiry
        expiry_date = (datetime.strptime(date, '%Y-%m-%d') + timedelta(days=7)).strftime('%Y-%m-%d')
        
        # Get options chain
        chain = self.get_options_data(date, expiry_date)
        
        if len(chain) == 0:
            logger.warning(f"No options data for {date} expiry {expiry_date}")
            return None
        
        if strategy == "BUY_CALL_SPREAD":
            # Buy ATM call, Sell OTM call
            long_call = chain[(chain['strike'] == round_spot) & (chain['option_type'] == 'CE')]
            short_call = chain[(chain['strike'] == round_spot + 300) & (chain['option_type'] == 'CE')]
            
            if len(long_call) == 0 or len(short_call) == 0:
                return None
            
            entry_premium = long_call['close_price'].values[0] - short_call['close_price'].values[0]
            max_profit = (300 - entry_premium) * 25 * lot_size
            max_loss = entry_premium * 25 * lot_size
            
            trade = Trade(
                trade_id=f"{date}_{strategy}_{lot_size}",
                date=date,
                strategy=strategy,
                entry_strike_long=round_spot,
                entry_strike_short=round_spot + 300,
                entry_premium=entry_premium,
                expiry=expiry_date,
                lot_size=lot_size,
                max_profit=max_profit,
                max_loss=max_loss
            )
        
        elif strategy == "BUY_PUT_SPREAD":
            # Buy ATM put, Sell OTM put
            long_put = chain[(chain['strike'] == round_spot) & (chain['option_type'] == 'PE')]
            short_put = chain[(chain['strike'] == round_spot - 300) & (chain['option_type'] == 'PE')]
            
            if len(long_put) == 0 or len(short_put) == 0:
                return None
            
            entry_premium = long_put['close_price'].values[0] - short_put['close_price'].values[0]
            max_profit = (300 - entry_premium) * 25 * lot_size
            max_loss = entry_premium * 25 * lot_size
            
            trade = Trade(
                trade_id=f"{date}_{strategy}_{lot_size}",
                date=date,
                strategy=strategy,
                entry_strike_long=round_spot,
                entry_strike_short=round_spot - 300,
                entry_premium=entry_premium,
                expiry=expiry_date,
                lot_size=lot_size,
                max_profit=max_profit,
                max_loss=max_loss
            )
        
        elif strategy == "IRON_BUTTERFLY":
            # Sell call spread + Sell put spread
            # For simplicity, using similar pricing
            calls = chain[(chain['option_type'] == 'CE') & (chain['strike'] == round_spot)]
            puts = chain[(chain['option_type'] == 'PE') & (chain['strike'] == round_spot)]
            
            if len(calls) == 0 or len(puts) == 0:
                return None
            
            entry_premium = (calls['close_price'].values[0] + puts['close_price'].values[0]) / 2
            max_profit = entry_premium * 25 * lot_size
            max_loss = (100 - entry_premium) * 25 * lot_size
            
            trade = Trade(
                trade_id=f"{date}_{strategy}_{lot_size}",
                date=date,
                strategy=strategy,
                entry_strike_long=round_spot,
                entry_strike_short=round_spot,
                entry_premium=entry_premium,
                expiry=expiry_date,
                lot_size=lot_size,
                max_profit=max_profit,
                max_loss=max_loss
            )
        
        return trade
    
    def get_premium_next_day(self, trade: Trade, exit_date: str) -> float:
        """Get premium for trade on exit date"""
        chain = self.get_options_data(exit_date, trade.expiry)
        
        if len(chain) == 0:
            return None
        
        if trade.strategy in ["BUY_CALL_SPREAD", "BUY_PUT_SPREAD"]:
            opt_type = "CE" if trade.strategy == "BUY_CALL_SPREAD" else "PE"
            
            long_leg = chain[(chain['strike'] == trade.entry_strike_long) & (chain['option_type'] == opt_type)]
            short_leg = chain[(chain['strike'] == trade.entry_strike_short) & (chain['option_type'] == opt_type)]
            
            if len(long_leg) == 0 or len(short_leg) == 0:
                return None
            
            exit_premium = long_leg['close_price'].values[0] - short_leg['close_price'].values[0]
        
        else:  # Iron Butterfly
            calls = chain[(chain['option_type'] == 'CE') & (chain['strike'] == trade.entry_strike_long)]
            puts = chain[(chain['option_type'] == 'PE') & (chain['strike'] == trade.entry_strike_short)]
            
            if len(calls) == 0 or len(puts) == 0:
                return None
            
            exit_premium = (calls['close_price'].values[0] + puts['close_price'].values[0]) / 2
        
        return exit_premium
    
    def backtest(self, start_date: str = None, end_date: str = None, max_risk_per_trade: float = 2000):
        """
        Run backtest on historical data
        
        Args:
            start_date: Backtest start date (YYYY-MM-DD)
            end_date: Backtest end date (YYYY-MM-DD)
            max_risk_per_trade: Maximum risk per trade
        """
        # Get date range
        if start_date is None or end_date is None:
            db_start, db_end = self.get_dates_range()
            if start_date is None:
                # Start 1 year ago for more data
                start_dt = datetime.strptime(db_start, '%Y-%m-%d')
                start_date = (start_dt + timedelta(days=365)).strftime('%Y-%m-%d')
            if end_date is None:
                end_date = db_end
        
        logger.info(f"Starting backtest from {start_date} to {end_date}")
        
        current_date = start_date
        trade_count = 0
        win_count = 0
        loss_count = 0
        total_pnl = 0
        
        while current_date and current_date <= end_date:
            # Get market data
            spot = self.get_spot_price(current_date)
            if spot is None:
                next_date = self.get_next_trading_date(current_date)
                if next_date is None:
                    break
                current_date = next_date
                continue
            
            # Analyze market condition
            gap_info = self.detect_gap(current_date)
            
            # Skip if not in trading hours
            if datetime.strptime(current_date, '%Y-%m-%d').hour > 10:
                next_date = self.get_next_trading_date(current_date)
                if next_date is None:
                    break
                current_date = next_date
                continue
            
            # Estimate IV rank (simplified)
            iv_rank = np.random.uniform(20, 80)  # Placeholder
            
            # Decide strategy
            strategy = self.decide_strategy(gap_info, iv_rank)
            
            if strategy != "NO_TRADE":
                # Build and execute trade
                lot_size = max(1, int(max_risk_per_trade / 5000))
                trade = self.build_trade(current_date, spot, strategy, iv_rank, lot_size)
                
                if trade:
                    # Hold for 1-2 days
                    exit_date = self.get_next_trading_date(current_date)
                    if exit_date is None:
                        break
                    
                    exit_premium = self.get_premium_next_day(trade, exit_date)
                    
                    if exit_premium is None:
                        next_date = self.get_next_trading_date(current_date)
                        if next_date is None:
                            break
                        current_date = next_date
                        continue
                    
                    # Calculate P&L
                    trade.calculate_exit_pnl(exit_premium, exit_date)
                    
                    # Check exit conditions
                    if trade.pnl >= trade.max_profit * 0.75:
                        trade.status = TradeStatus.TARGET_HIT
                        win_count += 1
                    elif trade.pnl <= -trade.max_loss:
                        trade.status = TradeStatus.STOPLOSS_HIT
                        loss_count += 1
                    else:
                        trade.status = TradeStatus.TIME_EXIT
                        if trade.pnl > 0:
                            win_count += 1
                        else:
                            loss_count += 1
                    
                    total_pnl += trade.pnl
                    trade_count += 1
                    self.trades.append(trade)
            
            next_date = self.get_next_trading_date(current_date)
            if next_date is None:
                break
            current_date = next_date
        
        # Calculate statistics
        win_rate = (win_count / trade_count * 100) if trade_count > 0 else 0
        avg_win = (total_pnl / win_count) if win_count > 0 else 0
        avg_loss = (total_pnl / loss_count) if loss_count > 0 else 0
        
        results = {
            "backtest_period": f"{start_date} to {end_date}",
            "total_trades": trade_count,
            "winning_trades": win_count,
            "losing_trades": loss_count,
            "win_rate": f"{win_rate:.2f}%",
            "total_pnl": f"₹{total_pnl:.2f}",
            "avg_win": f"₹{avg_win:.2f}",
            "avg_loss": f"₹{avg_loss:.2f}",
            "profit_factor": avg_win / abs(avg_loss) if avg_loss != 0 else 0
        }
        
        logger.info(f"Backtest completed: {trade_count} trades")
        return results
    
    def get_trade_summary(self) -> pd.DataFrame:
        """Get summary of all trades"""
        data = []
        for trade in self.trades:
            data.append({
                'date': trade.date,
                'strategy': trade.strategy,
                'entry_premium': trade.entry_premium,
                'exit_premium': trade.exit_premium if trade.exit_premium else 0,
                'pnl': trade.pnl,
                'max_profit': trade.max_profit,
                'max_loss': trade.max_loss,
                'status': trade.status.value,
                'days_held': trade.days_held
            })
        
        return pd.DataFrame(data)


# ==================== EXAMPLE USAGE ====================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("NIFTY OPTIONS BACKTESTING ENGINE")
    print("="*60)
    
    backtester = NiftyBacktester(db_path="nifty_options_5years.db")
    
    print("\n[Backtesting] Running strategy on historical data...")
    results = backtester.backtest(
        start_date=None,
        end_date=None,
        max_risk_per_trade=2000
    )
    
    print("\n[Backtest Results]:")
    for key, value in results.items():
        print(f"  {key}: {value}")
    
    if len(backtester.trades) > 0:
        print("\n[Trade Summary]:")
        summary_df = backtester.get_trade_summary()
        print(summary_df.head(10))
        print(f"\nTotal trades: {len(summary_df)}")
