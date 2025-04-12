# network_analysis.py
import networkx as nx
from pyvis.network import Network
import sqlite3
import json
from pathlib import Path
import os

# Database connection helper
def get_db_connection():
    conn = sqlite3.connect('job_market.db')
    conn.row_factory = sqlite3.Row
    return conn

def generate_network_html(graph, filename, title="Network Analysis", height="600px", width="100%"):
    """
    Generate HTML file from a NetworkX graph using PyVis
    """
    # Create output directory if it doesn't exist
    output_dir = Path("static/networks")
    os.makedirs(output_dir, exist_ok=True)
    
    # Create PyVis network
    net = Network(height=height, width=width, directed=True, notebook=False)
    
    # Set network options for better visualization
    net.set_options("""
    {
      "nodes": {
        "font": {"size": 12},
        "scaling": {"min": 10, "max": 30}
      },
      "edges": {
        "color": {"inherit": true},
        "smooth": {"type": "dynamic"},
        "arrows": {"to": {"enabled": true}}
      },
      "physics": {
        "barnesHut": {"gravitationalConstant": -80000, "springLength": 250},
        "stabilization": {"iterations": 1000}
      }
    }
    """)
    
    # Add the NetworkX graph to PyVis
    net.from_nx(graph)
    
    # Save the network to an HTML file
    output_path = output_dir / filename
    net.save_graph(str(output_path))
    
    # Return the relative path for the Flask template
    return f"networks/{filename}"

def get_user_similarity_network():
    """
    Generate a network showing connections between users based on shared skills
    """
    # Create graph
    G = nx.Graph()
    
    conn = get_db_connection()
    
    # Get all users
    users = conn.execute("SELECT id, name, email, skills_data FROM users").fetchall()
    
    # User nodes with skills
    user_skills = {}
    
    for user in users:
        user_id = user['id']
        user_name = user['name']
        
        # Add user node
        G.add_node(f"user_{user_id}", 
                  label=user_name,
                  title=f"User: {user_name}",
                  group="users",
                  shape="circle",
                  color="#4169E1")  # Royal Blue
        
        # Parse skills data
        try:
            if user['skills_data'] and user['skills_data'].strip():
                skills_data = json.loads(user['skills_data'])
                
                # Get proficient skills
                proficient_skills = skills_data.get('proficientSkills', [])
                
                # Store user's skills
                user_skills[user_id] = set(proficient_skills)
                
                # Add skills nodes and connections
                for skill in proficient_skills:
                    # Normalize skill name
                    skill_name = skill.lower().strip()
                    
                    # Add skill node if it doesn't exist
                    if not G.has_node(f"skill_{skill_name}"):
                        G.add_node(f"skill_{skill_name}", 
                                  label=skill,
                                  title=f"Skill: {skill}",
                                  group="skills",
                                  shape="diamond",
                                  color="#28a745")  # Green
                    
                    # Add edge between user and skill
                    G.add_edge(f"user_{user_id}", f"skill_{skill_name}", 
                              title="has_skill",
                              color="#aaaaaa")
        except Exception as e:
            print(f"Error processing skills for user {user_id}: {e}")
    
    # Get Quiz Results to add more skill connections
    quiz_results = conn.execute("""
        SELECT user_id, proficient_skills FROM user_quiz_results
        WHERE proficient_skills IS NOT NULL AND proficient_skills != '[]'
    """).fetchall()
    
    for result in quiz_results:
        user_id = result['user_id']
        
        # Skip if user doesn't exist (might have been deleted)
        if not G.has_node(f"user_{user_id}"):
            continue
            
        try:
            proficient_skills = json.loads(result['proficient_skills'])
            
            # Initialize user skills set if not exists
            if user_id not in user_skills:
                user_skills[user_id] = set()
                
            # Add skills from quiz results
            for skill in proficient_skills:
                # Normalize skill name
                skill_name = skill.lower().strip()
                user_skills[user_id].add(skill_name)
                
                # Add skill node if it doesn't exist
                if not G.has_node(f"skill_{skill_name}"):
                    G.add_node(f"skill_{skill_name}", 
                              label=skill,
                              title=f"Skill: {skill}",
                              group="skills",
                              shape="diamond",
                              color="#28a745")  # Green
                
                # Add edge between user and skill
                G.add_edge(f"user_{user_id}", f"skill_{skill_name}", 
                          title="has_skill",
                          color="#aaaaaa")
        except Exception as e:
            print(f"Error processing quiz results for user {user_id}: {e}")
    
    # Create edges between users based on shared skills
    user_ids = list(user_skills.keys())
    
    for i in range(len(user_ids)):
        for j in range(i+1, len(user_ids)):
            user1_id = user_ids[i]
            user2_id = user_ids[j]
            
            # Find shared skills
            shared_skills = user_skills[user1_id].intersection(user_skills[user2_id])
            
            # Add edge if they share skills
            if len(shared_skills) > 0:
                G.add_edge(f"user_{user1_id}", f"user_{user2_id}", 
                          title=f"Shares {len(shared_skills)} skills",
                          value=len(shared_skills),
                          width=len(shared_skills),
                          color="#ff7f0e")  # Orange
    
    conn.close()
    
    return G

