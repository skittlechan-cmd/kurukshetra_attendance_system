import sqlite3
import csv
import secrets
import os

# Configuration
DATABASE = 'hackathon.db'

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

def import_teams():
    """Import teams from kurukshetra.csv"""
    conn = get_db()
    with open('kurukshetra.csv', 'r', encoding='utf-8') as file:
        # Clean up column names by removing extra whitespace
        headers = next(file).strip().split(',')
        headers = [h.strip() for h in headers]
        csv_reader = csv.DictReader(file, fieldnames=headers)
        teams_imported = 0
        members_imported = 0
        
        current_team_id = None
        current_team_name = None
        
        for row in csv_reader:
            # Skip completely empty rows
            if not any(row.values()):
                continue
                
            # If row has an ID, it's a new team
            if row['ID']:
                team_id = f"T{row['ID'].zfill(3)}"  # Convert 1 to T001, etc
                current_team_id = team_id
                current_team_name = row['Team Name']
                
                # Check if team already exists
                existing_team = conn.execute(
                    'SELECT id FROM teams WHERE team_id = ?', (team_id,)
                ).fetchone()
                
                if not existing_team:
                    try:
                        # Generate unique token for team
                        token = secrets.token_urlsafe(16)
                        
                        # Insert team
                        conn.execute('''
                            INSERT INTO teams (
                                team_id, name, college, team_size, leader_name, 
                                leader_email, leader_phone, token
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            team_id, 
                            row['Team Name'].strip(),
                            row['College names'].strip() if row['College names'] else '',
                            2,  # Default to 2 since that seems to be the common team size
                            row['Team Members'].strip() if row['Team Members'] else '',
                            row['Email Address'].strip() if row['Email Address'] else row['Team Leader Email'].strip(),
                            row['Phone no.'].strip() if row['Phone no.'] else '',
                            token
                        ))
                        teams_imported += 1
                        conn.commit()
                    except Exception as e:
                        print(f"Error importing team {team_id}: {str(e)}")
            
            # If we have a current team and the row has team member info
            if current_team_id and row['Team Members']:
                # Check if member already exists
                existing_member = conn.execute('''
                    SELECT id FROM members 
                    WHERE team_id = ? AND name = ?
                ''', (current_team_id, row['Team Members'].strip())).fetchone()
                
                if not existing_member:
                    # Insert member
                    conn.execute('''
                        INSERT INTO members (
                            team_id, name, phone, gender
                        ) VALUES (?, ?, ?, ?)
                    ''', (
                        current_team_id,
                        row['Team Members'].strip(),
                        row['Phone no.'].strip() if row['Phone no.'] else None,
                        row['Gender'].strip() if row['Gender'] else None
                    ))
                    members_imported += 1
        
        conn.commit()
        print(f"Imported {teams_imported} teams and {members_imported} members")

if __name__ == '__main__':
    # Initialize database
    if not os.path.exists(DATABASE):
        print("Initializing database...")
        init_db()
    
    # Import teams
    print("Importing teams...")
    import_teams()
