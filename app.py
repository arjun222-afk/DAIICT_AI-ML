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
from ai_utils import get_career_path_recommendations, save_user_recommendations
from network_analysis import generate_network_html, get_user_similarity_network, get_skill_job_network, get_full_network
import os
from pathlib import Path
from ai_utils import get_resume_tips, get_interview_tips, format_tips_html
import markdown
# from interview_utils import generate_initial_interview_questions, generate_follow_up_question, generate_interview_analysis
from interview_utils import (
    get_db_connection,
    generate_initial_interview_questions,
    generate_follow_up_question,
    generate_interview_analysis
)


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
    user_id = session.get('user_id', None)
    print(f"Session data in skill_assessment route: {session}")
    print(f"User ID from session: {user_id}")
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
        
        numbers = re.findall(r'\d+', salary_text)
        if not numbers:
            salary_ranges["Not Specified"] += 1
            continue
        
        try:
            max_salary = max(int(num) for num in numbers)
            if max_salary < 1000:
                max_salary *= 1000
                
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
        
        numbers = re.findall(r'\d+', exp_text)
        if not numbers:
            exp_ranges["Not Specified"] += 1
            continue
        
        try:
            max_exp = max(int(num) for num in numbers)
            
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
    
    date_counts = {}
    
    for row in posting_dates:
        date_text = row['Posted_on']
        try:
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
    
    query += " LIMIT 100"
    
    cursor = conn.cursor()
    cursor.execute(query, params)
    results = cursor.fetchall()
    conn.close()
    
    jobs = []
    for row in results:
        job = dict(row)
        jobs.append(job)
    
    return jsonify(jobs)

@app.route('/api/market_summary')
def market_summary():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) as total FROM job_market_data")
    total_jobs = cursor.fetchone()['total']
    
    cursor.execute("SELECT COUNT(DISTINCT company) as company_count FROM job_market_data")
    company_count = cursor.fetchone()['company_count']
    
    cursor.execute("SELECT COUNT(DISTINCT job_location) as location_count FROM job_market_data")
    location_count = cursor.fetchone()['location_count']
    
    cursor.execute("SELECT AVG(company_rating) as avg_rating FROM job_market_data WHERE company_rating IS NOT NULL")
    avg_rating = cursor.fetchone()['avg_rating']
    
    conn.close()
    
    return jsonify({
        "total_jobs": total_jobs,
        "unique_companies": company_count,
        "unique_locations": location_count,
        "average_company_rating": round(avg_rating, 2) if avg_rating else 0
    })

@app.route('/api/quiz')
def quiz_questions():
    category = request.args.get('category', 'technical')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, question, options, correct_answer, skill FROM quiz_questions WHERE category = ?",
        (category,)
    )
    rows = cursor.fetchall()
    conn.close()
    
    questions = []
    for row in rows:
        questions.append({
            "id": row['id'],
            "question": row['question'],
            "options": json.loads(row['options']),
            "correctAnswer": row['correct_answer'],
            "skill": row['skill']
        })
    
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

