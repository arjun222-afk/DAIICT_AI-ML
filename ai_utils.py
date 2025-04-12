# ai_utils.py
import os
import markdown
from dotenv import load_dotenv
import re
import sqlite3
import json
from openai import OpenAI
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY")
)

genai.configure(api_key=os.environ.get("AIzaSyB_cnjcZST321HoNqrK0uXNbe-t2lyYjRg"))

def get_career_path_recommendations(user_skills, quiz_results):
    """
    Generate personalized career path recommendations based on user skills and quiz results
    
    Args:
        user_skills (dict): Dictionary containing user's skills data
        quiz_results (list): List of user's quiz results
    
    Returns:
        dict: Career path recommendations with scores and rationales
    """
    # Extract relevant skills information
    proficient_skills = user_skills.get('proficientSkills', [])
    improvement_skills = user_skills.get('improvementSkills', [])
    
    # Get quiz scores by category
    technical_score = 0
    soft_skills_score = 0
    quiz_count = 0
    
    for result in quiz_results:
        category = result.get('category')
        score = result.get('score', 0)
        
        if category == 'technical':
            technical_score += score
            quiz_count += 1
        elif category == 'soft':
            soft_skills_score += score
            quiz_count += 1
    
    # Calculate average scores if quizzes were taken
    if quiz_count > 0:
        avg_technical = technical_score / quiz_count if technical_score > 0 else 0
        avg_soft = soft_skills_score / quiz_count if soft_skills_score > 0 else 0
    else:
        avg_technical = 0
        avg_soft = 0
    
    # Get available career paths from database
    conn = sqlite3.connect('job_market.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM career_paths")
    career_paths = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    # Create prompt for AI to analyze skills and recommend career paths
    prompt = f"""
    I'm a job seeker with the following skills profile:
    
    Proficient skills: {', '.join(proficient_skills)}
    Skills needing improvement: {', '.join(improvement_skills)}
    Technical assessment score: {avg_technical:.1f}/10
    Soft skills assessment score: {avg_soft:.1f}/10
    
    Based on my profile, please analyze the following career paths and rank them in order of best fit for me.
    For each path, provide:
    1. A matching score (0-100)
    2. A brief personalized explanation of why this path matches my skills
    3. Key skills I already have that align with this path
    4. Skills I should develop to excel in this path
    
    Career paths to consider:
    """
    
    for path in career_paths:
        prompt += f"""
    {path['title']}:
    - Description: {path['description']}
    - Required skills: {path['required_skills']}
    - Growth potential: {path['growth_potential']}
    - Market demand: {path['market_demand']}
    """
    
    prompt += """
    Return your answer as a JSON object with this structure:
    {
      "recommendations": [
        {
          "career_path_id": 1,
          "title": "Career Path Title",
          "matching_score": 85,
          "rationale": "Personalized explanation of the match",
          "matching_skills": ["Skill 1", "Skill 2"],
          "skills_to_develop": ["Skill A", "Skill B"]
        },
        ...
      ]
    }
    
    Only include the JSON in your response, nothing else.
    """
    
    try:
        # Configure Gemini model settings
        generation_config = {
            "temperature": 0.2,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 2048,
        }
        
        safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }
        
        # Initialize Gemini model
        model = genai.GenerativeModel(
            model_name="gemini-1.5-pro",
            generation_config=generation_config,
            safety_settings=safety_settings
        )
        
        # Make API call to Gemini
        response = model.generate_content(prompt)
        
        # Parse and return the JSON response
        result_text = response.text
        
        # Extract just the JSON part (handling potential markdown code blocks)
        if '```json' in result_text:
            json_str = result_text.split('```json')[1].split('```')[0].strip()
        elif '```' in result_text:
            json_str = result_text.split('```')[1].strip() 
        else:
            json_start = result_text.find('{')
            json_end = result_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = result_text[json_start:json_end]
            else:
                return {"error": "Failed to parse AI response"}
        
        recommendations = json.loads(json_str)
        return recommendations
            
    except Exception as e:
        print(f"Error getting career recommendations: {e}")
        return {"error": str(e)}

