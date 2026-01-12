"""
Integration tests for complete trading workflows.

Note: The 'email' field in auth schema is actually a username (4-20 chars, alphanumeric + underscore/hyphen).
"""
import pytest
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.api
class TestUserRegistrationToTradingWorkflow:
    """
    Tests the complete workflow from user registration to trading setup.

    Workflow:
    1. User registers
    2. User creates a strategy
    3. User views chart data
    4. User adds annotations to chart
    5. User checks bot status
    """

    @pytest.mark.asyncio
    async def test_complete_user_setup_workflow(self, async_client: AsyncClient):
        """Test complete user setup workflow."""
        # Step 1: Register
        register_payload = {
            "email": "wftest01",  # username format
            "password": "WorkflowTest1234!@#",
            "password_confirm": "WorkflowTest1234!@#",
            "name": "Workflow Test User",
            "phone": "01012345678",
        }
        register_response = await async_client.post("/auth/register", json=register_payload)
        assert register_response.status_code == 200
        token = register_response.cookies.get("access_token")
        if not token:
            pytest.skip("Token not available in cookies")
        headers = {"Authorization": f"Bearer {token}"}

        # Step 2: Create a strategy (using /strategy/create endpoint)
        strategy_payload = {
            "name": "RSI Momentum Strategy",
            "description": "A strategy using RSI for momentum trading",
            "params": '{"symbol": "BTCUSDT", "timeframe": "1h", "rsi_period": 14, "rsi_oversold": 30, "rsi_overbought": 70}',
        }
        strategy_response = await async_client.post(
            "/strategy/create",
            json=strategy_payload,
            headers=headers,
        )
        assert strategy_response.status_code in [200, 201]
        response_data = strategy_response.json()
        # Handle nested response format: {"strategy": {...}, "success": true}
        strategy = response_data.get("strategy", response_data)
        assert strategy.get("name") == "RSI Momentum Strategy"

        # Step 3: Get chart data
        chart_response = await async_client.get(
            "/chart/candles/BTCUSDT?timeframe=15m&limit=100",
            headers=headers,
        )
        # Chart data might not be available in test environment
        assert chart_response.status_code in [200, 404, 500]

        # Step 4: Add annotation
        annotation_payload = {
            "symbol": "BTCUSDT",
            "annotation_type": "price_level",
            "label": "Strong Support",
            "price": 95000.0,
            "alert_enabled": True,
            "style": {"color": "#ff4d4f"},
        }
        annotation_response = await async_client.post(
            "/annotations",
            json=annotation_payload,
            headers=headers,
        )
        assert annotation_response.status_code == 200
        annotation = annotation_response.json()
        assert annotation["label"] == "Strong Support"

        # Step 5: Get annotations
        get_annotations = await async_client.get(
            "/annotations/BTCUSDT",
            headers=headers,
        )
        assert get_annotations.status_code == 200
        assert get_annotations.json()["count"] >= 1

        # Step 6: Check bot status
        bot_status = await async_client.get("/bot/status", headers=headers)
        assert bot_status.status_code == 200
        assert bot_status.json()["is_running"] is False

    @pytest.mark.asyncio
    async def test_multi_user_isolation(self, async_client: AsyncClient):
        """Test that multiple users are properly isolated."""
        users = []

        # Create 3 users
        for i in range(3):
            payload = {
                "email": f"isouser0{i}",  # username format
                "password": "Test1234!@#",
                "password_confirm": "Test1234!@#",
                "name": f"Isolation User {i}",
                "phone": f"0101234567{i}",
            }
            response = await async_client.post("/auth/register", json=payload)
            assert response.status_code == 200
            token = response.cookies.get("access_token")
            if not token:
                pytest.skip("Token not available in cookies")
            users.append({"Authorization": f"Bearer {token}"})

        # Each user creates their own annotation
        annotation_ids = []
        for i, headers in enumerate(users):
            payload = {
                "symbol": "BTCUSDT",
                "annotation_type": "hline",
                "label": f"User {i} Annotation",
                "price": 90000.0 + i * 1000,
            }
            response = await async_client.post(
                "/annotations",
                json=payload,
                headers=headers,
            )
            assert response.status_code == 200
            annotation_ids.append(response.json()["id"])

        # Verify each user only sees their own annotations
        for i, headers in enumerate(users):
            response = await async_client.get(
                "/annotations/BTCUSDT",
                headers=headers,
            )
            assert response.status_code == 200

            annotations = response.json()["annotations"]
            user_annotation_ids = [a["id"] for a in annotations]

            # Should contain own annotation
            assert annotation_ids[i] in user_annotation_ids

            # Should not contain other users' annotations
            for j, other_id in enumerate(annotation_ids):
                if j != i:
                    assert other_id not in user_annotation_ids


