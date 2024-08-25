from flask import Flask, render_template, request, jsonify
import neo4j
import openai
import json
import requests
import os
import logging

app = Flask(__name__)

def query_openai_api(prompt):
    api_key = config['openai_api_key']  # 从环境变量中获取API密钥
    if not api_key:
        raise ValueError("Setting OPENAI_API_KEY")

    url = "https://api.openai.com/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "gpt-4o-mini",  # 确保你使用的是正确的模型名称
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ]
    }

    proxies = {
        "http": "http://host.docker.internal:1087",
        "https": "http://host.docker.internal:1087"
    }

    response = requests.post(url, headers=headers, json=data, proxies=proxies)

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"请求失败，状态码: {response.status_code}, 返回内容: {response.text}")



def load_config():
    config_path = './config/config.json'
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, 'r') as f:
        config = json.load(f)

    return config

config = load_config()

# Initialize Neo4j driver
neo4j_driver = neo4j.GraphDatabase.driver(
    uri="bolt://neo4j:7687",
    auth=("neo4j", "password")
)

def get_db_connection():
    return neo4j_driver.session()

@app.route('/')
def index():
    username = request.args.get('username')  # 从URL中获取username参数
    user_data = {}

    if username:
        with get_db_connection() as session:
            result = session.run("""
            MATCH (u:User {username: $username}) 
            RETURN u.username AS username, u.course AS course, u.level AS level, u.goal AS goal, u.skills AS skills 
            LIMIT 1
            """, username=username)
            record = result.single()
            if record:
                user_data = dict(record)

    return render_template('index.html', user_data=user_data)  # 将用户数据传递给模板

@app.route('/save_form', methods=['POST'])
def save_form():
    data = request.json
    with get_db_connection() as session:
        session.run("""
        MERGE (u:User {username: $username})
        SET u.course = $course, u.level = $level, u.goal = $goal, u.skills = $skills
        """, username=data['username'], course=data['course'], level=data['level'], goal=data['goal'], skills=data['skills'])
    return jsonify({'message': 'Form saved successfully'})


@app.route('/get_learning_state', methods=['GET'])
def get_learning_state():
    username = request.args.get('username')
    with get_db_connection() as session:
        user = session.run("""
        MATCH (u:User {username: $username})
        RETURN u.course AS course, u.level AS level, u.goal AS goal, u.skills AS skills
        """, username=username).single()

    if user:
        return jsonify({
            'learning_state': {
                'course': user['course'],
                'level': user['level'],
                'goal': user['goal'],
                'skills': user['skills']
            }
        })
    else:
        return jsonify({'error': 'User not found'}), 404

@app.route('/generate_prompt', methods=['POST'])
def generate_prompt():
    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    username = data.get('username')
    if not username:
        return jsonify({'error': 'Username is required'}), 400

    # 从Neo4j获取用户的知识图谱
    with get_db_connection() as session:
        result = session.run("""
            MATCH (u:User {username: $username})
            RETURN u.course AS course, u.level AS level, u.goal AS goal, u.skills AS skills
            LIMIT 1
        """, username=username)
        user_data = result.single()

    if not user_data:
        return jsonify({'error': 'User not found'}), 404

    # 提取知识图谱信息
    knowledge_graph = {
        "course": user_data["course"],
        "level": user_data["level"],
        "goal": user_data["goal"],
        "skills": user_data["skills"]
    }

    # 使用GPT提取关键字
    keywords = split_keywords(data['input'])

    # 根据关键字和知识图谱生成Prompt
    prompt = generate_prompt_by(keywords, knowledge_graph)

    return jsonify({'prompt': prompt})

def split_keywords(user_input):
    prompt = f"You are an AI assistant designed to help students with personalized learning. A student wants to learn a topic and has asked the following question: '{user_input}' Please identify the keywords in the question. Focus on extracting terms that are directly relevant to the student's educational needs. notice, just return the keywords."
    response = query_openai_api(prompt)
    # 输出API响应的调试信息
    print(f"API response: {response}")

    # 从响应中提取内容 (假设API返回的结构是我们期望的)
    if 'choices' in response and len(response['choices']) > 0:
        keywords_text = response['choices'][0]['message']['content']
        print(f"Extracted keywords text: {keywords_text}")
    else:
        raise Exception("未能从OpenAI API中提取关键词")

    # 假设GPT返回一个逗号分隔的字符串，处理成列表
    keywords = [keyword.strip() for keyword in keywords_text.split(",") if keyword.strip()]
    print(f"Final extracted keywords: {keywords}")

    return keywords


def generate_prompt_by(keywords, knowledge_graph):
    # 生成的学习路径Prompt
    return f"Learning path for {keywords} based on your knowledge in {knowledge_graph['course']} at {knowledge_graph['level']} level."

# 配置日志
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

@app.route('/query_gpt', methods=['POST'])
def query_gpt():
    data = request.json
    prompt = data['prompt']

    # 调用 OpenAI API 获取响应
    response = query_openai_api(prompt)

    # 提取API返回的内容部分
    content = response['choices'][0]['message']['content']

    # 返回提取的内容
    return jsonify({'response': content})



@app.route('/handle_response', methods=['POST'])
def handle_response():
    data = request.json
    logging.debug(f"Received data: {data}")

    if data['type'] == 'good':
        content = data.get('content', '')
        logging.debug(f"Content to process: {content}")

        # 提取关键字，假设提取结果
        keywords = split_keywords(content)
        logging.debug(f"Extracted keywords: {keywords}")

        with get_db_connection() as session:
            for keyword in keywords:
                logging.debug(f"Updating knowledge graph for user: {data['username']} with skill: {keyword}")
                session.run("""
                MATCH (u:User {username: $username}) 
                SET u.skills = coalesce(u.skills, '') + ', ' + $keyword
                """, username=data['username'], keyword=keyword)

        logging.debug("Knowledge graph updated successfully.")
        return jsonify({'message': 'Knowledge graph updated with new skills!'})

    logging.debug("Received response type is not 'good'. Acknowledging response.")
    return jsonify({'message': 'Response acknowledged.'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
