# 🚀 Quick Reference Guide

**For**: Developers continuing this project
**Purpose**: Fast lookup of critical information
**Updated**: 2025-12-03

---

## 📍 Three Core Features Status

### 1. 🚦 Automated Trading Start/Stop

**Status**: ⚠️ **70% Complete** - Needs 3 critical fixes

| Component | Status | Notes |
|-----------|--------|-------|
| Start bot API | ✅ Working | `/bot/start` endpoint functional |
| Stop bot API | ⚠️ Partial | Stops loop but **doesn't close positions** |
| Strategy execution | ⚠️ Partial | **Only 1 candle** passed (needs 100) |
| Real-time data | ❌ Not active | Still using **mock prices** |
| Force close | ❌ Missing | **CRITICAL SAFETY ISSUE** |

**Fix Priority**:
1. 🔴🔴🔴 Add force close on stop (1.5h)
2. 🔴🔴🔴 Load 100 historical candles (2h)
3. 🟡 Switch to real Bitget WebSocket (0.5h)

---

### 2. 📚 Strategy Management

**Status**: ✅ **100% Complete**

| Feature | Status |
|---------|--------|
| Create strategy | ✅ Working |
| List strategies | ✅ Working |
| Appear in Bot Control | ✅ Working |
| Appear in Backtest | ✅ Working |
| Active/inactive filter | ✅ Working |
| User isolation | ✅ Working |

**No action needed** - Fully functional

---

### 3. 📈 Backtesting

**Status**: ✅ **95% Complete** - One missing feature

| Feature | Status | Notes |
|---------|--------|-------|
| Auto-fetch historical data | ✅ Working | From Bitget API |
| Date range selection | ✅ Working | User picks dates |
| Status tracking | ✅ Working | queued → running → completed |
| Equity curve | ✅ Working | Displayed in chart |
| Trade list | ✅ Working | All trades shown |
| Performance metrics | ❌ Missing | Returns `{}` instead of stats |

**Fix Priority**:
1. 🔴🔴 Calculate metrics (1h) - total_return, win_rate, sharpe_ratio, etc.

**Historical Period Available**:
- 1h candles: ~8 days
- 4h candles: ~33 days (1 month)
- 1D candles: ~200 days (6.5 months)

---

## 🔥 Critical Files to Know

### Backend Core
```
backend/src/api/bot.py          ← Bot start/stop endpoints
backend/src/api/backtest.py     ← Backtest execution
backend/src/services/bot_runner.py  ← Live trading loop
backend/src/services/bitget_rest.py ← Bitget API client
```

### Frontend Core
```
frontend/src/pages/BotControl.jsx       ← Bot control UI
frontend/src/pages/Strategy.jsx         ← Strategy management
frontend/src/components/strategy/BacktestRunner.jsx  ← Backtest UI
```

### Configuration
```
backend/trading.db              ← SQLite database
backend/.env (create this!)     ← Environment variables
```

---

## ⚡ Quick Commands

### Start Services
```bash
# Backend
cd backend
export DATABASE_URL="sqlite+aiosqlite:///./trading.db"
export ENCRYPTION_KEY="Dz9w_blEMa-tMD5hqK6V7yiaYecQBdsTaO0PJR3ESn8="
uvicorn src.main:app --reload --port 8000 > /tmp/backend.log 2>&1 &

# Frontend
cd frontend
npm start &
```

### Check Logs
```bash
tail -f /tmp/backend.log                    # All logs
tail -f /tmp/backend.log | grep ERROR       # Errors only
tail -f /tmp/backend.log | grep backtest    # Backtest logs
```

### Test Backtest
```bash
cd /Users/mr.joo/Desktop/auto-dashboard
bash test_backtest_workflow.sh
```

