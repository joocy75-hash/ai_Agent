# Requirements Document

## Introduction

This document defines the requirements for critical security fixes in the AI Trading Platform backend. These fixes address vulnerabilities identified in the security audit, including JWT token logging exposure, duplicate security implementations, and inadequate rate limiting.

## Glossary

- **JWT**: JSON Web Token - A compact, URL-safe means of representing claims to be transferred between two parties
- **Rate_Limiter**: A middleware component that restricts the number of requests a user can make within a time window
- **Request_Context_Middleware**: Middleware that logs request information and manages request context
- **Security_Module**: The module responsible for JWT token creation, validation, and password hashing
- **Sanitizer**: A function that removes or masks sensitive information from data before logging

## Requirements

### Requirement 1: JWT Token Logging Vulnerability Fix

**User Story:** As a security administrator, I want to ensure JWT tokens are never logged in plain text, so that authentication credentials cannot be exposed through log files.

#### Acceptance Criteria

1. WHEN the Request_Context_Middleware logs request headers, THE Sanitizer SHALL mask the Authorization header value with '[MASKED]'
2. WHEN the Request_Context_Middleware logs request headers, THE Sanitizer SHALL mask the Cookie header value with '[MASKED]'
3. WHEN the Request_Context_Middleware logs request headers, THE Sanitizer SHALL mask the X-API-Key header value with '[MASKED]'
4. WHEN the Request_Context_Middleware logs request headers, THE Sanitizer SHALL mask the X-Auth-Token header value with '[MASKED]'
5. THE Sanitizer SHALL perform case-insensitive matching on header names
6. WHEN a header is not in the sensitive headers list, THE Sanitizer SHALL preserve the original header value

### Requirement 2: Duplicate JWT Implementation Removal

**User Story:** As a developer, I want a single source of truth for JWT operations, so that security implementations are consistent and maintainable.

#### Acceptance Criteria

1. THE Security_Module at `backend/src/utils/security.py` SHALL be removed from the codebase
2. WHEN any module imports JWT functions from security.py, THE import SHALL be changed to use jwt_auth.py
3. WHEN the security.py file is removed, THE system SHALL continue to function without import errors
4. THE jwt_auth.py module SHALL be the single source of truth for all JWT operations

### Requirement 3: User-Based Rate Limiting Enhancement

**User Story:** As a system administrator, I want rate limiting to be based on authenticated user identity, so that rate limits are accurately applied per user rather than per IP address.

#### Acceptance Criteria

1. WHEN a request contains a valid JWT token, THE Rate_Limiter SHALL extract the user ID from the token payload
2. WHEN a request contains a valid JWT token, THE Rate_Limiter SHALL use the format "user_{user_id}" as the rate limit key
3. WHEN a request does not contain a valid JWT token, THE Rate_Limiter SHALL use the format "anon_{client_ip}" as the rate limit key
4. IF the JWT token is invalid or expired, THEN THE Rate_Limiter SHALL log a warning and fall back to IP-based limiting
5. THE Rate_Limiter SHALL import the verify_access_token function from jwt_auth.py

### Requirement 4: Code Quality Auto-Fixes

**User Story:** As a developer, I want automated code quality fixes applied, so that the codebase follows consistent coding standards.

#### Acceptance Criteria

1. WHEN Ruff auto-fix is executed, THE system SHALL fix all auto-fixable linting issues
2. WHEN bare except clauses exist, THE system SHALL replace them with specific exception types
3. WHEN unused variables exist, THE system SHALL remove or prefix them with underscore
4. WHEN unused imports exist, THE system SHALL remove them from the codebase
