"""Foundation smoke tests — run without requiring a live database."""


def test_health_endpoint(client):
    response = client.get('/api/v1/health')
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'ok'
    assert data['service'] == 'jeyvro-backend'


def test_api_404_returns_json(client):
    response = client.get('/api/v1/definitely-not-a-real-endpoint')
    assert response.status_code == 404
    assert response['Content-Type'] == 'application/json'
    assert response.json()['error'] == 'not_found'
