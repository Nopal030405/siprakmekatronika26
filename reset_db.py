import sqlite3
import os

DB_NAME = os.path.join(os.path.dirname(os.path.abspath(__file__)), "siprak.db")

def reset_database():
    if not os.path.exists(DB_NAME):
        print(f"Database {DB_NAME} not found.")
        return

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    print("Resetting database...")
    
    # Tables to clear
    tables = ['grades', 'submissions', 'modules', 'users', 'courses']
    
    for table in tables:
        c.execute(f"DELETE FROM {table}")
        print(f"Cleared table: {table}")
        
    # Reset sequences
    c.execute("DELETE FROM sqlite_sequence")
    
    # Re-seed Admin
    # 1. Default Course
    c.execute("INSERT INTO courses (name, description) VALUES (?, ?)", 
              ('Sistem Kontrol', 'Praktikum Sistem Kontrol Mekatronika 2026'))
    course_id = c.lastrowid
    
    # 2. Admin User
    c.execute("INSERT INTO users (name, role, group_id, password, course_id, is_admin, is_co_asprak, pembukuan_score) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
              ('naufal', 'ASPRAK', 0, 'admin123', course_id, 1, 0, 0))
    
    conn.commit()
    conn.close()
    print("Database has been reset to clean state (Admin only).")

if __name__ == '__main__':
    reset_database()
