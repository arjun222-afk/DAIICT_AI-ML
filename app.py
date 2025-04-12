# app.py
from flask import Flask, render_template, request, jsonify,redirect
import sqlite3
import pandas as pd
import json
from datetime import datetime
import re
from auth_utils import register_user, login_user, get_user_by_id, get_user_quiz_results
from flask import session, redirect, url_for, flash
import json
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)

# Database connection helper
def get_db_connection():
    conn = sqlite3.connect('job_market.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.template_filter('fromjson')
def fromjson_filter(value):
    try:
        return json.loads(value)
    except (ValueError, TypeError):
        return []

@app.route('/')
def index():
    return render_template('base.html')

@app.route('/job_market_analysis')
def job_market_analysis():
    return render_template('job_market_analysis.html')

@app.route('/skill_assessment')
def skill_assessment():
    print("Session data:", session)
    return render_template('skill_assessment.html')

@app.route('/api/job_count_by_location')
def job_count_by_location():
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT job_location, COUNT(*) as count FROM job_market_data GROUP BY job_location ORDER BY count DESC LIMIT 10", conn)
    conn.close()
    return jsonify(df.to_dict(orient='records'))

@app.route('/api/top_skills')
def top_skills():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT required_skills FROM job_market_data")
    all_skills = cursor.fetchall()
    conn.close()
    
    # Process the skills
    skill_count = {}
    for row in all_skills:
        if row['required_skills']:
            skills = row['required_skills'].split(',')
            for skill in skills:
                skill = skill.strip().lower()
                if skill:
                    skill_count[skill] = skill_count.get(skill, 0) + 1
    
    # Convert to list of dicts and sort
    skill_list = [{"skill": skill, "count": count} for skill, count in skill_count.items()]
    skill_list.sort(key=lambda x: x["count"], reverse=True)
    
    return jsonify(skill_list[:20])  # Return top 20 skills

@app.route('/api/salary_distribution')
def salary_distribution():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT salary_offered FROM job_market_data WHERE salary_offered IS NOT NULL AND salary_offered != ''")
    salaries = cursor.fetchall()
    conn.close()
    
    # Process the salaries
    salary_ranges = {
        "0-50k": 0,
        "50k-75k": 0,
        "75k-100k": 0,
        "100k-125k": 0,
        "125k-150k": 0,
        "150k+": 0,
        "Not Specified": 0
    }
    
    for row in salaries:
        salary_text = row['salary_offered']
        if not salary_text:
            salary_ranges["Not Specified"] += 1
            continue
        
        # Extract numbers from salary text
        numbers = re.findall(r'\d+', salary_text)
        if not numbers:
            salary_ranges["Not Specified"] += 1
            continue
        
        # Convert to integer, assuming the largest number is the max salary
        try:
            max_salary = max(int(num) for num in numbers)
            # Check if it's in thousands or actual value
            if max_salary < 1000:  # Assuming it's in thousands (e.g., 75 means 75k)
                max_salary *= 1000
                
            # Categorize
            if max_salary <= 50000:
                salary_ranges["0-50k"] += 1
            elif max_salary <= 75000:
                salary_ranges["50k-75k"] += 1
            elif max_salary <= 100000:
                salary_ranges["75k-100k"] += 1
            elif max_salary <= 125000:
                salary_ranges["100k-125k"] += 1
            elif max_salary <= 150000:
                salary_ranges["125k-150k"] += 1
            else:
                salary_ranges["150k+"] += 1
        except:
            salary_ranges["Not Specified"] += 1
    
    result = [{"range": key, "count": value} for key, value in salary_ranges.items()]
    return jsonify(result)

@app.route('/api/experience_required')
def experience_required():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT exp_required FROM job_market_data WHERE exp_required IS NOT NULL AND exp_required != ''")
    experience_data = cursor.fetchall()
    conn.close()
    
    # Process the experience data
    exp_ranges = {
        "Entry Level (0-2 years)": 0,
        "Mid Level (3-5 years)": 0,
        "Senior Level (6-10 years)": 0,
        "Expert Level (10+ years)": 0,
        "Not Specified": 0
    }
    
    for row in experience_data:
        exp_text = row['exp_required']
        if not exp_text:
            exp_ranges["Not Specified"] += 1
            continue
        
        # Extract numbers from experience text
        numbers = re.findall(r'\d+', exp_text)
        if not numbers:
            exp_ranges["Not Specified"] += 1
            continue
        
        # Convert to integer, assuming the largest number is the max experience
        try:
            max_exp = max(int(num) for num in numbers)
            
            # Categorize
            if max_exp <= 2:
                exp_ranges["Entry Level (0-2 years)"] += 1
            elif max_exp <= 5:
                exp_ranges["Mid Level (3-5 years)"] += 1
            elif max_exp <= 10:
                exp_ranges["Senior Level (6-10 years)"] += 1
            else:
                exp_ranges["Expert Level (10+ years)"] += 1
        except:
            exp_ranges["Not Specified"] += 1
    
    result = [{"range": key, "count": value} for key, value in exp_ranges.items()]
    return jsonify(result)

@app.route('/api/company_ratings')
def company_ratings():
    conn = get_db_connection()
    df = pd.read_sql_query("""
        SELECT company, AVG(company_rating) as avg_rating, COUNT(*) as job_count 
        FROM job_market_data 
        WHERE company_rating IS NOT NULL 
        GROUP BY company 
        HAVING job_count > 1
        ORDER BY avg_rating DESC 
        LIMIT 10
    """, conn)
    conn.close()
    return jsonify(df.to_dict(orient='records'))

@app.route('/api/job_posting_trends')
def job_posting_trends():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT Posted_on FROM job_market_data WHERE Posted_on IS NOT NULL AND Posted_on != ''")
    posting_dates = cursor.fetchall()
    conn.close()
    
    # Process the dates
    date_counts = {}
    
    for row in posting_dates:
        date_text = row['Posted_on']
        try:
            # Try different date formats
            date_formats = [
                "%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", 
                "%B %d, %Y", "%d %B %Y", "%Y/%m/%d"
            ]
            
            parsed_date = None
            for fmt in date_formats:
                try:
                    parsed_date = datetime.strptime(date_text, fmt)
                    break
                except:
                    continue
            
            if parsed_date:
                month_year = parsed_date.strftime("%Y-%m")
                date_counts[month_year] = date_counts.get(month_year, 0) + 1
            else:
                continue
        except:
            continue
    
    # Sort by date
    sorted_dates = sorted(date_counts.items())
    result = [{"date": date, "count": count} for date, count in sorted_dates]
    
    return jsonify(result)

@app.route('/api/job_search')
def job_search():
    skill = request.args.get('skill', '')
    location = request.args.get('location', '')
    exp_min = request.args.get('exp_min', '')
    exp_max = request.args.get('exp_max', '')
    
    conn = get_db_connection()
    query = "SELECT * FROM job_market_data WHERE 1=1"
    params = []
    
    if skill:
        query += " AND required_skills LIKE ?"
        params.append(f"%{skill}%")
    
    if location:
        query += " AND job_location LIKE ?"
        params.append(f"%{location}%")
    
    # Limit results for performance
    query += " LIMIT 100"
    
    cursor = conn.cursor()
    cursor.execute(query, params)
    results = cursor.fetchall()
    conn.close()
    
    # Convert to list of dicts
    jobs = []
    for row in results:
        job = dict(row)
        jobs.append(job)
    
    return jsonify(jobs)

@app.route('/api/market_summary')
def market_summary():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Total job count
    cursor.execute("SELECT COUNT(*) as total FROM job_market_data")
    total_jobs = cursor.fetchone()['total']
    
    # Count unique companies
    cursor.execute("SELECT COUNT(DISTINCT company) as company_count FROM job_market_data")
    company_count = cursor.fetchone()['company_count']
    
    # Count unique locations
    cursor.execute("SELECT COUNT(DISTINCT job_location) as location_count FROM job_market_data")
    location_count = cursor.fetchone()['location_count']
    
    # Average salary calculation (simplified)
    cursor.execute("SELECT AVG(company_rating) as avg_rating FROM job_market_data WHERE company_rating IS NOT NULL")
    avg_rating = cursor.fetchone()['avg_rating']
    
    conn.close()
    
    return jsonify({
        "total_jobs": total_jobs,
        "unique_companies": company_count,
        "unique_locations": location_count,
        "average_company_rating": round(avg_rating, 2) if avg_rating else 0
    })

# Updated quiz questions endpoint to fetch from database
@app.route('/api/quiz')
def quiz_questions():
    category = request.args.get('category', 'technical')
    
    # Connect to database and fetch questions
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, question, options, correct_answer, skill FROM quiz_questions WHERE category = ?",
        (category,)
    )
    rows = cursor.fetchall()
    conn.close()
    
    # Format questions for API response
    questions = []
    for row in rows:
        questions.append({
            "id": row['id'],
            "question": row['question'],
            "options": json.loads(row['options']),
            "correctAnswer": row['correct_answer'],
            "skill": row['skill']
        })
    
    # If no questions found in database, use fallback questions
    if not questions:
        if category == 'technical':
            questions = [
                {
                    "id": 1,
                    "question": "Which language is primarily used for web front-end development?",
                    "options": ["Python", "JavaScript", "Java", "C++"],
                    "correctAnswer": "JavaScript",
                    "skill": "front_end"
                },
                # Additional fallback technical questions...
            ]
        else:
            questions = [
                {
                    "id": 1,
                    "question": "Which approach would be most effective when dealing with a disagreement in a team?",
                    "options": ["Avoid the conflict altogether", "Listen to all perspectives and find a compromise", "Insist on your way if you believe it's right", "Let someone else make the decision"],
                    "correctAnswer": "Listen to all perspectives and find a compromise",
                    "skill": "conflict_resolution"
                },
                # Additional fallback soft skills questions...
            ]
    
    return jsonify(questions)

