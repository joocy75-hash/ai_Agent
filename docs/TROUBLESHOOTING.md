# Troubleshooting Guide

This guide covers common issues and their solutions for the AI Trading Platform.

## API Error Codes

### 400 Bad Request
**Cause**: Invalid request parameters or malformed data.

**Solutions**:
- Check request body format (JSON)
- Verify required fields are present
- Validate data types match expected schema
- Check for special characters in string fields

### 401 Unauthorized
**Cause**: Missing or invalid authentication token.

**Solutions**:
- Ensure `Authorization: Bearer <token>` header is present
- Check if token has expired (default: 24 hours)
- Verify token was issued for the correct environment
- Re-login to obtain a new token

### 403 Forbidden
**Cause**: User lacks permission for the requested resource.

**Solutions**:
- Verify user role (admin vs regular user)
- Check if resource belongs to the authenticated user
- For admin endpoints, ensure admin role is assigned
- Check IP whitelist for admin endpoints

### 404 Not Found
**Cause**: Requested resource does not exist.

**Solutions**:
- Verify the endpoint URL is correct
- Check if the resource ID exists
- Ensure the resource hasn't been deleted
- Verify API version in URL

### 413 Payload Too Large
**Cause**: Upload file or request body exceeds size limits.

**Solutions**:
- File upload limit: 10MB per file
- User storage quota: 100MB total
- Maximum files per user: 50
- Reduce file size or delete old files

### 429 Too Many Requests
**Cause**: Rate limit exceeded.

**Solutions**:
- General API: 60 requests/minute (authenticated), 30 requests/minute (anonymous)
- Backtest API: 5 requests/minute
- Wait for the `Retry-After` header duration
- Implement exponential backoff in client

### 500 Internal Server Error
**Cause**: Unexpected server error.

**Solutions**:
- Check server logs for detailed error
- Verify database connection
- Check external service availability (Redis, exchange APIs)
- Report issue with request details

## Deployment Issues

### Database Connection Failed
**Symptoms**: Application fails to start, "Connection refused" errors.

**Solutions**:
```bash
# Check PostgreSQL is running
docker-compose ps

# Verify database URL in .env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/dbname

# Test connection
psql -h localhost -U user -d dbname
```

### Redis Connection Failed
**Symptoms**: Rate limiting falls back to in-memory, cache misses.

**Solutions**:
```bash
# Check Redis is running
redis-cli ping

# Verify Redis URL in .env
REDIS_URL=redis://localhost:6379/0

# Check Redis memory usage
redis-cli info memory
```

### Migration Errors
**Symptoms**: "Table already exists" or "Column not found" errors.

**Solutions**:
```bash
# Check current migration version
alembic current

# View migration history
alembic history

# Upgrade to latest
alembic upgrade head

# If stuck, stamp current version
alembic stamp head
```

## Authentication Issues

### JWT Token Invalid
**Symptoms**: 401 errors on authenticated endpoints.

**Solutions**:
- Check `JWT_SECRET` environment variable is set
- Verify token hasn't expired
- Ensure token is from the same environment
- Check for clock skew between servers

### 2FA Not Working
**Symptoms**: TOTP codes rejected.

**Solutions**:
- Verify device time is synchronized (NTP)
- Check TOTP secret is correctly stored
- Allow 30-second window for code validity
- Re-setup 2FA if persistent issues

### OAuth Login Failed
**Symptoms**: Social login redirects fail.

**Solutions**:
- Verify OAuth credentials in environment
- Check callback URL matches configuration
- Ensure OAuth provider is accessible
- Check for CORS issues in browser

## Bot and Trading Issues

### Bot Won't Start
**Symptoms**: Bot status shows "stopped" after start command.

**Solutions**:
- Verify API keys are configured
- Check exchange connection
- Ensure sufficient balance
- Review bot logs for specific errors

### Orders Not Executing
**Symptoms**: Signals generated but no trades.

**Solutions**:
- Check exchange API permissions
- Verify minimum order size met
- Check position limits
- Review risk settings

### Backtest Stuck
**Symptoms**: Backtest status remains "running" indefinitely.

**Solutions**:
- Check for large date ranges
- Verify data availability for symbol
- Monitor server resources (CPU, memory)
- Cancel and retry with smaller range

## Performance Issues

### Slow API Responses
**Symptoms**: Response times > 1 second.

**Solutions**:
- Check database query performance
- Verify Redis cache is working
- Monitor server CPU/memory
- Check for N+1 query issues

### High Memory Usage
**Symptoms**: Server memory > 80%.

**Solutions**:
- Restart application to clear caches
- Check for memory leaks in logs
- Reduce concurrent backtest limit
- Increase server memory

## Getting Help

If issues persist:
1. Check application logs: `docker-compose logs -f backend`
2. Review recent changes in git history
3. Search existing issues on GitHub
4. Create a new issue with:
   - Error message
   - Steps to reproduce
   - Environment details
   - Relevant logs