@app.route('/api/submit_quiz_results', methods=['POST'])
def submit_quiz_results():
    data = request.json
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    session_user_id = session.get('user_id')
    data_user_id = data.get('user_id')

    if session_user_id and (not data_user_id or data_user_id != session_user_id):
        user_id = session_user_id
        print(f"Using session user_id: {user_id} instead of data user_id: {data_user_id}")
    else:
        user_id = data_user_id
    
    if not user_id:
        return jsonify({"error": "No user ID provided"}), 400
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        proficient_skills = data.get('proficientSkills', [])
        improvement_skills = data.get('improvementSkills', [])
        
        if isinstance(proficient_skills, list):
            proficient_skills = json.dumps(proficient_skills)
        
        if isinstance(improvement_skills, list):
            improvement_skills = json.dumps(improvement_skills)
        
        cursor.execute("""
            INSERT INTO user_quiz_results 
            (user_id, category, proficient_skills, improvement_skills, score, completed_at) 
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            data.get('category'),
            proficient_skills,
            improvement_skills,
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


app.secret_key = os.environ.get('SECRET_KEY')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')
        
        user_skills = request.form.get('user_skills', '{}')
        
        user_id, error = register_user(name, email, password, user_skills)
        
        if error:
            flash(error, 'danger')
            return render_template('signup.html') 
        
        session['user_id'] = user_id
        session['user_email'] = email
        
        return redirect('/dashboard')
    
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user_id, error = login_user(email, password)
        
        if error:
            flash(error, 'danger')
            return render_template('login.html')
        
        user = get_user_by_id(user_id)
        
        session['user_id'] = user_id
        session['user_email'] = email
        
        return redirect('/dashboard')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# Update to the dashboard route in app.py
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')
    
    user_id = session['user_id']
    user = get_user_by_id(user_id)
    
    if not user:
        session.clear()
        return redirect('/login')
    
    quiz_results = get_user_quiz_results(user_id)
    
    # Get interview history
    interview_history = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """SELECT * FROM user_interview_results 
               WHERE user_id = ? 
               ORDER BY completed_at DESC LIMIT 5""",
            (user_id,)
        )
        interview_history = cursor.fetchall()
        conn.close()
    except Exception as e:
        print(f"Error fetching interview history: {e}")
    
    skills_data = {}
    try:
        if user['skills_data'] and user['skills_data'].strip():
            skills_data = json.loads(user['skills_data'])
    except Exception as e:
        print(f"Error parsing skills data: {e}")
        skills_data = {}
    
    return render_template('dashboard.html', 
                          user=user, 
                          skills=skills_data, 
                          quiz_results=quiz_results,
                          interview_history=interview_history)

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect('/login')
    
    user_id = session['user_id']
    user = get_user_by_id(user_id)
    
    if not user:
        session.clear()
        return redirect('/login')
    
    quiz_results = get_user_quiz_results(user_id)
    
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
        if not isinstance(data, dict):
            return jsonify({"error": "Invalid data format"}), 400
            
        if 'proficientSkills' in data and not isinstance(data['proficientSkills'], list):
            data['proficientSkills'] = []
            
        if 'improvementSkills' in data and not isinstance(data['improvementSkills'], list):
            data['improvementSkills'] = []
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET skills_data = ? WHERE id = ?",
            (json.dumps(data), user_id)
        )
        
        conn.commit()
        conn.close()
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.template_filter('markdown')
def markdown_filter(text):
    return markdown.markdown(text)

@app.route('/resume_tips')
def resume_tips_page():
    """Display the resume and interview tips page with job role selection"""
    if 'user_id' not in session:
        return redirect('/login')
    
    conn = get_db_connection()
    job_roles = conn.execute('SELECT * FROM job_roles ORDER BY role_name').fetchall()
    conn.close()
    
    return render_template('resume_tips.html', 
                          job_roles=job_roles,
                          tips=None,
                          current_role=None,
                          tips_type=None)

@app.route('/resume_tips/<int:role_id>/<tips_type>')
def get_role_tips(role_id, tips_type):
    
    """Get tips for a specific job role and tips type"""
    if 'user_id' not in session:
        return redirect('/login')
    
    if tips_type not in ['resume', 'interview']:
        return redirect('/resume_tips')
    
    conn = get_db_connection()
    current_role = conn.execute('SELECT * FROM job_roles WHERE id = ?', 
                              (role_id,)).fetchone()
    
    job_roles = conn.execute('SELECT * FROM job_roles ORDER BY role_name').fetchall()
    conn.close()
    
    if not current_role:
        return redirect('/resume_tips')
    
    if tips_type == 'resume':
        tips_md = get_resume_tips(current_role['role_name'])
    else:  
        tips_md = get_interview_tips(current_role['role_name'])

    tips = format_tips_html(tips_md)
    
    return render_template('resume_tips.html',
                          job_roles=job_roles,
                          tips=tips,
                          current_role=current_role,
                          tips_type=tips_type)



# INTERVIEW RELATED ROUTES
@app.route('/virtual_interview')
def virtual_interview():
    # Get job roles from the database
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, role_name FROM job_roles")
    job_roles = cursor.fetchall()
    conn.close()
    
    # Get user skills if logged in
    skills = {}
    if 'user_id' in session:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT skills_data FROM users WHERE id = ?", (session['user_id'],))
        user = cursor.fetchone()
        conn.close()
        
        if user and user['skills_data']:
            skills = json.loads(user['skills_data'])
    
    return render_template('virtual_interview.html', job_roles=job_roles, skills=skills)

@app.route('/api/start_interview', methods=['POST'])
def start_interview():
    if 'user_id' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    data = request.json
    user_id = session['user_id']
    skill_area = data.get('skill_area')
    job_role = data.get('job_role')
    
    # Generate initial greeting and first question based on skill area
    interview_data = generate_initial_interview_questions(skill_area, job_role)
    
    # Store interview session in database
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO interview_sessions 
           (user_id, skill_area, job_role, started_at, status) 
           VALUES (?, ?, ?, ?, ?)""",
        (user_id, skill_area, job_role, datetime.now().isoformat(), 'in_progress')
    )
    interview_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return jsonify({
        "interview_id": interview_id,
        "greeting": interview_data["greeting"],
        "first_question": interview_data["first_question"]
    })