def get_skill_job_network():
    """
    Generate a network showing connections between skills and jobs
    """
    # Create directed graph (skills -> jobs)
    G = nx.DiGraph()
    
    conn = get_db_connection()
    
    # Get top jobs
    jobs = conn.execute("""
        SELECT id, job_post, company, required_skills 
        FROM job_market_data 
        WHERE required_skills IS NOT NULL AND required_skills != ''
        LIMIT 100
    """).fetchall()
    
    # Get skills from the quiz_questions table for more skill nodes
    skills = conn.execute("""
        SELECT DISTINCT skill FROM quiz_questions
        WHERE skill IS NOT NULL AND skill != ''
    """).fetchall()
    
    # Add skill nodes from quiz questions
    for skill_row in skills:
        skill = skill_row['skill'].lower().strip()
        
        # Add skill node if it doesn't exist
        if not G.has_node(f"skill_{skill}"):
            G.add_node(f"skill_{skill}", 
                      label=skill.title(),
                      title=f"Skill: {skill.title()}",
                      group="skills",
                      shape="diamond",
                      color="#28a745")  # Green
    
    # Process jobs and their required skills
    for job in jobs:
        job_id = job['id']
        job_post = job['job_post']
        company = job['company']
        job_label = f"{job_post}"
        
        # Add job node
        G.add_node(f"job_{job_id}", 
                  label=job_label,
                  title=f"{job_post} at {company}",
                  group="jobs",
                  shape="box",
                  color="#dc3545")  # Red
        
        # Process skills and add connections
        if job['required_skills']:
            skills_list = job['required_skills'].split(',')
            
            for skill in skills_list:
                # Normalize skill name
                skill_name = skill.lower().strip()
                
                if not skill_name:
                    continue
                
                # Add skill node if it doesn't exist
                if not G.has_node(f"skill_{skill_name}"):
                    G.add_node(f"skill_{skill_name}", 
                              label=skill_name.title(),
                              title=f"Skill: {skill_name.title()}",
                              group="skills",
                              shape="diamond",
                              color="#28a745")  # Green
                
                # Add edge from skill to job
                G.add_edge(f"skill_{skill_name}", f"job_{job_id}", 
                          title="required_for",
                          color="#aaaaaa")
    
    conn.close()
    
    return G

