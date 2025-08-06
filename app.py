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
from flask import Flask, render_template, g, jsonify
from dotenv import load_dotenv

# --- Application Setup ---

# Load environment variables from the .env file. This should be one of the
# first things the application does to ensure all config is available.
load_dotenv()

app = Flask(__name__)
# The 'instance_relative_config=True' argument is not strictly needed here
# because we manually construct the path, but it's good practice as it makes
# Flask aware of the 'instance' folder.
app.config.from_mapping(
    DATABASE=os.path.join(app.instance_path, os.getenv('DATABASE_PATH', 'database.sqlite'))
)

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

# --- Application Routes ---

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
