import os
import io
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory, send_file
from werkzeug.utils import secure_filename
from database import get_db
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill

app = Flask(__name__)
app.secret_key = 'super_secret_siprak_key' # for session and flash

GDRIVE_UPLOAD_FOLDER = r'G:\My Drive\Siprak'
LOCAL_UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')

# Use Google Drive if available, otherwise fall back to local
if os.path.isdir(r'G:\My Drive'):
    UPLOAD_FOLDER = GDRIVE_UPLOAD_FOLDER
    print(f"[SiPrak] Uploads will be saved to Google Drive: {UPLOAD_FOLDER}")
else:
    UPLOAD_FOLDER = LOCAL_UPLOAD_FOLDER
    print(f"[SiPrak] Google Drive not found. Using local folder: {UPLOAD_FOLDER}")

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'zip'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# =======================
# HELPER FUNCTIONS
# =======================
def get_letter_grade(score):
    """Convert numeric score to letter grade."""
    if score >= 85:
        return 'A'
    elif score >= 80:
        return 'B+'
    elif score >= 75:
        return 'B'
    elif score >= 70:
        return 'C+'
    elif score >= 60:
        return 'C'
    elif score >= 50:
        return 'D+'
    elif score >= 40:
        return 'D'
    else:
        return 'E'

def calculate_module_avg(grade):
    """Calculate average score for a single module: (TP + Praktikum + Modul) / 3"""
    tp = grade.get('tp_score', 0) or 0
    prak = grade.get('praktikum_score', 0) or 0
    modul = grade.get('modul_score', 0) or 0
    return round((int(tp) + int(prak) + int(modul)) / 3, 1)

def calculate_total(grades_dict, modules):
    """Calculate total: average of all module averages + pembukuan."""
    if not modules or not grades_dict:
        return 0
    
    module_avgs = []
    pembukuan_total = 0
    for m in modules:
        g = grades_dict.get(m['id'], {})
        avg = calculate_module_avg(g)
        module_avgs.append(avg)
        pembukuan_total += int(g.get('pembukuan_score', 0) or 0)
    
    if module_avgs:
        modules_avg = sum(module_avgs) / len(module_avgs)
    else:
        modules_avg = 0
    
    pembukuan_avg = pembukuan_total / len(modules) if modules else 0
    total = modules_avg + pembukuan_avg
    return round(min(total, 100), 1)

def get_allowed_groups(asprak_name):
    """Return allowed groups for a given asprak."""
    name = asprak_name.lower()
    if name == 'nopal':
        return (1, 6, 7)
    elif name == 'afrian':
        return (2, 8, 11)
    elif name == 'aza':
        return (3, 5, 9)
    elif name == 'asad':
        return (4, 10, 12)
    return ()

@app.context_processor
def inject_user():
    user = None
    if 'user_id' in session:
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        conn.close()
    return dict(current_user=user)

@app.route('/')
def index():
    return render_template('index.html')

# =======================
# PRAKTIKAN ROUTES
# =======================
@app.route('/praktikan', methods=['GET'])
def praktikan_dashboard():
    conn = get_db()
    groups = conn.execute('SELECT DISTINCT group_id FROM users WHERE role="PRAKTIKAN" ORDER BY group_id').fetchall()
    modules = conn.execute('SELECT * FROM modules').fetchall()
    conn.close()
    return render_template('praktikan.html', groups=groups, modules=modules)

