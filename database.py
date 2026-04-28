import sqlite3
import os

DB_NAME = "siprak.db"

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    # Users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            role TEXT NOT NULL, -- 'ASPRAK' or 'PRAKTIKAN'
            group_id INTEGER,
            password TEXT -- for ASPRAK
        )
    ''')
    
    # Modules table
    c.execute('''
        CREATE TABLE IF NOT EXISTS modules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            is_open INTEGER DEFAULT 1
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
    
    # Grades table
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

    # Seeding
    # Clear existing users to reset to image specifications
    c.execute("DELETE FROM users")
    
    # 4 Asprak from image
    aspraks = [
        ('nopal', 'ASPRAK', 0, 'pass1'), # Asprak 1 (Peach)
        ('afrian', 'ASPRAK', 0, 'pass2'), # Asprak 2 (Yellow)
        ('aza', 'ASPRAK', 0, 'pass3'),    # Asprak 3 (Green)
        ('asad', 'ASPRAK', 0, 'pass4')     # Asprak 4 (Blue)
    ]
    c.executemany("INSERT INTO users (name, role, group_id, password) VALUES (?, ?, ?, ?)", aspraks)
    
    # Praktikan Mapping from image
    # Format: (Name, GroupID)
    praktikan_data = [
        # Kel 1 (Nopal)
        ('Lutfi', 1), ('Freya', 1), ('Dodi', 1),
        # Kel 2 (Afrian)
        ('Resi', 2), ('Iqbal', 2), ('Fajar madiun', 2),
        # Kel 3 (Aza)
        ('Anis', 3), ('fajar nganjuk', 3), ('erna', 3),
        # Kel 4 (Asad)
        ('Mufti', 4), ('Fadil', 4), ('Bahrul', 4),
        # Kel 5 (Aza)
        ('Ival', 5), ('Wisnu', 5), ('Devan', 5),
        # Kel 6 (Nopal)
        ('Gita', 6), ('Aril', 6), ('Sindu', 6),
        # Kel 7 (Nopal)
        ('Nopal22', 7), ('Septy', 7), ('Sodiq', 7),
        # Kel 8 (Afrian)
        ('Imdad', 8), ('Akbar', 8), ('Naila', 8),
        # Kel 9 (Aza)
        ('Afrizal', 9), ('Haqqi', 9), ('Bagus', 9),
        # Kel 10 (Asad)
        ('Danang', 10), ('Ihsan', 10), ('tika', 10),
        # Kel 11 (Afrian)
        ('Hapids', 11), ('Bahril', 11), ('Zikro', 11),
        # Kel 12 (Asad)
        ('Lazuardi', 12), ('Sahroni', 12), ('Karim', 12), ('Darma', 12)
    ]
    
    for name, group_id in praktikan_data:
        c.execute("INSERT INTO users (name, role, group_id, password) VALUES (?, ?, ?, ?)", (name, 'PRAKTIKAN', group_id, None))
        
    # Ensure Modul 1 exists if fresh
    c.execute("SELECT COUNT(*) FROM modules")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO modules (name, description, is_open) VALUES (?, ?, ?)", ('Modul 1', 'Silakan kumpulkan Modul 1.', 1))
        
    conn.commit()
    conn.close()

def migrate():
    """Simple migration to add columns if they don't exist."""
    conn = get_db()
    c = conn.cursor()
    # Add description if not exist
    try:
        c.execute("ALTER TABLE modules ADD COLUMN description TEXT")
    except sqlite3.OperationalError:
        pass
    # Add is_open if not exist
    try:
        c.execute("ALTER TABLE modules ADD COLUMN is_open INTEGER DEFAULT 1")
    except sqlite3.OperationalError:
        pass
    # Add pembukuan_score if not exist
    try:
        c.execute("ALTER TABLE grades ADD COLUMN pembukuan_score INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    migrate()
    print("Database initialized and migrated successfully.")

