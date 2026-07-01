"""
CORRECTED Nifty Adaptive Options Trading Strategy
Buy Spreads (Good Risk-Reward) instead of Sell Spreads (Bad Risk-Reward)
"""

from dataclasses import dataclass
from enum import Enum
from datetime import datetime, time
from typing import Optional, Dict


class StrategyType(Enum):
    """Trading strategies with POSITIVE risk-reward"""
    BUY_CALL_SPREAD = "buy_call_spread"
    BUY_PUT_SPREAD = "buy_put_spread"
    IRON_BUTTERFLY = "iron_butterfly"
    NO_TRADE = "no_trade"


@dataclass
class SpreadSetup:
    """Spread configuration with risk-reward metrics"""
    strategy: StrategyType
    long_strike: int
    short_strike: int
    debit_paid: float
    width: int
    max_profit: float
    max_loss: float
    
    @property
    def risk_reward_ratio(self) -> float:
        """Calculate risk-reward ratio"""
        return self.max_profit / self.max_loss if self.max_loss > 0 else 0
    
    @property
    def breakeven_win_rate(self) -> float:
        """Calculate win rate needed to break even (simplified)"""
        if (self.max_profit + self.max_loss) > 0:
            return self.max_loss / (self.max_profit + self.max_loss)
        return 0