@app.route('/api/submit_interview_answer', methods=['POST'])
def submit_interview_answer():
    if 'user_id' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    data = request.json
    user_id = session['user_id']
    interview_id = data.get('interview_id')
    question = data.get('question')
    answer = data.get('answer')
    is_final = data.get('is_final', False)
    
    # Save the Q&A pair to database
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO interview_qa 
           (interview_id, question, answer, timestamp) 
           VALUES (?, ?, ?, ?)""",
        (interview_id, question, answer, datetime.now().isoformat())
    )
    conn.commit()
    
    # Get interview context
    cursor.execute(
        "SELECT skill_area, job_role FROM interview_sessions WHERE id = ?",
        (interview_id,)
    )
    session_data = cursor.fetchone()
    conn.close()
    
    if is_final:
        # If this is the final answer, don't generate a new question
        return jsonify({
            "success": True
        })
    else:
        # Generate next question based on previous answer
        next_data = generate_follow_up_question(
            session_data['skill_area'], 
            session_data['job_role'],
            question, 
            answer
        )
        
        return jsonify({
            "next_question": next_data["next_question"],
            "is_final": next_data.get("is_final", False)
        })

@app.route('/api/complete_interview', methods=['POST'])
def complete_interview():
    if 'user_id' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    data = request.json
    interview_id = data.get('interview_id')
    
    # Generate analysis and feedback from the interview
    analysis, feedback = generate_interview_analysis(interview_id)
    
    # Update interview status and save analysis
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """UPDATE interview_sessions 
           SET status = ?, completed_at = ?, analysis = ?, feedback = ?
           WHERE id = ?""",
        ('completed', datetime.now().isoformat(), json.dumps(analysis), json.dumps(feedback), interview_id)
    )
    conn.commit()
    conn.close()
    
    return jsonify({
        "success": True,
        "analysis": analysis,
        "feedback": feedback
    })


@app.route('/api/save_interview_results', methods=['POST'])
def save_interview_results():
    if 'user_id' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    data = request.json
    user_id = session['user_id']
    interview_id = data.get('interview_id')
    
    if not interview_id:
        return jsonify({"error": "No interview ID provided"}), 400
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get interview session data
        cursor.execute(
            """SELECT skill_area, job_role, analysis, feedback, completed_at 
               FROM interview_sessions 
               WHERE id = ? AND user_id = ?""",
            (interview_id, user_id)
        )
        
        interview = cursor.fetchone()
        if not interview:
            return jsonify({"error": "Interview not found"}), 404
        
        # Parse the analysis and feedback JSON
        analysis = json.loads(interview['analysis']) if interview['analysis'] else {}
        feedback = json.loads(interview['feedback']) if interview['feedback'] else {}
        
        # Calculate overall score (average of technical and communication)
        technical_score = analysis.get('technical_score', 0)
        communication_score = analysis.get('communication_score', 0)
        overall_score = (technical_score + communication_score) // 2
        
        # Insert into user_interview_results
        cursor.execute(
            """INSERT INTO user_interview_results
               (user_id, interview_id, technical_score, communication_score, overall_score,
                skill_area, job_role, completed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                user_id, interview_id, technical_score, communication_score, overall_score,
                interview['skill_area'], interview['job_role'], interview['completed_at']
            )
        )
        
        # Update user skills data with new insights
        cursor.execute("SELECT skills_data FROM users WHERE id = ?", (user_id,))
        user_skills_row = cursor.fetchone()
        
        if user_skills_row and user_skills_row['skills_data']:
            try:
                skills_data = json.loads(user_skills_row['skills_data'])
                
                # Add skills that need improvement to the improvement list if not already there
                improvement_skills = skills_data.get('improvementSkills', [])
                for skill in feedback.get('areas_for_improvement', []):
                    skill_keyword = extract_skill_keyword(skill)
                    if skill_keyword and skill_keyword not in improvement_skills:
                        improvement_skills.append(skill_keyword)
                
                # Update the skills data
                skills_data['improvementSkills'] = improvement_skills
                skills_data['lastInterviewScore'] = overall_score
                skills_data['lastInterviewDate'] = interview['completed_at']
                
                # Save back to database
                cursor.execute(
                    "UPDATE users SET skills_data = ? WHERE id = ?",
                    (json.dumps(skills_data), user_id)
                )
            except Exception as e:
                print(f"Error updating user skills data: {e}")
        
        conn.commit()
        conn.close()
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def extract_skill_keyword(text):
    """Extract a skill keyword from feedback text"""
    # This is a simple implementation - in a production system, you'd use NLP or a more sophisticated approach
    # Common technical skills to look for
    common_skills = [
        "javascript", "python", "java", "react", "angular", "vue", "nodejs", "express", 
        "django", "flask", "spring", "hibernate", "sql", "database", "nosql", "mongodb",
        "firebase", "aws", "azure", "gcp", "docker", "kubernetes", "ci/cd", "git",
        "data structures", "algorithms", "system design", "oop", "functional programming",
        "testing", "debugging", "problem solving", "communication", "teamwork",
        "time management", "organization", "leadership", "creativity", "critical thinking"
    ]
    
    # Check if any common skill appears in the text
    text_lower = text.lower()
    for skill in common_skills:
        if skill in text_lower:
            return skill
    
    return None




