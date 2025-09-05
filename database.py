import sqlite3

DB_NAME = "expenses.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    return conn

def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS periods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            period TEXT UNIQUE
        )
    """)
    conn.commit()
    conn.close()

def fetch_all_periods():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT period FROM periods ORDER BY id")
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]

def add_period(period):
    conn = get_connection()
    conn.execute("INSERT OR IGNORE INTO periods (period) VALUES (?)", (period,))
    conn.commit()
    conn.close()

# Initialize DB on import
init_db()
