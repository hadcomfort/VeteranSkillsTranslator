# ==============================================================================
#  Data Import Script
# ==============================================================================
#
#  DESCRIPTION:
#  This script is a one-time utility to set up the application's database.
#  It reads occupation and skill data from a JSON file (`data.json`) and
#  populates a SQLite database. This script is designed to be idempotent;
#  it first deletes any existing tables to ensure a clean slate on each run.
#
#  USAGE:
#  Run this script from the root of the project directory:
#  > python scripts/import_data.py
#
#  ENVIRONMENT VARIABLES:
#  - DATABASE_PATH: The file path for the SQLite database. This is loaded
#    from the .env file.
#
# ==============================================================================

import os
import sqlite3
import json
from dotenv import load_dotenv

def main():
    """
    Orchestrates the database setup process: loading environment variables,
    connecting to the database, creating tables, and importing data.
    """
    # --- Environment Setup ---
    # Load environment variables from .env file located in the project root.
    # find_dotenv() will search for the .env file in the parent directories,
    # which is crucial for running this script from the project root.
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    load_dotenv(os.path.join(project_root, '.env'))

    db_path = os.getenv('DATABASE_PATH')

    if not db_path:
        print("Error: DATABASE_PATH environment variable not set.")
        print("Please ensure a .env file exists in the project root with the DATABASE_PATH variable.")
        return

    # Ensure the instance directory exists.
    db_dir = os.path.dirname(db_path)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)
        print(f"Created directory: {db_dir}")

    # --- Database Connection and Schema Creation ---
    try:
        # The 'with' statement ensures the connection is automatically closed.
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            print(f"Successfully connected to database at {db_path}")

            # Drop existing tables to ensure a fresh start (idempotency).
            # This is useful for development and testing.
            print("Dropping existing tables if they exist...")
            cursor.execute("DROP TABLE IF EXISTS user_saved_skills")
            cursor.execute("DROP TABLE IF EXISTS users")
            cursor.execute("DROP TABLE IF EXISTS skills")
            cursor.execute("DROP TABLE IF EXISTS occupations")

            # Create the 'users' table.
            print("Creating 'users' table...")
            cursor.execute("""
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL
                )
            """)

            # Create the 'occupations' table.
            # This table stores the Military Occupational Specialty (MOS) codes
            # and their corresponding titles.
            print("Creating 'occupations' table...")
            cursor.execute("""
                CREATE TABLE occupations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mos_code TEXT NOT NULL UNIQUE,
                    title TEXT NOT NULL
                )
            """)

            # Create the 'skills' table.
            # This table stores the individual skill bullet points.
            # It uses a foreign key to link each skill back to an occupation.
            # The ON DELETE CASCADE ensures that if an occupation is deleted,
            # all its associated skills are also deleted.
            print("Creating 'skills' table...")
            cursor.execute("""
                CREATE TABLE skills (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    occupation_id INTEGER NOT NULL,
                    description TEXT NOT NULL,
                    FOREIGN KEY (occupation_id) REFERENCES occupations (id) ON DELETE CASCADE
                )
            """)

            # Create the 'user_saved_skills' table.
            # This table links users to the skills they have saved.
            print("Creating 'user_saved_skills' table...")
            cursor.execute("""
                CREATE TABLE user_saved_skills (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    skill_description TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            """)

            print("Database tables created successfully.")

            # --- Data Import ---
            import_data(cursor)

            # Commit the changes to the database.
            conn.commit()
            print("Data committed to the database.")

    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except FileNotFoundError:
        print(f"Error: data.json not found in project root.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

def import_data(cursor):
    """
    Reads data from data.json and inserts it into the database tables.

    Args:
        cursor: A sqlite3.Cursor object to execute SQL commands.
    """
    print("\nStarting data import from data.json...")

    # Construct the path to data.json relative to this script's location.
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    json_path = os.path.join(project_root, 'data.json')

    with open(json_path, 'r') as f:
        data = json.load(f)

    # --- Import Occupations ---
    occupations_data = data.get('occupations', [])
    if not occupations_data:
        print("No occupations found in data.json.")
        return

    print(f"Importing {len(occupations_data)} occupations...")
    for occ in occupations_data:
        # Using parameterized queries to prevent SQL injection.
        cursor.execute(
            "INSERT INTO occupations (mos_code, title) VALUES (?, ?)",
            (occ['mos'], occ['title'])
        )
    print("Occupations imported successfully.")

    # --- Import Skills ---
    skills_data = data.get('skills', {})
    if not skills_data:
        print("No skills found in data.json.")
        return

    print(f"Importing skills for {len(skills_data)} occupations...")
    for mos_code, skills_list in skills_data.items():
        # First, get the primary key of the occupation we just inserted.
        cursor.execute("SELECT id FROM occupations WHERE mos_code = ?", (mos_code,))
        result = cursor.fetchone()

        if result:
            occupation_id = result[0]
            for skill_desc in skills_list:
                cursor.execute(
                    "INSERT INTO skills (occupation_id, description) VALUES (?, ?)",
                    (occupation_id, skill_desc)
                )
            print(f"  - Imported {len(skills_list)} skills for {mos_code}")
        else:
            print(f"  - Warning: Could not find occupation_id for {mos_code}. Skills not imported.")

    print("\nData import process finished.")

if __name__ == "__main__":
    main()
