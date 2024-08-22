from flask import Flask, render_template, request, jsonify
import neo4j
import openai
import json
import os

app = Flask(__name__)

def query_openai_api(prompt):
    try:
        response = openai.Completion.create(
            engine="gpt-4-turbo",  # 使用你希望的模型
            prompt=prompt,
            max_tokens=150,  # 设置返回的token数量
            n=1,  # 只返回一个响应
            stop=None,
            temperature=0.7  # 设置创意程度
        )
        return response.choices[0].text.strip()
    except Exception as e:
        return f"Error querying OpenAI API: {str(e)}"

def load_config():
    config_path = './config/config.json'
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, 'r') as f:
        config = json.load(f)

    return config

config = load_config()
openai.api_key = config['openai_api_key']

# Initialize Neo4j driver
neo4j_driver = neo4j.GraphDatabase.driver(
    uri="bolt://neo4j:7687",
    auth=("neo4j", "password")
)

def get_db_connection():
    return neo4j_driver.session()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/save_form', methods=['POST'])
def save_form():
    data = request.json
    with get_db_connection() as session:
        session.run("""
        MERGE (u:User {username: $username})
        SET u.course = $course, u.level = $level, u.goal = $goal, u.skills = $skills
        """, username=data['username'], course=data['course'], level=data['level'], goal=data['goal'], skills=data['skills'])
    return jsonify({'message': 'Form saved successfully'})

@app.route('/get_user_data', methods=['GET'])
def get_user_data():
    username = request.args.get('username')  # 获取前端传递的用户名
    with get_db_connection() as session:
        result = session.run("MATCH (u:User {username: $username}) RETURN u.course AS course, u.level AS level, u.goal AS goal, u.skills AS skills LIMIT 1", username=username)
        user_data = result.single()
        if user_data:
            return jsonify(dict(user_data))
        return jsonify({})

@app.route('/generate_prompt', methods=['POST'])
def generate_prompt():
    data = request.json
    keywords = split_keywords(data['input'])
    knowledge_graph = {"course": "cs1", "level": "beginner"}  # Simplified for demo
    prompt = generate_prompt_by(keywords, knowledge_graph)
    return jsonify({'prompt': prompt})

def split_keywords(user_input):
    return user_input.split()

def generate_prompt_by(keywords, knowledge_graph):
    return f"Learning path for {keywords} based on your knowledge in {knowledge_graph['course']} at {knowledge_graph['level']} level."

@app.route('/query_gpt', methods=['POST'])
def query_gpt():
    data = request.json
    prompt = data['prompt']

    # Simulated GPT-4 response for demo purposes
    response = query_openai_api(prompt)

    # Simulate streaming by splitting response into chunks
    lines = response.split('.')
    return jsonify({'response': '.\n'.join(lines)})


@app.route('/handle_response', methods=['POST'])
def handle_response():
    data = request.json
    if data['type'] == 'good':
        with get_db_connection() as session:
            session.run("""
            MATCH (u:User {username: $username}) 
            SET u.skills = coalesce(u.skills, '') + ', NLP Basics'
            """, username=data['username'])
        return jsonify({'message': 'Knowledge graph updated!'})
    return jsonify({'message': 'Response acknowledged.'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
