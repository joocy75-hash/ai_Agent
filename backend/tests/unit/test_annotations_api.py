"""
Unit tests for chart annotations API endpoints.

Note: The 'email' field in auth schema is actually a username (4-20 chars, alphanumeric + underscore/hyphen).
Note: Auth responses now use cookies for tokens.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.unit
@pytest.mark.api
class TestAnnotationsCRUD:
    """Tests for annotations CRUD operations."""

    @pytest.fixture
    async def auth_user(self, async_client: AsyncClient):
        """Create a user for annotation tests."""
        payload = {
            "email": "annottest01",  # username format
            "password": "Test1234!@#",
            "password_confirm": "Test1234!@#",
            "name": "Annotation Test User",
            "phone": "01012345678",
        }
        response = await async_client.post("/auth/register", json=payload)
        assert response.status_code == 200
        
        # Get token from cookies
        token = response.cookies.get("access_token")
        if not token:
            pytest.skip("Token not available in cookies")
        return {"Authorization": f"Bearer {token}"}

    @pytest.mark.asyncio
    async def test_create_annotation(self, async_client: AsyncClient, auth_user):
        """Test creating a new annotation."""
        payload = {
            "symbol": "BTCUSDT",
            "annotation_type": "hline",
            "label": "Support Level",
            "price": 95000.0,
            "style": {"color": "#52c41a", "lineWidth": 2},
        }

        response = await async_client.post(
            "/annotations",
            json=payload,
            headers=auth_user,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "BTCUSDT"
        assert data["annotation_type"] == "hline"
        assert data["label"] == "Support Level"
        assert data["price"] == 95000.0
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_price_level_annotation(self, async_client: AsyncClient, auth_user):
        """Test creating a price level annotation with alert."""
        payload = {
            "symbol": "ETHUSDT",
            "annotation_type": "price_level",
            "label": "ETH Alert at 4000",
            "price": 4000.0,
            "alert_enabled": True,
            "alert_direction": "above",  # Valid values: "above" or "below"
            "style": {"color": "#ff4d4f", "lineWidth": 2},
        }

        response = await async_client.post(
            "/annotations",
            json=payload,
            headers=auth_user,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["annotation_type"] == "price_level"
        assert data["alert_enabled"] is True
        assert data["alert_triggered"] is False

    @pytest.mark.asyncio
    async def test_get_annotations_by_symbol(self, async_client: AsyncClient, auth_user):
        """Test getting annotations for a specific symbol."""
        # Create some annotations first
        for i in range(3):
            payload = {
                "symbol": "BTCUSDT",
                "annotation_type": "hline",
                "label": f"Level {i}",
                "price": 90000.0 + i * 1000,
            }
            await async_client.post("/annotations", json=payload, headers=auth_user)

        # Get annotations
        response = await async_client.get(
            "/annotations/BTCUSDT",
            headers=auth_user,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "BTCUSDT"
        assert data["count"] >= 3
        assert len(data["annotations"]) >= 3

    @pytest.mark.asyncio
    async def test_get_annotations_empty(self, async_client: AsyncClient, auth_user):
        """Test getting annotations for symbol with no annotations."""
        response = await async_client.get(
            "/annotations/XYZUSDT",
            headers=auth_user,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "XYZUSDT"
        assert data["count"] == 0
        assert data["annotations"] == []

    @pytest.mark.asyncio
    async def test_update_annotation(self, async_client: AsyncClient, auth_user):
        """Test updating an annotation."""
        # Create annotation
        create_payload = {
            "symbol": "BTCUSDT",
            "annotation_type": "hline",
            "label": "Original Label",
            "price": 95000.0,
        }
        create_response = await async_client.post(
            "/annotations",
            json=create_payload,
            headers=auth_user,
        )
        annotation_id = create_response.json()["id"]

        # Update annotation
        update_payload = {
            "label": "Updated Label",
            "price": 96000.0,
        }
        response = await async_client.put(
            f"/annotations/{annotation_id}",
            json=update_payload,
            headers=auth_user,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["label"] == "Updated Label"
        assert data["price"] == 96000.0

    @pytest.mark.asyncio
    async def test_delete_annotation(self, async_client: AsyncClient, auth_user):
        """Test deleting an annotation."""
        # Create annotation
        create_payload = {
            "symbol": "BTCUSDT",
            "annotation_type": "hline",
            "label": "To Delete",
            "price": 95000.0,
        }
        create_response = await async_client.post(
            "/annotations",
            json=create_payload,
            headers=auth_user,
        )
        annotation_id = create_response.json()["id"]

        # Delete annotation
        response = await async_client.delete(
            f"/annotations/{annotation_id}",
            headers=auth_user,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["deleted_id"] == annotation_id

        # Verify it's deleted
        get_response = await async_client.get(
            f"/annotations/detail/{annotation_id}",
            headers=auth_user,
        )
        assert get_response.status_code == 404


@pytest.mark.unit
@pytest.mark.api
class TestAnnotationsToggle:
    """Tests for annotation toggle operations."""

    @pytest.fixture
    async def auth_user(self, async_client: AsyncClient):
        """Create a user for toggle tests."""
        payload = {
            "email": "toggletest01",  # username format
            "password": "Test1234!@#",
            "password_confirm": "Test1234!@#",
            "name": "Toggle Test User",
            "phone": "01012345678",
        }
        response = await async_client.post("/auth/register", json=payload)
        assert response.status_code == 200
        
        # Get token from cookies
        token = response.cookies.get("access_token")
        if not token:
            pytest.skip("Token not available in cookies")
        return {"Authorization": f"Bearer {token}"}

    @pytest.fixture
    async def created_annotation(self, async_client: AsyncClient, auth_user):
        """Create an annotation for toggle tests."""
        payload = {
            "symbol": "BTCUSDT",
            "annotation_type": "hline",
            "label": "Toggle Test",
            "price": 95000.0,
        }
        response = await async_client.post(
            "/annotations",
            json=payload,
            headers=auth_user,
        )
        return response.json()

    @pytest.mark.asyncio
    async def test_toggle_visibility(self, async_client: AsyncClient, auth_user, created_annotation):
        """Test toggling annotation visibility."""
        annotation_id = created_annotation["id"]

        # Initially active
        assert created_annotation["is_active"] is True

        # Toggle off
        response = await async_client.post(
            f"/annotations/{annotation_id}/toggle",
            headers=auth_user,
        )
        assert response.status_code == 200
        assert response.json()["is_active"] is False

        # Toggle on
        response = await async_client.post(
            f"/annotations/{annotation_id}/toggle",
            headers=auth_user,
        )
        assert response.status_code == 200
        assert response.json()["is_active"] is True

    @pytest.mark.asyncio
    async def test_toggle_lock(self, async_client: AsyncClient, auth_user, created_annotation):
        """Test toggling annotation lock."""
        annotation_id = created_annotation["id"]

        # Initially unlocked
        assert created_annotation["is_locked"] is False

        # Lock
        response = await async_client.post(
            f"/annotations/{annotation_id}/lock",
            headers=auth_user,
        )
        assert response.status_code == 200
        assert response.json()["is_locked"] is True

        # Try to update locked annotation - should fail
        update_response = await async_client.put(
            f"/annotations/{annotation_id}",
            json={"label": "Should Fail"},
            headers=auth_user,
        )
        assert update_response.status_code == 403

        # Unlock
        response = await async_client.post(
            f"/annotations/{annotation_id}/lock",
            headers=auth_user,
        )
        assert response.status_code == 200
        assert response.json()["is_locked"] is False


@pytest.mark.unit
@pytest.mark.api
class TestAnnotationsAlerts:
    """Tests for price alert functionality."""

    @pytest.fixture
    async def auth_user(self, async_client: AsyncClient):
        """Create a user for alert tests."""
        payload = {
            "email": "alerttest01",  # username format
            "password": "Test1234!@#",
            "password_confirm": "Test1234!@#",
            "name": "Alert Test User",
            "phone": "01012345678",
        }
        response = await async_client.post("/auth/register", json=payload)
        assert response.status_code == 200
        
        # Get token from cookies
        token = response.cookies.get("access_token")
        if not token:
            pytest.skip("Token not available in cookies")
        return {"Authorization": f"Bearer {token}"}

    @pytest.fixture
    async def price_level_annotation(self, async_client: AsyncClient, auth_user):
        """Create a price level annotation."""
        payload = {
            "symbol": "BTCUSDT",
            "annotation_type": "price_level",
            "label": "Alert Test",
            "price": 100000.0,
            "alert_enabled": True,
        }
        response = await async_client.post(
            "/annotations",
            json=payload,
            headers=auth_user,
        )
        return response.json()

    @pytest.mark.asyncio
    async def test_reset_alert(self, async_client: AsyncClient, auth_user, price_level_annotation, async_session):
        """Test resetting a triggered alert."""
        from src.database.models import ChartAnnotation

        annotation_id = price_level_annotation["id"]

        # Manually trigger the alert in DB
        from sqlalchemy import select
        result = await async_session.execute(
            select(ChartAnnotation).where(ChartAnnotation.id == annotation_id)
        )
        annotation = result.scalar_one_or_none()
        if annotation:
            annotation.alert_triggered = True
            await async_session.commit()

        # Reset alert
        response = await async_client.post(
            f"/annotations/{annotation_id}/reset-alert",
            headers=auth_user,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["alert_triggered"] is False

    @pytest.mark.asyncio
    async def test_reset_alert_non_price_level(self, async_client: AsyncClient, auth_user):
        """Test resetting alert on non-price_level annotation fails."""
        # Create a regular hline annotation
        payload = {
            "symbol": "BTCUSDT",
            "annotation_type": "hline",
            "label": "Regular Line",
            "price": 95000.0,
        }
        response = await async_client.post(
            "/annotations",
            json=payload,
            headers=auth_user,
        )
        annotation_id = response.json()["id"]

        # Try to reset alert - should fail
        reset_response = await async_client.post(
            f"/annotations/{annotation_id}/reset-alert",
            headers=auth_user,
        )
        assert reset_response.status_code == 400


@pytest.mark.unit
@pytest.mark.api
class TestAnnotationsAuth:
    """Tests for annotation authentication."""

    @pytest.mark.asyncio
    async def test_get_annotations_no_auth(self, async_client: AsyncClient):
        """Test getting annotations without authentication fails."""
        response = await async_client.get("/annotations/BTCUSDT")
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_create_annotation_no_auth(self, async_client: AsyncClient):
        """Test creating annotation without authentication fails."""
        payload = {
            "symbol": "BTCUSDT",
            "annotation_type": "hline",
            "label": "Test",
            "price": 95000.0,
        }
        response = await async_client.post("/annotations", json=payload)
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_user_isolation(self, async_client: AsyncClient):
        """Test that users can only see their own annotations."""
        # Create user 1
        payload1 = {
            "email": "user1iso01",  # username format
            "password": "Test1234!@#",
            "password_confirm": "Test1234!@#",
            "name": "User 1",
            "phone": "01012345678",
        }
        response1 = await async_client.post("/auth/register", json=payload1)
        token1 = response1.cookies.get("access_token")
        if not token1:
            pytest.skip("Token not available in cookies")
        headers1 = {"Authorization": f"Bearer {token1}"}

        # Create user 2
        payload2 = {
            "email": "user2iso01",  # username format
            "password": "Test1234!@#",
            "password_confirm": "Test1234!@#",
            "name": "User 2",
            "phone": "01012345679",
        }
        response2 = await async_client.post("/auth/register", json=payload2)
        token2 = response2.cookies.get("access_token")
        if not token2:
            pytest.skip("Token not available in cookies")
        headers2 = {"Authorization": f"Bearer {token2}"}

        # User 1 creates annotation
        annotation_payload = {
            "symbol": "BTCUSDT",
            "annotation_type": "hline",
            "label": "User 1 Only",
            "price": 95000.0,
        }
        create_response = await async_client.post(
            "/annotations",
            json=annotation_payload,
            headers=headers1,
        )
        annotation_id = create_response.json()["id"]

        # User 2 should not see User 1's annotations
        get_response = await async_client.get(
            "/annotations/BTCUSDT",
            headers=headers2,
        )
        user2_annotations = get_response.json()["annotations"]
        user2_ids = [a["id"] for a in user2_annotations]
        assert annotation_id not in user2_ids

        # User 2 should not be able to access User 1's annotation directly
        detail_response = await async_client.get(
            f"/annotations/detail/{annotation_id}",
            headers=headers2,
        )
        assert detail_response.status_code == 404
