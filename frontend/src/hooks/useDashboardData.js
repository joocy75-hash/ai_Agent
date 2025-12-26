import { useState, useEffect } from 'react';
import snapshotCache from '../services/snapshotCache';
import { analyticsAPI } from '../api/analytics';
import { botAPI } from '../api/bot';
import { orderAPI } from '../api/order';

// Cache TTL: 30 seconds - skip background revalidation if cache is fresh
const CACHE_TTL = 30000;

/**
 * Custom hook implementing Stale-While-Revalidate pattern for dashboard data
 *
 * Key features:
 * - Instant cache reads on mount (synchronous, no loading state)
 * - Smart background revalidation (skip if cache is fresh, delay if cached)
 * - Graceful error handling (keep stale data on failure)
 * - hasData determines skeleton visibility, NOT isRefreshing
 */
export default function useDashboardData() {
  // Initialize state synchronously from cache
  const cachedData = snapshotCache.get();
  const cacheExists = snapshotCache.exists();

  const [tradeStats, setTradeStats] = useState(cachedData?.tradeStats || null);
  const [periodProfits, setPeriodProfits] = useState(cachedData?.periodProfits || null);
  const [botStatus, setBotStatus] = useState(cachedData?.botStatus || null);
  const [recentTrades, setRecentTrades] = useState(cachedData?.recentTrades || []);
  const [hasData, setHasData] = useState(cacheExists);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(cachedData?.timestamp || null);

  /**
   * Revalidate function - fetch fresh data and update cache
   */
  const revalidate = async () => {
    setIsRefreshing(true);

    try {
      // Call all APIs in parallel with graceful error handling
      const [summaryResult, statusResult, historyResult] = await Promise.all([
        analyticsAPI.getDashboardSummary().catch(() => null),
        botAPI.getStatus().catch(() => null),
        orderAPI.getOrderHistory(10).catch(() => null),
      ]);

      // Parse and update states - transform API response to Dashboard format
      let newTradeStats = tradeStats;
      let newPeriodProfits = periodProfits;
      if (summaryResult) {
        // Transform API response to tradeStats format (matches Dashboard.jsx)
        const perfAll = summaryResult.performance_all || {};
        const riskMetrics = summaryResult.risk_metrics || {};

        newTradeStats = {
          totalTrades: riskMetrics.total_trades || 0,
          winRate: riskMetrics.win_rate || 0,
          winningTrades: perfAll.winning_trades || 0,
          losingTrades: perfAll.losing_trades || 0,
          avgPnl: perfAll.total_pnl && perfAll.total_trades
            ? (perfAll.total_pnl / perfAll.total_trades).toFixed(2)
            : 0,
          totalReturn: perfAll.total_return || 0,
          bestTrade: perfAll.best_trade?.pnl_percent || 0,
          worstTrade: perfAll.worst_trade?.pnl_percent || 0,
          longCount: perfAll.total_trades || 0,
          shortCount: 0,
        };

        // Transform API response to periodProfits format
        const perfDaily = summaryResult.performance_daily || {};
        const perfWeekly = summaryResult.performance_weekly || {};
        const perfMonthly = summaryResult.performance_monthly || {};

        newPeriodProfits = {
          daily: { return: perfDaily.total_return || 0, pnl: perfDaily.total_pnl || 0 },
          weekly: { return: perfWeekly.total_return || 0, pnl: perfWeekly.total_pnl || 0 },
          monthly: { return: perfMonthly.total_return || 0, pnl: perfMonthly.total_pnl || 0 },
          allTime: { return: perfAll.total_return || 0, pnl: perfAll.total_pnl || 0 },
        };

        setTradeStats(newTradeStats);
        setPeriodProfits(newPeriodProfits);
      }

      let newBotStatus = botStatus;
      if (statusResult) {
        newBotStatus = statusResult;
        setBotStatus(newBotStatus);
      }

      let newRecentTrades = recentTrades;
      if (historyResult?.trades && Array.isArray(historyResult.trades)) {
        newRecentTrades = historyResult.trades;
        setRecentTrades(newRecentTrades);
      }

      // Save to cache
      const timestamp = new Date().toISOString();
      snapshotCache.set({
        tradeStats: newTradeStats,
        periodProfits: newPeriodProfits,
        botStatus: newBotStatus,
        recentTrades: newRecentTrades,
        timestamp,
      });

      setLastUpdated(timestamp);
      setHasData(true);
    } catch (error) {
      console.error('Error revalidating dashboard data:', error);
      // Keep existing data on error (no clearing)
    } finally {
      setIsRefreshing(false);
    }
  };

  // Revalidate on mount with smart caching strategy
  useEffect(() => {
    // Check cache age - skip revalidation if cache is fresh (< 30 seconds)
    const cacheAge = cachedData?.timestamp ? Date.now() - new Date(cachedData.timestamp).getTime() : Infinity;

    if (cacheExists && cacheAge < CACHE_TTL) {
      console.log('[useDashboardData] Fresh cache exists, skipping revalidation');
      return;
    }

    // If cache exists but stale, delay revalidation for smoother UX (show cache first)
    if (cacheExists) {
      const timer = setTimeout(() => {
        console.log('[useDashboardData] Stale cache detected, background revalidation started');
        revalidate();
      }, 500);
      return () => clearTimeout(timer);
    }

    // No cache - fetch immediately
    console.log('[useDashboardData] No cache, fetching data immediately');
    revalidate();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return {
    tradeStats,
    periodProfits,
    botStatus,
    recentTrades,
    hasData,
    isRefreshing,
    lastUpdated,
    revalidate,
  };
}
