import sqlite3
import csv
import secrets
import os
import re

def extract_team_size(size_str):
    """
    Extract team size from string, handling cases like:
    - Plain numbers ("2", "3")
    - Ranges ("3-5", "Team(3-5)")
    Returns the maximum possible team size or 2 as default
    """
    if not size_str or not str(size_str).strip():
        return 2
        
    # Clean the string
    size_str = str(size_str).strip()
    
    # Try to find any numbers in the string
    numbers = re.findall(r'\d+', size_str)
    
    if not numbers:
        return 2
    
    # Convert all found numbers to integers and take the maximum
    # This handles both single numbers and ranges
    return max(int(num) for num in numbers)

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
        # Read using CSV DictReader with the file's own headers
        csv_reader = csv.DictReader(file)
        # Print the headers to debug
        print("CSV Headers:", csv_reader.fieldnames)
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
                print(f"Processing team with ID: {row['ID']}")
                team_id = f"T{row['ID'].zfill(3)}"  # Convert 1 to T001, etc
                current_team_id = team_id
                current_team_name = row['Team Name']
                
                # Check if team already exists
                existing_team = conn.execute(
                    'SELECT id FROM teams WHERE team_id = ?', (team_id,)
                ).fetchone()
                
                if not existing_team:
                    try:
                        # Generate sequential token based on numeric part of team_id
                        numeric_id = row['ID'].zfill(3)  # Get the numeric part and pad with zeros
                        token = f"team_{numeric_id}"  # This will create tokens like team_001, team_002, etc
                        
                        # Insert team
                        conn.execute('''
                            INSERT INTO teams (
                                team_id, name, college, team_size, leader_name, 
                                leader_email, leader_phone, token
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            team_id, 
                            row['Team Name'].strip() if row['Team Name'] else '',
                            row['College names'].strip() if row['College names'] else '',
                            extract_team_size(row['Team Size']) if row['Team Size'] and row['Team Size'].strip() else 2,
                            row['            Team Members'].strip() if row['            Team Members'] else '',
                            row['Team Leader Email'].strip() if row['Team Leader Email'] else row['Email Address'].strip(),
                            row['      Phone no.'].strip() if row['      Phone no.'] else '',
                            token
                        ))
                        teams_imported += 1
                        conn.commit()
                        print(f"Successfully imported team {team_id}: {row['Team Name'].strip()}")
                    except Exception as e:
                        print(f"Error importing team {team_id}: {str(e)}")
            
            # If we have a current team and the row has team member info
            # Handle team members
            if current_team_id:
                print(f"Checking member data for team {current_team_id}: {row['            Team Members'] if '            Team Members' in row else 'No member data'}")
            if current_team_id and row.get('            Team Members'):
                # Check if member already exists
                existing_member = conn.execute('''
                    SELECT id FROM members 
                    WHERE team_id = ? AND name = ?
                ''', (current_team_id, row['            Team Members'].strip())).fetchone()
                
                if not existing_member:
                    # Insert member
                    try:
                        conn.execute('''
                            INSERT INTO members (
                                team_id, name, phone, gender
                            ) VALUES (?, ?, ?, ?)
                        ''', (
                            current_team_id,
                            row['            Team Members'].strip(),
                            row['      Phone no.'].strip() if row['      Phone no.'] else None,
                            row['        Gender'].strip() if row['        Gender'] else None
                        ))
                        conn.commit()
                        members_imported += 1
                        print(f"Successfully added member {row['            Team Members'].strip()} to team {current_team_id}")
                    except Exception as e:
                        print(f"Error adding member to team {current_team_id}: {str(e)}")
        
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