@app.route('/praktikan/submit', methods=['POST'])
def praktikan_submit():
    group_id = request.form.get('group_id')
    module_id = request.form.get('module_id')
    praktikan_name = request.form.get('praktikan_name')
    
    if 'file' not in request.files:
        flash('Tidak ada file bagian form', 'error')
        return redirect(url_for('praktikan_dashboard'))
    
    file = request.files['file']
    if file.filename == '':
        flash('Tidak ada file yang dipilih', 'error')
        return redirect(url_for('praktikan_dashboard'))
        
    if file and allowed_file(file.filename):
        conn = get_db()
        # Check if module is open
        module = conn.execute('SELECT is_open FROM modules WHERE id = ?', (module_id,)).fetchone()
        if not module or not module['is_open']:
            flash('Pengumpulan untuk modul ini sudah ditutup!', 'error')
            conn.close()
            return redirect(url_for('praktikan_dashboard'))

        # Check if already submitted
        existing = conn.execute('SELECT * FROM submissions WHERE group_id = ? AND module_id = ?', (group_id, module_id)).fetchone()
        if existing:
            flash('Kelompok Anda sudah mengumpulkan untuk modul ini!', 'error')
            conn.close()
            return redirect(url_for('praktikan_dashboard'))
            
        user = conn.execute('SELECT id FROM users WHERE role="PRAKTIKAN" AND group_id=? AND name LIKE ?', (group_id, f'%{praktikan_name}%')).fetchone()
        user_id = user['id'] if user else None
        
        filename = secure_filename(f"Kelompok_{group_id}_Modul_{module_id}_{file.filename}")
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        conn.execute('INSERT INTO submissions (module_id, group_id, file_path, submitted_by) VALUES (?, ?, ?, ?)',
                     (module_id, group_id, filename, user_id))
        conn.commit()
        conn.close()
        
        flash('Modul berhasil dikumpulkan!', 'success')
        return redirect(url_for('praktikan_dashboard'))
    else:
        flash('Ekstensi file tidak diizinkan. Gunakan PDF/DOC/DOCX/ZIP', 'error')
        return redirect(url_for('praktikan_dashboard'))


# =======================
# ASPRAK ROUTES
# =======================
@app.route('/asprak/login', methods=['GET', 'POST'])
def asprak_login():
    # Redirect if already logged in
    if 'role' in session and session['role'] == 'ASPRAK':
        return redirect(url_for('asprak_dashboard'))
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        password = request.form.get('password')
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE role="ASPRAK" AND LOWER(name)=LOWER(?) AND password=?', (name, password)).fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user['id']
            session['role'] = user['role']
            return redirect(url_for('asprak_dashboard'))
        else:
            flash('Login gagal, periksa nama atau password', 'error')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/asprak')
def asprak_dashboard():
    if 'role' not in session or session['role'] != 'ASPRAK':
        return redirect(url_for('asprak_login'))
        
    conn = get_db()
    modules = conn.execute('SELECT * FROM modules').fetchall()
    
    user_id = session['user_id']
    user = conn.execute('SELECT name FROM users WHERE id=?', (user_id,)).fetchone()
    asprak_name = user['name']
    allowed_groups = get_allowed_groups(asprak_name)

    placeholders = ','.join('?' for _ in allowed_groups)
    
    if not allowed_groups:
        submissions = []
        praktikans_raw = []
    else:
        # Get submissions and check if files still exist on disk
        submissions_raw = conn.execute(f'''
            SELECT s.*, m.name as module_name, u.name as submitter_name
            FROM submissions s
            JOIN modules m ON s.module_id = m.id
            LEFT JOIN users u ON s.submitted_by = u.id
            WHERE s.group_id IN ({placeholders})
            ORDER BY s.timestamp DESC
        ''', allowed_groups).fetchall()
        
        # Check file existence and clean up missing files
        submissions = []
        for sub in submissions_raw:
            sub_dict = dict(sub)
            file_full_path = os.path.join(app.config['UPLOAD_FOLDER'], sub['file_path'])
            if os.path.exists(file_full_path):
                sub_dict['file_exists'] = True
            else:
                # File was deleted from Drive, remove from DB
                conn.execute('DELETE FROM submissions WHERE id=?', (sub['id'],))
                conn.commit()
                continue  # skip this entry
            submissions.append(sub_dict)
        
        praktikans_raw = conn.execute(f'''
            SELECT * FROM users 
            WHERE role="PRAKTIKAN" AND group_id IN ({placeholders})
            ORDER BY group_id, name
        ''', allowed_groups).fetchall()
    
    # Build praktikan data with grades and totals
    praktikans = []
    modules_list = [dict(m) for m in modules]
    for p in praktikans_raw:
        p_dict = dict(p)
        grades_raw = conn.execute('SELECT * FROM grades WHERE praktikan_id=?', (p['id'],)).fetchall()
        p_dict['grades'] = {g['module_id']: dict(g) for g in grades_raw}
        
        # Calculate total and letter grade
        total = calculate_total(p_dict['grades'], modules_list)
        p_dict['total'] = total
        p_dict['letter'] = get_letter_grade(total)
        praktikans.append(p_dict)
        
    conn.close()
    return render_template('asprak.html', modules=modules, submissions=submissions, praktikans=praktikans,
                           calculate_module_avg=calculate_module_avg)

