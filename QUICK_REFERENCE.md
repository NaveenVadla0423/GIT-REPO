# Nifty Adaptive Strategy - Quick Reference Guide

## 🚀 QUICK START (Copy-Paste Ready)

### Morning Checklist (Before 9:30 AM)
```
[ ] Check previous close price
[ ] Check opening price (calculate gap %)
[ ] Check IV Rank (broker chart)
[ ] Decision: What strategy to trade today?
```

---

## 📋 LIVE TRADE EXAMPLES

### EXAMPLE 1: Gap-Up Morning (Today's Setup)
```
Spot: 23,400 (Gap-up from 23,050)
Gap: +1.5% ✅
IV Rank: 72 ✅
Market Time: 9:35 AM ✅

→ STRATEGY: SELL CALL SPREAD (Bear Call)

SETUP:
  Sell  23,400 CE @ ₹140
  Buy   23,700 CE @ ₹50
  ─────────────────────
  NET CREDIT: ₹90 per share
  
EXECUTION:
  Lot Size: 1 (25 shares)
  Total Credit Received: ₹90 × 25 = ₹2,250
  Max Loss: (300 - 90) × 25 = ₹5,250
  Max Profit: ₹2,250
  Target Exit: ₹1,125 (50% of max profit)
  Stop-Loss: After ₹5,250 loss
  
EXIT PLAN:
  ✅ If premium falls to ₹45: EXIT (Profit ₹1,125)
  ❌ If premium rises to ₹135: EXIT (Loss ₹1,125)
  🕐 If 2:30 PM: EXIT (whatever P&L)
```

---

### EXAMPLE 2: Gap-Down Morning
```
Spot: 22,750 (Gap-down from 23,050)
Gap: -1.3% ✅
IV Rank: 68 ✅
Market Time: 9:35 AM ✅

→ STRATEGY: SELL PUT SPREAD (Bear Put)

SETUP:
  Sell  22,750 PE @ ₹145
  Buy   22,450 PE @ ₹55
  ─────────────────────
  NET CREDIT: ₹90 per share
  
EXECUTION:
  Lot Size: 1 (25 shares)
  Total Credit Received: ₹90 × 25 = ₹2,250
  Max Loss: ₹5,250
  Max Profit: ₹2,250
  Target Exit: ₹1,125
  Stop-Loss: ₹5,250 loss
  
EXIT PLAN:
  ✅ If premium falls to ₹45: EXIT (Profit ₹1,125)
  ❌ If premium rises to ₹135: EXIT (Loss ₹1,125)
  🕐 Last 30 mins: CLOSE OUT
```

---

### EXAMPLE 3: Neutral Market (10:00 AM)
```
Spot: 23,100 (No gap or tiny gap)
Gap: +0.2% (Neutral)
IV Rank: 50 (Normal)
Time: 10:00 AM (after stabilization)

→ STRATEGY: IRON CONDOR

SETUP:
  Sell  23,100 CE @ ₹120
  Buy   23,400 CE @ ₹40
  Sell  23,100 PE @ ₹120
  Buy   22,800 PE @ ₹40
  ───────────────────────
  NET CREDIT: (120-40) + (120-40) = ₹160

EXECUTION:
  Lot Size: 1
  Total Credit: ₹160 × 25 = ₹4,000
  Max Loss: (300 - 160) × 25 = ₹3,500
  Max Profit: ₹4,000
  Profit Target: ₹2,000 (50% of max profit)
  Zone of Profit: 22,800 - 23,400 (6% band)
  
EXIT PLAN:
  ✅ If premium decays to ₹80: EXIT (Profit ₹2,000)
  ❌ If premium rises to ₹240: EXIT (Loss ₹2,000)
  🕐 2:30 PM: FORCED EXIT
```

---

## 💹 POSITION SIZING TABLE

Based on Account Size & Max Risk Per Trade:

```
ACCOUNT      MAX RISK    RECOMMENDED LOTS
─────────────────────────────────────────
₹1,00,000      ₹2,000         1 lot
₹2,00,000      ₹4,000         1-2 lots
₹5,00,000      ₹10,000        2 lots
₹10,00,000     ₹20,000        3-4 lots
```

**Formula:**
```
Lots = (Account × 0.02) / Max Loss Per Lot
     = (Account × 0.02) / 5000
```

---

## ⏰ TRADE TIMING RULES

### Best Entry Times
- **Gap strategies**: 9:30 - 9:45 AM (first 15 mins)
- **Iron Condor**: 10:00 - 10:30 AM (after market settles)

### Exit Windows
- **Target Hit**: EXIT IMMEDIATELY ✅
- **Stop-Loss Hit**: EXIT IMMEDIATELY ❌  
- **Last 30 mins (2:30 PM)**: EXIT (collect remaining theta)

