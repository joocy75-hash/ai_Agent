# Implementation Plan: Security Fixes

## Overview

This implementation plan addresses critical security vulnerabilities in the AI Trading Platform backend. Tasks are ordered to minimize risk: starting with the most isolated changes (header sanitization), then import migration, and finally rate limiting enhancement.

## Tasks

- [x] 1. Implement Header Sanitizer
  - [x] 1.1 Add `_sanitize_headers` method to RequestContextMiddleware
    - Create method that masks sensitive headers (authorization, cookie, x-api-key, x-auth-token)
    - Implement case-insensitive header name matching
    - Return sanitized dictionary with '[MASKED]' for sensitive values
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6_

  - [ ]* 1.2 Write property test for header sanitization
    - **Property 1: Sensitive Header Masking**
    - **Property 2: Non-Sensitive Header Preservation**
    - **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6**

  - [x] 1.3 Update middleware to use sanitizer in logging
    - Modify any logging statements that output headers to use `_sanitize_headers`
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [x] 2. Remove Duplicate JWT Implementation
  - [x] 2.1 Update test file imports
    - Change `from src.utils.security import hash_password` to use jwt_auth.py
    - File: `backend/tests/unit/test_auth_api.py`
    - _Requirements: 2.2_

  - [x] 2.2 Delete security.py file
    - Remove `backend/src/utils/security.py`
    - _Requirements: 2.1_

  - [x] 2.3 Verify system startup
    - Run the application to ensure no import errors
    - Run existing tests to verify functionality
    - _Requirements: 2.3, 2.4_

- [x] 3. Checkpoint - Verify header sanitization and JWT consolidation
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Enhance Rate Limiting with User ID
  - [x] 4.1 Update RateLimitMiddleware to extract user ID from JWT
    - Import verify_access_token from jwt_auth.py
    - Implement user ID extraction with fallback to IP
    - Use format "user_{user_id}" for authenticated requests
    - Use format "anon_{client_ip}" for anonymous requests
    - Log warning on invalid JWT tokens
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [ ]* 4.2 Write property test for rate limit key generation
    - **Property 3: Authenticated User Rate Limit Key Format**
    - **Property 4: Anonymous User Rate Limit Key Format**
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.4**

- [x] 5. Apply Code Quality Auto-Fixes
  - [x] 5.1 Run Ruff auto-fix
    - Execute `ruff check --fix backend/src/`
    - Review and commit changes
    - _Requirements: 4.1_

  - [x] 5.2 Fix remaining bare except clauses manually
    - Search for `except:` without exception type
    - Replace with specific exception types (Exception, ValueError, etc.)
    - _Requirements: 4.2_

  - [x] 5.3 Clean up unused variables and imports
    - Run `ruff check backend/src/ --select F401,F841`
    - Fix any remaining issues
    - _Requirements: 4.3, 4.4_

- [x] 6. Final Checkpoint - Run all tests
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Update MASTER_WORK_PLAN.md
  - [x] 7.1 Mark Day 1 security tasks as complete
    - Update checkboxes in the master work plan
    - Update progress tracking table
    - _Requirements: Documentation_

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
