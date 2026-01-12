# Design Document: Week 1 High Priority Tasks

## Overview

This document describes the design for Week 1 high-priority infrastructure improvements in the AI Trading Platform. The implementation focuses on four key areas: upload quota management, distributed rate limiting, test reliability, and documentation completeness. These improvements are essential for production stability and scalability.

## Architecture

The improvements involve modifications to the middleware layer, utility modules, and test infrastructure:

```
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Application                      │
├─────────────────────────────────────────────────────────────┤
│  Middleware Layer                                            │
│  ┌─────────────────────┐  ┌─────────────────────┐           │
│  │ RateLimitMiddleware │  │ UploadMiddleware    │           │
│  │ (Redis-based)       │  │                     │           │
│  │ ┌─────────────────┐ │  │ ┌─────────────────┐ │           │
│  │ │ DistributedRate │ │  │ │ UploadQuota     │ │           │
│  │ │ Limiter         │ │  │ │ Manager         │ │           │
│  │ └─────────────────┘ │  │ └─────────────────┘ │           │
│  └─────────────────────┘  └─────────────────────┘           │
├─────────────────────────────────────────────────────────────┤
│  Utils Layer                                                 │
│  ┌─────────────────────┐  ┌─────────────────────┐           │
│  │ file_validators.py  │  │ redis_client.py     │           │
│  │ + UploadQuotaManager│  │ (new)               │           │
│  └─────────────────────┘  └─────────────────────┘           │
├─────────────────────────────────────────────────────────────┤
│  Database Layer                                              │
│  ┌─────────────────────┐                                    │
│  │ UserFile model      │                                    │
│  │ (tracking uploads)  │                                    │
│  └─────────────────────┘                                    │
└─────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### Component 1: Upload Quota Manager

**Location**: `backend/src/utils/file_validators.py`

**Interface**:
```python
class UploadQuotaManager:
    """Manage upload quotas and storage limits"""
    
    MAX_PER_USER_MB: int = 100  # 100MB per user
    MAX_TOTAL_STORAGE_GB: int = 100  # 100GB total
    MAX_FILES_PER_USER: int = 50
    
    async def check_user_quota(
        self, 
        user_id: int, 
        file_size_bytes: int, 
        db: AsyncSession
    ) -> tuple[bool, str]:
        """
        Check if user has quota for new file.
        
        Args:
            user_id: The user's ID
            file_size_bytes: Size of the file to upload
            db: Database session
            
        Returns:
            Tuple of (allowed: bool, message: str)
        """
    
    async def check_global_quota(
        self, 
        file_size_bytes: int, 
        db: AsyncSession
    ) -> tuple[bool, str]:
        """
        Check total system storage quota.
        
        Args:
            file_size_bytes: Size of the file to upload
            db: Database session
            
        Returns:
            Tuple of (allowed: bool, message: str)
        """
    
    async def get_user_usage(
        self, 
        user_id: int, 
        db: AsyncSession
    ) -> dict:
        """
        Get user's current storage usage statistics.
        
        Returns:
            Dict with used_bytes, file_count, quota_bytes, quota_files
        """
```

### Component 2: Distributed Rate Limiter

**Location**: `backend/src/middleware/rate_limit.py`

**Interface**:
```python
class DistributedRateLimiter:
    """Redis-based rate limiting for distributed deployments"""
    
    def __init__(self, redis_url: str):
        """
        Initialize with Redis connection.
        
        Args:
            redis_url: Redis connection URL
        """
    
    async def is_rate_limited(
        self, 
        key: str, 
        limit: int, 
        period: int
    ) -> tuple[bool, int]:
        """
        Check if request is rate limited using Redis.
        
        Args:
            key: Rate limit key (user_id or IP)
            limit: Maximum requests allowed
            period: Time window in seconds
            
        Returns:
            Tuple of (is_limited: bool, retry_after: int)
        """
    
    async def get_remaining(
        self, 
        key: str, 
        limit: int
    ) -> int:
        """
        Get remaining requests for a key.
        
        Args:
            key: Rate limit key
            limit: Maximum requests allowed
            
        Returns:
            Number of remaining requests
        """
```

**Redis Key Structure**:
- Pattern: `rate_limit:{key_type}:{identifier}:{endpoint_category}`
- Example: `rate_limit:user:123:backtest`
- TTL: Set to the rate limit period

**Fallback Behavior**:
When Redis is unavailable, the system falls back to in-memory rate limiting with a warning log.

### Component 3: Test Fixtures and Mocks

**Location**: `backend/tests/conftest.py`

The test failures are primarily caused by:
1. Missing or incorrect async fixtures
2. Mock configuration errors for database sessions
3. Missing test database setup

**Key Fixes**:
```python
@pytest.fixture
async def async_session():
    """Properly configured async database session for tests"""
    
@pytest.fixture
def mock_monitoring():
    """Properly mocked monitoring service"""