# Enhanced version of submit_quiz_results endpoint
@app.route('/api/submit_quiz_results', methods=['POST'])
def submit_quiz_results():
    data = request.json
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    # Extract user_id if the user is logged in (you'll need to implement session management)
    user_id = data.get('user_id')
    print(12)
    print(user_id)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Insert quiz results into database
        cursor.execute("""
            INSERT INTO user_quiz_results 
            (user_id, category, proficient_skills, improvement_skills, score, completed_at) 
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            data.get('category'),
            json.dumps(data.get('proficientSkills', [])),
            json.dumps(data.get('improvementSkills', [])),
            data.get('score'),
            data.get('completedAt')
        ))
        
        result_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            "success": True, 
            "message": "Quiz results saved successfully",
            "result_id": result_id
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Add a secret key for session management
# app.secret_key = os.environ.get('SECRET_KEY', 'dev_secret_key')
app.secret_key = os.environ.get('SECRET_KEY')

# In app.py - Update the signup route
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        # Process the signup form
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')
        
        # Get stored skills from the form
        user_skills = request.form.get('user_skills', '{}')
        
        # Register the user
        user_id, error = register_user(name, email, password, user_skills)
        
        if error:
            flash(error, 'danger')
            return render_template('signup.html')  # This line is correct but missing flash messages in template
        
        # Set user session
        session['user_id'] = user_id
        session['user_name'] = name
        
        # Redirect to dashboard
        return redirect('/dashboard')
    
    # GET request - show signup form
    return render_template('signup.html')

# Add login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Authenticate user
        user_id, error = login_user(email, password)
        
        if error:
            flash(error, 'danger')
            return render_template('login.html')
        
        # Get user info
        user = get_user_by_id(user_id)
        
        # Set session - this is critical
        session['user_id'] = user_id
        session['user_name'] = user['name']
        
        print("Session after login:", session)  # Debugging
        
        # Redirect to dashboard
        return redirect('/dashboard')
    
    # GET request - show login form
    return render_template('login.html')

# Add logout route
@app.route('/logout')
def logout():
    # Clear session
    session.clear()
    return redirect('/')

# Add dashboard route
@app.route('/dashboard')
def dashboard():
    # Check if user is logged in
    if 'user_id' not in session:
        return redirect('/login')
    
    # Get user information
    user_id = session['user_id']
    user = get_user_by_id(user_id)
    print(user)


    if not user:
        session.clear()
        return redirect('/login')
    
    # Get user's quiz results
    quiz_results = get_user_quiz_results(user_id)
    
    # Process skills data
    skills_data = {}
    try:
        if user['skills_data']:
            skills_data = json.loads(user['skills_data'])
    except:
        skills_data = {}
    
    return render_template('dashboard.html', 
                          user=user, 
                          skills=skills_data, 
                          quiz_results=quiz_results)

@app.route('/profile')
def profile():
    # Check if user is logged in
    if 'user_id' not in session:
        return redirect('/login')
    
    # Get user information
    user_id = session['user_id']
    user = get_user_by_id(user_id)
    
    if not user:
        session.clear()
        return redirect('/login')
    
    # Get user's quiz results
    quiz_results = get_user_quiz_results(user_id)
    
    # Process skills data
    skills_data = {}
    try:
        if user['skills_data']:
            skills_data = json.loads(user['skills_data'])
    except:
        skills_data = {}
    
    return render_template('profile.html', 
                          user=user, 
                          skills=skills_data, 
                          quiz_results=quiz_results)

@app.route('/api/update_user_skills', methods=['POST'])
def update_user_skills():
    if 'user_id' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    data = request.json
    user_id = session['user_id']
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Update the user's skills_data in the database
        cursor.execute(
            "UPDATE users SET skills_data = ? WHERE id = ?",
            (json.dumps(data), user_id)
        )
        
        conn.commit()
        conn.close()
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)