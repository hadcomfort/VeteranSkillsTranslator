# ==============================================================================
#  API Unit Tests for the Military Skills Translator
# ==============================================================================
#
#  DESCRIPTION:
#  This test suite uses pytest and the Flask test client to validate the
#  correctness of the backend API. The tests are designed to be run from
#  the project's root directory using the `pytest` command.
#
#  TESTING PRINCIPLES:
#  - Isolation: Each test function tests a single piece of functionality.
#  - Repeatability: Tests should produce the same result every time they are
#    run, without requiring a live server or external dependencies. The test
#    client simulates requests.
#  - Clarity: Test function names and assertions are written to be as clear
#    and descriptive as possible.
#
# ==============================================================================

import pytest
import json
import sys
import os

# This is a common pattern for making a package's modules available for testing
# when the test suite is located in a subdirectory.
# We add the project's root directory to Python's path.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app as flask_app # Import the Flask app instance

# --- Pytest Fixtures ---

@pytest.fixture
def app():
    """
    A pytest fixture that provides the Flask app instance for the tests.
    It also configures the app for testing, ensuring the database path
    is correctly resolved.
    """
    # Set the TESTING flag to True. This can disable error catching during
    # request handling, so that you get better error reports when performing
    # test requests against the application.
    flask_app.config.update({
        "TESTING": True,
    })

    # The DATABASE_PATH in .env is relative ('instance/database.sqlite').
    # When pytest runs, the current working directory may not be the project root,
    # causing the relative path to fail. Here, we create an absolute path
    # to the database and override the config for the test session.
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    db_path = os.path.join(project_root, os.getenv('DATABASE_PATH'))
    flask_app.config['DATABASE'] = db_path


    yield flask_app

@pytest.fixture
def client(app):
    """
    A pytest fixture that configures and provides a test client for the Flask app.

    The test client allows us to send HTTP requests to the application without
    having to run it on a live web server. This is the standard way to test
#    Flask applications.
    """
    # This client can be used to make requests that don't modify the session,
    # like simple GET requests.
    return app.test_client()

@pytest.fixture
def runner(app):
    """
    A fixture that provides a test runner that can be used to invoke CLI commands.
    We also use this opportunity to initialize the database for a clean slate
    before tests run.
    """
    # Before yielding, we set up the database.
    # This ensures every test function gets a clean database.
    with app.app_context():
        # This is a simplified way to re-initialize the db for tests.
        # In a larger app, you might use a dedicated test database or transactions.
        from scripts.import_data import main as init_db
        init_db()

    return app.test_cli_runner()

# --- Authentication Test Cases ---

def test_register(client):
    """Test user registration."""
    # Test successful registration
    response = client.post('/api/register', json={
        'username': 'testuser',
        'password': 'password123'
    })
    assert response.status_code == 201
    assert 'User created successfully' in response.get_json()['message']

    # Test registering a duplicate username
    response = client.post('/api/register', json={
        'username': 'testuser',
        'password': 'password123'
    })
    assert response.status_code == 400
    assert 'already registered' in response.get_json()['error']

def test_login_logout(client):
    """Test user login and logout."""
    # First, register a user to test with
    client.post('/api/register', json={'username': 'loginuser', 'password': 'password'})

    # Test successful login
    response = client.post('/api/login', json={
        'username': 'loginuser',
        'password': 'password'
    })
    assert response.status_code == 200
    assert 'Logged in successfully' in response.get_json()['message']

    # After login, a session cookie should be set.
    # We can check this by making a request to a protected route.
    response = client.get('/api/skills')
    assert response.status_code == 200 # Should succeed

    # Test logout
    response = client.get('/api/logout')
    assert response.status_code == 200

    # After logout, the session should be cleared.
    response = client.get('/api/skills')
    assert response.status_code == 401 # Should fail with Unauthorized

def test_login_invalid_credentials(client):
    """Test login with incorrect credentials."""
    client.post('/api/register', json={'username': 'creduser', 'password': 'password'})

    # Test with incorrect password
    response = client.post('/api/login', json={
        'username': 'creduser',
        'password': 'wrongpassword'
    })
    assert response.status_code == 400
    assert 'Incorrect password' in response.get_json()['error']

    # Test with incorrect username
    response = client.post('/api/login', json={
        'username': 'wronguser',
        'password': 'password'
    })
    assert response.status_code == 400
    assert 'Incorrect username' in response.get_json()['error']


# --- API Test Cases ---

def test_get_skills_success(client):
    """
    Tests the successful retrieval of skills for a valid MOS code.

    Scenario: A GET request is made to /api/mos/11B.
    Expectation: The server responds with a 200 OK status, the correct JSON
                 content type, and a payload containing the title and skills
                 for an Infantryman.
    """
    # Act: Send a GET request to a known valid endpoint.
    response = client.get("/api/mos/11B")

    # Assert: Check the response status and headers.
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'application/json'

    # Assert: Check the response payload.
    data = response.get_json()
    assert data['title'] == "Infantryman"
    assert isinstance(data['skills'], list)
    assert len(data['skills']) == 4 # Based on our sample data.json
    assert "Operated and maintained a variety of small arms and heavy weapons, ensuring operational readiness for missions." in data['skills']

def test_get_skills_not_found(client):
    """
    Tests the API's behavior when a non-existent MOS code is requested.

    Scenario: A GET request is made to /api/mos/XYZ, which does not exist.
    Expectation: The server responds with a 404 Not Found status, a content
                 type of 'application/problem+json', and a response body that
                 conforms to the RFC 7807 problem details standard.
    """
    # Act: Send a GET request to a known invalid endpoint.
    response = client.get("/api/mos/XYZ")

    # Assert: Check the response status and headers.
    assert response.status_code == 404
    assert response.headers['Content-Type'] == 'application/problem+json'

    # Assert: Check the RFC 7807 compliant response body.
    problem_details = response.get_json()
    assert problem_details['title'] == "Not Found"
    assert problem_details['status'] == 404
    assert "The requested MOS code 'XYZ' was not found." in problem_details['detail']
    assert problem_details['instance'] == "/api/mos/XYZ"

def test_root_path(client):
    """
    Tests that the root path ('/') returns a successful HTML response.

    Scenario: A GET request is made to the root of the application.
    Expectation: The server responds with a 200 OK status and HTML content,
                 indicating that the main page is being served correctly.
    """
    # Act: Send a GET request to the root URL.
    response = client.get("/")

    # Assert: Check the status code and content type.
    assert response.status_code == 200
    assert 'text/html' in response.content_type

    # Assert: Check for some expected content in the HTML body.
    # This confirms that the template is rendering.
    assert b"Military Skills Translator" in response.data
