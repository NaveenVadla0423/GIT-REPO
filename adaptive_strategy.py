"""
Nifty Adaptive Options Trading Strategy
Works on Gap-Up, Gap-Down, and Neutral market conditions
Minimal losses with high probability profits
"""

from dataclasses import dataclass
from enum import Enum
from datetime import datetime, time
from typing import Optional, Dict
import json


class MarketCondition(Enum):
    """Market condition classifications"""
    GAP_UP_STRONG = "gap_up_strong"
    GAP_UP_MODERATE = "gap_up_moderate"
    GAP_DOWN_STRONG = "gap_down_strong"
    GAP_DOWN_MODERATE = "gap_down_moderate"
    NO_GAP = "no_gap"


class StrategyType(Enum):
    """Trading strategies"""
    SELL_CALL_SPREAD = "sell_call_spread"
    SELL_PUT_SPREAD = "sell_put_spread"
    IRON_CONDOR = "iron_condor"
    NO_TRADE = "no_trade"


class TradeStatus(Enum):
    """Trade status tracking"""
    ACTIVE = "active"
    TARGET_HIT = "target_hit"
    STOPLOSS_HIT = "stoploss_hit"
    TIME_EXIT = "time_exit"
    CLOSED = "closed"


@dataclass
class TradeSetup:
    """Single trade configuration"""
    strategy: StrategyType
    entry_time: datetime
    entry_premium: float
    max_profit: float
    max_loss: float
    strike_long: int
    strike_short: int
    lot_size: int = 1
    
    @property
    def target_profit(self) -> float:
        """50% of max profit is the target"""
        return self.max_profit * 0.5


@dataclass
class Position:
    """Active position tracker"""
    trade_id: str
    setup: TradeSetup
    entry_time: datetime
    entry_premium: float
    current_premium: float
    status: TradeStatus = TradeStatus.ACTIVE
    pnl: float = 0.0
    
    def update_pnl(self, current_premium: float):
        """Update profit/loss"""
        self.current_premium = current_premium
        self.pnl = (self.entry_premium - current_premium) * self.setup.lot_size * 25  # 25 = multiplier
    
    def check_exit_condition(self) -> Optional[TradeStatus]:
        """Determine if trade should exit"""
        # Check target hit
        if self.pnl >= self.setup.target_profit:
            return TradeStatus.TARGET_HIT
        
        # Check stop loss
        if self.pnl <= -self.setup.max_loss:
            return TradeStatus.STOPLOSS_HIT
        
        # Check time exit (2:30 PM)
        if datetime.now().time() >= time(14, 30):
            return TradeStatus.TIME_EXIT
        
        return None


