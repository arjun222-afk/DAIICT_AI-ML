# interview_utils.py
import json
import os
from dotenv import load_dotenv
import sqlite3
import google.generativeai as genai

load_dotenv()
genai.configure(api_key=os.environ.get('GEMINI_API_KEY'))

# Define the model name to use - using a standard model that should be available
MODEL_NAME = "gemini-1.5-flash"  # This is the standard model name that replaced gemini-flash-2.0

def get_db_connection():
    conn = sqlite3.connect('job_market.db')
    conn.row_factory = sqlite3.Row
    return conn

def generate_initial_interview_questions(skill_area, job_role):
    """Generate the first easy technical question for the interview"""
    # Generate interview context with Gemini
    system_prompt = f"""You are conducting a non-coding virtual interview for a {job_role} position.
The interview focuses on assessing the candidate's basic understanding of {skill_area} through easy, beginner-friendly questions.
Do NOT ask the candidate to write or explain code. Avoid algorithmic or implementation-heavy questions.
Ask only one simple, conceptual, or scenario-based question per response.
Do NOT include greetings, introductions, or names.
Return your response as JSON with a single field: 'first_question'."""
    
    user_prompt = f"Start a non-coding technical interview for a {job_role} position, focused on {skill_area}."

    
    try:
        # Create the model with the defined model name
        model = genai.GenerativeModel(MODEL_NAME)
        
        # Generate content with the model
        response = model.generate_content([
            {"role": "user", "parts": [f"{system_prompt}\n\n{user_prompt}"]}
        ])
        
        # First, clean the response text in case it contains markdown formatting
        response_text = response.text.strip()
        if response_text.startswith("```") and response_text.endswith("```"):
            # Extract content from code block
            clean_text = response_text.strip('```')
            if clean_text.startswith('json'):
                clean_text = clean_text[4:].strip()
        else:
            clean_text = response_text
            
        # Try to find JSON object if text contains other elements
        if not clean_text.startswith('{'):
            import re
            json_match = re.search(r'(\{.*\})', clean_text, re.DOTALL)
            if json_match:
                clean_text = json_match.group(1)
        
        try:
            result = json.loads(clean_text)
            return {
                "greeting": result.get("greeting", f"Hello, I'll be interviewing you for the {job_role} position today, focusing on {skill_area}."),
                "first_question": result.get("first_question", f"Let's start with a question about {skill_area}. Can you explain your experience with it?")
            }
        except Exception as e:
            print(f"Error parsing AI response: {e}")
            print(f"Cleaned response: {clean_text}")
            return {
                "greeting": f"Hello, I'll be interviewing you for the {job_role} position today, focusing on {skill_area}.",
                "first_question": f"Let's start with a question about {skill_area}. Can you explain your experience with it?"
            }
    except Exception as e:
        print(f"Error generating content: {e}")
        return {
            "greeting": f"Hello, I'll be interviewing you for the {job_role} position today, focusing on {skill_area}.",
            "first_question": f"Let's start with a question about {skill_area}. Can you explain your experience with it?"
        }
        
def generate_follow_up_question(skill_area, job_role, previous_question, previous_answer):
    """Generate a follow-up question based on the previous answer"""
    # Track how many questions have been asked in this thread to determine when to end
    question_count = get_question_count_for_current_interview(previous_question)
    
    # Set a flag for ending the interview after a reasonable number of questions
    is_final = question_count >= 5
    
    if is_final:
        end_prompt = f"This should be the final question of the interview. After this question, please include a brief closing statement thanking the candidate."
    else:
        end_prompt = "The interview should continue after this question."
    
    system_prompt = f"""You are an experienced technical interviewer for {job_role} positions.
    You are conducting a virtual interview focused on {skill_area}.
    
    IMPORTANT: The candidate has just answered the following question:
    "{previous_question}"
    
    With this answer:
    "{previous_answer}"
    
    Based on the candidate's specific answer above, ask a relevant follow-up question that directly references
    something they mentioned. The question must logically follow from their exact response and probe deeper
    into a specific detail or claim they made.
    
    {end_prompt}
    
    RESPONSE FORMAT: A simple JSON object with the following structure:
    {{"next_question": "Your follow-up question here"}}
    """

    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(system_prompt)
        
        response_text = response.text.strip()
        
        # Clean up the response
        if response_text.startswith("```") and response_text.endswith("```"):
            # Extract content from code block
            clean_text = response_text.strip('```')
            if clean_text.startswith('json'):
                clean_text = clean_text[4:].strip()
        else:
            clean_text = response_text
            
        # Try to find JSON object if text contains other elements
        if not clean_text.startswith('{'):
            import re
            json_match = re.search(r'(\{.*\})', clean_text, re.DOTALL)
            if json_match:
                clean_text = json_match.group(1)
        
        try:
            result = json.loads(clean_text)
            next_question = result.get("next_question", "")
            
            # Ensure the question references the previous answer
            if not next_question or not any(keyword in next_question.lower() for keyword in previous_answer.lower().split() if len(keyword) > 4):
                # If the generated question doesn't reference the answer, create a fallback
                keywords = [word for word in previous_answer.lower().split() 
                            if len(word) > 4 and word not in ["about", "would", "could", "should", "there", "their", "which", "where", "when", "what"]]
                if keywords:
                    key_topic = max(keywords, key=len)  # Use the longest keyword as it might be most significant
                    next_question = f"You mentioned {key_topic}. Could you elaborate more on your experience with that specifically?"
            
            # For logging purposes
            print(f"Generated follow-up question: {next_question}")
            
            return {
                "next_question": next_question or f"Based on your answer, how would you apply your knowledge of {skill_area} in a real-world scenario?",
                "end_message": result.get("end_message", ""),
                "is_final": is_final
            }
                
        except Exception as e:
            print(f"Error parsing AI response: {e}")
            print(f"Cleaned text: {clean_text}")
            # Create a fallback
            return {
                "next_question": f"Based on what you just shared, could you elaborate on how your {skill_area} skills would help you in this {job_role} role?",
                "is_final": is_final
            }
            
    except Exception as e:
        print(f"Error in follow-up question generation: {e}")
        # Create a fallback that references the answer
        words = previous_answer.split()
        if len(words) >= 5:
            topic = words[min(4, len(words)-1)]  # Get a word from the answer to reference
            return {
                "next_question": f"You mentioned '{topic}'. Can you tell me more about your experience with that in the context of {skill_area}?",
                "is_final": is_final
            }
        return {
            "next_question": f"Based on what you just shared, how would you apply your {skill_area} knowledge to solve a complex problem in a {job_role} position?",
            "is_final": is_final
        }