```

## Data Models

### UserFile Model (New)

```python
class UserFile(Base):
    """Track user file uploads for quota management"""
    __tablename__ = "user_files"
    
    id: int  # Primary key
    user_id: int  # Foreign key to users
    filename: str  # Original filename
    file_size_bytes: int  # File size in bytes
    file_path: str  # Storage path
    mime_type: str  # MIME type
    created_at: datetime  # Upload timestamp
    
    # Indexes
    __table_args__ = (
        Index('idx_user_files_user_id', 'user_id'),
    )
```

### Rate Limit Configuration

```python
RATE_LIMIT_CONFIG = {
    "default": {"limit": 60, "period": 60},  # 60 req/min
    "backtest": {"limit": 5, "period": 60},  # 5 req/min
    "api_key": {"limit": 3, "period": 3600},  # 3 req/hour
    "anonymous": {"limit": 30, "period": 60},  # 30 req/min
}
```


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: User Storage Quota Enforcement

*For any* user with current storage usage U bytes and any file of size F bytes, the Upload_Quota_Manager SHALL allow the upload if and only if (U + F) ≤ 100MB, and SHALL reject with a descriptive message otherwise.

**Validates: Requirements 1.1, 1.2**

### Property 2: User File Count Enforcement

*For any* user with current file count C and any upload attempt, the Upload_Quota_Manager SHALL allow the upload if and only if C < 50, and SHALL reject with a descriptive message otherwise.

**Validates: Requirements 1.3, 1.4**

### Property 3: Global Storage Quota Enforcement

*For any* global storage usage G bytes and any file of size F bytes, the Upload_Quota_Manager SHALL allow the upload if and only if (G + F) ≤ 100GB, and SHALL reject with a descriptive message otherwise.

**Validates: Requirements 1.5, 1.6**

### Property 4: Usage Statistics Accuracy

*For any* user with known file uploads, the Upload_Quota_Manager SHALL return usage statistics where used_bytes equals the sum of all file sizes and file_count equals the number of files.

**Validates: Requirements 1.7**

### Property 5: Rate Limit Request Counting

*For any* sequence of N requests with the same rate limit key within the time window, the Distributed_Rate_Limiter SHALL track exactly N requests in Redis.

**Validates: Requirements 2.1**

### Property 6: Rate Limit Enforcement with Retry-After

*For any* rate limit key with limit L and period P, when request count exceeds L within P seconds, the Distributed_Rate_Limiter SHALL return a 429 status with retry-after time ≤ P seconds.

**Validates: Requirements 2.3, 2.4**

### Property 7: Endpoint-Specific Rate Limits

*For any* two different endpoint categories with different configured limits, the Distributed_Rate_Limiter SHALL enforce the respective limits independently.

**Validates: Requirements 2.6**

## Error Handling

### Upload Quota Errors

When quota is exceeded, return HTTP 413 with descriptive message:
```python
raise HTTPException(
    status_code=413,
    detail=f"Upload quota exceeded. Used: {used_mb:.1f}MB, Limit: {limit_mb}MB"
)
```

### Rate Limit Errors

When rate limited, return HTTP 429 with retry-after header:
```python
raise HTTPException(
    status_code=429,
    detail=f"Rate limit exceeded. Retry in {retry_after} seconds.",
    headers={"Retry-After": str(retry_after)}
)
```

### Redis Connection Errors

When Redis is unavailable, log warning and fall back to in-memory:
```python
try:
    return await self._redis_check(key, limit, period)
except RedisConnectionError:
    logger.warning("Redis unavailable, falling back to in-memory rate limiting")
    return self._memory_check(key, limit, period)
```

## Testing Strategy

### Unit Tests

Unit tests will verify specific examples and edge cases:

1. **Upload Quota Tests**:
   - Test user at exactly 100MB limit
   - Test user with 0 files
   - Test user with exactly 50 files
   - Test global quota at boundary

2. **Rate Limiter Tests**:
   - Test first request sets TTL
   - Test Redis fallback when connection fails
   - Test different endpoint categories

3. **Test Infrastructure Fixes**:
   - Fix async fixture configuration
   - Fix mock database session setup
   - Fix monitoring service mocks

### Property-Based Tests

Property-based tests will use **Hypothesis** library to verify universal properties:

**Configuration**:
- Minimum 100 iterations per property test
- Tag format: **Feature: week1-high-priority, Property {number}: {property_text}**

**Property Tests**:

1. **Property 1 Test**: Generate random user storage states (0-150MB) and file sizes (1KB-50MB), verify quota enforcement
2. **Property 2 Test**: Generate random file counts (0-60) and verify file count enforcement
3. **Property 3 Test**: Generate random global storage states and verify global quota enforcement
4. **Property 4 Test**: Generate random file upload histories and verify statistics accuracy
5. **Property 5 Test**: Generate random request sequences and verify Redis count accuracy
6. **Property 6 Test**: Generate request sequences exceeding limits and verify 429 response with retry-after
7. **Property 7 Test**: Generate requests to different endpoint categories and verify independent limits

### Integration Tests

1. **End-to-End Upload Test**: Upload files until quota exceeded, verify rejection
2. **Distributed Rate Limit Test**: Simulate multiple server instances sharing Redis
3. **Fallback Test**: Disconnect Redis and verify in-memory fallback works
