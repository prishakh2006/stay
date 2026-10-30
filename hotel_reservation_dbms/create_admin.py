import getpass
import os

import mysql.connector
from werkzeug.security import generate_password_hash


def main():
    if "MYSQL_PASSWORD" not in os.environ:
        raise RuntimeError("Set MYSQL_PASSWORD before connecting to MySQL.")

    database_config = {
        "host": os.environ.get("DB_HOST", "localhost"),
        "user": os.environ.get("DB_USER", "root"),
        "password": os.environ["MYSQL_PASSWORD"],
        "database": os.environ.get("DB_NAME", "hotel_reservation"),
    }

    username = input("Admin username: ").strip()
    if not username or len(username) > 80:
        raise ValueError("Username is required and must be 80 characters or fewer.")

    password = getpass.getpass("Admin password (hidden): ")
    confirmation = getpass.getpass("Confirm admin password: ")
    if len(password) < 8 or len(password) > 256:
        raise ValueError("Password must be between 8 and 256 characters.")
    if password != confirmation:
        raise ValueError("The password confirmation does not match.")

    connection = None
    cursor = None
    try:
        connection = mysql.connector.connect(**database_config)
        cursor = connection.cursor()
        cursor.execute(
            """INSERT INTO `User` (username, password_hash, role, customer_id)
               VALUES (%s, %s, 'admin', NULL)""",
            (username, generate_password_hash(password)))
        connection.commit()
        print("Admin account created.")
    except mysql.connector.IntegrityError as error:
        if connection:
            connection.rollback()
        if error.errno == 1062:
            raise ValueError("That username is already in use.") from error
        raise
    except mysql.connector.Error:
        if connection:
            connection.rollback()
        raise
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


if __name__ == "__main__":
    main()
