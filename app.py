from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import sqlite3
import os
from datetime import datetime
import secrets
import segno
from io import StringIO, BytesIO
import csv

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')

# Configuration
DATABASE = 'hackathon.db'
ADMIN_TOKEN = os.environ.get('ADMIN_TOKEN', 'admin123')
BASE_URL = os.environ.get('BASE_URL', 'http://localhost:5000')

def get_db():
    """Get database connection"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database with tables"""
    conn = get_db()
    
    # Teams table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            college TEXT NOT NULL,
            team_size INTEGER,
            leader_name TEXT NOT NULL,
            leader_email TEXT NOT NULL,
            leader_phone TEXT NOT NULL,
            token TEXT UNIQUE NOT NULL,
            is_present INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Members table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id TEXT NOT NULL,
            name TEXT NOT NULL,
            phone TEXT,
            gender TEXT,
            is_present INTEGER DEFAULT 0,
            FOREIGN KEY (team_id) REFERENCES teams (team_id)
        )
    ''')
    
    # Team attendance log
    conn.execute('''
        CREATE TABLE IF NOT EXISTS team_attendance_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id TEXT NOT NULL,
            action TEXT NOT NULL,
            by_who TEXT NOT NULL,
            at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (team_id) REFERENCES teams (team_id)
        )
    ''')
    
    # Member attendance log
    conn.execute('''
        CREATE TABLE IF NOT EXISTS member_attendance_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            by_who TEXT NOT NULL,
            at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (member_id) REFERENCES members (id)
        )
    ''')
    
    conn.commit()
    conn.close()

def require_admin_token():
    """Check if admin token is provided"""
    token = request.args.get('token') or request.form.get('token')
    if token != ADMIN_TOKEN:
        return False
    return True

@app.route('/')
def index():
    """Home page"""
    # Check if admin token is provided
    is_admin = request.args.get('token') == ADMIN_TOKEN
    return render_template('index.html', 
                         is_admin=is_admin,
                         admin_token=ADMIN_TOKEN,
                         base_url=BASE_URL)

@app.route('/scan')
def scan():
    """Scan page - shows team info and attendance controls"""
    token = request.args.get('t')
    if not token:
        return render_template('scan.html', error="No token provided")
    
    conn = get_db()
    team = conn.execute(
        'SELECT * FROM teams WHERE token = ?', (token,)
    ).fetchone()
    
    if not team:
        conn.close()
        return render_template('scan.html', error="Invalid token")
    
    # Get team members
    members = conn.execute(
        'SELECT * FROM members WHERE team_id = ?', (team['team_id'],)
    ).fetchall()
    
    conn.close()
    
    return render_template('scan.html', team=dict(team), members=[dict(m) for m in members])

@app.route('/dashboard')
def dashboard():
    """Dashboard page"""
    return render_template('dashboard.html')

@app.route('/api/team/by-token')
def get_team_by_token():
    """Get team info by token"""
    token = request.args.get('token')
    if not token:
        return jsonify({'error': 'Token required'}), 400
    
    conn = get_db()
    team = conn.execute(
        'SELECT * FROM teams WHERE token = ?', (token,)
    ).fetchone()
    
    if not team:
        conn.close()
        return jsonify({'error': 'Team not found'}), 404
    
    # Get members
    members = conn.execute(
        'SELECT * FROM members WHERE team_id = ?', (team['team_id'],)
    ).fetchall()
    
    conn.close()
    
    return jsonify({
        'team': dict(team),
        'members': [dict(m) for m in members]
    })

@app.route('/api/team/action', methods=['POST'])
def team_action():
    """Mark team in/out"""
    data = request.get_json()
    token = data.get('token')
    action = data.get('action')  # 'in' or 'out'
    by_who = data.get('by_who', 'system')
    
    if not token or not action:
        return jsonify({'error': 'Token and action required'}), 400
    
    conn = get_db()
    team = conn.execute(
        'SELECT * FROM teams WHERE token = ?', (token,)
    ).fetchone()
    
    if not team:
        conn.close()
        return jsonify({'error': 'Team not found'}), 404
    
    # Update team presence
    is_present = 1 if action == 'in' else 0
    conn.execute(
        'UPDATE teams SET is_present = ? WHERE token = ?',
        (is_present, token)
    )
    
    # Log the action
    conn.execute(
        'INSERT INTO team_attendance_log (team_id, action, by_who) VALUES (?, ?, ?)',
        (team['team_id'], action, by_who)
    )
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'action': action})

@app.route('/api/member/action', methods=['POST'])
def member_action():
    """Mark member in/out"""
    data = request.get_json()
    member_id = data.get('member_id')
    action = data.get('action')  # 'in' or 'out'
    by_who = data.get('by_who', 'system')
    
    if not member_id or not action:
        return jsonify({'error': 'Member ID and action required'}), 400
    
    conn = get_db()
    member = conn.execute(
        'SELECT * FROM members WHERE id = ?', (member_id,)
    ).fetchone()
    
    if not member:
        conn.close()
        return jsonify({'error': 'Member not found'}), 404
    
    # Update member presence
    is_present = 1 if action == 'in' else 0
    conn.execute(
        'UPDATE members SET is_present = ? WHERE id = ?',
        (is_present, member_id)
    )
    
    # Log the action
    conn.execute(
        'INSERT INTO member_attendance_log (member_id, action, by_who) VALUES (?, ?, ?)',
        (member_id, action, by_who)
    )
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'action': action})

@app.route('/api/stats')
def get_stats():
    """Get attendance statistics"""
    conn = get_db()
    
    # Team stats
    team_total = conn.execute('SELECT COUNT(*) as count FROM teams').fetchone()['count']
    team_present = conn.execute('SELECT COUNT(*) as count FROM teams WHERE is_present = 1').fetchone()['count']
    
    # Member stats
    member_total = conn.execute('SELECT COUNT(*) as count FROM members').fetchone()['count']
    member_present = conn.execute('SELECT COUNT(*) as count FROM members WHERE is_present = 1').fetchone()['count']
    
    # Get all teams with member counts and member details
    teams = conn.execute('''
        SELECT t.*, COUNT(m.id) as member_count,
               SUM(m.is_present) as members_present
        FROM teams t
        LEFT JOIN members m ON t.team_id = m.team_id
        GROUP BY t.id
        ORDER BY t.name
    ''').fetchall()
    
    # Convert teams to list of dicts and add member details for each team
    team_list = []
    for team in teams:
        team_dict = dict(team)
        
        # Get members for this team
        members = conn.execute('''
            SELECT id, name, phone, is_present 
            FROM members 
            WHERE team_id = ?
            ORDER BY name
        ''', (team['team_id'],)).fetchall()
        
        team_dict['members'] = [dict(m) for m in members]
        team_list.append(team_dict)
    
    conn.close()
    
    return jsonify({
        'teams': {
            'total': team_total,
            'present': team_present
        },
        'members': {
            'total': member_total,
            'present': member_present
        },
        'team_list': team_list
    })

@app.route('/admin/import-csv', methods=['GET', 'POST'])
def import_csv():
    """Import teams and members from CSV"""
    if not require_admin_token():
        return jsonify({'error': 'Unauthorized'}), 401
    
    if request.method == 'GET':
        return '''
        <form method="post" enctype="multipart/form-data">
            <input type="hidden" name="token" value="''' + ADMIN_TOKEN + '''">
            <input type="file" name="file" accept=".csv" required>
            <button type="submit">Import CSV</button>
        </form>
        '''
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    try:
        # Read CSV content
        content = file.read().decode('utf-8')
        csv_reader = csv.DictReader(StringIO(content))
        
        conn = get_db()
        teams_imported = 0
        members_imported = 0
        
        for row in csv_reader:
            team_id = row['team_id'].strip()
            
            # Check if team already exists
            existing_team = conn.execute(
                'SELECT id FROM teams WHERE team_id = ?', (team_id,)
            ).fetchone()
            
            if not existing_team:
                # Generate unique token for team
                token = secrets.token_urlsafe(16)
                
                # Insert team
                conn.execute('''
                    INSERT INTO teams (team_id, name, college, leader_name, leader_email, leader_phone, token)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    team_id,
                    row['team_name'].strip(),
                    row['college'].strip(),
                    row['leader_name'].strip(),
                    row['leader_email'].strip(),
                    row['leader_phone'].strip(),
                    token
                ))
                teams_imported += 1
            
            # Insert member (always insert, even if team exists)
            if row['member_name'].strip():
                conn.execute('''
                    INSERT INTO members (team_id, name, phone)
                    VALUES (?, ?, ?)
                ''', (
                    team_id,
                    row['member_name'].strip(),
                    row['member_phone'].strip()
                ))
                members_imported += 1
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'teams_imported': teams_imported,
            'members_imported': members_imported
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/admin/generate-qrs')
def generate_qrs():
    """Generate QR codes for all teams"""
    if not require_admin_token():
        return jsonify({'error': 'Unauthorized'}), 401
    
    conn = get_db()
    teams = conn.execute('SELECT team_id, name, token FROM teams').fetchall()
    conn.close()
    
    qr_codes = []
    for team in teams:
        # Just use the token directly - the frontend will handle the URL construction
        token = team['token']
        
        # Generate QR code with just the token
        qr = segno.make(token)
        from io import BytesIO
        svg_io = BytesIO()
        qr.save(svg_io, kind='svg', scale=8)
        svg_content = svg_io.getvalue().decode('utf-8')  # Convert bytes to string
        
        qr_codes.append({
            'team_id': team['team_id'],
            'team_name': team['name'],
            'token': token,
            'url': token,  # Just show the token instead of full URL
            'svg': svg_content
        })
    
    # Return HTML page with all QR codes
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Team QR Codes</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background-color: white; }
            .qr-item { 
                margin-bottom: 30px; 
                page-break-after: auto; 
                border: 1px solid #ccc; 
                padding: 15px; 
                background-color: white;
            }
            .qr-item h3 { margin-top: 0; }
            .export-btn {
                position: fixed;
                top: 20px;
                right: 20px;
                padding: 10px 20px;
                background-color: #007bff;
                color: white;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                z-index: 1000;
            }
            .export-btn:hover {
                background-color: #0056b3;
            }
            @media print {
                .qr-item { 
                    page-break-inside: avoid;
                    border: 1px solid #ccc;
                    background-color: white;
                }
                .export-btn {
                    display: none;
                }
            }
        </style>
        <script>
            function exportToPDF() {
                window.print();
            }
        </script>
    </head>
    <body>
        <button class="export-btn" onclick="exportToPDF()">Export to PDF</button>
        <h1>Team QR Codes</h1>
    '''
    
    for qr in qr_codes:
        html += f'''
        <div class="qr-item">
            <h3>{qr['team_id']} - {qr['team_name']}</h3>
            <p><strong>Team Token:</strong> {qr['url']}</p>
            {qr['svg']}
        </div>
        '''
    
    html += '</body></html>'
    return html

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)