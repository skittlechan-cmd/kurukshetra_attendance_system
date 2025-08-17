#!/usr/bin/env python3
import sys
import os
import csv
import secrets
from io import StringIO
import segno
import sqlite3

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
    print("Initializing database...")
    
    conn = get_db()
    
    # Teams table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            college TEXT NOT NULL,
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
            phone TEXT NOT NULL,
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
    print("Database initialized successfully!")

def import_csv(csv_file):
    """Import teams and members from CSV file"""
    print(f"Importing data from {csv_file}...")
    
    if not os.path.exists(csv_file):
        print(f"Error: File {csv_file} not found!")
        return
    
    try:
        conn = get_db()
        teams_imported = 0
        members_imported = 0
        
        with open(csv_file, 'r') as file:
            csv_reader = csv.DictReader(file)
            
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
        
        print(f"Import completed successfully!")
        print(f"Teams imported: {teams_imported}")
        print(f"Members imported: {members_imported}")
        
    except Exception as e:
        print(f"Error importing CSV: {e}")

def generate_qrs():
    """Generate QR codes for all teams"""
    print("Generating QR codes...")
    
    conn = get_db()
    teams = conn.execute('SELECT team_id, name, token FROM teams').fetchall()
    conn.close()
    
    if not teams:
        print("No teams found in database!")
        return
    
    # Create QR codes directory if it doesn't exist
    if not os.path.exists('qr_codes'):
        os.makedirs('qr_codes')
    
    for team in teams:
        # Generate QR code URL
        url = f"{BASE_URL}/scan?t={team['token']}"
        
        # Generate QR code and save as SVG
        qr = segno.make(url)
        filename = f"qr_codes/{team['team_id']}.svg"
        qr.save(filename, scale=8)
        
        print(f"Generated QR for {team['team_id']} - {team['name']}")
    
    print(f"QR codes generated for {len(teams)} teams in 'qr_codes' directory")

def show_help():
    """Show help information"""
    print("""
Hackathon Attendance System Management CLI

Usage: python manage.py <command> [arguments]

Commands:
    init-db                 Initialize the database
    import-csv <file>       Import teams/members from CSV file
    generate-qrs            Generate QR codes for all teams
    help                    Show this help message

Examples:
    python manage.py init-db
    python manage.py import-csv example.csv
    python manage.py generate-qrs
    """)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        show_help()
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == 'init-db':
        init_db()
    elif command == 'import-csv':
        if len(sys.argv) < 3:
            print("Error: CSV file path required")
            print("Usage: python manage.py import-csv <file>")
            sys.exit(1)
        import_csv(sys.argv[2])
    elif command == 'generate-qrs':
        generate_qrs()
    elif command == 'help':
        show_help()
    else:
        print(f"Error: Unknown command '{command}'")
        show_help()
        sys.exit(1)