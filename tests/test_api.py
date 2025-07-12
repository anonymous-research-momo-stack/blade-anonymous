"""
API测试
"""

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_root():
    """测试根端点"""
    response = client.get("/api/v1/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "BSCA Expert Agent API"
    assert data["version"] == "1.0.0"


def test_health_check():
    """测试健康检查端点"""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "1.0.0"
    assert "BSCA Expert Agent API is running" in data["message"] 