def save_user_recommendations(user_id, recommendations):
    """
    Save generated career recommendations to the database
    
    Args:
        user_id (int): User ID
        recommendations (dict): Career recommendations from AI
    
    Returns:
        bool: Success status
    """
    try:
        conn = sqlite3.connect('job_market.db')
        cursor = conn.cursor()
        
        # Clear previous recommendations for this user
        cursor.execute("DELETE FROM user_career_recommendations WHERE user_id = ?", (user_id,))
        
        # Insert new recommendations
        for rec in recommendations.get('recommendations', []):
            cursor.execute("""
                INSERT INTO user_career_recommendations 
                (user_id, career_path_id, matching_score, recommendation_date)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                user_id, 
                rec.get('career_path_id'), 
                rec.get('matching_score')
            ))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        print(f"Error saving recommendations: {e}")
        return False


def get_resume_tips(job_role):
    """
    Get resume tips tailored to a specific job role using OpenRouter API
    """
    try:
        prompt = f"""
        Provide brief, point-wise resume tips for someone applying for a {job_role} position.
        
        Format your response as follows:
        
        ## Resume Tips for {job_role} 📄
        
        ### Key Skills ⭐
        - [Skill point 1]
        - [Skill point 2]
        - [Skill point 3]
        
        ### Experience to Highlight 💼
        - [Experience point 1]
        - [Experience point 2]
        
        ### Resume Structure 🏗️
        - [Structure point 1]
        - [Structure point 2]
        
        ### Common Mistakes to Avoid ⚠️
        - [Mistake 1]
        - [Mistake 2]
        
        ## Resources
        
        ### YouTube Videos 📺
        - [Resume Writing for {job_role} Positions](https://www.youtube.com/watch?v=BYUy1yvjHxE)
        - [Top {job_role} Resume Tips](https://www.youtube.com/watch?v=6bJ5CszY5QU)
        
        ### Helpful Articles 📚
        - [How to Write a Great {job_role} Resume](https://www.indeed.com/career-advice/resumes-cover-letters/software-engineer-resume)
        - [Resume Tips for {job_role} Professionals](https://www.linkedin.com/advice/3/how-can-you-make-your-software-engineer-resume-stand)
        
        Keep the tips section concise (around 150 words total).
        Use ONLY the specific URLs I've provided above for the resources section, as these are verified to exist.
        """
        
        response = client.chat.completions.create(
            model="meta-llama/llama-3.1-8b-instruct:free",
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating resume tips: {str(e)}"

def get_interview_tips(job_role):
    """
    Get interview tips tailored to a specific job role using OpenRouter API
    """
    try:
        prompt = f"""
        Provide brief, point-wise interview tips for someone applying for a {job_role} position.
        
        Format your response as follows:
        
        ## Interview Tips for {job_role} 🎯
        
        ### Common Questions ❓
        - [Question 1]: [Brief answer tip]
        - [Question 2]: [Brief answer tip]
        
        ### Technical Preparation 💻
        - [Technical tip 1]
        - [Technical tip 2]
        
        ### Questions to Ask 🙋
        - [Question to ask 1]
        - [Question to ask 2]
        
        ### Demonstrate Your Skills 💪
        - [Demonstration tip 1]
        - [Demonstration tip 2]
        
        ### Mistakes to Avoid 🚫
        - [Mistake 1]
        - [Mistake 2]
        
        ## Resources
        
        ### YouTube Videos 📺
        - [Interview Tips for {job_role} Roles](https://www.youtube.com/watch?v=1mHjMNZZvFo)
        - [How to Ace Your {job_role} Interview](https://www.youtube.com/watch?v=0DNH4T4J--4)
        
        ### Helpful Articles 📚
        - [Top {job_role} Interview Questions](https://www.glassdoor.com/blog/software-engineer-interview-questions/)
        - [Preparing for Your {job_role} Interview](https://www.themuse.com/advice/software-engineer-interview-prep-guide)
        
        Keep the tips section concise (around 150 words total).
        Use ONLY the specific URLs I've provided above for the resources section, as these are verified to exist.
        """
        
        response = client.chat.completions.create(
            model="meta-llama/llama-3.1-8b-instruct:free",
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating interview tips: {str(e)}"

def format_tips_html(markdown_text):
    """
    Convert markdown to HTML with some additional styling
    """
    html = markdown.markdown(markdown_text)
    
    html = html.replace('<h2>', '<h2 class="mt-4 mb-3">')
    html = html.replace('<h3>', '<h3 class="mt-3 mb-2 text-primary">')
    html = html.replace('<ul>', '<ul class="list-group list-group-flush mb-3">')
    html = html.replace('<li>', '<li class="list-group-item">')
    
    html = re.sub(r'<a href="(.*?)"', r'<a href="\1" target="_blank" rel="noopener noreferrer"', html)
    
    return html