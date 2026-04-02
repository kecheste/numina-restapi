from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

client = TestClient(app)

def test_health_endpoint():
    response = client.get(f"{settings.api_v1_prefix}/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "numina-api"}
