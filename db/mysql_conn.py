import mysql.connector
from mysql.connector import Error
from config import MYSQL

def get_connection():
    """Open a fresh connection (the 'phone line' to MySQL)."""
    return mysql.connector.connect(**MYSQL)

def run_query(sql, params=None, fetch=False):
    """
    Run one query safely.
    fetch=True  -> for SELECT, returns rows as dictionaries
    fetch=False -> for INSERT/UPDATE/DELETE, commits and returns rows affected
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql, params or ())   # values travel separately from the SQL text
        if fetch:
            return cursor.fetchall()
        conn.commit()                       # without this, changes are not saved
        return cursor.rowcount
    except Error as e:
        if conn:
            conn.rollback()                 # undo a half-finished change
        print(f"Database error: {e}")
        return None
    finally:
        if conn and conn.is_connected():
            conn.close()                    # always release the connection