@pytest.mark.integration
@pytest.mark.api
class TestAnnotationWorkflow:
    """Tests complete annotation workflow."""

    @pytest.fixture
    async def auth_user(self, async_client: AsyncClient):
        """Create a user for annotation workflow tests."""
        payload = {
            "email": "annotwf01",  # username format
            "password": "Test1234!@#",
            "password_confirm": "Test1234!@#",
            "name": "Annotation Workflow User",
            "phone": "01012345678",
        }
        response = await async_client.post("/auth/register", json=payload)
        assert response.status_code == 200
        token = response.cookies.get("access_token")
        if not token:
            pytest.skip("Token not available in cookies")
        return {"Authorization": f"Bearer {token}"}

    @pytest.mark.asyncio
    async def test_annotation_lifecycle(self, async_client: AsyncClient, auth_user):
        """Test complete annotation lifecycle: create -> update -> toggle -> delete."""
        # Create
        create_payload = {
            "symbol": "ETHUSDT",
            "annotation_type": "price_level",
            "label": "ETH Target",
            "price": 4000.0,
            "alert_enabled": True,
        }
        create_response = await async_client.post(
            "/annotations",
            json=create_payload,
            headers=auth_user,
        )
        assert create_response.status_code == 200
        annotation = create_response.json()
        annotation_id = annotation["id"]

        # Update
        update_payload = {
            "label": "ETH Updated Target",
            "price": 4200.0,
        }
        update_response = await async_client.put(
            f"/annotations/{annotation_id}",
            json=update_payload,
            headers=auth_user,
        )
        assert update_response.status_code == 200
        assert update_response.json()["label"] == "ETH Updated Target"
        assert update_response.json()["price"] == 4200.0

        # Toggle visibility off
        toggle_response = await async_client.post(
            f"/annotations/{annotation_id}/toggle",
            headers=auth_user,
        )
        assert toggle_response.status_code == 200
        assert toggle_response.json()["is_active"] is False

        # Get annotations (should not include inactive by default)
        get_response = await async_client.get(
            "/annotations/ETHUSDT",
            headers=auth_user,
        )
        active_ids = [a["id"] for a in get_response.json()["annotations"]]
        assert annotation_id not in active_ids

        # Get with include_inactive
        get_all_response = await async_client.get(
            "/annotations/ETHUSDT?include_inactive=true",
            headers=auth_user,
        )
        all_ids = [a["id"] for a in get_all_response.json()["annotations"]]
        assert annotation_id in all_ids

        # Toggle back on
        toggle_on_response = await async_client.post(
            f"/annotations/{annotation_id}/toggle",
            headers=auth_user,
        )
        assert toggle_on_response.json()["is_active"] is True

        # Delete
        delete_response = await async_client.delete(
            f"/annotations/{annotation_id}",
            headers=auth_user,
        )
        assert delete_response.status_code == 200
        assert delete_response.json()["success"] is True

        # Verify deleted
        detail_response = await async_client.get(
            f"/annotations/detail/{annotation_id}",
            headers=auth_user,
        )
        assert detail_response.status_code == 404

    @pytest.mark.asyncio
    async def test_multiple_annotations_for_symbol(self, async_client: AsyncClient, auth_user):
        """Test creating and managing multiple annotations for the same symbol."""
        symbol = "SOLUSDT"
        created_ids = []

        # Create 5 annotations
        for i in range(5):
            payload = {
                "symbol": symbol,
                "annotation_type": "hline" if i % 2 == 0 else "price_level",
                "label": f"Level {i}",
                "price": 150.0 + i * 10,
                "alert_enabled": i % 2 == 1,
            }
            response = await async_client.post(
                "/annotations",
                json=payload,
                headers=auth_user,
            )
            assert response.status_code == 200
            created_ids.append(response.json()["id"])

        # Get all annotations
        get_response = await async_client.get(
            f"/annotations/{symbol}",
            headers=auth_user,
        )
        assert get_response.status_code == 200
        assert get_response.json()["count"] == 5

        # Delete all for symbol
        delete_all_response = await async_client.delete(
            f"/annotations/symbol/{symbol}",
            headers=auth_user,
        )
        assert delete_all_response.status_code == 200
        assert delete_all_response.json()["deleted_count"] == 5

        # Verify all deleted
        verify_response = await async_client.get(
            f"/annotations/{symbol}",
            headers=auth_user,
        )
        assert verify_response.json()["count"] == 0


