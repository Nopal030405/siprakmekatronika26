import sqlite3
import os

DB_NAME = os.path.join(os.path.dirname(os.path.abspath(__file__)), "siprak.db")

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    # Courses table
    c.execute('''
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            drive_link TEXT
        )
    ''')
    
    # Users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            role TEXT NOT NULL,
            group_id INTEGER,
            password TEXT,
            course_id INTEGER,
            is_admin INTEGER DEFAULT 0,
            is_co_asprak INTEGER DEFAULT 0,
            pembukuan_score INTEGER DEFAULT 0,
            FOREIGN KEY(course_id) REFERENCES courses(id)
        )
    ''')
    
    # Modules table
    c.execute('''
        CREATE TABLE IF NOT EXISTS modules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            is_open INTEGER DEFAULT 1,
            course_id INTEGER,
            FOREIGN KEY(course_id) REFERENCES courses(id)
        )
    ''')
    
    # Submissions table
    c.execute('''
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            module_id INTEGER,
            group_id INTEGER,
            file_path TEXT,
            submitted_by INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(module_id) REFERENCES modules(id),
            FOREIGN KEY(submitted_by) REFERENCES users(id),
            UNIQUE(module_id, group_id)
        )
    ''')
    
    # Grades table (pembukuan_score kept for backward compat but no longer used per-module)
    c.execute('''
        CREATE TABLE IF NOT EXISTS grades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            praktikan_id INTEGER,
            module_id INTEGER,
            tp_score INTEGER DEFAULT 0,
            praktikum_score INTEGER DEFAULT 0,
            modul_score INTEGER DEFAULT 0,
            pembukuan_score INTEGER DEFAULT 0,
            graded_by INTEGER,
            FOREIGN KEY(praktikan_id) REFERENCES users(id),
            FOREIGN KEY(module_id) REFERENCES modules(id),
            FOREIGN KEY(graded_by) REFERENCES users(id),
            UNIQUE(praktikan_id, module_id)
        )
    ''')

    # ========================
    # SEEDING
    # ========================
    c.execute("DELETE FROM users")
    
    # Ensure course "Sistem Kontrol" exists
    c.execute("SELECT id FROM courses WHERE name='Sistem Kontrol'")
    course = c.fetchone()
    if not course:
        c.execute("INSERT INTO courses (name, description) VALUES (?, ?)", ('Sistem Kontrol', 'Praktikum Sistem Kontrol Mekatronika 2026'))
        course_id = c.lastrowid
    else:
        course_id = course[0]
    
    # Admin (Naufal) — is_admin=1
    c.execute("INSERT INTO users (name, role, group_id, password, course_id, is_admin, is_co_asprak, pembukuan_score) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
              ('naufal', 'ASPRAK', 0, 'admin123', course_id, 1, 0, 0))
    
    # Regular Aspraks for Sistem Kontrol
    aspraks = [
        ('afrian', 'ASPRAK', 0, 'pass2', course_id, 0, 0, 0),
        ('aza', 'ASPRAK', 0, 'pass3', course_id, 0, 0, 0),
        ('asad', 'ASPRAK', 0, 'pass4', course_id, 0, 0, 0),
    ]
    c.executemany("INSERT INTO users (name, role, group_id, password, course_id, is_admin, is_co_asprak, pembukuan_score) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", aspraks)
    
    # Viewer account (read-only access for portfolio)
    c.execute("INSERT INTO users (name, role, group_id, password, course_id, is_admin, is_co_asprak, pembukuan_score) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
              ('viewer', 'VIEWER', 0, 'lihat123', None, 0, 0, 0))
    
    # Praktikan for Sistem Kontrol
    praktikan_data = [
        ('Lutfi', 1), ('Freya', 1), ('Dodi', 1),
        ('Resi', 2), ('Iqbal', 2), ('Fajar madiun', 2),
        ('Anis', 3), ('fajar nganjuk', 3), ('erna', 3),
        ('Mufti', 4), ('Fadil', 4), ('Bahrul', 4),
        ('Ival', 5), ('Wisnu', 5), ('Devan', 5),
        ('Gita', 6), ('Aril', 6), ('Sindu', 6),
        ('Nopal22', 7), ('Septy', 7), ('Sodiq', 7),
        ('Imdad', 8), ('Akbar', 8), ('Naila', 8),
        ('Afrizal', 9), ('Haqqi', 9), ('Bagus', 9),
        ('Danang', 10), ('Ihsan', 10), ('tika', 10),
        ('Hapids', 11), ('Bahril', 11), ('Zikro', 11),
        ('Lazuardi', 12), ('Sahroni', 12), ('Karim', 12), ('Darma', 12),
    ]
    
    for name, group_id in praktikan_data:
        c.execute("INSERT INTO users (name, role, group_id, password, course_id, is_admin, is_co_asprak, pembukuan_score) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                  (name, 'PRAKTIKAN', group_id, None, course_id, 0, 0, 0))
        
    # Ensure Modul 1 exists for Sistem Kontrol
    c.execute("SELECT COUNT(*) FROM modules WHERE course_id=?", (course_id,))
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO modules (name, description, is_open, course_id) VALUES (?, ?, ?, ?)",
                  ('Modul 1', 'Silakan kumpulkan Modul 1.', 1, course_id))
        
    conn.commit()
    conn.close()

def migrate():
    """Simple migration to add columns if they don't exist."""
    conn = get_db()
    c = conn.cursor()
    
    # Courses table
    c.execute('''CREATE TABLE IF NOT EXISTS courses (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, description TEXT)''')
    
    # Add columns if not exist
    migrations = [
        ("modules", "description", "TEXT"),
        ("modules", "is_open", "INTEGER DEFAULT 1"),
        ("modules", "course_id", "INTEGER"),
        ("grades", "pembukuan_score", "INTEGER DEFAULT 0"),
        ("users", "course_id", "INTEGER"),
        ("users", "is_admin", "INTEGER DEFAULT 0"),
        ("users", "is_co_asprak", "INTEGER DEFAULT 0"),
        ("users", "pembukuan_score", "INTEGER DEFAULT 0"),
        ("courses", "drive_link", "TEXT"),
    ]
    
    for table, column, col_type in migrations:
        try:
            c.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
        except sqlite3.OperationalError:
            pass
    
    # Ensure viewer account exists
    viewer = c.execute("SELECT id FROM users WHERE role='VIEWER'").fetchone()
    if not viewer:
        c.execute("INSERT INTO users (name, role, group_id, password, course_id, is_admin) VALUES (?, ?, ?, ?, ?, ?)",
                  ('viewer', 'VIEWER', 0, 'lihat123', None, 0))
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    migrate()
    print("Database initialized and migrated successfully.")