# Career Path Recommendation Route


@app.route('/career_paths')
def career_paths_page():
    """Display the career paths recommendation page"""
    # Check if user is logged in
    if 'user_id' not in session:
        return redirect('/login')
    
    user_id = session['user_id']
    user = get_user_by_id(user_id)
    
    if not user:
        session.clear()
        return redirect('/login')
    
    # Get user's skills data and quiz results
    skills_data = {}
    try:
        if user['skills_data'] and user['skills_data'].strip():
            skills_data = json.loads(user['skills_data'])
    except Exception as e:
        print(f"Error parsing skills data: {e}")
        skills_data = {}
    
    quiz_results = get_user_quiz_results(user_id)
    
    # Check if user has taken any skill assessments
    has_skill_data = bool(skills_data) or bool(quiz_results)
    
    # Get existing recommendations if available
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get recommendations with career path details
    cursor.execute("""
        SELECT r.*, c.title, c.description, c.required_skills, c.growth_potential, 
               c.market_demand, c.avg_salary, c.next_steps
        FROM user_career_recommendations r
        JOIN career_paths c ON r.career_path_id = c.id
        WHERE r.user_id = ?
        ORDER BY r.matching_score DESC
    """, (user_id,))
    
    recommendations = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return render_template('career_paths.html',
                          user=user,
                          has_skill_data=has_skill_data,
                          recommendations=recommendations)

@app.route('/api/generate_career_recommendations', methods=['POST'])
def generate_career_recommendations():
    """Generate new career path recommendations for the user"""
    if 'user_id' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    user_id = session['user_id']
    user = get_user_by_id(user_id)
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    # Get user's skills data and quiz results
    skills_data = {}
    try:
        if user['skills_data'] and user['skills_data'].strip():
            skills_data = json.loads(user['skills_data'])
    except Exception as e:
        print(f"Error parsing skills data: {e}")
        skills_data = {}
    
    quiz_results = get_user_quiz_results(user_id)
    
    # Check if user has taken any skill assessments
    if not skills_data and not quiz_results:
        return jsonify({
            "error": "Please complete at least one skill assessment before generating career recommendations"
        }), 400
    
    # Generate recommendations using AI
    recommendations = get_career_path_recommendations(skills_data, quiz_results)
    
    if "error" in recommendations:
        return jsonify({"error": recommendations["error"]}), 500
    
    # Save recommendations to database
    save_success = save_user_recommendations(user_id, recommendations)
    
    if not save_success:
        return jsonify({"error": "Failed to save recommendations"}), 500
    
    return jsonify({
        "success": True,
        "recommendations": recommendations.get("recommendations", [])
    })