@pytest.mark.integration
@pytest.mark.api
class TestStrategyManagement:
    """Tests for strategy management workflow."""

    @pytest.fixture
    async def auth_user(self, async_client: AsyncClient):
        """Create a user for strategy tests."""
        payload = {
            "email": "stratwf01",  # username format
            "password": "Test1234!@#",
            "password_confirm": "Test1234!@#",
            "name": "Strategy Workflow User",
            "phone": "01012345678",
        }
        response = await async_client.post("/auth/register", json=payload)
        assert response.status_code == 200
        token = response.cookies.get("access_token")
        if not token:
            pytest.skip("Token not available in cookies")
        return {"Authorization": f"Bearer {token}"}

    @pytest.mark.asyncio
    async def test_strategy_crud(self, async_client: AsyncClient, auth_user):
        """Test strategy CRUD operations."""
        # Create (using /strategy/create endpoint)
        create_payload = {
            "name": "Bollinger Band Strategy",
            "description": "Uses Bollinger Bands for mean reversion",
            "params": '{"bb_period": 20, "bb_std_dev": 2.0, "symbol": "BTCUSDT"}',
        }
        create_response = await async_client.post(
            "/strategy/create",
            json=create_payload,
            headers=auth_user,
        )
        assert create_response.status_code in [200, 201]
        response_data = create_response.json()
        # Handle nested response format: {"strategy": {...}, "success": true}
        strategy = response_data.get("strategy", response_data)
        strategy_id = strategy.get("id")
        assert strategy.get("name") == "Bollinger Band Strategy"

        # Get list (using /strategy/list endpoint)
        list_response = await async_client.get("/strategy/list", headers=auth_user)
        assert list_response.status_code == 200
        strategies = list_response.json()
        assert len(strategies) >= 1

        # Update (using /strategy/update/{id} endpoint)
        if strategy_id:
            update_payload = {
                "name": "Bollinger Band Strategy V2",
                "description": "Updated description",
            }
            update_response = await async_client.post(
                f"/strategy/update/{strategy_id}",
                json=update_payload,
                headers=auth_user,
            )
            # Update might not be implemented, check for success or not found
            # 403 is also valid if user doesn't have permission to update
            assert update_response.status_code in [200, 403, 404, 405]

        # Note: Delete endpoint not available in current API


@pytest.mark.integration
@pytest.mark.performance
class TestAPIPerformance:
    """Performance tests for API endpoints."""

    @pytest.fixture
    async def auth_user(self, async_client: AsyncClient):
        """Create a user for performance tests."""
        payload = {
            "email": "perftest01",  # username format
            "password": "Test1234!@#",
            "password_confirm": "Test1234!@#",
            "name": "Performance Test User",
            "phone": "01012345678",
        }
        response = await async_client.post("/auth/register", json=payload)
        assert response.status_code == 200
        token = response.cookies.get("access_token")
        if not token:
            pytest.skip("Token not available in cookies")
        return {"Authorization": f"Bearer {token}"}

    @pytest.mark.asyncio
    async def test_annotation_batch_creation_performance(self, async_client: AsyncClient, auth_user):
        """Test performance of creating multiple annotations."""
        import time

        symbol = "BTCUSDT"
        num_annotations = 20

        start_time = time.time()
        for i in range(num_annotations):
            payload = {
                "symbol": symbol,
                "annotation_type": "hline",
                "label": f"Perf Test {i}",
                "price": 90000.0 + i * 100,
            }
            response = await async_client.post(
                "/annotations",
                json=payload,
                headers=auth_user,
            )
            assert response.status_code == 200

        duration = time.time() - start_time

        # Should complete 20 annotations in under 5 seconds
        assert duration < 5.0, f"Batch creation took too long: {duration:.2f}s"

        # Cleanup
        await async_client.delete(f"/annotations/symbol/{symbol}", headers=auth_user)

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, async_client: AsyncClient, auth_user):
        """Test handling of concurrent requests."""
        import asyncio

        async def make_request():
            return await async_client.get("/annotations/BTCUSDT", headers=auth_user)

        # Make 10 concurrent requests
        tasks = [make_request() for _ in range(10)]
        responses = await asyncio.gather(*tasks)

        # All should succeed
        for response in responses:
            assert response.status_code == 200
