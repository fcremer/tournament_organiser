import pytest
from app import app

@pytest.fixture
def client():
    app.testing = True
    return app.test_client()

def test_index_status_code(client):
    response = client.get('/')
    assert response.status_code == 200

def test_archive_status_code(client):
    response = client.get('/archive')
    assert response.status_code == 200