@app.route('/asprak/grade_batch', methods=['POST'])
def asprak_grade_batch():
    if 'role' not in session or session['role'] != 'ASPRAK':
        return redirect(url_for('asprak_login'))
        
    graded_by = session['user_id']
    conn = get_db()
    
    for key, value in request.form.items():
        # Handle Name Updates
        if key.startswith('praktikan_name_'):
            p_id = key.split('_')[2]
            new_name = value
            if new_name:
                conn.execute('UPDATE users SET name=? WHERE id=?', (new_name, p_id))

        # Handle Grade Updates
        if key.startswith('tp_score_'):
            parts = key.split('_')
            p_id = parts[2]
            m_id = parts[3]
            
            tp = value or 0
            prak = request.form.get(f'praktikum_score_{p_id}_{m_id}', 0)
            modul = request.form.get(f'modul_score_{p_id}_{m_id}', 0)
            pembukuan = request.form.get(f'pembukuan_score_{p_id}_{m_id}', 0)
            
            existing = conn.execute('SELECT id FROM grades WHERE praktikan_id=? AND module_id=?', (p_id, m_id)).fetchone()
            if existing:
                conn.execute('''
                    UPDATE grades 
                    SET tp_score=?, praktikum_score=?, modul_score=?, pembukuan_score=?, graded_by=?
                    WHERE id=?
                ''', (tp, prak, modul, pembukuan, graded_by, existing['id']))
            else:
                conn.execute('''
                    INSERT INTO grades (praktikan_id, module_id, tp_score, praktikum_score, modul_score, pembukuan_score, graded_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (p_id, m_id, tp, prak, modul, pembukuan, graded_by))
                
    conn.commit()
    conn.close()
    flash('Semua perubahan (nama & nilai) berhasil disimpan!', 'success')
    return redirect(url_for('asprak_dashboard'))

# =======================
# EXPORT EXCEL
# =======================
@app.route('/asprak/export')
def export_excel():
    if 'role' not in session or session['role'] != 'ASPRAK':
        return redirect(url_for('asprak_login'))
    
    conn = get_db()
    modules = conn.execute('SELECT * FROM modules').fetchall()
    modules_list = [dict(m) for m in modules]
    
    user = conn.execute('SELECT name FROM users WHERE id=?', (session['user_id'],)).fetchone()
    asprak_name = user['name']
    allowed_groups = get_allowed_groups(asprak_name)
    
    if not allowed_groups:
        flash('Tidak ada data untuk diekspor', 'error')
        conn.close()
        return redirect(url_for('asprak_dashboard'))
    
    placeholders = ','.join('?' for _ in allowed_groups)
    praktikans_raw = conn.execute(f'''
        SELECT * FROM users 
        WHERE role="PRAKTIKAN" AND group_id IN ({placeholders})
        ORDER BY group_id, name
    ''', allowed_groups).fetchall()
    
    # Get submissions status
    submissions = conn.execute(f'''
        SELECT module_id, group_id FROM submissions 
        WHERE group_id IN ({placeholders})
    ''', allowed_groups).fetchall()
    submission_set = {(s['module_id'], s['group_id']) for s in submissions}
    
    # Build data
    praktikans = []
    for p in praktikans_raw:
        p_dict = dict(p)
        grades_raw = conn.execute('SELECT * FROM grades WHERE praktikan_id=?', (p['id'],)).fetchall()
        p_dict['grades'] = {g['module_id']: dict(g) for g in grades_raw}
        total = calculate_total(p_dict['grades'], modules_list)
        p_dict['total'] = total
        p_dict['letter'] = get_letter_grade(total)
        praktikans.append(p_dict)
    
    conn.close()
    
    # Create Excel workbook
    wb = Workbook()
    ws = wb.active
    ws.title = f"Nilai {asprak_name}"
    
    # Styles
    header_font = Font(bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="4F46E5", end_color="4F46E5", fill_type="solid")
    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )
    center = Alignment(horizontal='center', vertical='center')
    grade_fill_a = PatternFill(start_color="D4EDDA", end_color="D4EDDA", fill_type="solid")
    grade_fill_e = PatternFill(start_color="F8D7DA", end_color="F8D7DA", fill_type="solid")
    
    # Header row
    headers = ['No', 'Nama', 'Kelompok']
    for m in modules_list:
        headers.extend([f'{m["name"]} TP', f'{m["name"]} Prak', f'{m["name"]} Modul', f'{m["name"]} Pembukuan', f'{m["name"]} Status'])
    headers.extend(['Total', 'Huruf'])
    
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center
        cell.border = thin_border
    
    # Data rows
    for row_idx, p in enumerate(praktikans, 2):
        ws.cell(row=row_idx, column=1, value=row_idx - 1).border = thin_border
        ws.cell(row=row_idx, column=1).alignment = center
        ws.cell(row=row_idx, column=2, value=p['name']).border = thin_border
        ws.cell(row=row_idx, column=3, value=f"Kel {p['group_id']}").border = thin_border
        ws.cell(row=row_idx, column=3).alignment = center
        
        col_idx = 4
        for m in modules_list:
            g = p['grades'].get(m['id'], {})
            tp = int(g.get('tp_score', 0) or 0)
            prak = int(g.get('praktikum_score', 0) or 0)
            modul = int(g.get('modul_score', 0) or 0)
            pembukuan = int(g.get('pembukuan_score', 0) or 0)
            
            # Check submission status
            submitted = (m['id'], p['group_id']) in submission_set
            status = '✅ Terkumpul' if submitted else '❌ Belum'
            
            for val in [tp, prak, modul, pembukuan]:
                cell = ws.cell(row=row_idx, column=col_idx, value=val)
                cell.border = thin_border
                cell.alignment = center
                col_idx += 1
            
            cell = ws.cell(row=row_idx, column=col_idx, value=status)
            cell.border = thin_border
            cell.alignment = center
            col_idx += 1
        
        # Total
        total_cell = ws.cell(row=row_idx, column=col_idx, value=p['total'])
        total_cell.border = thin_border
        total_cell.alignment = center
        total_cell.font = Font(bold=True)
        col_idx += 1
        
        # Letter grade
        letter_cell = ws.cell(row=row_idx, column=col_idx, value=p['letter'])
        letter_cell.border = thin_border
        letter_cell.alignment = center
        letter_cell.font = Font(bold=True, size=12)
        if p['letter'] in ('A', 'B+', 'B'):
            letter_cell.fill = grade_fill_a
        elif p['letter'] in ('D', 'E'):
            letter_cell.fill = grade_fill_e
    
    # Auto-fit column widths
    for col in ws.columns:
        max_length = 0
        for cell in col:
            if cell.value:
                max_length = max(max_length, len(str(cell.value)))
        ws.column_dimensions[col[0].column_letter].width = max(max_length + 3, 10)
    
    # Save to bytes
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'Nilai_Praktikum_{asprak_name}.xlsx'
    )

# =======================
# MODULE MANAGEMENT
# =======================
@app.route('/asprak/module/toggle_status', methods=['POST'])
def toggle_module_status():
    if 'role' not in session or session['role'] != 'ASPRAK':
        return redirect(url_for('asprak_login'))
    
    conn = get_db()
    user = conn.execute('SELECT name FROM users WHERE id=?', (session['user_id'],)).fetchone()
    if not user or user['name'].lower() != 'nopal':
        conn.close()
        flash('Hanya Asprak Utama (Nopal) yang dapat membuka/tutup pengumpulan', 'error')
        return redirect(url_for('asprak_dashboard'))
    
    module_id = request.form.get('module_id')
    current_status = request.form.get('current_status', type=int)
    new_status = 0 if current_status == 1 else 1
    
    conn.execute('UPDATE modules SET is_open=? WHERE id=?', (new_status, module_id))
    conn.commit()
    conn.close()
    
    msg = "dibuka" if new_status == 1 else "ditutup"
    flash(f'Pengumpulan modul berhasil {msg}!', 'success')
    return redirect(url_for('asprak_dashboard'))

@app.route('/asprak/module/add', methods=['POST'])
def add_module():
    if 'role' not in session or session['role'] != 'ASPRAK':
        return redirect(url_for('asprak_login'))
    
    conn = get_db()
    user = conn.execute('SELECT name FROM users WHERE id=?', (session['user_id'],)).fetchone()
    if not user or user['name'].lower() != 'nopal':
        conn.close()
        flash('Hanya Asprak Utama (Nopal) yang dapat menambah modul', 'error')
        return redirect(url_for('asprak_dashboard'))
    
    name = request.form.get('name')
    desc = request.form.get('description')
    
    if name:
        conn.execute('INSERT INTO modules (name, description, is_open) VALUES (?, ?, 1)', (name, desc))
        conn.commit()
        flash(f'Modul {name} berhasil ditambahkan', 'success')
    
    conn.close()
    return redirect(url_for('asprak_dashboard'))

@app.route('/asprak/module/edit', methods=['POST'])
def edit_module():
    if 'role' not in session or session['role'] != 'ASPRAK':
        return redirect(url_for('asprak_login'))
    
    conn = get_db()
    user = conn.execute('SELECT name FROM users WHERE id=?', (session['user_id'],)).fetchone()
    if not user or user['name'].lower() != 'nopal':
        conn.close()
        flash('Hanya Asprak Utama (Nopal) yang dapat mengedit modul', 'error')
        return redirect(url_for('asprak_dashboard'))
    
    module_id = request.form.get('module_id')
    name = request.form.get('name')
    desc = request.form.get('description')
    
    conn.execute('UPDATE modules SET name=?, description=? WHERE id=?', (name, desc, module_id))
    conn.commit()
    conn.close()
    flash('Instruksi modul berhasil diperbarui', 'success')
    return redirect(url_for('asprak_dashboard'))

@app.route('/asprak/submissions/delete/<int:id>', methods=['POST'])
def delete_submission(id):
    if 'role' not in session or session['role'] != 'ASPRAK':
        return redirect(url_for('asprak_login'))
        
    conn = get_db()
    sub = conn.execute('SELECT * FROM submissions WHERE id=?', (id,)).fetchone()
    if sub:
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], sub['file_path']))
        except Exception:
            pass
        conn.execute('DELETE FROM submissions WHERE id=?', (id,))
        conn.commit()
        flash('Pengumpulan berhasil direset/dihapus', 'success')
    conn.close()
    return redirect(url_for('asprak_dashboard'))

@app.route('/uploads/<name>')
def download_file(name):
    return send_from_directory(app.config['UPLOAD_FOLDER'], name)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
