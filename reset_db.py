import sqlite3
import os

# Gunakan path yang sama dengan database.py
DB_NAME = os.path.join(os.path.dirname(os.path.abspath(__file__)), "siprak.db")

def reset_all_data():
    if not os.path.exists(DB_NAME):
        print("Database tidak ditemukan.")
        return

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    print("--- Memulai Pembersihan Data ---")

    # 1. Hapus semua praktikan
    c.execute("DELETE FROM users WHERE role = 'PRAKTIKAN'")
    print(f"Hapus Praktikan: {c.rowcount} baris")

    # 2. Hapus semua asprak kecuali admin
    c.execute("DELETE FROM users WHERE role = 'ASPRAK' AND is_admin = 0")
    print(f"Hapus Asprak (non-admin): {c.rowcount} baris")

    # 3. Hapus semua modul
    c.execute("DELETE FROM modules")
    print(f"Hapus Modul: {c.rowcount} baris")

    # 4. Hapus semua pengumpulan (submissions)
    c.execute("DELETE FROM submissions")
    print(f"Hapus Submissions: {c.rowcount} baris")

    # 5. Hapus semua nilai (grades)
    c.execute("DELETE FROM grades")
    print(f"Hapus Nilai: {c.rowcount} baris")

    # 6. Kosongkan link GDrive dummy di tabel courses
    c.execute("UPDATE courses SET drive_link = NULL")
    print(f"Update Link GDrive Course: {c.rowcount} baris dikosongkan")

    conn.commit()
    conn.close()
    print("--- Pembersihan Selesai. Database sekarang bersih! ---")

if __name__ == '__main__':
    confirm = input("Apakah Anda yakin ingin MENGHAPUS semua data praktikan, modul, dan asprak (kecuali admin)? (y/n): ")
    if confirm.lower() == 'y':
        reset_all_data()
    else:
        print("Dibatalkan.")
