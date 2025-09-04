"""
Comprehensive tests for the web crawler API endpoints.
Tests both authentication test and field detection endpoints.
"""

import pytest
import asyncio
from httpx import AsyncClient
from fastapi import FastAPI
from src.main import create_app
from src.models.schemas import (
    AuthTestRequest, AuthTestResponse,
    FieldDetectionRequest, FieldDetectionResponse
)


@pytest.fixture
def app() -> FastAPI:
    """Create test application."""
    return create_app()


@pytest.fixture
async def client(app: FastAPI):
    """Create test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


class TestAuthTestEndpoint:
    """Tests for the authentication test endpoint."""
    
    @pytest.mark.asyncio
    async def test_auth_test_success(self, client):
        """Test successful authentication test."""
        payload = {
            "url": "https://httpbin.org/basic-auth/user/pass",
            "credentials": {
                "username": "user",
                "password": "pass"
            }
        }
        
        response = await client.post("/api/v1/web-crawlers/auth-test", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert "success" in data
        assert "message" in data
        assert "execution_time" in data
        assert "request_id" in data
        assert "timestamp" in data
    
    @pytest.mark.asyncio
    async def test_auth_test_invalid_url(self, client):
        """Test authentication test with invalid URL."""
        payload = {
            "url": "invalid-url",
            "credentials": {
                "username": "user",
                "password": "pass"
            }
        }
        
        response = await client.post("/api/v1/web-crawlers/auth-test", json=payload)
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_auth_test_missing_credentials(self, client):
        """Test authentication test with missing credentials."""
        payload = {
            "url": "https://example.com"
        }
        
        response = await client.post("/api/v1/web-crawlers/auth-test", json=payload)
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_auth_test_empty_credentials(self, client):
        """Test authentication test with empty credentials."""
        payload = {
            "url": "https://example.com",
            "credentials": {}
        }
        
        response = await client.post("/api/v1/web-crawlers/auth-test", json=payload)
        assert response.status_code == 200  # Should handle gracefully


class TestFieldDetectionEndpoint:
    """Tests for the field detection endpoint."""
    
    @pytest.mark.asyncio
    async def test_field_detection_success(self, client):
        """Test successful field detection."""
        payload = {
            "url": "https://httpbin.org/forms/post"
        }
        
        response = await client.post("/api/v1/web-crawlers/field-detection", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert "success" in data
        assert "fields" in data
        assert isinstance(data["fields"], list)
        assert "execution_time" in data
        assert "request_id" in data
        assert "timestamp" in data
    
    @pytest.mark.asyncio
    async def test_field_detection_invalid_url(self, client):
        """Test field detection with invalid URL."""
        payload = {
            "url": "invalid-url"
        }
        
        response = await client.post("/api/v1/web-crawlers/field-detection", json=payload)
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_field_detection_empty_url(self, client):
        """Test field detection with empty URL."""
        payload = {
            "url": ""
        }
        
        response = await client.post("/api/v1/web-crawlers/field-detection", json=payload)
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_field_detection_fields_structure(self, client):
        """Test the structure of detected fields."""
        payload = {
            "url": "https://httpbin.org/forms/post"
        }
        
        response = await client.post("/api/v1/web-crawlers/field-detection", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        fields = data["fields"]
        
        for field in fields:
            assert "name" in field
            assert "type" in field
            assert "selector" in field
            assert "description" in field
            assert isinstance(field.get("columns", []), list)


class TestHealthEndpoints:
    """Tests for health check endpoints."""
    
    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Test health check endpoint."""
        response = await client.get("/api/v1/web-crawlers/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["service"] == "easysuites-web-crawler"
    
    @pytest.mark.asyncio
    async def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = await client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "endpoints" in data


class TestErrorHandling:
    """Tests for error handling."""
    
    @pytest.mark.asyncio
    async def test_nonexistent_endpoint(self, client):
        """Test nonexistent endpoint."""
        response = await client.get("/nonexistent")
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_method_not_allowed(self, client):
        """Test method not allowed."""
        response = await client.get("/api/v1/web-crawlers/auth-test")
        assert response.status_code == 405
    
    @pytest.mark.asyncio
    async def test_invalid_json_payload(self, client):
        """Test invalid JSON payload."""
        response = await client.post(
            "/api/v1/web-crawlers/auth-test",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422


class TestSchemaValidation:
    """Tests for schema validation."""
    
    def test_auth_test_request_schema(self):
        """Test AuthTestRequest schema validation."""
        # Valid request
        request = AuthTestRequest(
            url="https://example.com",
            credentials={"username": "user", "password": "pass"}
        )
        assert request.url == "https://example.com"
        assert request.credentials == {"username": "user", "password": "pass"}
    
    def test_field_detection_request_schema(self):
        """Test FieldDetectionRequest schema validation."""
        # Valid request
        request = FieldDetectionRequest(url="https://example.com")
        assert request.url == "https://example.com"
    
    def test_auth_test_response_schema(self):
        """Test AuthTestResponse schema validation."""
        response = AuthTestResponse(
            success=True,
            message="Authentication successful",
            execution_time=2.5,
            request_id="test-123",
            timestamp="2024-01-01T00:00:00"
        )
        assert response.success is True
        assert response.message == "Authentication successful"
        assert response.execution_time == 2.5
    
    def test_field_detection_response_schema(self):
        """Test FieldDetectionResponse schema validation."""
        response = FieldDetectionResponse(
            success=True,
            fields=[
                {
                    "name": "test_field",
                    "type": "input",
                    "selector": "#test",
                    "description": "Test field",
                    "columns": []
                }
            ],
            execution_time=1.2,
            request_id="test-456",
            timestamp="2024-01-01T00:00:00"
        )
        assert response.success is True
        assert len(response.fields) == 1
        assert response.fields[0].name == "test_field"


class TestIntegrationScenarios:
    """Integration tests for real-world scenarios."""
    
    @pytest.mark.asyncio
    async def test_complete_workflow(self, client):
        """Test complete workflow: field detection followed by auth test."""
        
        # Step 1: Detect fields
        field_payload = {"url": "https://httpbin.org/forms/post"}
        field_response = await client.post("/api/v1/web-crawlers/field-detection", json=field_payload)
        assert field_response.status_code == 200
        
        field_data = field_response.json()
        assert field_data["success"] is True
        assert len(field_data["fields"]) > 0
        
        # Step 2: Test authentication (with dummy credentials)
        auth_payload = {
            "url": "https://httpbin.org/basic-auth/user/pass",
            "credentials": {
                "username": "user",
                "password": "pass"
            }
        }
        auth_response = await client.post("/api/v1/web-crawlers/auth-test", json=auth_payload)
        assert auth_response.status_code == 200
        
        auth_data = auth_response.json()
        assert "success" in auth_data
        assert "message" in auth_data
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, client):
        """Test handling of concurrent requests."""
        
        # Prepare multiple requests
        requests = [
            {"url": "https://httpbin.org/forms/post"},
            {"url": "https://httpbin.org/html"},
            {"url": "https://httpbin.org/json"}
        ]
        
        # Send concurrent field detection requests
        tasks = [
            client.post("/api/v1/web-crawlers/field-detection", json=req)
            for req in requests
        ]
        
        responses = await asyncio.gather(*tasks)
        
        # Verify all requests succeeded
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])