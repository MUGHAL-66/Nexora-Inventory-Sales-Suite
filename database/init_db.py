"""Initialize the database schema without modifying existing records."""

from database.connection import initialize_database


if __name__ == "__main__":
    initialize_database()
    print("Database initialization completed. Existing records were not dropped.")
