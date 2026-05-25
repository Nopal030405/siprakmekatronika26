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
            asprak_id INTEGER,
            FOREIGN KEY(course_id) REFERENCES courses(id),
            FOREIGN KEY(asprak_id) REFERENCES users(id)
        )
    ''')
    
    # Modules table
    c.execute('''
        CREATE TABLE IF NOT EXISTS modules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            is_open INTEGER DEFAULT 1,
            deadline DATETIME,
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
            submitter_name TEXT,
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

    # Project Spins table check
    try:
        c.execute("SELECT course_id FROM project_spins LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("DROP TABLE IF EXISTS project_spins")

    # Project Spins table
    c.execute('''
        CREATE TABLE IF NOT EXISTS project_spins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER,
            group_id INTEGER NOT NULL,
            representative_name TEXT NOT NULL,
            project_name TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(course_id) REFERENCES courses(id),
            UNIQUE(course_id, group_id)
        )
    ''')

    # Spin Options table check
    try:
        c.execute("SELECT course_id FROM spin_options LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("DROP TABLE IF EXISTS spin_options")

    # Spin Options table
    c.execute('''
        CREATE TABLE IF NOT EXISTS spin_options (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER,
            name TEXT NOT NULL,
            FOREIGN KEY(course_id) REFERENCES courses(id),
            UNIQUE(course_id, name)
        )
    ''')

    # Settings table
    c.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    ''')

    # ========================
    # CLEANUP & MINIMAL SEEDING
    # ========================
    # Only clear if you want a fresh start, but usually we just ensure Admin exists
    # c.execute("DELETE FROM users") # Uncomment this only if you want to wipe all users
    
    # Ensure course "Sistem Kontrol" exists as a starting point
    c.execute("SELECT id FROM courses WHERE name='Sistem Kontrol'")
    course = c.fetchone()
    if not course:
        c.execute("INSERT INTO courses (name, description) VALUES (?, ?)", ('Sistem Kontrol', 'Praktikum Sistem Kontrol Mekatronika 2026'))
        course_id = c.lastrowid
    else:
        course_id = course[0]
    
    # Seed default spin options and total groups for each course if empty
    c.execute("SELECT id FROM courses")
    courses = c.fetchall()
    for crs in courses:
        cid = crs[0]
        c.execute("SELECT COUNT(*) FROM spin_options WHERE course_id=?", (cid,))
        if c.fetchone()[0] == 0:
            default_projects = [
                "Sistem Kontrol Ketinggian Platform Lift dengan Penolakan Gangguan Beban",
                "Sistem Kontrol Posisi Bola pada Bidang Miring (Ball and Beam)",
                "Sistem Kontrol Intensitas Cahaya Ruangan",
                "Sistem Kontrol Gaya Angkat Propeller (Thrust Levitation)",
                "Sistem Kontrol Sudut Pendulum Terbalik (Inverted Pendulum)",
                "Sistem Kontrol Keseimbangan Platform Satu Sumbu (Tilt Balance)",
                "Sistem Kontrol Posisi Lengan Mekanik dengan Penolakan Gangguan Beban",
                "Sistem Kontrol Ketinggian Bola Mengambang (Floating Ball)",
                "Sistem Kontrol Tracking Cahaya Matahari (Solar Tracker)",
                "Sistem Kontrol Peredam Guncangan Aktif (Active Suspension)",
                "Sistem Kontrol Levitasi Magnetik (Magnetic Levitation)",
                "Sistem Kontrol Penahan Posisi Roda Reaksi (Reaction Wheel Stabilizer)"
            ]
            for p in default_projects:
                c.execute("INSERT OR IGNORE INTO spin_options (course_id, name) VALUES (?, ?)", (cid, p))

        c.execute("SELECT COUNT(*) FROM settings WHERE key=?", (f"total_groups_{cid}",))
        if c.fetchone()[0] == 0:
            c.execute("INSERT INTO settings (key, value) VALUES (?, '12')", (f"total_groups_{cid}",))

    # Ensure Admin exists
    try:
        admin = c.execute("SELECT id FROM users WHERE is_admin=1").fetchone()
    except sqlite3.OperationalError:
        admin = None
        
    if not admin:
        try:
            c.execute("INSERT INTO users (name, role, group_id, password, course_id, is_admin, is_co_asprak, pembukuan_score) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                      ('Labmekautm', 'ASPRAK', 0, 'Labmeka030405.', course_id, 1, 0, 0))
        except sqlite3.OperationalError:
            pass
    
    conn.commit()
    conn.close()

def migrate():
    """Simple migration to add columns if they don't exist."""
    conn = get_db()
    c = conn.cursor()
    
    # Courses table
    c.execute('''CREATE TABLE IF NOT EXISTS courses (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, description TEXT)''')
    
    # Project Spins table migration check
    try:
        c.execute("SELECT course_id FROM project_spins LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("DROP TABLE IF EXISTS project_spins")
        
    c.execute('''CREATE TABLE IF NOT EXISTS project_spins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_id INTEGER,
        group_id INTEGER NOT NULL,
        representative_name TEXT NOT NULL,
        project_name TEXT NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(course_id) REFERENCES courses(id),
        UNIQUE(course_id, group_id))''')

    # Spin Options table migration check
    try:
        c.execute("SELECT course_id FROM spin_options LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("DROP TABLE IF EXISTS spin_options")
        
    c.execute('''CREATE TABLE IF NOT EXISTS spin_options (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_id INTEGER,
        name TEXT NOT NULL,
        FOREIGN KEY(course_id) REFERENCES courses(id),
        UNIQUE(course_id, name))''')

    # Settings table
    c.execute('''CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL)''')

    # Seed default spin options and total groups for each course if empty
    c.execute("SELECT id FROM courses")
    courses = c.fetchall()
    for crs in courses:
        cid = crs[0]
        c.execute("SELECT COUNT(*) FROM spin_options WHERE course_id=?", (cid,))
        if c.fetchone()[0] == 0:
            default_projects = [
                "Sistem Kontrol Ketinggian Platform Lift dengan Penolakan Gangguan Beban",
                "Sistem Kontrol Posisi Bola pada Bidang Miring (Ball and Beam)",
                "Sistem Kontrol Intensitas Cahaya Ruangan",
                "Sistem Kontrol Gaya Angkat Propeller (Thrust Levitation)",
                "Sistem Kontrol Sudut Pendulum Terbalik (Inverted Pendulum)",
                "Sistem Kontrol Keseimbangan Platform Satu Sumbu (Tilt Balance)",
                "Sistem Kontrol Posisi Lengan Mekanik dengan Penolakan Gangguan Beban",
                "Sistem Kontrol Ketinggian Bola Mengambang (Floating Ball)",
                "Sistem Kontrol Tracking Cahaya Matahari (Solar Tracker)",
                "Sistem Kontrol Peredam Guncangan Aktif (Active Suspension)",
                "Sistem Kontrol Levitasi Magnetik (Magnetic Levitation)",
                "Sistem Kontrol Penahan Posisi Roda Reaksi (Reaction Wheel Stabilizer)"
            ]
            for p in default_projects:
                c.execute("INSERT OR IGNORE INTO spin_options (course_id, name) VALUES (?, ?)", (cid, p))

        c.execute("SELECT COUNT(*) FROM settings WHERE key=?", (f"total_groups_{cid}",))
        if c.fetchone()[0] == 0:
            c.execute("INSERT INTO settings (key, value) VALUES (?, '12')", (f"total_groups_{cid}",))
    
    # Add columns if not exist
    migrations = [
        ("modules", "description", "TEXT"),
        ("modules", "is_open", "INTEGER DEFAULT 1"),
        ("modules", "deadline", "DATETIME"),
        ("modules", "course_id", "INTEGER"),
        ("grades", "pembukuan_score", "INTEGER DEFAULT 0"),
        ("users", "course_id", "INTEGER"),
        ("users", "is_admin", "INTEGER DEFAULT 0"),
        ("users", "is_co_asprak", "INTEGER DEFAULT 0"),
        ("users", "pembukuan_score", "INTEGER DEFAULT 0"),
        ("users", "asprak_id", "INTEGER"),
        ("courses", "drive_link", "TEXT"),
        ("submissions", "submitter_name", "TEXT"),
    ]
    
    for table, column, col_type in migrations:
        try:
            c.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
        except sqlite3.OperationalError:
            pass
    
    # Ensure no viewer account exists (as requested in previous cleanup)
    c.execute("DELETE FROM users WHERE role='VIEWER'")
    
    # Update existing admin to new credentials
    c.execute("UPDATE users SET name='Labmekautm', password='Labmeka030405.' WHERE is_admin=1")
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    migrate()
    print("Database initialized and migrated successfully.")