class CorrectedNiftyStrategy:
    """Strategy focused on POSITIVE risk-reward ratios"""
    
    def __init__(self, account_balance: float = 500000, max_risk_per_trade: float = 2000):
        """
        Initialize strategy with fixed max risk per trade
        
        Args:
            account_balance: Account balance in INR
            max_risk_per_trade: Maximum loss per trade (fixed amount)
        """
        self.account_balance = account_balance
        self.max_risk_per_trade = max_risk_per_trade
        self.trades_log = []
    
    def detect_gap(self, prev_close: float, open_price: float) -> Dict:
        """Detect gap direction and magnitude"""
        gap_percent = ((open_price - prev_close) / prev_close) * 100
        gap_abs = abs(gap_percent)
        
        return {
            "gap_percent": gap_percent,
            "gap_abs": gap_abs,
            "direction": "UP" if gap_percent > 0 else "DOWN",
            "magnitude": "STRONG" if gap_abs > 1 else "MODERATE" if gap_abs > 0.5 else "NONE"
        }
    
    def get_iv_classification(self, iv_rank: float) -> str:
        """Classify volatility environment"""
        if iv_rank > 75:
            return "HIGH"
        elif iv_rank < 25:
            return "LOW"
        else:
            return "NORMAL"
    
    def decide_strategy(self, gap_info: Dict, iv_rank: float, current_time: time) -> StrategyType:
        """
        Decide strategy based on market conditions
        
        Gap-UP + High IV → BUY Call Spread (defensive on bounce-back)
        Gap-DOWN + High IV → BUY Put Spread (defensive on bounce-back)
        Neutral + Normal IV → Iron Butterfly
        """
        # Don't enter after 10:30 AM
        if current_time > time(10, 30):
            return StrategyType.NO_TRADE
        
        gap_percent = gap_info["gap_percent"]
        iv_class = self.get_iv_classification(iv_rank)
        
        # Gap-up: prices rallied hard, likely to pullback → buy call spread
        if gap_percent > 1 and iv_class == "HIGH":
            return StrategyType.BUY_CALL_SPREAD
        
        # Gap-down: prices fell hard, likely to bounce → buy put spread
        elif gap_percent < -1 and iv_class == "HIGH":
            return StrategyType.BUY_PUT_SPREAD
        
        # No gap + normal conditions → iron butterfly (theta play)
        elif abs(gap_percent) < 0.5 and iv_class == "NORMAL":
            return StrategyType.IRON_BUTTERFLY
        
        return StrategyType.NO_TRADE
    
    def build_buy_call_spread(self, spot: float) -> SpreadSetup:
        """
        Buy Call Spread after gap-up
        
        Logic: After gap-up, prices often consolidate or pull back slightly
        Strategy: Buy ATM call, Sell OTM call → profit if price falls back or stays flat
        
        Example (Spot 23,200):
          BUY  23,200 CE @ 120
          SELL 23,500 CE @ 40
          Debit: 80
          Max Profit: 300 - 80 = 220 (if both expire worthless or max payoff)
          Max Loss: 80 (initial debit)
          Ratio: 220:80 = 2.75:1
        """
        round_spot = round(spot / 100) * 100
        
        # Buy closer to ATM, sell 300-500 OTM
        long_strike = round_spot
        short_strike = round_spot + 300
        
        # Estimated premiums (adjust based on actual IV/expiry)
        long_premium = 120  # Approximate
        short_premium = 40  # Approximate
        
        debit = long_premium - short_premium
        width = short_strike - long_strike
        max_profit = (width - debit) * 25  # 25 = contract multiplier
        max_loss = debit * 25
        
        return SpreadSetup(
            strategy=StrategyType.BUY_CALL_SPREAD,
            long_strike=long_strike,
            short_strike=short_strike,
            debit_paid=debit,
            width=width,
            max_profit=max_profit,
            max_loss=max_loss
        )
    
    def build_buy_put_spread(self, spot: float) -> SpreadSetup:
        """
        Buy Put Spread after gap-down
        
        Logic: After gap-down, prices often bounce back
        Strategy: Buy ATM put, Sell OTM put → profit if price bounces or stays flat
        
        Example (Spot 22,800):
          BUY  22,800 PE @ 120
          SELL 22,500 PE @ 40
          Debit: 80
          Max Profit: 300 - 80 = 220
          Max Loss: 80
          Ratio: 220:80 = 2.75:1
        """
        round_spot = round(spot / 100) * 100
        
        # Buy closer to ATM, sell 300-500 OTM (lower strikes)
        long_strike = round_spot
        short_strike = round_spot - 300
        
        # Estimated premiums
        long_premium = 120
        short_premium = 40
        
        debit = long_premium - short_premium
        width = long_strike - short_strike
        max_profit = (width - debit) * 25
        max_loss = debit * 25
        
        return SpreadSetup(
            strategy=StrategyType.BUY_PUT_SPREAD,
            long_strike=long_strike,
            short_strike=short_strike,
            debit_paid=debit,
            width=width,
            max_profit=max_profit,
            max_loss=max_loss
        )
    
    def build_iron_butterfly(self, spot: float) -> SpreadSetup:
        """
        Iron Butterfly on neutral days
        
        Example (Spot 23,000):
          SELL 23,000 CE @ 80   / BUY 23,200 CE @ 20  → Credit: 60
          SELL 23,000 PE @ 80   / BUY 22,800 PE @ 20  → Credit: 60
          Total Credit: 120
          Max Profit: 120 (credit collected)
          Max Loss: 200 - 120 = 80 per leg, total 80
          Ratio: 120:80 = 1.5:1
        """
        round_spot = round(spot / 100) * 100
        
        # Call side
        call_width = 200
        call_credit = 60
        call_max_loss = call_width - call_credit
        
        # Put side
        put_width = 200
        put_credit = 60
        put_max_loss = put_width - put_credit
        
        total_credit = (call_credit + put_credit) * 25
        total_max_loss = max(call_max_loss, put_max_loss) * 25  # One leg max
        
        return SpreadSetup(
            strategy=StrategyType.IRON_BUTTERFLY,
            long_strike=0,  # N/A for butterfly
            short_strike=0,
            debit_paid=-total_credit,  # Negative because it's a credit
            width=0,
            max_profit=total_credit,
            max_loss=total_max_loss
        )
    
    def analyze_market(self, prev_close: float, open_price: float, iv_rank: float, current_spot: float) -> Dict:
        """
        Complete market analysis and recommendation
        """
        gap_info = self.detect_gap(prev_close, open_price)
        current_time = datetime.now().time()
        
        strategy = self.decide_strategy(gap_info, iv_rank, current_time)
        
        if strategy == StrategyType.NO_TRADE:
            return {
                "recommendation": "NO_TRADE",
                "reason": "Outside trading hours or unclear setup"
            }
        
        # Build appropriate spread
        if strategy == StrategyType.BUY_CALL_SPREAD:
            spread = self.build_buy_call_spread(current_spot)
        elif strategy == StrategyType.BUY_PUT_SPREAD:
            spread = self.build_buy_put_spread(current_spot)
        else:  # Iron Butterfly
            spread = self.build_iron_butterfly(current_spot)
        
        # Calculate position size based on max loss
        position_size = max(1, int(self.max_risk_per_trade / (spread.max_loss / 25)))
        
        adjusted_max_loss = spread.max_loss * position_size
        adjusted_max_profit = spread.max_profit * position_size
        
        return {
            "recommendation": strategy.value,
            "gap_info": gap_info,
            "iv_rank": iv_rank,
            "iv_class": self.get_iv_classification(iv_rank),
            "spread": {
                "long_strike": spread.long_strike,
                "short_strike": spread.short_strike,
                "debit_paid": spread.debit_paid,
                "width": spread.width
            },
            "metrics": {
                "max_profit_per_lot": spread.max_profit,
                "max_loss_per_lot": spread.max_loss,
                "risk_reward_ratio": spread.risk_reward_ratio,
                "breakeven_win_rate": f"{spread.breakeven_win_rate*100:.1f}%"
            },
            "position": {
                "lots": position_size,
                "total_max_loss": adjusted_max_loss,
                "total_max_profit": adjusted_max_profit,
                "target_profit": adjusted_max_profit * 0.75
            },
            "exit_rules": {
                "target_hit": f"Exit at ₹{adjusted_max_profit * 0.75:.0f} profit (75% of max)",
                "stop_loss": f"Exit if loss reaches ₹{-adjusted_max_loss:.0f}",
                "time_exit": "2:30 PM (end of day)"
            }
        }


