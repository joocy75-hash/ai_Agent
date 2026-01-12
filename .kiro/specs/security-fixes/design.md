# Design Document: Security Fixes

## Overview

This document describes the design for critical security fixes in the AI Trading Platform backend. The fixes address three main vulnerabilities: JWT token logging exposure, duplicate security implementations, and inadequate rate limiting. The implementation follows a minimal-change approach to reduce risk while ensuring security compliance.

## Architecture

The security fixes involve modifications to three main components:

```
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Application                      │
├─────────────────────────────────────────────────────────────┤
│  Middleware Layer                                            │
│  ┌─────────────────────┐  ┌─────────────────────┐           │
│  │ RequestContext      │  │ RateLimitMiddleware │           │
│  │ Middleware          │  │                     │           │
│  │ ┌─────────────────┐ │  │ ┌─────────────────┐ │           │
│  │ │ _sanitize_      │ │  │ │ _get_user_id    │ │           │
│  │ │ headers()       │ │  │ │ _from_request() │ │           │
│  │ └─────────────────┘ │  │ └─────────────────┘ │           │
│  └─────────────────────┘  └─────────────────────┘           │
├─────────────────────────────────────────────────────────────┤
│  Utils Layer                                                 │
│  ┌─────────────────────┐  ┌─────────────────────┐           │
│  │ jwt_auth.py         │  │ security.py         │           │
│  │ (Primary)           │  │ (TO BE REMOVED)     │           │
│  │ - JWTAuth class     │  │ - hash_password     │           │
│  │ - verify_password   │  │ - verify_password   │           │
│  │ - get_password_hash │  │ - create_access_    │           │
│  │ - create_access_    │  │   token             │           │
│  │   token             │  │ - decode_token      │           │
│  │ - verify_token      │  └─────────────────────┘           │
│  └─────────────────────┘                                    │
└─────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### Component 1: Header Sanitizer

**Location**: `backend/src/middleware/request_context.py`

**Interface**:
```python
def _sanitize_headers(self, headers: dict) -> dict:
    """
    Remove sensitive information from headers before logging.
    
    Args:
        headers: Dictionary of HTTP headers
        
    Returns:
        Sanitized headers with sensitive values masked as '[MASKED]'
    """
```

**Sensitive Headers** (case-insensitive):
- `authorization`
- `cookie`
- `x-api-key`
- `x-auth-token`

### Component 2: Rate Limiter User ID Extractor

**Location**: `backend/src/middleware/rate_limit.py`

**Interface**:
```python
def get_user_id_from_request(self, request: Request) -> str:
    """
    Extract user ID from JWT token for accurate per-user rate limiting.
    
    Args:
        request: FastAPI Request object
        
    Returns:
        Rate limit key in format:
        - "user_{user_id}" for authenticated requests
        - "anon_{client_ip}" for anonymous requests
    """
```

### Component 3: JWT Auth Module (Consolidated)

**Location**: `backend/src/utils/jwt_auth.py`

The existing `jwt_auth.py` already contains all necessary JWT functionality. The `security.py` file will be removed, and any imports will be redirected to `jwt_auth.py`.

**Functions to migrate from security.py**:
- `hash_password` → Already exists as `JWTAuth.get_password_hash`
- `verify_password` → Already exists as `JWTAuth.verify_password`
- `create_access_token` → Already exists as `JWTAuth.create_access_token`
- `decode_token` → Already exists as `JWTAuth.decode_token`

## Data Models

No new data models are required. The existing data structures are sufficient:

```python
# Rate limit key format
rate_limit_key: str  # "user_{user_id}" or "anon_{client_ip}"

# Sanitized headers
sanitized_headers: dict[str, str]  # Header name -> value or '[MASKED]'
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Sensitive Header Masking

*For any* HTTP headers dictionary containing sensitive headers (authorization, cookie, x-api-key, x-auth-token), the sanitizer SHALL replace their values with '[MASKED]' regardless of the original value or header name casing.

**Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5**

### Property 2: Non-Sensitive Header Preservation

*For any* HTTP headers dictionary, headers that are not in the sensitive headers list SHALL be preserved with their original values unchanged.

**Validates: Requirements 1.6**

### Property 3: Authenticated User Rate Limit Key Format

*For any* request containing a valid JWT token with a user_id claim, the rate limiter SHALL return a key in the format "user_{user_id}" where user_id matches the token's user_id claim.

**Validates: Requirements 3.1, 3.2**

### Property 4: Anonymous User Rate Limit Key Format

*For any* request without a valid JWT token (missing, invalid, or expired), the rate limiter SHALL return a key in the format "anon_{client_ip}" where client_ip is the request's client IP address.

**Validates: Requirements 3.3, 3.4**

## Error Handling

### Header Sanitization Errors

The sanitizer should never raise exceptions. If the headers dictionary is malformed:
- Return an empty dictionary for None input
- Handle non-string keys/values gracefully

### Rate Limiting Errors

JWT token validation errors should be caught and logged:
```python
try:
    payload = verify_access_token(token)
    return f"user_{payload.get('sub')}"
except Exception:
    logger.warning(f"Invalid JWT token for rate limiting: {request.url.path}")
    return f"anon_{request.client.host}"
```

### Import Migration Errors

After removing `security.py`, any remaining imports will cause ImportError at startup. This is intentional to ensure all imports are properly migrated.

## Testing Strategy

### Unit Tests

Unit tests will verify specific examples and edge cases:

1. **Header Sanitizer Tests**:
   - Test each sensitive header individually
   - Test case variations (AUTHORIZATION, authorization, Authorization)
   - Test non-sensitive headers are preserved
   - Test empty headers dictionary
   - Test headers with None values

2. **Rate Limiter Tests**:
   - Test valid JWT token extraction
   - Test invalid JWT token fallback
   - Test missing token fallback
   - Test expired token fallback

3. **Import Migration Tests**:
   - Verify no imports from security.py exist
   - Verify jwt_auth.py exports all required functions

### Property-Based Tests

Property-based tests will use **Hypothesis** library to verify universal properties:

**Configuration**:
- Minimum 100 iterations per property test
- Tag format: **Feature: security-fixes, Property {number}: {property_text}**

**Property Tests**:

1. **Property 1 Test**: Generate random headers with sensitive header names (various casings) and verify all are masked
2. **Property 2 Test**: Generate random headers without sensitive names and verify all are preserved
3. **Property 3 Test**: Generate valid JWT tokens with random user_ids and verify key format
4. **Property 4 Test**: Generate invalid/missing tokens and verify fallback key format

### Integration Tests

1. **System Startup Test**: Verify the application starts without import errors after security.py removal
2. **End-to-End Rate Limiting Test**: Verify rate limiting works correctly for authenticated and anonymous users
