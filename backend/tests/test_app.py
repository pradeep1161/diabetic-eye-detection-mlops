import pytest
from backend.app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_health_check(client):
    """Test the health check endpoint."""
    response = client.get('/api/health')
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data['status'] == 'healthy'

def test_analyze_no_image(client):
    """Test the analyze endpoint without providing an image."""
    response = client.post('/api/analyze')
    assert response.status_code == 400
    json_data = response.get_json()
    assert 'error' in json_data