class NiftyAdaptiveStrategy:
    """Main strategy engine"""
    
    def __init__(self, account_balance: float = 500000, max_risk_percent: float = 0.02):
        """
        Initialize strategy
        
        Args:
            account_balance: Starting account balance in INR
            max_risk_percent: Max risk per trade as % of account (default 2%)
        """
        self.account_balance = account_balance
        self.max_risk_percent = max_risk_percent
        self.positions: Dict[str, Position] = {}
        self.trades_executed = 0
        self.daily_pnl = 0.0
        self.consecutive_losses = 0
    
    def detect_market_gap(self, previous_close: float, opening_price: float) -> MarketCondition:
        """
        Identify gap direction and magnitude
        
        Args:
            previous_close: Previous day closing price
            opening_price: Current day opening price
        
        Returns:
            MarketCondition enum
        """
        gap_percent = ((opening_price - previous_close) / previous_close) * 100
        
        if gap_percent > 1:
            return MarketCondition.GAP_UP_STRONG
        elif gap_percent > 0.5:
            return MarketCondition.GAP_UP_MODERATE
        elif gap_percent < -1:
            return MarketCondition.GAP_DOWN_STRONG
        elif gap_percent < -0.5:
            return MarketCondition.GAP_DOWN_MODERATE
        else:
            return MarketCondition.NO_GAP
    
    def get_iv_condition(self, iv_rank: float) -> str:
        """
        Classify volatility condition
        
        Args:
            iv_rank: IV Rank as percentage (0-100)
        
        Returns:
            Volatility condition string
        """
        if iv_rank > 75:
            return "HIGH_IV"
        elif iv_rank < 25:
            return "LOW_IV"
        else:
            return "NORMAL_IV"
    
    def analyze_market_condition(
        self,
        previous_close: float,
        opening_price: float,
        iv_rank: float
    ) -> StrategyType:
        """
        Determine best strategy based on market conditions
        
        Args:
            previous_close: Previous closing price
            opening_price: Opening price
            iv_rank: IV Rank (0-100)
        
        Returns:
            Best StrategyType to trade
        """
        gap_condition = self.detect_market_gap(previous_close, opening_price)
        iv_condition = self.get_iv_condition(iv_rank)
        gap_percent = ((opening_price - previous_close) / previous_close) * 100
        
        # Check trading hours
        if datetime.now().time() > time(10, 30):
            return StrategyType.NO_TRADE  # Too late to enter
        
        # Strategy selection logic
        if gap_percent > 1 and iv_rank > 60:
            return StrategyType.SELL_CALL_SPREAD
        elif gap_percent < -1 and iv_rank > 60:
            return StrategyType.SELL_PUT_SPREAD
        elif abs(gap_percent) < 0.5 and 25 < iv_rank < 75:
            return StrategyType.IRON_CONDOR
        else:
            return StrategyType.NO_TRADE
    
    def calculate_spread_legs(self, spot: float, strategy: StrategyType) -> Dict:
        """
        Calculate entry strikes for the strategy
        
        Args:
            spot: Current spot price
            strategy: Strategy type
        
        Returns:
            Dictionary with strike details
        """
        # Round to nearest 100
        round_spot = round(spot / 100) * 100
        
        if strategy == StrategyType.SELL_CALL_SPREAD:
            return {
                "sell_strike": round_spot,
                "buy_strike": round_spot + 300,
                "max_profit": 100,  # Per lot
                "max_loss": 200,     # Per lot
                "description": f"Sell {round_spot}CE / Buy {round_spot + 300}CE"
            }
        
        elif strategy == StrategyType.SELL_PUT_SPREAD:
            return {
                "sell_strike": round_spot,
                "buy_strike": round_spot - 300,
                "max_profit": 100,
                "max_loss": 200,
                "description": f"Sell {round_spot}PE / Buy {round_spot - 300}PE"
            }
        
        elif strategy == StrategyType.IRON_CONDOR:
            return {
                "sell_call": round_spot,
                "buy_call": round_spot + 300,
                "sell_put": round_spot,
                "buy_put": round_spot - 300,
                "max_profit": 160,  # Total credit
                "max_loss": 140,    # Width - credit
                "description": f"IC: Sell {round_spot}CE/{round_spot}PE @ {round_spot ± 300}"
            }
        
        return {}
    
    def create_trade(
        self,
        spot: float,
        strategy: StrategyType,
        entry_premium: float,
        lot_size: int = 1
    ) -> TradeSetup:
        """
        Create a trade setup
        
        Args:
            spot: Current spot price
            strategy: Strategy type
            entry_premium: Premium received/paid
            lot_size: Number of lots to trade
        
        Returns:
            TradeSetup object
        """
        legs = self.calculate_spread_legs(spot, strategy)
        
        # Calculate position size based on account risk
        max_loss_per_lot = legs["max_loss"]
        position_size = int(
            (self.account_balance * self.max_risk_percent) / (max_loss_per_lot * lot_size)
        )
        
        trade = TradeSetup(
            strategy=strategy,
            entry_time=datetime.now(),
            entry_premium=entry_premium,
            max_profit=legs["max_profit"] * position_size,
            max_loss=legs["max_loss"] * position_size,
            strike_long=legs.get("buy_strike", legs.get("buy_call")),
            strike_short=legs.get("sell_strike", legs.get("sell_call")),
            lot_size=position_size
        )
        
        return trade
    
    def manage_positions(self, current_premiums: Dict[str, float]) -> Dict:
        """
        Check all active positions and determine exits
        
        Args:
            current_premiums: Dict of {trade_id: current_premium}
        
        Returns:
            Dict with exits to execute
        """
        exits = {
            "target_hits": [],
            "stoploss_hits": [],
            "time_exits": []
        }
        
        for trade_id, premium in current_premiums.items():
            if trade_id not in self.positions:
                continue
            
            position = self.positions[trade_id]
            position.update_pnl(premium)
            
            exit_condition = position.check_exit_condition()
            
            if exit_condition == TradeStatus.TARGET_HIT:
                exits["target_hits"].append(trade_id)
            elif exit_condition == TradeStatus.STOPLOSS_HIT:
                exits["stoploss_hits"].append(trade_id)
            elif exit_condition == TradeStatus.TIME_EXIT:
                exits["time_exits"].append(trade_id)
        
        return exits
    
    def get_daily_performance(self) -> Dict:
        """Get today's performance metrics"""
        total_pnl = sum(p.pnl for p in self.positions.values())
        
        return {
            "daily_pnl": total_pnl,
            "trades_executed": self.trades_executed,
            "active_positions": len([p for p in self.positions.values() if p.status == TradeStatus.ACTIVE]),
            "win_count": len([p for p in self.positions.values() if p.pnl > 0]),
            "loss_count": len([p for p in self.positions.values() if p.pnl < 0])
        }


# Example usage
if __name__ == "__main__":
    # Initialize strategy
    strategy = NiftyAdaptiveStrategy(account_balance=500000, max_risk_percent=0.02)
    
    # Example: Market opens with gap-up and high IV
    previous_close = 23000
    opening_price = 23300  # 1.3% gap up
    iv_rank = 70  # High volatility
    current_spot = 23250
    
    # Analyze market
    best_strategy = strategy.analyze_market_condition(previous_close, opening_price, iv_rank)
    print(f"Best Strategy: {best_strategy.value}")
    
    # Get trade setup
    if best_strategy != StrategyType.NO_TRADE:
        legs = strategy.calculate_spread_legs(current_spot, best_strategy)
        print(f"Setup: {legs['description']}")
        print(f"Max Profit: ₹{legs['max_profit']}")
        print(f"Max Loss: ₹{legs['max_loss']}")
        
        # Create trade
        trade = strategy.create_trade(
            spot=current_spot,
            strategy=best_strategy,
            entry_premium=legs["max_profit"],
            lot_size=1
        )
        print(f"\nTrade Created:")
        print(f"  Target Profit: ₹{trade.target_profit}")
        print(f"  Max Loss: ₹{trade.max_loss}")
        print(f"  Risk-Reward: 1:{trade.target_profit/trade.max_loss:.2f}")
