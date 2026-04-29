import sqlite3
conn = sqlite3.connect('siprak.db')
conn.row_factory = sqlite3.Row
for r in conn.execute("SELECT name,password,role FROM users WHERE role='ASPRAK' OR role='VIEWER'").fetchall():
    print(dict(r))
conn.close()