@app.route('/api/career_path_details/<int:path_id>')
def career_path_details(path_id):
    """Get details for a specific career path"""
    if 'user_id' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get the career path details
    cursor.execute("SELECT * FROM career_paths WHERE id = ?", (path_id,))
    career_path = cursor.fetchone()
    
    if not career_path:
        conn.close()
        return jsonify({"error": "Career path not found"}), 404
    
    # Get the user's matching score for this path
    user_id = session['user_id']
    cursor.execute("""
        SELECT matching_score, recommendation_date
        FROM user_career_recommendations
        WHERE user_id = ? AND career_path_id = ?
    """, (user_id, path_id))
    
    recommendation = cursor.fetchone()
    conn.close()
    
    # Format the response
    result = dict(career_path)
    if recommendation:
        result['matching_score'] = recommendation['matching_score']
        result['recommendation_date'] = recommendation['recommendation_date']
    
    return jsonify(result)

@app.route('/network_analysis')
def network_analysis():
    """Display the network analysis page with visualizations"""
    # Check if user is logged in
    if 'user_id' not in session:
        return redirect('/login')
    
    # Generate the networks if they don't exist
    user_network_file = "networks/user_similarity_network.html"
    skill_job_network_file = "networks/skill_job_network.html"
    full_network_file = "networks/full_network.html"
    
    # Check if the network files exist and create them if they don't
    user_network_path = Path("static") / user_network_file
    skill_job_network_path = Path("static") / skill_job_network_file
    full_network_path = Path("static") / full_network_file
    
    if not user_network_path.exists():
        try:
            G = get_user_similarity_network()
            user_network_file = generate_network_html(G, "user_similarity_network.html", "User Similarity Network")
        except Exception as e:
            print(f"Error generating user similarity network: {e}")
            user_network_file = "error.html"
    
    if not skill_job_network_path.exists():
        try:
            G = get_skill_job_network()
            skill_job_network_file = generate_network_html(G, "skill_job_network.html", "Skills & Jobs Network")
        except Exception as e:
            print(f"Error generating skill job network: {e}")
            skill_job_network_file = "error.html"
    
    if not full_network_path.exists():
        try:
            G = get_full_network()
            full_network_file = generate_network_html(G, "full_network.html", "Complete Network View")
        except Exception as e:
            print(f"Error generating full network: {e}")
            full_network_file = "error.html"
    
    # Get network statistics
    conn = get_db_connection()
    user_count = conn.execute("SELECT COUNT(*) as count FROM users").fetchone()['count']
    
    # Count skills from quiz_questions
    skill_count = conn.execute("""
        SELECT COUNT(DISTINCT skill) as count FROM quiz_questions
        WHERE skill IS NOT NULL AND skill != ''
    """).fetchone()['count']
    
    # Count jobs
    job_count = conn.execute("SELECT COUNT(*) as count FROM job_market_data").fetchone()['count']
    conn.close()
    
    return render_template('network_analysis.html',
                          user_network_file=user_network_file,
                          skill_job_network_file=skill_job_network_file,
                          full_network_file=full_network_file,
                          user_count=user_count,
                          skill_count=skill_count,
                          job_count=job_count)

@app.route('/api/refresh_network')
def refresh_network():
    """API endpoint to refresh a specific network visualization"""
    # Check if user is logged in
    if 'user_id' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    network_type = request.args.get('type', '')
    
    try:
        if network_type == 'user-network':
            G = get_user_similarity_network()
            file_path = generate_network_html(G, "user_similarity_network.html", "User Similarity Network")
        elif network_type == 'skill-job-network':
            G = get_skill_job_network()
            file_path = generate_network_html(G, "skill_job_network.html", "Skills & Jobs Network")
        elif network_type == 'full-network':
            G = get_full_network()
            file_path = generate_network_html(G, "full_network.html", "Complete Network View")
        else:
            return jsonify({"error": "Invalid network type"}), 400
            
        return jsonify({"success": True, "file_path": file_path})
    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 500

