#!/usr/bin/env python3
"""
AI Cost Optimization Integration Verification Script

This script verifies that the AI cost optimization system is properly integrated.
Run this before starting the application to catch any configuration issues.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))


async def verify_imports():
    """Test 1: Verify all modules can be imported"""
    print("\n" + "="*60)
    print("Test 1: Verifying imports...")
    print("="*60)

    try:
        from src.services.ai_optimization import (
            IntegratedAIService,
            EventDrivenOptimizer,
            PromptCacheManager,
            ResponseCacheManager,
            SmartSamplingManager,
            CostTracker,
            MarketEvent,
            EventPriority,
            EventType,
            SamplingStrategy
        )
        print("✅ AI optimization modules imported successfully")

        from src.services import (
            initialize_ai_service,
            shutdown_ai_service,
            get_ai_service_instance,
            get_redis_instance
        )
        print("✅ Service initialization functions imported successfully")

        from src.api.ai_cost import router
        print("✅ AI cost API router imported successfully")

        return True

    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False


async def verify_environment():
    """Test 2: Verify environment variables"""
    print("\n" + "="*60)
    print("Test 2: Verifying environment variables...")
    print("="*60)

    required_vars = {
        "DEEPSEEK_API_KEY": "DeepSeek API key for AI calls",
    }

    optional_vars = {
        "REDIS_HOST": "Redis host (default: localhost)",
        "REDIS_PORT": "Redis port (default: 6379)",
        "REDIS_DB": "Redis database (default: 0)",
    }

    all_ok = True

    # Check required variables
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: {description}")
            print(f"   Value: {'*' * 8}{value[-4:]}")  # Show last 4 chars
        else:
            print(f"❌ {var}: {description}")
            print(f"   Missing! Set this in your .env file")
            all_ok = False

    # Check optional variables
    for var, description in optional_vars.items():
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: {description}")
            print(f"   Value: {value}")
        else:
            print(f"⚠️  {var}: {description}")
            print(f"   Using default value")

    return all_ok


async def verify_redis_connection():
    """Test 3: Verify Redis connection"""
    print("\n" + "="*60)
    print("Test 3: Verifying Redis connection...")
    print("="*60)

    try:
        import redis.asyncio as redis

        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", 6379))
        redis_db = int(os.getenv("REDIS_DB", 0))

        client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            decode_responses=True,
            socket_connect_timeout=5
        )

        # Test connection
        await client.ping()
        print(f"✅ Redis connection successful")
        print(f"   Host: {redis_host}")
        print(f"   Port: {redis_port}")
        print(f"   DB: {redis_db}")

        # Test set/get
        await client.set("ai_test_key", "test_value", ex=10)
        value = await client.get("ai_test_key")
        if value == "test_value":
            print("✅ Redis read/write test passed")
        else:
            print("❌ Redis read/write test failed")
            return False

        await client.close()
        return True

    except redis.ConnectionError as e:
        print(f"⚠️  Redis connection failed: {e}")
        print("⚠️  AI service will run in degraded mode (no caching)")
        print("   To enable caching, start Redis:")
        print("   - macOS: brew services start redis")
        print("   - Ubuntu: sudo systemctl start redis-server")
        return False

    except Exception as e:
        print(f"❌ Redis test failed: {e}")
        return False


async def verify_ai_service_initialization():
    """Test 4: Verify AI service can be initialized"""
    print("\n" + "="*60)
    print("Test 4: Verifying AI service initialization...")
    print("="*60)

    try:
        from src.services import initialize_ai_service, shutdown_ai_service, get_ai_service_instance

        # Initialize
        await initialize_ai_service()
        print("✅ AI service initialized successfully")

        # Get instance
        ai_service = get_ai_service_instance()
        print(f"✅ AI service instance retrieved")
        print(f"   Model: {ai_service.MODEL_VERSION}")
        print(f"   Base URL: {ai_service.BASE_URL}")

        # Check components
        if ai_service.prompt_cache:
            print("✅ Prompt cache enabled")
        if ai_service.response_cache:
            print("✅ Response cache enabled")
        if ai_service.sampling_manager:
            print("✅ Smart sampling enabled")
        if ai_service.event_optimizer:
            print("✅ Event-driven optimizer enabled")
        if ai_service.cost_tracker:
            print("✅ Cost tracker enabled")

        # Shutdown
        await shutdown_ai_service()
        print("✅ AI service shutdown successfully")

        return True

    except Exception as e:
        print(f"❌ AI service initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def verify_api_endpoints():
    """Test 5: Verify API endpoints are registered"""
    print("\n" + "="*60)
    print("Test 5: Verifying API endpoints...")
    print("="*60)

    try:
        from src.api.ai_cost import router

        routes = [route for route in router.routes]
        print(f"✅ Found {len(routes)} API endpoints:")

        for route in routes:
            if hasattr(route, 'methods') and hasattr(route, 'path'):
                methods = ", ".join(route.methods)
                print(f"   {methods:10} {route.path}")

        expected_endpoints = [
            "/stats",
            "/daily",
            "/monthly",
            "/budget-alert",
            "/agent-breakdown",
            "/event-stats",
            "/sampling-strategy",
            "/event-thresholds",
            "/clear-cache"
        ]

        registered_paths = [route.path for route in routes if hasattr(route, 'path')]

        for endpoint in expected_endpoints:
            full_path = f"/ai-cost{endpoint}"
            if any(endpoint in path for path in registered_paths):
                print(f"   ✅ {endpoint}")
            else:
                print(f"   ❌ {endpoint} (not found)")

        return True

    except Exception as e:
        print(f"❌ API endpoint verification failed: {e}")
        return False


async def main():
    """Run all verification tests"""
    print("\n" + "="*70)
    print(" AI COST OPTIMIZATION INTEGRATION VERIFICATION ".center(70, "="))
    print("="*70)

    results = {
        "Imports": await verify_imports(),
        "Environment": await verify_environment(),
        "Redis": await verify_redis_connection(),
        "AI Service": await verify_ai_service_initialization(),
        "API Endpoints": await verify_api_endpoints()
    }

    # Summary
    print("\n" + "="*70)
    print(" VERIFICATION SUMMARY ".center(70, "="))
    print("="*70)

    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name:20} {status}")

    all_passed = all(results.values())

    print("="*70)
    if all_passed:
        print(" ✅ ALL TESTS PASSED - SYSTEM READY ".center(70, "="))
        print("="*70)
        print("\nYou can now start the application:")
        print("  cd backend")
        print("  uvicorn src.main:app --reload")
        print("\nAPI docs will be available at:")
        print("  http://localhost:8000/docs")
        print("\nAI Cost endpoints:")
        print("  http://localhost:8000/api/v1/ai-cost/stats")
        return 0
    else:
        print(" ❌ SOME TESTS FAILED - FIX ISSUES ABOVE ".center(70, "="))
        print("="*70)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