def get_full_network():
    """
    Generate a comprehensive network with users, skills, and jobs
    """
    # Create directed graph
    G = nx.DiGraph()
    
    conn = get_db_connection()
    
    # Get all users
    users = conn.execute("SELECT id, name, email, skills_data FROM users").fetchall()
    
    # Get top jobs
    jobs = conn.execute("""
        SELECT id, job_post, company, required_skills 
        FROM job_market_data 
        WHERE required_skills IS NOT NULL AND required_skills != ''
        LIMIT 50
    """).fetchall()
    
    # Add user nodes with skills
    for user in users:
        user_id = user['id']
        user_name = user['name']
        
        # Add user node
        G.add_node(f"user_{user_id}", 
                  label=user_name,
                  title=f"User: {user_name}",
                  group="users",
                  shape="circle",
                  color="#4169E1")  # Royal Blue
        
        # Parse skills data
        try:
            if user['skills_data'] and user['skills_data'].strip():
                skills_data = json.loads(user['skills_data'])
                
                # Get proficient skills
                proficient_skills = skills_data.get('proficientSkills', [])
                
                # Add skills nodes and connections
                for skill in proficient_skills:
                    # Normalize skill name
                    skill_name = skill.lower().strip()
                    
                    # Add skill node if it doesn't exist
                    if not G.has_node(f"skill_{skill_name}"):
                        G.add_node(f"skill_{skill_name}", 
                                  label=skill,
                                  title=f"Skill: {skill}",
                                  group="skills",
                                  shape="diamond",
                                  color="#28a745")  # Green
                    
                    # Add edge between user and skill
                    G.add_edge(f"user_{user_id}", f"skill_{skill_name}", 
                              title="has_skill",
                              color="#aaaaaa")
        except Exception as e:
            print(f"Error processing skills for user {user_id}: {e}")
    
    # Get Quiz Results to add more skill connections
    quiz_results = conn.execute("""
        SELECT user_id, proficient_skills FROM user_quiz_results
        WHERE proficient_skills IS NOT NULL AND proficient_skills != '[]'
    """).fetchall()
    
    for result in quiz_results:
        user_id = result['user_id']
        
        # Skip if user doesn't exist (might have been deleted)
        if not G.has_node(f"user_{user_id}"):
            continue
            
        try:
            proficient_skills = json.loads(result['proficient_skills'])
            
            # Add skills from quiz results
            for skill in proficient_skills:
                # Normalize skill name
                skill_name = skill.lower().strip()
                
                # Add skill node if it doesn't exist
                if not G.has_node(f"skill_{skill_name}"):
                    G.add_node(f"skill_{skill_name}", 
                              label=skill,
                              title=f"Skill: {skill}",
                              group="skills",
                              shape="diamond",
                              color="#28a745")  # Green
                
                # Add edge between user and skill
                G.add_edge(f"user_{user_id}", f"skill_{skill_name}", 
                          title="has_skill",
                          color="#aaaaaa")
        except Exception as e:
            print(f"Error processing quiz results for user {user_id}: {e}")
    
    # Process jobs and their required skills
    for job in jobs:
        job_id = job['id']
        job_post = job['job_post']
        company = job['company']
        job_label = f"{job_post}"
        
        # Add job node
        G.add_node(f"job_{job_id}", 
                  label=job_label,
                  title=f"{job_post} at {company}",
                  group="jobs",
                  shape="box",
                  color="#dc3545")  # Red
        
        # Process skills and add connections
        if job['required_skills']:
            skills_list = job['required_skills'].split(',')
            
            for skill in skills_list:
                # Normalize skill name
                skill_name = skill.lower().strip()
                
                if not skill_name:
                    continue
                
                # Add skill node if it doesn't exist
                if not G.has_node(f"skill_{skill_name}"):
                    G.add_node(f"skill_{skill_name}", 
                              label=skill_name.title(),
                              title=f"Skill: {skill_name.title()}",
                              group="skills",
                              shape="diamond",
                              color="#28a745")  # Green
                
                # Add edge from skill to job
                G.add_edge(f"skill_{skill_name}", f"job_{job_id}", 
                          title="required_for",
                          color="#aaaaaa")
    
    conn.close()
    
    return G