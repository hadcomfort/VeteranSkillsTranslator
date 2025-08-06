# ==============================================================================
#  Military Skills Translator - Core Application
# ==============================================================================
#
#  DESCRIPTION:
#  This Flask application serves as the backend for the Military Skills
#  Translator. It provides two main endpoints:
#  1. A web interface (`/`) that renders the main HTML page.
#  2. A JSON API (`/api/mos/<mos_code>`) that provides skill data for a
#     given Military Occupational Specialty (MOS).
#
#  ARCHITECTURE:
#  - Stateless: The application itself does not hold any state between
#    requests, making it suitable for deployment with multiple worker
#    processes (e.g., using a WSGI server like Gunicorn).
#  - Configuration over Code: Key settings like the database path are loaded
#    from environment variables, not hardcoded. This is managed by `python-dotenv`.
#  - Database Management: Database connections are opened on a per-request
#    basis and closed automatically after the request is handled. This is a
#    robust pattern for managing resources in a web application.
#
# ==============================================================================

import os
import sqlite3
from flask import Flask, render_template, g, jsonify, request, session
from werkzeug.security import check_password_hash, generate_password_hash
from dotenv import load_dotenv
import functools

# --- Application Setup ---

# Load environment variables from the .env file. This should be one of the
# first things the application does to ensure all config is available.
load_dotenv()

app = Flask(__name__)
# The 'instance_relative_config=True' argument is not strictly needed here
# because we manually construct the path, but it's good practice as it makes
# Flask aware of the 'instance' folder.
app.config.from_mapping(
    SECRET_KEY=os.getenv('SECRET_KEY', 'dev'), # Default 'dev' key is for development only
    DATABASE=os.path.join(app.instance_path, os.getenv('DATABASE_PATH', 'database.sqlite'))
)

# --- Security Warning for Default Key in Production ---
#
# Check if the application is running in a production environment and is still
# using the default 'dev' secret key. This is a critical security risk. A strong,
# unique secret key should be set in the .env file for production deployments.
if os.getenv('FLASK_ENV') == 'production' and app.config['SECRET_KEY'] == 'dev':
    app.logger.warning('CRITICAL SECURITY WARNING: The default SECRET_KEY is in use in a production environment. Please set a strong, unique key in your .env file.')

# --- Auth Blueprint and Routes ---

@app.route('/api/register', methods=['POST'])
def register():
    """Registers a new user."""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    db = get_db()
    error = None

    if not username:
        error = 'Username is required.'
    elif not password:
        error = 'Password is required.'

    if error is None:
        try:
            db.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, generate_password_hash(password)),
            )
            db.commit()
        except db.IntegrityError:
            error = f"User {username} is already registered."
        else:
            return jsonify({'message': 'User created successfully'}), 201

    return jsonify({'error': error}), 400

@app.route('/api/login', methods=['POST'])
def login():
    """Logs a user in."""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    db = get_db()
    error = None
    user = db.execute(
        'SELECT * FROM users WHERE username = ?', (username,)
    ).fetchone()

    if user is None:
        error = 'Incorrect username.'
    elif not check_password_hash(user['password_hash'], password):
        error = 'Incorrect password.'

    if error is None:
        session.clear()
        session['user_id'] = user['id']
        return jsonify({'message': 'Logged in successfully'})

    return jsonify({'error': error}), 400

@app.route('/api/logout')
def logout():
    """Logs the current user out."""
    session.clear()
    return jsonify({'message': 'Logged out successfully'})

@app.before_request
def load_logged_in_user():
    """If a user id is in the session, load the user object from the db."""
    user_id = session.get('user_id')

    if user_id is None:
        g.user = None
    else:
        g.user = get_db().execute(
            'SELECT * FROM users WHERE id = ?', (user_id,)
        ).fetchone()

def login_required(view):
    """View decorator that redirects anonymous users to the login page."""
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return jsonify({'error': 'Authorization required'}), 401
        return view(**kwargs)
    return wrapped_view


# --- Database Connection Management ---

def get_db():
    """
    Establishes and retrieves the database connection for the current request.

    This function uses Flask's application context (`g`) to store the database
    connection. This ensures that the connection is created only once per
    request and is available to any part of the application logic that needs it.
    Using `sqlite3.Row` as the `row_factory` allows accessing query results
    like dictionaries (e.g., row['column_name']), which is more readable.
    """
    if 'db' not in g:
        try:
            g.db = sqlite3.connect(
                app.config['DATABASE'],
                detect_types=sqlite3.PARSE_DECLTYPES
            )
            g.db.row_factory = sqlite3.Row
        except sqlite3.OperationalError as e:
            # This is a critical error, often meaning the database file or path
            # doesn't exist or has permission issues.
            app.logger.error(f"Database connection failed: {e}")
            # In a real app, you might want a more user-friendly error page.
            # For this API-focused app, we let it fail loudly during development.
            raise
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    """
    Closes the database connection at the end of the request.

    Flask automatically calls this function after a request has been handled,
    ensuring that the database connection is always closed, even if an error
    occurred. This prevents resource leaks.
    """
    db = g.pop('db', None)
    if db is not None:
        db.close()