def generate_interview_analysis(interview_id):
    """Generate analysis and feedback based on the complete interview"""
    # Retrieve all Q&A pairs for this interview
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get interview context
    cursor.execute(
        "SELECT skill_area, job_role FROM interview_sessions WHERE id = ?", 
        (interview_id,)
    )
    interview_session = cursor.fetchone()
    
    if not interview_session:
        conn.close()
        print(f"No interview session found with ID {interview_id}")
        return {
            "technical_score": 70,
            "communication_score": 70,
            "strengths": ["No interview data found"]
        }, {
            "areas_for_improvement": ["Try starting a new interview"],
            "overall_feedback": "We couldn't find the interview data.",
            "next_steps": ["Try another practice interview"]
        }
    
    # Get all Q&A pairs
    cursor.execute(
        "SELECT question, answer FROM interview_qa WHERE interview_id = ? ORDER BY timestamp",
        (interview_id,)
    )
    qa_pairs = cursor.fetchall()
    conn.close()
    
    # Format the interview transcript
    transcript = "\n\n".join([f"Q: {qa['question']}\nA: {qa['answer']}" for qa in qa_pairs])
    
    # Get AI analysis
    system_prompt = f"""You are an expert in technical interviews for {interview_session['job_role']} positions.
    Analyze the following interview transcript focused on {interview_session['skill_area']} skills.
    Provide an assessment of the candidate's technical knowledge, communication skills, and problem-solving approach.
    Also provide specific, actionable feedback on how they can improve.
    
    Your response MUST be in the following JSON format:
    {{
        "technical_score": <number between 0-100>,
        "communication_score": <number between 0-100>,
        "strengths": [<array of specific strengths>],
        "areas_for_improvement": [<array of specific areas to improve>],
        "overall_feedback": "<paragraph of overall assessment>",
        "next_steps": [<array of recommended actions>]
    }}
    """
    
    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content([
            {"role": "user", "parts": [f"{system_prompt}\n\nInterview transcript:\n{transcript}"]}
        ])
        
        # Clean up response text
        response_text = response.text.strip()
        if response_text.startswith("```") and response_text.endswith("```"):
            # Extract content from code block
            clean_text = response_text.strip('```')
            if clean_text.startswith('json'):
                clean_text = clean_text[4:].strip()
        else:
            clean_text = response_text
            
        # Try to find JSON object if text contains other elements
        if not clean_text.startswith('{'):
            import re
            json_match = re.search(r'(\{.*\})', clean_text, re.DOTALL)
            if json_match:
                clean_text = json_match.group(1)
        
        try:
            result = json.loads(clean_text)
            
            analysis = {
                "technical_score": result.get("technical_score", 70),
                "communication_score": result.get("communication_score", 70),
                "strengths": result.get("strengths", ["Good understanding of basic concepts"])
            }
            
            feedback = {
                "areas_for_improvement": result.get("areas_for_improvement", ["Practice more technical explanations"]),
                "overall_feedback": result.get("overall_feedback", "Your interview showed promising skills but needs further development."),
                "next_steps": result.get("next_steps", ["Review fundamental concepts", "Practice explaining technical solutions"])
            }
            
            # For logging
            print("Generated interview analysis:")
            print(json.dumps(analysis, indent=2))
            print("Generated feedback:")
            print(json.dumps(feedback, indent=2))
            
            return analysis, feedback
        except Exception as e:
            print(f"Error parsing AI response: {e}")
            print(f"Cleaned text: {clean_text}")
            return {
                "technical_score": 70,
                "communication_score": 70,
                "strengths": ["Unable to generate detailed analysis"]
            }, {
                "areas_for_improvement": ["Practice more interview questions"],
                "overall_feedback": "We were unable to generate a complete analysis of your interview.",
                "next_steps": ["Try another practice interview"]
            }
    except Exception as e:
        print(f"Error in interview analysis: {e}")
        return {
            "technical_score": 70,
            "communication_score": 70,
            "strengths": ["Unable to generate detailed analysis"]
        }, {
            "areas_for_improvement": ["Practice more interview questions"],
            "overall_feedback": "We were unable to generate a complete analysis of your interview.",
            "next_steps": ["Try another practice interview"]
        }

def get_question_count_for_current_interview(question):
    """Simple helper to track how many questions have been asked based on the complexity of the current question"""
    # This is a very simple implementation - in a real system, you'd track this in the database
    # Here we're just using the length/complexity of the question as a crude approximation
    words = question.split()
    if len(words) > 20:
        return 4  # Complex question, probably later in the interview
    elif len(words) > 15:
        return 3
    elif len(words) > 10:
        return 2
    else:
        return 1  # Simple question, probably early in the interview