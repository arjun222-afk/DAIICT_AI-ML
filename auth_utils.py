from werkzeug.security import generate_password_hash, check_password_hash
from flask import session
import sqlite3

def get_db_connection():
    conn = sqlite3.connect('job_market.db')
    conn.row_factory = sqlite3.Row
    return conn

def register_user(name, email, password, skills_data='{}'):
    """Register a new user and return their ID"""
    password_hash = generate_password_hash(password)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if email already exists
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        existing_user = cursor.fetchone()
        
        if existing_user:
            conn.close()
            return None, "Email already registered"
        
        # Insert new user
        cursor.execute(
            "INSERT INTO users (name, email, password_hash, skills_data) VALUES (?, ?, ?, ?)",
            (name, email, password_hash, skills_data)
        )
        
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return user_id, None
    except Exception as e:
        return None, str(e)

def login_user(email, password):
    """Authenticate a user and return their ID"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, password_hash FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        conn.close()
        
        if not user or not check_password_hash(user['password_hash'], password):
            return None, "Invalid email or password"
        
        return user['id'], None
    except Exception as e:
        return None, str(e)

def get_user_by_id(user_id):
    """Get user information by ID"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, name, email, created_at, skills_data FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        conn.close()
        
        if not user:
            return None
        
        # Convert to dictionary
        return dict(user)
    except:
        return None

def get_user_quiz_results(user_id):
    """Get quiz results for a specific user"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM user_quiz_results 
            WHERE user_id = ? 
            ORDER BY completed_at DESC
        """, (user_id,))
        
        results = cursor.fetchall()
        conn.close()
        
        # Convert to list of dictionaries
        return [dict(result) for result in results]
    except:
        return []