# --- Page-serving Routes ---

@app.route("/")
def index():
    """
    Serves the main application page.

    It queries the database for all available military occupations and passes
    them to the `index.html` template. This populates the dropdown menu on
    the frontend.
    """
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT mos_code, title FROM occupations ORDER BY title ASC")
        occupations = cursor.fetchall()
        return render_template("index.html", occupations=occupations)
    except Exception as e:
        app.logger.error(f"Failed to fetch occupations for index page: {e}")
        # Render a simple error message if the database fails.
        return "Error: Could not connect to the database to fetch occupations.", 500

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/register')
def register_page():
    return render_template('register.html')

@app.route('/profile')
@login_required
def profile_page():
    return render_template('profile.html')


@app.route('/api/skills', methods=['GET', 'POST'])
@login_required
def saved_skills():
    """Manages saved skills for the logged-in user."""
    db = get_db()
    if request.method == 'POST':
        data = request.get_json()
        skill_description = data.get('skill_description')
        if not skill_description:
            return jsonify({'error': 'Skill description is required.'}), 400

        db.execute(
            'INSERT INTO user_saved_skills (user_id, skill_description) VALUES (?, ?)',
            (g.user['id'], skill_description)
        )
        db.commit()
        return jsonify({'message': 'Skill saved successfully'}), 201

    # GET request
    skills = db.execute(
        'SELECT id, skill_description FROM user_saved_skills WHERE user_id = ?',
        (g.user['id'],)
    ).fetchall()
    return jsonify([dict(row) for row in skills])

@app.route('/api/skills/<int:skill_id>', methods=['DELETE'])
@login_required
def delete_skill(skill_id):
    """Deletes a saved skill."""
    db = get_db()
    db.execute(
        'DELETE FROM user_saved_skills WHERE id = ? AND user_id = ?',
        (skill_id, g.user['id'])
    )
    db.commit()
    return jsonify({'message': 'Skill deleted successfully'})


@app.route("/api/mos/<string:mos_code>")
def get_skills_for_mos(mos_code):
    """
    API endpoint to retrieve skills for a given MOS code.

    On Success:
    Returns a JSON object containing the MOS title and a list of skill
    descriptions.
    Example:
    {
      "title": "Infantryman",
      "skills": ["Skill 1", "Skill 2"]
    }

    On Failure (MOS not found):
    Returns a 404 Not Found response that conforms to the RFC 7807 "Problem
    Details for HTTP APIs" standard. This provides a machine-readable error
    format that clients can reliably parse.
    """
    try:
        db = get_db()
        cursor = db.cursor()

        # Query for the occupation and its skills using a JOIN.
        # This is more efficient than running two separate queries.
        query = """
            SELECT o.title, s.description
            FROM occupations o
            JOIN skills s ON o.id = s.occupation_id
            WHERE o.mos_code = ?
        """
        cursor.execute(query, (mos_code,))
        rows = cursor.fetchall()

        if not rows:
            # If the query returns no results, the MOS code is not in the database.
            # Construct the RFC 7807 problem details response.
            problem = {
                "type": "about:blank",
                "title": "Not Found",
                "status": 404,
                "detail": f"The requested MOS code '{mos_code}' was not found.",
                "instance": f"/api/mos/{mos_code}"
            }
            # The `jsonify` function correctly sets the Content-Type header
            # to `application/json`, but for strict RFC 7807 compliance,
            # `application/problem+json` is preferred.
            response = jsonify(problem)
            response.headers['Content-Type'] = 'application/problem+json'
            return response, 404

        # Process the query results into the desired JSON structure.
        title = rows[0]['title']
        skills = [row['description'] for row in rows]

        return jsonify({
            "title": title,
            "skills": skills
        })

    except Exception as e:
        # Catch-all for other potential server errors (e.g., database connection issues).
        app.logger.error(f"API error for MOS '{mos_code}': {e}")
        problem = {
            "type": "about:blank",
            "title": "Internal Server Error",
            "status": 500,
            "detail": "An unexpected error occurred on the server.",
            "instance": f"/api/mos/{mos_code}"
        }
        response = jsonify(problem)
        response.headers['Content-Type'] = 'application/problem+json'
        return response, 500

if __name__ == '__main__':
    # This block allows running the app directly for development purposes.
    # > python app.py
    # For production, a WSGI server like Gunicorn or Waitress should be used.
    app.run(debug=True)
