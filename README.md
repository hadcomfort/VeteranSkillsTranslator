# Military Skills Translator

A production-grade, single-page web application designed to help military veterans translate their occupational skills into compelling, resume-ready bullet points. This project serves as a blueprint for modern web development, emphasizing best practices in security, accessibility, testing, and maintainability.

![Military Skills Translator Screenshot](https://i.imgur.com/your-screenshot.png)  <!-- Replace with an actual screenshot URL -->

## Core Principles

This application was built with a "staff-level" engineering mindset, prioritizing patterns that ensure long-term success for a development team.

*   **Production-Ready Architecture**: The backend is a stateless Flask application, suitable for deployment with any WSGI server (like Gunicorn or Waitress) and multiple worker processes.
*   **Separation of Concerns**: Configuration is kept separate from code. All environment-specific values are loaded from a `.env` file.
*   **Test-Driven Mindset**: The API is validated by a comprehensive suite of `pytest` unit tests, ensuring reliability and preventing regressions.
*   **Security by Default**: The frontend avoids XSS vulnerabilities by exclusively using `.textContent` for rendering API data. No `innerHTML` is used.
*   **Accessibility as Foundational (WCAG 2.1 AA)**: The application is fully keyboard and screen reader accessible, featuring programmatic focus management and ARIA live regions for communicating asynchronous state changes.
*   **Resilient Asynchronous Operations**: All user-initiated `fetch` requests are hardened against race conditions using the `AbortController` pattern.
*   **Scalable CSS**: Styles are built with CSS Custom Properties (Design Tokens) and a BEM-like naming convention to ensure maintainability.

## Technical Specifications

*   **Backend**: Python 3, Flask
*   **Frontend**: Vanilla JavaScript (ES6+), HTML5, CSS3
*   **Testing**: Pytest
*   **Database**: SQLite (file-based)
*   **Dependency Management**: `pip` and `requirements.txt`

## Getting Started

Follow these instructions to set up and run the project on your local machine.

### 1. Prerequisites

*   Python 3.8+
*   `pip` for package management
*   A virtual environment tool (like `venv`)

### 2. Setup Instructions

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/military-skills-translator.git
    cd military-skills-translator
    ```

2.  **Create and activate a Python virtual environment:**
    This isolates the project's dependencies from your global Python installation.
    ```bash
    # For Unix/macOS
    python3 -m venv venv
    source venv/bin/activate

    # For Windows
    python -m venv venv
    .\\venv\\Scripts\\activate
    ```

3.  **Install the required dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Create the local environment file (`.env`):**
    Copy the contents below into a new file named `.env` in the project root. This file is ignored by Git and stores your local configuration.
    ```env
    # .env
    FLASK_ENV=development
    DATABASE_PATH=instance/database.sqlite
    ```

5.  **Initialize the database:**
    Run the data import script **once** to create the SQLite database and populate it with the sample data from `data.json`.
    ```bash
    python scripts/import_data.py
    ```
    You should see output confirming the creation of tables and the import of data. The database file will be created at `instance/database.sqlite`.

### 3. Running the Application

1.  **Run the automated tests (optional but recommended):**
    Verify that the backend is working correctly before starting the server.
    ```bash
    pytest
    ```
    All tests should pass.

2.  **Start the Flask development server:**
    ```bash
    flask run
    ```
    The application will now be running at: **http://127.0.0.1:5000**

Open the URL in your web browser to use the Military Skills Translator.