---

## 📊 TRADE JOURNAL TEMPLATE

Use this to track every trade:

```
DATE: ___________
Market Gap: _____ % (UP/DOWN)
IV Rank: _____ (HIGH/NORMAL/LOW)

TRADE 1:
├─ Strategy: _____________
├─ Entry Time: __________
├─ Setup: _______________
├─ Entry Premium: ₹_____
├─ Current Premium: ₹____
├─ P&L: ₹_____
└─ Exit Reason: ✅/❌/🕐

DAILY SUMMARY:
├─ Total Trades: _____
├─ Winning Trades: _____
├─ Losing Trades: _____
├─ Daily P&L: ₹_____
└─ Win Rate: _____%
```

---

## 🚨 SAFETY RULES (DO NOT BREAK!)

```
1️⃣  ONLY trade in first 30 mins of market open
    ❌ NO afternoon entries

2️⃣  ALWAYS use defined-risk legs (never naked)
    ❌ NO naked calls/puts

3️⃣  TARGET = 50% of max profit (high probability exit)
    ❌ DON'T be greedy

4️⃣  STOP-LOSS = 100% of max profit
    ❌ DON'T hold beyond this

5️⃣  EXIT by 2:30 PM latest
    ❌ NO overnight holds

6️⃣  Max 2 consecutive losses → STOP TRADING
    ❌ AVOID revenge trading

7️⃣  Daily loss limit: 5% of account
    ❌ SHUT DOWN if hit

8️⃣  ONLY trade spreads (not naked)
    ✅ DEFINED RISK always
```

---

## 💰 EXPECTED RETURNS

### Conservative Projections (Actual May Vary)

**Per Trade:**
- Win Rate: 75-80%
- Avg Win: ₹1,500-2,000
- Avg Loss: ₹2,000-3,000
- Profit Factor: 1.8x

**Monthly (20 trading days, 1 trade/day):**
- Win Rate: 75% → 15 wins, 5 losses
- Gross: (15 × 1500) - (5 × 2500) = ₹22,500 - 12,500 = ₹10,000
- **Monthly Return: 2% (₹10K on ₹5L account)**

**Yearly:**
- 12 months × ₹10K = ₹1,20,000
- **Annual Return: 24%** (realistic expectation)

---

## 🔄 DAILY WORKFLOW

```
9:15 AM   → Check gap & IV rank
9:30 AM   → Decide strategy
9:32 AM   → Place order (first entry)
9:35 AM   → Confirm fill & set alerts
10:30 AM  → Monitor position
2:00 PM   → Check for exits
2:25 PM   → Begin exit if still open
2:30 PM   → CLOSE ALL (if open)
3:30 PM   → Log trade in journal
```

---

## 🎯 ADAPTATION RULES

### If Losing Money?
1. Reduce lot size (cut position size by 50%)
2. Wait for clearer setups (higher IV rank)
3. Review trade journal for patterns

### If Winning Consistently?
1. Increase lot size gradually (max 1 extra lot)
2. Expand IV rank thresholds slightly
3. Test adding a 2nd daily trade

### Market Changes?
- **Earnings week**: Reduce lot size by 50%
- **High volatility (IV>80)**: Skip iron condor, only sell spreads
- **Very low volatility (IV<15)**: Consider buying spreads instead

---

## 🔧 QUICK DECISION TREE

```
Opening Time?
│
├─ YES (9:30-10:30)
│  │
│  └─ Calculate Gap %
│     │
│     ├─ Gap > ±1% & IV > 60?
│     │  └─ YES → SELL SPREAD (Call/Put based on direction)
│     │
│     ├─ Gap < ±0.5% & IV 25-75?
│     │  └─ YES → IRON CONDOR
│     │
│     └─ Other → NO TRADE
│
└─ NO (After 10:30)
   └─ NO NEW TRADES
      (Only manage existing)
```

---

## 📞 TROUBLESHOOTING

### "Premium not moving as expected?"
→ Low liquidity or too far OTM. Use different strikes.

### "Losing more than projected?"
→ Market gapped against you. Adjust strikes further OTM.

### "Not getting target fills?"
→ Use limit orders 1-2 points better. Be patient.

### "Can't exit at target?"
→ Reduce lot size so orders fill faster.

---

## ✅ CHECKLIST FOR FIRST 5 TRADES

- [ ] Paper traded this strategy
- [ ] Calculated own lot size (based on account)
- [ ] Set up trade alerts in broker
- [ ] Have pre-calculated strikes ready
- [ ] Know exact entry/exit prices BEFORE market open
- [ ] Tracked first 5 trades in journal
- [ ] Reviewed & understand all 3 market scenarios

