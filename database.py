import sqlite3
import json

DB_FILE = "income_expense.db"

# Initialize DB if not exists
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Table for periods
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS periods (
        period TEXT PRIMARY KEY,
        incomes TEXT,
        expenses TEXT,
        comment TEXT,
        budget_goal REAL
    )
    """)
    
    conn.commit()
    conn.close()

# Insert or update a period
def insert_period(period, incomes, expenses, comment="", budget_goal=0):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Convert dicts to JSON
    incomes_json = json.dumps(incomes)
    expenses_json = json.dumps(expenses)
    
    cursor.execute("""
        INSERT INTO periods (period, incomes, expenses, comment, budget_goal)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(period) DO UPDATE SET
            incomes=excluded.incomes,
            expenses=excluded.expenses,
            comment=excluded.comment,
            budget_goal=excluded.budget_goal
    """, (period, incomes_json, expenses_json, comment, budget_goal))
    
    conn.commit()
    conn.close()

# Fetch all periods
def fetch_all_periods():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("SELECT period FROM periods ORDER BY period")
    rows = cursor.fetchall()
    
    conn.close()
    return [r[0] for r in rows]

# Get data for a period
def get_period(period):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("SELECT incomes, expenses, comment, budget_goal FROM periods WHERE period=?", (period,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            "incomes": json.loads(row[0]),
            "expenses": json.loads(row[1]),
            "comment": row[2],
            "budget_goal": row[3]
        }
    else:
        return {
            "incomes": {},
            "expenses": {},
            "comment": "",
            "budget_goal": 0
        }

# Run this once to create the DB
init_db()