@app.route('/api/network_stats')
def network_stats():
    """API endpoint to get network statistics"""
    # Check if user is logged in
    if 'user_id' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    try:
        # Get user skills network and analyze
        user_network = get_user_similarity_network()
        
        # Calculate some basic statistics
        user_nodes = [node for node in user_network.nodes() if node.startswith('user_')]
        skill_nodes = [node for node in user_network.nodes() if node.startswith('skill_')]
        
        # Find most connected users (users with most skills)
        user_connections = {}
        for user in user_nodes:
            user_connections[user] = len(list(user_network.neighbors(user)))
        
        top_users = sorted(user_connections.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Find most common skills (skills connected to most users)
        skill_connections = {}
        for skill in skill_nodes:
            skill_connections[skill] = len(list(user_network.neighbors(skill)))
        
        top_skills = sorted(skill_connections.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Get job skills network data
        job_network = get_skill_job_network()
        job_nodes = [node for node in job_network.nodes() if node.startswith('job_')]
        
        return jsonify({
            "success": True,
            "user_count": len(user_nodes),
            "skill_count": len(skill_nodes),
            "job_count": len(job_nodes),
            "top_users": [{"id": user.replace("user_", ""), "connections": conns} for user, conns in top_users],
            "top_skills": [{"name": skill.replace("skill_", ""), "connections": conns} for skill, conns in top_skills]
        })
    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 500

# Add a utility function to find skill recommendations based on network analysis
@app.route('/api/skill_recommendations')
def skill_recommendations():
    """Get skill recommendations for the current user based on network analysis"""
    if 'user_id' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    user_id = session['user_id']
    user_node = f"user_{user_id}"
    
    try:
        # Get user similarity network
        G = get_user_similarity_network()
        
        # Check if user exists in the network
        if user_node not in G.nodes():
            return jsonify({
                "error": "User not found in network. Please complete a skill assessment first.",
                "success": False
            }), 404
        
        # Get user's current skills
        user_skills = set()
        for neighbor in G.neighbors(user_node):
            if neighbor.startswith('skill_'):
                user_skills.add(neighbor.replace('skill_', ''))
        
        # Find similar users (users connected to the current user)
        similar_users = []
        for neighbor in G.neighbors(user_node):
            if neighbor.startswith('user_'):
                similar_users.append(neighbor)
        
        # Get skills from similar users that the current user doesn't have
        recommended_skills = {}
        for similar_user in similar_users:
            for skill_node in G.neighbors(similar_user):
                if skill_node.startswith('skill_'):
                    skill_name = skill_node.replace('skill_', '')
                    if skill_name not in user_skills:
                        if skill_name in recommended_skills:
                            recommended_skills[skill_name] += 1
                        else:
                            recommended_skills[skill_name] = 1
        
        # Sort recommendations by frequency
        sorted_recommendations = sorted(recommended_skills.items(), key=lambda x: x[1], reverse=True)
        
        # Get job market demand for these skills
        skill_job_network = get_skill_job_network()
        skill_demand = {}
        
        for skill, _ in sorted_recommendations:
            skill_node = f"skill_{skill}"
            if skill_node in skill_job_network.nodes():
                connected_jobs = list(skill_job_network.neighbors(skill_node))
                skill_demand[skill] = len(connected_jobs)
        
        # Format the final recommendations
        final_recommendations = []
        for skill, frequency in sorted_recommendations[:10]:  # Top 10 recommendations
            final_recommendations.append({
                "skill": skill,
                "peer_frequency": frequency,
                "job_demand": skill_demand.get(skill, 0)
            })
        
        return jsonify({
            "success": True,
            "current_skills": list(user_skills),
            "recommendations": final_recommendations
        })
    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 500





if __name__ == '__main__':
    app.run(debug=True)