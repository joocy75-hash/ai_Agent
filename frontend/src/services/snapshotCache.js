/**
 * Dashboard Snapshot Cache
 * localStorage-based caching for dashboard data
 *
 * Cache Strategy:
 * - Always display cached data if available (instant load)
 * - Check staleness (24h TTL) to determine if background refresh needed
 * - Invalidate on version mismatch or userId change
 */

const CACHE_KEY = 'dashboard_snapshot';
const CACHE_VERSION = 1;
const CACHE_TTL = 24 * 60 * 60 * 1000; // 24 hours in milliseconds

/**
 * Snapshot structure:
 * {
 *   version: number,
 *   updatedAt: number (timestamp),
 *   userId: string,
 *   tradeStats: {
 *     totalTrades: number,
 *     winRate: number,
 *     winningTrades: number,
 *     losingTrades: number,
 *     avgPnl: number,
 *     totalReturn: number,
 *     bestTrade: number,
 *     worstTrade: number,
 *     longCount: number,
 *     shortCount: number
 *   },
 *   periodProfits: {
 *     daily: { return: number, pnl: number },
 *     weekly: { return: number, pnl: number },
 *     monthly: { return: number, pnl: number },
 *     allTime: { return: number, pnl: number }
 *   },
 *   botStatus: {
 *     isRunning: boolean,
 *     strategy: string,
 *     lastUpdated: number
 *   },
 *   recentTrades: array (last 10 trades)
 * }
 */

const snapshotCache = {
  /**
   * Retrieve cached snapshot
   * @returns {Object|null} Cached snapshot or null if not found/invalid
   */
  get() {
    try {
      const cached = localStorage.getItem(CACHE_KEY);
      if (!cached) {
        return null;
      }

      const snapshot = JSON.parse(cached);

      // Version mismatch check
      if (snapshot.version !== CACHE_VERSION) {
        console.log('[SnapshotCache] Version mismatch, clearing cache');
        this.clear();
        return null;
      }

      // UserId check (validate against current user)
      const currentUserId = localStorage.getItem('userId');
      if (currentUserId && snapshot.userId !== currentUserId) {
        console.log('[SnapshotCache] UserId mismatch, clearing cache');
        this.clear();
        return null;
      }

      console.log('[SnapshotCache] Cache hit', {
        age: Date.now() - snapshot.updatedAt,
        stale: this.isStale()
      });

      return snapshot;
    } catch (error) {
      console.error('[SnapshotCache] Error reading cache:', error);
      this.clear();
      return null;
    }
  },

  /**
   * Save snapshot to cache
   * @param {Object} snapshot - Dashboard snapshot data
   */
  set(snapshot) {
    try {
      const currentUserId = localStorage.getItem('userId');

      const cacheData = {
        version: CACHE_VERSION,
        updatedAt: Date.now(),
        userId: currentUserId || 'unknown',
        tradeStats: snapshot.tradeStats || {},
        periodProfits: snapshot.periodProfits || {},
        botStatus: snapshot.botStatus || {},
        recentTrades: snapshot.recentTrades || []
      };

      localStorage.setItem(CACHE_KEY, JSON.stringify(cacheData));
      console.log('[SnapshotCache] Cache updated', {
        userId: cacheData.userId,
        timestamp: new Date(cacheData.updatedAt).toISOString()
      });
    } catch (error) {
      console.error('[SnapshotCache] Error writing cache:', error);
      // If quota exceeded, clear cache and retry once
      if (error.name === 'QuotaExceededError') {
        this.clear();
        try {
          localStorage.setItem(CACHE_KEY, JSON.stringify({
            version: CACHE_VERSION,
            updatedAt: Date.now(),
            userId: localStorage.getItem('userId') || 'unknown',
            ...snapshot
          }));
        } catch (retryError) {
          console.error('[SnapshotCache] Retry failed:', retryError);
        }
      }
    }
  },

  /**
   * Remove cache
   */
  clear() {
    try {
      localStorage.removeItem(CACHE_KEY);
      console.log('[SnapshotCache] Cache cleared');
    } catch (error) {
      console.error('[SnapshotCache] Error clearing cache:', error);
    }
  },

  /**
   * Check if cache is stale (older than TTL)
   * @returns {boolean} True if cache is stale or doesn't exist
   */
  isStale() {
    try {
      const cached = localStorage.getItem(CACHE_KEY);
      if (!cached) {
        return true;
      }

      const snapshot = JSON.parse(cached);
      const age = Date.now() - snapshot.updatedAt;

      return age > CACHE_TTL;
    } catch (error) {
      console.error('[SnapshotCache] Error checking staleness:', error);
      return true;
    }
  },

  /**
   * Check if cache exists
   * @returns {boolean} True if valid cache exists
   */
  exists() {
    try {
      const cached = localStorage.getItem(CACHE_KEY);
      if (!cached) {
        return false;
      }

      const snapshot = JSON.parse(cached);

      // Must have valid version
      if (snapshot.version !== CACHE_VERSION) {
        return false;
      }

      // Must match current userId
      const currentUserId = localStorage.getItem('userId');
      if (currentUserId && snapshot.userId !== currentUserId) {
        return false;
      }

      return true;
    } catch (error) {
      console.error('[SnapshotCache] Error checking existence:', error);
      return false;
    }
  },

  /**
   * Get cache age in milliseconds
   * @returns {number|null} Age in ms or null if no cache
   */
  getAge() {
    try {
      const cached = localStorage.getItem(CACHE_KEY);
      if (!cached) {
        return null;
      }

      const snapshot = JSON.parse(cached);
      return Date.now() - snapshot.updatedAt;
    } catch (error) {
      console.error('[SnapshotCache] Error getting age:', error);
      return null;
    }
  },

  /**
   * Get cache info for debugging
   * @returns {Object|null} Cache metadata
   */
  getInfo() {
    try {
      const cached = localStorage.getItem(CACHE_KEY);
      if (!cached) {
        return null;
      }

      const snapshot = JSON.parse(cached);
      const age = Date.now() - snapshot.updatedAt;

      return {
        version: snapshot.version,
        userId: snapshot.userId,
        updatedAt: new Date(snapshot.updatedAt).toISOString(),
        age: age,
        ageMinutes: Math.floor(age / 60000),
        stale: age > CACHE_TTL,
        size: new Blob([cached]).size
      };
    } catch (error) {
      console.error('[SnapshotCache] Error getting info:', error);
      return null;
    }
  }
};

export default snapshotCache;
