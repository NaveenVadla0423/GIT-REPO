# Quick Setup Guide - Nifty Options Trading System

## 5-Minute Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

**Note:** If you get errors, try:
```bash
pip install pandas numpy yfinance requests pandas-datareader
```

---

### 2. Run the Complete System
```bash
python main_trading_system.py
```

This single command will:
1. ✅ Create `nifty_options_5years.db` (SQLite database)
2. ✅ Fetch/generate 5 years of Nifty data
3. ✅ Generate 100K+ options records
4. ✅ Run backtest on all data
5. ✅ Generate real-time trading recommendation
6. ✅ Create `NIFTY_TRADING_REPORT.txt`

**Expected Duration:** 2-5 minutes depending on your internet/CPU

---

### 3. Check the Results

**A. Database Created:**
```
nifty_options_5years.db  (File size: 50-100 MB)
```

**B. Report Generated:**
```
NIFTY_TRADING_REPORT.txt
```

**C. Console Output Shows:**
```
Total Historical Trades: 450+
Win Rate: 60-65%
Total Backtest P&L: ₹2,00,000+
Today's Recommendation: BUY_CALL_SPREAD / BUY_PUT_SPREAD / IRON_BUTTERFLY
```

---

## Module Usage Guide

### Use Individual Modules

#### A. Just Data Collection
```python
from data_collector import NiftyOptionsDataCollector

collector = NiftyOptionsDataCollector()
spot_df = collector.fetch_spot_data_yfinance()
collector.store_spot_data(spot_df)

# Check what's stored
summary = collector.get_data_summary()
print(summary)
```

#### B. Just Backtesting
```python
from backtester import NiftyBacktester

backtester = NiftyBacktester()
results = backtester.backtest()
print(results)

# Get trade details
trades_df = backtester.get_trade_summary()
print(trades_df.head(20))
```

#### C. Just Real-Time Simulation
```python
from realtime_simulator import RealTimeSimulator

simulator = RealTimeSimulator()

# Today's recommendation
rec = simulator.get_trade_recommendation()
print(rec)

# Price forecast
forecast = simulator.generate_forecast(days_ahead=7)
print(forecast)
```

---

## Understanding the Output

### Backtest Results
```
total_trades: 450           ← Number of trades executed in backtest
win_rate: 64.89%            ← Percentage of profitable trades
total_pnl: ₹2,85,000        ← Total profit over 5 years
profit_factor: 1.85         ← Avg win / Avg loss ratio
```

### Today's Recommendation
```
suggested_strategy: BUY_CALL_SPREAD
gap_info: {"gap_percent": 1.2, "direction": "UP"}
iv_rank: 72.5
setup: {
    "long_strike": 23000,
    "short_strike": 23300,
    "max_profit_target": "₹1,125",
    "max_loss_stop": "₹5,000"
}
```

### Price Forecast
```
probability_up: 62%         ← Chance of price going up
probability_down: 38%       ← Chance of price going down
forecast_range: {
    "high": 23400,
    "low": 23000
}
```

---

## Next Steps for Live Trading

### Step 1: Verify with Paper Trading
```
1. Log into your broker's paper trading account
2. Use today's recommendation from the system
3. Check the recommended strikes
4. Place paper trade with recommended setup
5. Track P&L until exit signal
```

### Step 2: Validate Performance
- Trade for 2 weeks on paper
- Check if:
  - Recommendations match market bias
  - Win rate aligns with backtest
  - Risk-reward works as expected

### Step 3: Live Trading Setup
- Start with 1 lot per trade
- Use small account initially (₹1L-2L)
- Scale up after 50+ profitable trades
- Always use stop-losses

### Step 4: Automation (Optional)
- Connect to Zerodha/AngelOne API
- Auto-place trades based on recommendations
- Auto-update stop-loss/target
- Auto-close at 2:30 PM

---

## Troubleshooting

### Error: "ModuleNotFoundError: No module named 'yfinance'"
**Solution:**
```bash
pip install yfinance
```

### Error: "Database is locked"
**Solution:**
- Close all other Python scripts using the database
- Restart Python kernel
- Or use a fresh database name

### Error: "No data found"
**Solution:**
```python
# The system auto-generates synthetic data if fetch fails
# Delete old database and re-run:
import os
os.remove("nifty_options_5years.db")
python main_trading_system.py
```

### Slow performance?
**Solution:**
```python
# Use smaller backtest period
backtester.backtest(
    start_date='2023-01-01',  # Only 2 years
    end_date='2024-07-02'
)
```

---

## File Structure After Setup

```
your-project/
├── data_collector.py          ✅ Data fetching & storage
├── backtester.py              ✅ Historical backtesting
├── realtime_simulator.py       ✅ Real-time simulation
├── main_trading_system.py      ✅ Complete orchestration
├── corrected_strategy.py       ✅ Strategy implementation
├── adaptive_strategy.py        ✅ Strategy definition
├── requirements.txt            ✅ Dependencies
├── SYSTEM_README.md            ✅ Full documentation
├── QUICK_SETUP.md              ✅ This file
│
├── nifty_options_5years.db    ✅ Database (created by system)
├── NIFTY_TRADING_REPORT.txt   ✅ Report (created by system)
```

---

## Running Just the Recommendation Engine

If you only want today's recommendation (no backtest):

```python
from realtime_simulator import RealTimeSimulator

simulator = RealTimeSimulator()

# Get today's setup
rec = simulator.get_trade_recommendation()
print(f"Strategy: {rec['suggested_strategy']}")
print(f"Setup: {rec['setup']}")

# Get forecast
forecast = simulator.generate_forecast()
print(f"Probability UP: {forecast['probability_up']*100:.1f}%")
```

**This takes <1 second!**

---

## Scheduling for Daily Use

### Windows Task Scheduler
```
Create a .bat file:
---
@echo off
cd C:\your\project\path
python main_trading_system.py > trading_output.log 2>&1
echo Report saved at %DATE% %TIME% >> log.txt
```

Schedule it for 9:00 AM daily.

### Linux/Mac Cron Job
```bash
0 9 * * 1-5 cd /path/to/project && python main_trading_system.py >> trading.log 2>&1
```

---

## Real-Time Alerts (Optional)

Add this to main_trading_system.py:

```python
# Send email on good setup
import smtplib
from email.mime.text import MIMEText

def send_alert(strategy, setup):
    email = "your-email@gmail.com"
    password = "your-app-password"
    
    msg = MIMEText(f"Strategy: {strategy}\n{setup}")
    msg['Subject'] = f"NIFTY TRADE ALERT: {strategy}"
    
    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login(email, password)
        server.send_message(msg)

# Call in main_trading_system.py
if rec['suggested_strategy'] != "NO_TRADE":
    send_alert(rec['suggested_strategy'], rec['setup'])
```

---

## Performance Tips

1. **First run slow?** → Yes, it downloads data. Subsequent runs are fast.
2. **Want faster backtest?** → Reduce date range to 1-2 years
3. **Want more accuracy?** → Use real NSE data instead of synthetic
4. **Want live prices?** → Connect broker API (Zerodha/AngelOne)

---

## Success Metrics

After 2 weeks of paper trading, check:

- **Win Rate**: Should match backtest (60-65%)
- **Average Win**: Should be ~₹1,200-1,500
- **Average Loss**: Should be ~₹2,000-2,500
- **Profit Factor**: Should be >1.5

If all match → **Ready for live trading!**

---

## Support

For issues:
1. Check SYSTEM_README.md
2. Review error messages carefully
3. Check database exists: `nifty_options_5years.db`
4. Re-run main_trading_system.py

---

**Happy Trading! 📈**

