"""
API Endpoint Tests

Integration tests for API endpoints with security validations.
These tests verify that endpoints properly validate inputs and reject invalid requests.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
@pytest.mark.security
class TestQueryEndpointSecurity:
    """Test query endpoint security validations"""
    
    def test_invalid_ticker_rejected(self, test_client: TestClient):
        """Invalid ticker formats should be rejected"""
        response = test_client.post(
            "/api/query/premium-summary",
            json={
                "ticker": "invalid123",  # Numbers not allowed
                "option_type": "call",
                "duration_days": 30
            }
        )
        assert response.status_code == 400
        assert "ticker" in response.json()["detail"].lower()
    
    def test_sql_injection_blocked(self, test_client: TestClient):
        """SQL injection attempts should be blocked"""
        response = test_client.post(
            "/api/query/premium-summary",
            json={
                "ticker": "AAPL'; DROP TABLE stocks; --",
                "option_type": "call",
                "duration_days": 30
            }
        )
        assert response.status_code == 400
    
    def test_invalid_option_type_rejected(self, test_client: TestClient):
        """Invalid option types should be rejected"""
        response = test_client.post(
            "/api/query/premium-summary",
            json={
                "ticker": "AAPL",
                "option_type": "invalid",
                "duration_days": 30
            }
        )
        assert response.status_code == 400
    
    def test_negative_strike_price_rejected(self, test_client: TestClient):
        """Negative strike prices should be rejected"""
        response = test_client.post(
            "/api/query/premium-by-strike",
            json={
                "ticker": "AAPL",
                "option_type": "call",
                "strike_price": -100.0,
                "duration_days": 30
            }
        )
        assert response.status_code == 400
    
    def test_excessive_duration_rejected(self, test_client: TestClient):
        """Duration exceeding max (365 days) should be rejected"""
        response = test_client.post(
            "/api/query/premium-summary",
            json={
                "ticker": "AAPL",
                "option_type": "call",
                "duration_days": 500  # Over 365 limit
            }
        )
        assert response.status_code == 400


@pytest.mark.integration
@pytest.mark.security
class TestWatchlistEndpointSecurity:
    """Test watchlist endpoint security validations"""
    
    def test_add_invalid_ticker_rejected(self, test_client: TestClient):
        """Adding invalid ticker should be rejected"""
        response = test_client.post(
            "/api/watchlist/add",
            json={
                "ticker": "invalid_ticker!",
                "company_name": "Test Company"
            }
        )
        assert response.status_code == 400
    
    def test_add_xss_in_company_name_sanitized(self, test_client: TestClient):
        """XSS attempts in company name should be sanitized"""
        response = test_client.post(
            "/api/watchlist/add",
            json={
                "ticker": "TEST",
                "company_name": "<script>alert('xss')</script>Test Company"
            }
        )
        # Should succeed after sanitization or reject
        assert response.status_code in [200, 400]
        if response.status_code == 200:
            # If accepted, verify script tags were removed
            assert "<script>" not in response.json().get("message", "")
    
    def test_remove_invalid_ticker_rejected(self, test_client: TestClient):
        """Removing invalid ticker should be rejected"""
        response = test_client.delete(
            "/api/watchlist/remove",
            json={
                "ticker": "123INVALID"
            }
        )
        assert response.status_code == 400


@pytest.mark.integration
@pytest.mark.security
class TestSchedulerEndpointSecurity:
    """Test scheduler endpoint security validations"""
    
    def test_invalid_polling_interval_rejected(self, test_client: TestClient):
        """Polling interval outside valid range should be rejected"""
        # Too low
        response = test_client.put(
            "/api/scheduler/config",
            json={
                "polling_interval_minutes": 0
            }
        )
        assert response.status_code == 400
        
        # Too high
        response = test_client.put(
            "/api/scheduler/config",
            json={
                "polling_interval_minutes": 2000  # Over 1440 limit
            }
        )
        assert response.status_code == 400
    
    def test_invalid_stock_delay_rejected(self, test_client: TestClient):
        """Stock delay outside valid range should be rejected"""
        response = test_client.put(
            "/api/scheduler/config",
            json={
                "stock_delay_seconds": 500  # Over 300 limit
            }
        )
        assert response.status_code == 400
    
    def test_invalid_max_expirations_rejected(self, test_client: TestClient):
        """Max expirations outside valid range should be rejected"""
        # Too low
        response = test_client.put(
            "/api/scheduler/config",
            json={
                "max_expirations": 0
            }
        )
        assert response.status_code == 400
        
        # Too high
        response = test_client.put(
            "/api/scheduler/config",
            json={
                "max_expirations": 150  # Over 100 limit
            }
        )
        assert response.status_code == 400
    
    def test_invalid_timezone_rejected(self, test_client: TestClient):
        """Invalid timezone should be rejected"""
        response = test_client.put(
            "/api/scheduler/config",
            json={
                "timezone": "Invalid/Timezone"
            }
        )
        assert response.status_code == 400
        assert "timezone" in response.json()["detail"].lower()


@pytest.mark.integration
class TestHealthEndpoint:
    """Test health check endpoint"""
    
    def test_health_endpoint_accessible(self, test_client: TestClient):
        """Health endpoint should be accessible"""
        response = test_client.get("/health")
        assert response.status_code in [200, 503]  # 200 healthy, 503 degraded
    
    def test_health_response_structure(self, test_client: TestClient):
        """Health endpoint should return proper structure"""
        response = test_client.get("/health")
        data = response.json()
        
        assert "status" in data
        assert "service" in data
        assert "checks" in data
        assert "database" in data["checks"]
        assert "scheduler" in data["checks"]