### Database Queries
```bash
cd backend

# Active strategies
sqlite3 trading.db "SELECT id, name, is_active FROM strategies WHERE is_active=1;"

# Recent trades
sqlite3 trading.db "SELECT * FROM trades ORDER BY created_at DESC LIMIT 5;"

# Backtest results
sqlite3 trading.db "SELECT id, final_balance, status FROM backtest_results ORDER BY created_at DESC LIMIT 5;"
```

---

## 🎯 Implementation Checklist

### Must Fix Before Production

- [ ] **Force close positions on bot stop**
  - File: `backend/src/api/bot.py`
  - Line: 56-79
  - Add: Get positions → Close all → Log results
  - Time: 1.5 hours

- [ ] **Load 100 historical candles for live trading**
  - File: `backend/src/services/bot_runner.py`
  - Line: 44-110 (`_run_loop` method)
  - Add: `deque(maxlen=100)` → Load candles → Pass to strategy
  - Time: 2 hours

- [ ] **Calculate backtest metrics**
  - File: `backend/src/api/backtest.py`
  - Line: 80-180 (`_run_backtest_background`)
  - Add: Calculate total_return, win_rate, profit_factor, etc.
  - Time: 1 hour

- [ ] **Switch to real Bitget WebSocket**
  - File: `backend/src/database/db.py`
  - Line: 51-56
  - Change: Comment mock, uncomment real
  - Time: 5 minutes + testing

---

## 🚨 Common Errors & Quick Fixes

### Error: `KeyError: 'close'`
**Cause**: Market data not in candle format
**Fix**: Check `bot_runner.py:130-139` - candle object creation
**Prevention**: Never modify candle structure

### Error: `The margin mode cannot be empty`
**Cause**: Missing `marginMode` in order
**Fix**: Check `bitget_rest.py:222` - must have `"marginMode": "crossed"`
**Prevention**: Don't remove this field

### Error: `Parameter verification failed`
**Cause**: Wrong Bitget API parameters
**Fix**:
- Symbol: "BTCUSDT" not "BTC/USDT"
- Interval: "1H" not "1h" (uppercase!)
- Add: `"productType": "USDT-FUTURES"`

### Error: Backtest dropdown empty
**Status**: ✅ Fixed in Session 5
**Solution**: StrategyList now calls `onStrategiesLoaded()` callback

---

## 📊 Test Account

```
Email: admin@admin.com
Password: admin
User ID: 6
```

Use this for testing. Create new accounts for production users.

---

## 🔐 Security Checklist

- [x] JWT authentication implemented
- [x] API keys encrypted in database
- [x] User data isolated (user_id filtering)
- [x] Password hashing
- [ ] HTTPS for production (not implemented yet)
- [ ] Rate limiting (implemented but test thoroughly)

---

## 📈 Success Metrics

### Feature 1: Trading
✅ Success = Bot stops AND positions close automatically

### Feature 2: Strategies
✅ Success = New strategy appears in both Bot Control and Backtest dropdowns

### Feature 3: Backtest
✅ Success = Metrics show actual numbers (not null)

---

## 💡 Quick Tips

1. **Always filter by user_id** in database queries (security!)
2. **Never use await on sync sessions** (causes errors)
3. **Test with small amounts first** (real money at stake)
4. **Check logs frequently** (`tail -f /tmp/backend.log`)
5. **Backup database before major changes** (`cp trading.db trading.db.backup`)

---

## 📞 Need More Info?

| Question | Document |
|----------|----------|
| "What's the full history?" | [WORK_LOG.md](WORK_LOG.md) |
| "How do I implement fixes?" | [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) |
| "What's the current status?" | [CURRENT_STATUS_SUMMARY.md](CURRENT_STATUS_SUMMARY.md) |
| "Quick lookup?" | This file! |

---

## 🎯 Next 3 Actions

1. **Read** [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) → Issue 1.1
2. **Implement** force close in `backend/src/api/bot.py`
3. **Test** with real bot → start → stop → verify positions closed

**Time to Production**: ~5 hours focused work

---

*Last Updated*: 2025-12-03
*Quick Reference v1.0*
