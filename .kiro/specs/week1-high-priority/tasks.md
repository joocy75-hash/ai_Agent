# Implementation Plan: Week 1 High Priority Tasks

## Overview

This implementation plan addresses critical infrastructure improvements for the AI Trading Platform. Tasks are ordered to minimize risk: starting with database model changes, then utility classes, middleware updates, test fixes, and finally documentation.

## Tasks

- [x] 1. Create UserFile Database Model
  - [x] 1.1 Add UserFile model to database/models.py
    - Create UserFile class with id, user_id, filename, file_size_bytes, file_path, mime_type, created_at
    - Add foreign key relationship to User model
    - Add index on user_id for efficient queries
    - _Requirements: 1.1, 1.7_

  - [x] 1.2 Create Alembic migration for UserFile table
    - Generate migration file
    - Test migration up and down
    - _Requirements: 1.1_

- [x] 2. Implement Upload Quota Manager
  - [x] 2.1 Create UploadQuotaManager class in file_validators.py
    - Define constants: MAX_PER_USER_MB=100, MAX_FILES_PER_USER=50, MAX_TOTAL_STORAGE_GB=100
    - Implement check_user_quota method
    - Implement check_global_quota method
    - Implement get_user_usage method
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7_

  - [ ]* 2.2 Write property tests for upload quota
    - **Property 1: User Storage Quota Enforcement**
    - **Property 2: User File Count Enforcement**
    - **Property 3: Global Storage Quota Enforcement**
    - **Property 4: Usage Statistics Accuracy**
    - **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7**

  - [x] 2.3 Integrate quota checks into upload API endpoint
    - Modify backend/src/api/upload.py to use UploadQuotaManager
    - Add quota check before file save
    - Return 413 status on quota exceeded
    - _Requirements: 1.2, 1.4, 1.6_

- [x] 3. Checkpoint - Verify upload quota implementation
  - All quota management code implemented
  - Database model and migration created
  - Upload API integrated with quota checks

- [x] 4. Implement Distributed Rate Limiter
  - [x] 4.1 Create Redis client utility
    - Create backend/src/utils/redis_client.py
    - Implement async Redis connection with connection pooling
    - Add connection health check method
    - _Requirements: 2.1_

  - [x] 4.2 Create DistributedRateLimiter class
    - Add to backend/src/middleware/rate_limit.py
    - Implement is_rate_limited method using Redis INCR and EXPIRE
    - Implement get_remaining method
    - Add fallback to in-memory when Redis unavailable
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [ ]* 4.3 Write property tests for rate limiting
    - **Property 5: Rate Limit Request Counting**
    - **Property 6: Rate Limit Enforcement with Retry-After**
    - **Property 7: Endpoint-Specific Rate Limits**
    - **Validates: Requirements 2.1, 2.3, 2.4, 2.6**

  - [x] 4.4 Update RateLimitMiddleware to use DistributedRateLimiter
    - Modify dispatch method to use Redis-based limiter
    - Add retry-after header to 429 responses
    - Configure endpoint-specific limits
    - _Requirements: 2.3, 2.4, 2.6_

- [x] 5. Checkpoint - Verify rate limiting implementation
  - DistributedRateLimiter with Redis support implemented
  - In-memory fallback working
  - All rate limit tests passing (9/9)

- [-] 6. Fix Test Suite Failures
  - [x] 6.1 Fix test_monitoring.py failures
    - Update monitoring service mock configuration
    - Fix AttributeError issues with SimpleMonitor
    - _Requirements: 3.1, 3.2_

  - [x] 6.2 Fix test_rate_limit.py failures
    - Update rate limit tests for new Redis-based implementation
    - Add mock Redis for unit tests
    - _Requirements: 3.1_

  - [ ] 6.3 Fix test_integration.py failures
    - Fix async fixture configuration in conftest.py
    - Update database session mocks
    - Fix authentication flow tests
    - _Requirements: 3.2_

  - [ ] 6.4 Fix test_backtest_engine.py failures
    - Fix coroutine handling issues
    - Update async test patterns
    - _Requirements: 3.2_

  - [ ] 6.5 Fix test_auth_api.py and test_annotations_api.py errors
    - Fix database session configuration
    - Update mock setups
    - _Requirements: 3.1_

  - [x] 6.6 Verify 80% pass rate achieved
    - Run full test suite
    - Document remaining failures if any
    - Current: 267 passed, 25 failed, 24 errors = 84.5% pass rate ✓
    - _Requirements: 3.3_

- [x] 7. Checkpoint - Verify test suite improvements
  - Test pass rate: 84.5% (267 passed, 25 failed, 24 errors)
  - Target 80% achieved ✓

- [-] 8. Documentation Improvements
  - [x] 8.1 Create troubleshooting guide
    - Create docs/TROUBLESHOOTING.md
    - Document common API error codes (400, 401, 403, 404, 413, 429, 500)
    - Document deployment issues and solutions
    - Document database connection issues
    - Document authentication issues
    - _Requirements: 5.1, 5.2, 5.3, 5.4_

  - [ ] 8.2 Add missing docstrings to API functions
    - Review and update backend/src/api/*.py files
    - Ensure all public functions have parameter and return documentation
    - _Requirements: 4.1, 4.2_

  - [ ] 8.3 Add missing docstrings to Agent classes
    - Review and update backend/src/agents/**/agent.py files
    - Ensure all Agent classes have purpose and usage documentation
    - _Requirements: 4.3_

- [ ] 9. Final Checkpoint - Run all tests and verify documentation
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 10. Update MASTER_WORK_PLAN.md
  - [ ] 10.1 Mark Week 1 tasks as complete
    - Update checkboxes in the master work plan
    - Update progress tracking table
    - _Requirements: Documentation_

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
