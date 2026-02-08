import pytest
from server import flask_app
from state import global_state

@pytest.fixture
def client():
    flask_app.config['TESTING'] = True
    with flask_app.test_client() as client:
        yield client

def test_get_response_default(client):
    """Test response endpoint with default state."""
    # Reset state just in case
    global_state.update_response("No response yet.")
    
    rv = client.get('/response')
    json_data = rv.get_json()
    
    assert rv.status_code == 200
    assert json_data == {"response": "No response yet."}

def test_get_response_updated(client):
    """Test response endpoint after state update."""
    global_state.update_response("New AI Code Hint")
    
    rv = client.get('/response')
    json_data = rv.get_json()
    
    assert rv.status_code == 200
    assert json_data == {"response": "New AI Code Hint"}
