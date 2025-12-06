# 🎯 Implementation Plan - Core Features

**Target**: Fully functional automated trading system for regular users
**Last Updated**: 2025-12-03
**Priority**: Fix critical issues blocking production readiness

---

## 📋 Implementation Status Overview

| Feature | Status | Priority | Estimated Time |
|---------|--------|----------|----------------|
| **1. Auto Trading Start/Stop** | ⚠️ Partial | 🔴🔴🔴 Critical | 3 hours |
| **2. Strategy Management** | ✅ Working | 🟢 Low | 30 min (enhancements) |
| **3. Backtesting** | ✅ Working | 🟡 Medium | 1 hour (metrics) |

---

## 1. 🚦 Automated Trading Start/Stop

### Current Implementation

**What Works** ✅:
- Start bot API: `/bot/start` (POST)
- Stop bot API: `/bot/stop` (POST)
- Status check: `/bot/status` (GET)
- Database state management (bot_status table)
- Frontend UI (BotControl.jsx)

**Critical Issues** 🔴:

#### Issue 1.1: Force Close Not Implemented
**File**: [bot.py:56-79](backend/src/api/bot.py#L56-L79)

**Current Code**:
```python
@router.post("/stop")
async def stop_bot(...):
    manager: BotManager = request.app.state.bot_manager
    await manager.stop_bot(user_id)  # ❌ Only stops loop, doesn't close positions
    await upsert_status(session, user_id, strategy_id or 0, False)
    return BotStatusResponse(...)
```

**Problem**: Bot stops but positions remain open

**Solution Needed**:
```python
@router.post("/stop")
async def stop_bot(
    request: Request,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """봇 중지 및 전체 포지션 청산 (JWT 인증 필요)"""

    # 1. Get current bot status
    result = await session.execute(
        select(BotStatus).where(BotStatus.user_id == user_id)
    )
    status = result.scalars().first()
    strategy_id = status.strategy_id if status else None

    # 2. Get user's Bitget API credentials
    from ..database.models import UserAccount
    from ..utils.encryption import decrypt

    account_result = await session.execute(
        select(UserAccount).where(UserAccount.user_id == user_id)
    )
    account = account_result.scalars().first()

    if not account:
        raise HTTPException(status_code=400, detail="Bitget API keys not configured")

    # 3. Initialize Bitget REST client
    from ..services.bitget_rest import BitgetRestClient

    bitget_client = BitgetRestClient(
        api_key=decrypt(account.api_key),
        api_secret=decrypt(account.secret_key),
        passphrase=decrypt(account.passphrase) if account.passphrase else ""
    )

    # 4. Close all positions (CRITICAL STEP!)
    try:
        # Get all open positions
        positions = await bitget_client.get_positions(product_type="USDT-FUTURES")

        closed_positions = []
        for position in positions:
            if float(position.get('total', 0)) > 0:  # Has open position
                symbol = position['symbol']
                hold_side = position.get('holdSide', 'long')  # long or short

                # Close position
                from ..services.bitget_rest import PositionSide
                pos_side = PositionSide.LONG if hold_side == 'long' else PositionSide.SHORT

                result = await bitget_client.close_position(
                    symbol=symbol,
                    side=pos_side,
                    margin_coin="USDT"
                )

                closed_positions.append({
                    "symbol": symbol,
                    "side": hold_side,
                    "result": result
                })

                logger.info(f"✅ Closed {hold_side} position for {symbol}: {result}")

        logger.info(f"Force closed {len(closed_positions)} positions for user {user_id}")

    except Exception as e:
        logger.error(f"❌ Failed to close positions for user {user_id}: {e}")
        # Continue with bot stop even if position close fails
        # User can manually close positions if needed

    # 5. Stop bot loop
    manager: BotManager = request.app.state.bot_manager
    await manager.stop_bot(user_id)
    await upsert_status(session, user_id, strategy_id or 0, False)

    # 6. Record in resource manager
    resource_manager.stop_bot(user_id, f"bot_{user_id}")

    return BotStatusResponse(
        user_id=user_id,
        strategy_id=strategy_id,
        is_running=False,
        message=f"Bot stopped. Closed {len(closed_positions)} positions."
    )
```

**Testing**:
1. Start bot with strategy
2. Wait for bot to open position (check via `/bot/status` or Bitget website)
3. Click "Stop Bot" in frontend
4. Verify all positions are closed
5. Check logs for "Force closed X positions"

**Estimated Time**: 1.5 hours

---

#### Issue 1.2: Single Candle Problem
**File**: [bot_runner.py:44-110](backend/src/services/bot_runner.py#L44-L110)

**Problem**: Bot only passes 1 candle to strategies
- RSI needs 14+ candles
- EMA needs 26+ candles
- Current signals are unreliable

**Solution**: See WORK_LOG.md "Critical Issue #2" for complete implementation

**Code Location**: `_run_loop()` method in BotRunner class

**Key Changes**:
1. Import `deque` from collections
2. Create `candle_buffer = deque(maxlen=100)` before main loop
3. Load 100 historical candles from Bitget API on bot start
4. Append each new candle to buffer in main loop
5. Pass `list(candle_buffer)` to strategy instead of `[single_candle]`

**Testing**:
1. Start bot
2. Check logs for "✅ Loaded 100 historical candles"
3. Verify strategy receives 100 candles (add debug log)
4. Check that RSI/EMA calculations are accurate

**Estimated Time**: 2 hours

---

#### Issue 1.3: Mock Price Generator Active
**File**: [db.py:51-56](backend/src/database/db.py#L51-L56)

**Problem**: Using simulated prices instead of real Bitget WebSocket

**Current Code**:
```python
# Line 51-52
asyncio.create_task(mock_price_generator(market_queue))
logger.info("✅ Mock price generator started")

# Line 55-56 (commented out)
# asyncio.create_task(bitget_ws_collector(market_queue))
# logger.info("✅ Bitget WebSocket collector started")
```

**Solution**:
```python
# Comment out mock
# asyncio.create_task(mock_price_generator(market_queue))
# logger.info("✅ Mock price generator started")

# Uncomment real WebSocket
asyncio.create_task(bitget_ws_collector(market_queue))
logger.info("✅ Bitget WebSocket collector started")
```

**⚠️ Prerequisites**:
- Complete Issue 1.2 (historical candles) first
- Test thoroughly with mock data before switching
- Have user's Bitget API keys configured

**Testing**:
1. Backend restart after code change
2. Check logs for "✅ Bitget WebSocket collector started"
3. Monitor real-time price updates
4. Verify prices match Bitget website

**Estimated Time**: 5 minutes (code change) + 30 min (testing)

---

## 2. 📚 Strategy Management

### Current Implementation

**Status**: ✅ **FULLY WORKING**

**Features Working**:
- Create new strategy (Frontend: StrategyForm.jsx, Backend: ai_strategy.py)
- List user's strategies (Frontend: StrategyList.jsx)
- View strategy details
- Activate/deactivate strategies (is_active flag)
- Strategy selection in Bot Control ✅
- Strategy selection in Backtest ✅ (fixed in Session 5)

**Recent Fixes** (Session 5):
1. ✅ Strategy list now appears in backtest dropdown
   - Modified Strategy.jsx to add callback
   - StrategyList calls `onStrategiesLoaded()`
   - BacktestRunner receives strategies as prop

2. ✅ Inactive strategies filtered out
   - Both `/strategy/list` and `/ai/strategies/list` filter by `is_active = True`
   - Users only see active strategies in dropdowns

**How It Works**:

1. **User Creates Strategy**:
   - Frontend: Fill form (name, type, parameters)
   - Backend: POST `/ai/strategies/create`
   - Database: Insert into `strategies` table with `user_id`
   - Response: Strategy saved with unique ID

2. **Strategy Appears in Bot Control**:
   - Frontend: GET `/ai/strategies/list` (user's strategies)
   - Frontend: GET `/strategy/list` (public strategies)
   - Dropdown shows: Strategy name, type, symbol
   - User selects strategy → strategy_id saved to bot_status

3. **Bot Uses Selected Strategy**:
   - Bot reads `bot_status.strategy_id`
   - Loads strategy from database
   - Parses `strategy.params` JSON
   - Maps `type` field to strategy class (e.g., "rsi" → RsiStrategy)
   - Executes strategy with live candles

**Database Schema**:
```sql
CREATE TABLE strategies (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,  -- NULL for public strategies
    name TEXT,
    code TEXT,  -- e.g., "rsi_strategy"
    params TEXT,  -- JSON: {"type": "rsi", "symbol": "BTC/USDT", ...}
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP
);
```

**Example params JSON**:
```json
{
    "type": "rsi",
    "symbol": "BTC/USDT",
    "timeframe": "1h",
    "rsi_period": 14,
    "overbought": 70,
    "oversold": 30
}
```

**Strategy Registry**:
File: [strategy_loader.py](backend/src/services/strategy_loader.py)

Maps `type` to strategy class:
- "rsi" → RsiStrategy
- "ema" → EmaStrategy
- "openclose" → SimpleOpenCloseStrategy

**Minor Enhancements** (Optional - Low Priority):

1. **Strategy Deletion**:
   - Currently can only deactivate (`is_active = 0`)
   - Add DELETE endpoint to permanently remove strategy
   - **Estimated Time**: 20 minutes

2. **Strategy Editing**:
   - Add PUT `/ai/strategies/{id}` endpoint
   - Allow updating name, params without creating new strategy
   - **Estimated Time**: 30 minutes

**Testing Checklist** ✅:
- [x] Create new RSI strategy
- [x] Strategy appears in list
- [x] Strategy appears in Bot Control dropdown
- [x] Strategy appears in Backtest dropdown
- [x] Inactive strategy doesn't appear
- [x] Bot uses correct strategy when started
- [x] Only user's own strategies visible (data isolation)

---

## 3. 📈 Backtesting

### Current Implementation

**Status**: ✅ **WORKING** - Just completed in Session 5!

**Features Working**:
- CSV-free workflow ✅
- Automatic historical data fetch from Bitget API ✅
- Date range selection (user picks dates) ✅
- Status tracking (queued → running → completed/failed) ✅
- Equity curve display ✅
- Trade list display ✅
- Result polling (frontend checks every 1 second) ✅

**Test Results** (Verified):
```
Strategy: RSI Strategy (ID: 3)
Period: 2025-11-01 to 2025-11-30 (1 month)
Initial Balance: 10,000 USDT
Final Balance: 10,857 USDT
Return: +8.57%
Trades: 2
Status: completed ✅
Historical Data: Auto-fetched 200 candles from Bitget ✅
```

**How It Works**:

1. **User Initiates Backtest**:
   - Frontend: BacktestRunner.jsx
   - Select strategy from dropdown
   - Pick date range (e.g., last 1 month)
   - Set initial balance (default 10,000)
   - Click "백테스트 시작"

2. **Backend Fetches Historical Data**:
   - POST `/backtest/start` with `{strategy_id, start_date, end_date, initial_balance}`
   - Backend gets strategy from database
   - Extracts symbol and timeframe from strategy.params
   - Converts symbol: "BTC/USDT" → "BTCUSDT"
   - Calls Bitget API: `get_historical_candles()`
   - Saves candles to CSV file in `backtest_data/` directory

3. **Backtest Execution**:
   - Background task runs strategy against historical candles
   - Records each trade (entry, exit, PnL)
   - Calculates equity curve
   - Saves to `backtest_results` and `backtest_trades` tables
   - Updates status: "queued" → "running" → "completed"

4. **Result Display**:
   - Frontend polls `/backtest/result/{id}` every 1 second
   - When status = "completed", shows results
   - Displays equity curve chart
   - Shows trade list with cumulative PnL

**Available Historical Periods**:

| Timeframe | Candles per Request | Period Covered | Example Use Case |
|-----------|---------------------|----------------|------------------|
| 1m | 200 | ~3.3 hours | High-frequency strategies |
| 5m | 200 | ~16.7 hours | Intraday trading |
| 15m | 200 | ~50 hours (~2 days) | Short-term strategies |
| 30m | 200 | ~100 hours (~4 days) | Day trading |
| **1h** | 200 | ~8.3 days | **Most common** |
| 4h | 200 | ~33 days (~1 month) | Swing trading |
| 1D | 200 | ~200 days (~6.5 months) | Long-term strategies |

**Current Limitation**:
- Single request = 200 candles maximum
- For longer periods, need to chain multiple requests
- **Recommendation**: Start with 1-month backtests (1h or 4h timeframe)

**Extension for Longer Periods**:
```python
# Future enhancement: Chain multiple requests
async def get_historical_candles_extended(symbol, interval, start_date, end_date):
    all_candles = []
    current_end = end_date

    while len(all_candles) < desired_count:
        batch = await bitget_client.get_historical_candles(
            symbol=symbol,
            interval=interval,
            start_time=start_date,
            end_time=current_end,
            limit=200
        )
        all_candles = batch + all_candles

        # Update current_end to oldest candle timestamp
        current_end = batch[0]['timestamp'] - 1

        if len(batch) < 200:
            break  # No more data available

    return all_candles
```

**Critical Issue**: Metrics Not Calculated 🔴

**Problem**:
- Backtest completes successfully
- `final_balance` is correct
- BUT `metrics` field is empty: `{}`
- Summary shows "null" for all performance stats

**Why Critical**:
Users can't evaluate strategy performance without metrics. They need to see:
- Total return %
- Win rate %
- Profit factor
- Sharpe ratio
- Maximum drawdown %

**Solution**:

File: [backtest.py:80-180](backend/src/api/backtest.py#L80-L180)

Add metrics calculation in `_run_backtest_background()` function after backtest completes:

```python
def _run_backtest_background(result_id, user_id, request_dict, session_factory):
    """백테스트 백그라운드 태스크 실행"""

    # ... existing code: fetch data, run backtest ...

    # After backtest completes successfully:
    try:
        # Calculate performance metrics
        initial_balance = float(request_dict['initial_balance'])
        final_balance = float(result.final_balance)

        # Total return
        total_return = ((final_balance - initial_balance) / initial_balance) * 100

        # Trade statistics
        total_trades = len(all_trades)
        if total_trades > 0:
            winning_trades = [t for t in all_trades if t['pnl'] > 0]
            losing_trades = [t for t in all_trades if t['pnl'] < 0]

            win_count = len(winning_trades)
            loss_count = len(losing_trades)
            win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0

            # Profit factor
            gross_profit = sum(t['pnl'] for t in winning_trades)
            gross_loss = abs(sum(t['pnl'] for t in losing_trades))
            profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0

            # Average win/loss
            avg_win = (gross_profit / win_count) if win_count > 0 else 0
            avg_loss = (gross_loss / loss_count) if loss_count > 0 else 0
        else:
            win_rate = 0
            profit_factor = 0
            avg_win = 0
            avg_loss = 0

        # Maximum drawdown
        equity_curve = json.loads(result.equity_curve) if result.equity_curve else []
        max_dd = 0
        peak = equity_curve[0] if equity_curve else initial_balance

        for balance in equity_curve:
            if balance > peak:
                peak = balance
            drawdown = ((peak - balance) / peak * 100) if peak > 0 else 0
            if drawdown > max_dd:
                max_dd = drawdown

        # Sharpe ratio (simplified - assumes 0% risk-free rate)
        if len(equity_curve) > 1:
            returns = []
            for i in range(1, len(equity_curve)):
                ret = (equity_curve[i] - equity_curve[i-1]) / equity_curve[i-1]
                returns.append(ret)

            import numpy as np
            mean_return = np.mean(returns)
            std_return = np.std(returns)
            sharpe_ratio = (mean_return / std_return * np.sqrt(252)) if std_return > 0 else 0
        else:
            sharpe_ratio = 0

        # Compile metrics
        metrics = {
            "total_return": round(total_return, 2),
            "total_trades": total_trades,
            "win_rate": round(win_rate, 2),
            "profit_factor": round(profit_factor, 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "sharpe_ratio": round(sharpe_ratio, 2),
            "max_drawdown": round(max_dd, 2)
        }

        # Save metrics to database
        result.metrics = json.dumps(metrics)
        session.commit()

        logger.info(f"✅ Backtest metrics calculated for result {result_id}: {metrics}")

    except Exception as e:
        logger.error(f"❌ Failed to calculate metrics for result {result_id}: {e}")
        # Metrics calculation failed, but backtest result is still valid
```

**Testing**:
1. Run backtest with RSI strategy
2. Wait for completion
3. Check result - should show:
   - Total Return: 8.57%
   - Total Trades: 2
   - Win Rate: 50%
   - Profit Factor: X.XX
   - Sharpe Ratio: X.XX
   - Max Drawdown: X.XX%

**Estimated Time**: 1 hour

**Dependencies**:
```bash
pip3 install numpy  # For Sharpe ratio calculation
```

---

## 📊 Implementation Priority Order

| Order | Task | Priority | Time | Blocker |
|-------|------|----------|------|---------|
| 1 | Force close positions on bot stop | 🔴🔴🔴 | 1.5h | **Critical - Financial risk** |
| 2 | Load historical candles for live trading | 🔴🔴🔴 | 2h | **Critical - Accuracy** |
| 3 | Calculate backtest metrics | 🔴🔴 | 1h | **High - User cannot evaluate strategies** |
| 4 | Switch to real Bitget WebSocket | 🟡 | 0.5h | **After #1 & #2** |
| 5 | Strategy deletion feature | 🟢 | 0.3h | Optional enhancement |
| 6 | Strategy editing feature | 🟢 | 0.5h | Optional enhancement |

**Total Critical Path Time**: ~5 hours

---

## ✅ Testing Checklist (After Implementation)

### Automated Trading
- [ ] Start bot with strategy
- [ ] Verify 100 historical candles loaded
- [ ] Verify bot receives real-time Bitget data (not mock)
- [ ] Verify strategy generates accurate signals
- [ ] Verify orders placed on Bitget
- [ ] Verify trades recorded in database
- [ ] **Stop bot**
- [ ] **Verify ALL positions are closed automatically** ⚠️
- [ ] Verify bot status changes to STOPPED

### Strategy Management
- [x] Create new strategy
- [x] Strategy appears in Bot Control dropdown
- [x] Strategy appears in Backtest dropdown
- [x] Inactive strategy hidden
- [x] Only user's own strategies visible
- [ ] Delete strategy (if implemented)
- [ ] Edit strategy (if implemented)

### Backtesting
- [x] Select strategy
- [x] Pick date range
- [x] Submit backtest
- [x] Auto-fetch historical data from Bitget
- [x] View results with equity curve
- [x] View trade list
- [ ] **See performance metrics (not null)** ⚠️

---

## 📝 Notes for Implementation

### Important Considerations

1. **User Data Isolation** - CRITICAL for security:
   - Always filter by `user_id` in database queries
   - Never show other users' strategies, trades, or balances
   - Validate user_id from JWT token

2. **Error Handling**:
   - Gracefully handle Bitget API errors
   - Don't crash bot if one trade fails
   - Log all errors for debugging
   - Show user-friendly messages in frontend

3. **Position Management**:
   - Always check position exists before closing
   - Handle both long and short positions
   - Use `reduce_only=True` for closing orders
   - Verify position is fully closed (check remaining size)

4. **Performance**:
   - Backtest with 200 candles is fast (<5 seconds)
   - Loading 100 candles on bot start takes ~2 seconds
   - Real-time WebSocket data has minimal latency

5. **Testing Approach**:
   - Use small amounts for live trading tests
   - Always test with mock data first
   - Verify positions on Bitget website
   - Check database records match actual trades

---

## 🎯 Success Criteria

**System is production-ready when**:

✅ **Feature 1: Auto Trading**
- [x] Bot starts successfully
- [ ] Bot loads 100 historical candles
- [ ] Bot receives real Bitget market data
- [ ] Strategies generate accurate signals
- [ ] Orders execute on Bitget
- [ ] **Positions auto-close when bot stops** ⚠️

✅ **Feature 2: Strategy Management**
- [x] Users can create custom strategies
- [x] Strategies appear in all dropdowns
- [x] Strategies correctly linked to bot
- [x] Only active strategies shown
- [x] User data isolation works

✅ **Feature 3: Backtesting**
- [x] Users can backtest any strategy
- [x] Historical data auto-fetched
- [x] Results displayed accurately
- [ ] **Performance metrics calculated** ⚠️
- [x] Trade history available

---

**Next Steps**: Implement in priority order (1 → 4)

**Total Estimated Time to Production**: ~5 hours

**Last Updated**: 2025-12-03
**Document Owner**: Development Team
**Review**: Required before production deployment

---