# ==================== EXAMPLE USAGE ====================

if __name__ == "__main__":
    strategy = CorrectedNiftyStrategy(
        account_balance=500000,
        max_risk_per_trade=2000
    )
    
    # SCENARIO 1: Gap-Up Morning
    print("=" * 60)
    print("SCENARIO 1: Gap-Up Morning")
    print("=" * 60)
    
    analysis = strategy.analyze_market(
        prev_close=23050,
        open_price=23350,  # +1.3% gap
        iv_rank=70,
        current_spot=23300
    )
    
    print(f"Strategy: {analysis['recommendation']}")
    print(f"Gap: {analysis['gap_info']['gap_percent']:.2f}%")
    print(f"IV Class: {analysis['iv_class']}")
    print(f"\nRisk-Reward: 1:{analysis['metrics']['risk_reward_ratio']:.2f} ✅")
    print(f"Breakeven Win Rate: {analysis['metrics']['breakeven_win_rate']}")
    print(f"\nPosition Size: {analysis['position']['lots']} lot(s)")
    print(f"Max Loss: ₹{analysis['position']['total_max_loss']:.0f}")
    print(f"Max Profit: ₹{analysis['position']['total_max_profit']:.0f}")
    print(f"Target Profit: ₹{analysis['position']['target_profit']:.0f}")
    
    # SCENARIO 2: Gap-Down Morning
    print("\n" + "=" * 60)
    print("SCENARIO 2: Gap-Down Morning")
    print("=" * 60)
    
    analysis = strategy.analyze_market(
        prev_close=23050,
        open_price=22750,  # -1.3% gap
        iv_rank=68,
        current_spot=22800
    )
    
    print(f"Strategy: {analysis['recommendation']}")
    print(f"Gap: {analysis['gap_info']['gap_percent']:.2f}%")
    print(f"IV Class: {analysis['iv_class']}")
    print(f"\nRisk-Reward: 1:{analysis['metrics']['risk_reward_ratio']:.2f} ✅")
    print(f"Breakeven Win Rate: {analysis['metrics']['breakeven_win_rate']}")
    print(f"\nMax Loss: ₹{analysis['position']['total_max_loss']:.0f}")
    print(f"Max Profit: ₹{analysis['position']['total_max_profit']:.0f}")
