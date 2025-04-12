# ai_utils.py
import os
import markdown
from dotenv import load_dotenv
import re
from openai import OpenAI

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY")
)

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