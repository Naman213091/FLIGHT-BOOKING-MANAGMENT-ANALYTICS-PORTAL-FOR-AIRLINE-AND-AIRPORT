"""
db.py
Handles the MySQL connection for the Flight Booking & Analytics Portal.
"""

import mysql.connector
from mysql.connector import pooling

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "your_password",   # change this
    "database": "flight_portal",
}

# A small connection pool so multiple requests don't fight over one connection
connection_pool = pooling.MySQLConnectionPool(
    pool_name="flight_pool",
    pool_size=5,
    **DB_CONFIG
)


def get_connection():
    """Grab a connection from the pool."""
    return connection_pool.get_connection()


def run_query(query, params=None, fetch=False, fetch_one=False, commit=False):
    """
    Small helper to avoid repeating boilerplate cursor code everywhere.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(query, params or ())
        result = None
        if fetch_one:
            result = cursor.fetchone()
        elif fetch:
            result = cursor.fetchall()
        if commit:
            conn.commit()
            result = cursor.lastrowid
        return result
    finally:
        cursor.close()
        conn.close()
