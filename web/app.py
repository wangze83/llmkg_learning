from flask import Flask, render_template, request, jsonify
import neo4j
import openai
import json
import requests
import os
import logging
from sklearn.feature_extraction.text import TfidfVectorizer

app = Flask(__name__)


def query_openai_api(prompt, context=None):
    api_key = config['openai_api_key']
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set")

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    messages = [{"role": "system",
                 "content": "You are an experienced educator and learning assistant, helping students in a clear and concise manner."}]

    if context:
        messages.append({"role": "system", "content": f"Context: {context}"})

    prompt_with_length_limit = f"{prompt} Please keep your response educational and focused."

    messages.append({"role": "user", "content": prompt_with_length_limit})

    data = {
        "model": config.get("model_name", "gpt-4o-mini"),
        "messages": messages,
        "max_tokens": 200
    }

    if config.get("use_proxies", False):
        proxies = {
            "http": config.get("proxy_http"),
            "https": config.get("proxy_https")
        }
    else:
        proxies = None

    try:
        response = requests.post(url, headers=headers, json=data, proxies=proxies, timeout=10)

        response.raise_for_status()
        return response.json()

    except requests.exceptions.Timeout:
        logging.error("Request timed out.")
        raise Exception("Request timed out. Please try again later.")

    except requests.exceptions.RequestException as e:
        logging.error(f"Request failed: {e}")
        raise Exception(f"Request failed: {response.status_code}, {response.text}")


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
    username = request.args.get('username')
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

    return render_template('index.html', user_data=user_data)


@app.route('/save_form', methods=['POST'])
def save_form():
    data = request.json
    with get_db_connection() as session:
        session.run("""
        MERGE (u:User {username: $username})
        SET u.course = $course, u.level = $level, u.goal = $goal, u.skills = $skills
        """, username=data['username'], course=data['course'], level=data['level'], goal=data['goal'],
                    skills=data['skills'])
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
                'skills': user['skills'],
                'username': username
            }
        })
    else:
        return jsonify({'error': 'User not found'}), 404


def get_user_knowledge_graph(username):
    with get_db_connection() as session:
        result = session.run("""
            MATCH (u:User {username: $username})
            RETURN u.course AS course, u.level AS level, u.goal AS goal, u.skills AS skills
            LIMIT 1
        """, username=username)
        user_data = result.single()

    if user_data:
        return {
            "course": user_data["course"],
            "level": user_data["level"],
            "goal": user_data["goal"],
            "skills": user_data["skills"]
        }
    else:
        return None


@app.route('/generate_prompt', methods=['POST'])
def generate_prompt():
    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    username = data.get('username')
    if not username:
        return jsonify({'error': 'Username is required'}), 400

    user_data = get_user_knowledge_graph(username)

    if not user_data:
        return jsonify({'error': 'User not found'}), 404

    knowledge_graph = {
        "course": user_data["course"],
        "level": user_data["level"],
        "goal": user_data["goal"],
        "skills": user_data["skills"]
    }

    keywords = split_keywords(data['input'])

    level = knowledge_graph["level"]
    if level == "beginner":
        template = "As a learning assistant, guide the student through the basics of {keywords} relevant to {course}, ensuring clarity and engagement."
    elif level == "intermediate":
        template = "Provide a detailed explanation of {keywords}, incorporating practical examples from {course}. Ensure the content is challenging yet approachable."
    elif level == "advanced":
        template = "Discuss advanced concepts of {keywords}, and explore how they apply to real-world scenarios in {course}. The student has experience with {skills}."
    else:
        template = "Describe {keywords}."

    skills = knowledge_graph["skills"]
    if isinstance(skills, str):
        skills = skills
    else:
        skills = ", ".join(skills)

    if skills:
        template += " Also, consider the student's prior knowledge in {skills}."

    logging.debug(f"skills log: {knowledge_graph['skills']}")

    prompt = template.format(
        keywords=", ".join(keywords),
        course=knowledge_graph["course"],
        skills=skills
    )

    logging.debug(f"prompt log: {prompt}")
    previous_context = data.get('search-input', '')
    if previous_context:
        prompt = f"Previously, the student was learning about {previous_context}. Now, {prompt}"

    return jsonify({'prompt': prompt})


def split_keywords(user_input):
    try :
        prompt = (
            f"Extract the most relevant and significant programming keywords from the following text. Python functions can be used directly."
            f"Exclude common phrases or words that express the user's intention or desires, such as 'keywords', 'Here are the', 'want', 'get start', 'learn' etc. "
            f"Text: '{user_input}'"
        )

        response = query_openai_api(prompt)
        if 'choices' in response and len(response['choices']) > 0:
            keywords = response['choices'][0]['message']['content'].strip().split(', ')
            extract_keywords = extract_keywords_func(keywords)
            filtered_keywords = [kw for kw in extract_keywords if kw.lower() not in {'want', 'get start'}]
            logging.debug(f"Extract keywords: {filtered_keywords}")
            return filtered_keywords
        else:
            raise Exception("Failed to extract keywords from OpenAI API")
    except Exception as e:
        logging.error(f" split_keywords Failed to process content: {e}")
        return []

def extract_keywords_func(filtered_text):
    # Check if filtered_text is a list, and if so, join it into a single string
    if isinstance(filtered_text, list):
        filtered_text = '\n'.join(filtered_text)

    logging.error(f"extract_keywords_func_filtered_text: {filtered_text}")

    # Now, split the input string by newlines and remove any bullet points
    keywords = [line.replace('- ', '').strip() for line in filtered_text.split('\n') if line.strip()]
    return keywords

def extract_keywords_tfidf(text, top_n=5):
    vectorizer = TfidfVectorizer(stop_words='english', max_features=top_n)
    tfidf_matrix = vectorizer.fit_transform([text])
    keywords = vectorizer.get_feature_names_out()
    return keywords


logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def is_response_acceptable(verification_content):
    verification_content = verification_content.lower()

    relevance_indicators = ["relevant", "appropriate", "crucial", "fundamental", "key concepts"]
    clarity_indicators = ["clear", "organized", "structured", "helps in understanding", "effectively demonstrates"]

    # Check for at least one indicator of relevance and one of clarity
    is_relevant = any(phrase in verification_content for phrase in relevance_indicators)
    is_clear = any(phrase in verification_content for phrase in clarity_indicators)

    return is_relevant and is_clear

@app.route('/query_gpt', methods=['POST'])
def query_gpt():
    data = request.json
    prompt = data['prompt']
    username = data['username']

    user_data = get_user_knowledge_graph(username)
    if not user_data:
        return jsonify({'error': 'User not found'}), 404

    response = query_openai_api(prompt)
    content = response['choices'][0]['message']['content']
    logging.debug(f"query_gpt origin content: {content}")

    verification_prompt = (
        "You are a helpful assistant. A student with the following knowledge graph is learning:"
        f"Course: {user_data['course']}, Level: {user_data['level']}, Goal: {user_data['goal']}, "
        f"Skills: {user_data['skills']}. The student received the following information from an AI-generated response:"
        f"'{content}'. Please assess whether this response is generally helpful and appropriate for the student's knowledge level and goals. "
        "Focus on whether the information is relevant and reasonably clear, considering the student's current understanding."
    )

    verification_response = query_openai_api(verification_prompt)
    verification_content = verification_response['choices'][0]['message']['content']
    logging.debug(f"verification_content: {verification_content}")

    if is_response_acceptable(verification_content):
        return jsonify({'response': content})
    else:
        return jsonify({
            'response': 'The generated content may not be accurate or well-structured. Please revise the prompt or try again.'})


def get_next_prompts(previous_query_result, previous_prompt):
    username = request.args.get('username')
    user_data = get_user_knowledge_graph(username)

    if not user_data:
        return jsonify({'error': 'User not found'}), 404

    level = user_data.get("level", "beginner")
    course = user_data.get("course", "unknown course")
    skills = user_data.get("skills", [])
    goal = user_data.get("goal", "")

    if level == "beginner":
        template = (
            "A beginner student studying {course} with the goal of {goal} received the following result: '{previous_query_result}'. "
            "Generate 3 simple, foundational prompts that directly address the student's learning. "
            "Only include the title or question of the prompt, without any further explanation or code.")
    elif level == "intermediate":
        template = (
            "A student with intermediate knowledge in {course} and aiming for {goal} got the following result: '{previous_query_result}'. "
            "Generate 3 prompts that challenge the student to deepen their understanding and apply their knowledge. "
            "Provide only the title or question for each prompt, without any additional explanation.")
    elif level == "advanced":
        template = (
            "An advanced student proficient in {skills} and studying {course} with the goal of {goal} got the following result: '{previous_query_result}'. "
            "Generate 3 complex, high-level prompts that push the student towards mastery and research-level understanding. "
            "Include only the title or question for each prompt, without any introductory remarks.")
    else:
        template = (
            "Based on the previous result: '{previous_query_result}', generate 3 next prompts for the student's further learning. "
            "Provide only the titles or questions for these prompts, without any additional content.")

    prompt = template.format(previous_query_result=previous_query_result, course=course, skills=", ".join(skills),
                             goal=goal)

    response = query_openai_api(previous_prompt, prompt)

    if 'choices' in response and len(response['choices']) > 0:
        next_prompts = response['choices'][0]['message']['content']
    else:
        raise Exception("Failed to get next step hint from OpenAI API")

    return next_prompts


@app.route('/next_prompts', methods=['POST'])
def next_prompts():
    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    previous_query_result = data.get('previous_query_result')
    previous_prompt = data.get('previous_prompt')

    if not previous_query_result or not previous_prompt:
        return jsonify({'error': 'Both previous_query_result and previous_prompt are required'}), 400

    next_prompts = get_next_prompts(previous_query_result, previous_prompt)

    return jsonify({'next_prompts': next_prompts})


@app.route('/handle_response', methods=['POST'])
def handle_response():
    data = request.json
    logging.debug(f"Received data: {data}")

    if data['type'] == 'good':
        username = data.get('username', '')
        response = data.get('response')
        prompt = data.get('prompt')
        logging.debug(f"Content to process: {response}")

        # Check for the specific phrase in the response
        if "The generated content may not be accurate or well-structured. Please revise the prompt or try again." in response:
            logging.debug(
                "Received response contains a notice about inaccurate content. Acknowledging without further action.")
            return jsonify({'message': 'Response acknowledged. No action taken due to the content warning.'})

        try:
            logging.debug("11111111111111111111111111111111111111111111111111")

            keywords = split_keywords(prompt)
            logging.debug(f"handle_response Extracted keywords: {keywords}")
            logging.debug("2222222222222222222222222222222222222222222222")

            with get_db_connection() as session:
                existing_skills_result = session.run("""
                MATCH (u:User {username: $username})
                RETURN u.skills AS skills
                """, username=username)

                existing_skills_record = existing_skills_result.single()
                existing_skills = existing_skills_record['skills'].split(', ') \
                    if existing_skills_record and existing_skills_record['skills'] \
                    else []

                new_keywords = [keyword for keyword in keywords if keyword not in existing_skills]
                logging.debug(f"New keywords to add: {new_keywords}")

                new_keywords = new_keywords[:2]
                logging.debug(f"Selected top 2 new keywords: {new_keywords}")

                if new_keywords:
                    session.run("""
                    MATCH (u:User {username: $username})
                    SET u.skills = COALESCE(u.skills, '') + CASE 
                        WHEN u.skills IS NULL OR u.skills = '' THEN $new_skills 
                        ELSE ', ' + $new_skills 
                    END
                    """, username=username, new_skills=', '.join(new_keywords))
                    logging.debug(f"Knowledge graph updated with new skills: {new_keywords}")
                else:
                    logging.debug(f"No new skills to update for user: {username}")

            return jsonify({'message': 'Knowledge graph updated with new skills!'})

        except Exception as e:
            logging.error(f"Failed to process content: {e}")
            return jsonify({'error': 'Failed to update knowledge graph'}), 500

    logging.debug("Received response type is not 'good'. Acknowledging response.")
    return jsonify({'message': 'Response acknowledged.'})

@app.route('/get_knowledge_graph', methods=['GET'])
def get_knowledge_graph():
    username = request.args.get('username')
    user_data = get_user_knowledge_graph(username)

    if user_data:
        nodes = [
            {
                "data": {
                    "id": "User",
                    "label": username
                }
            },
            {
                "data": {
                    "id": "Course",
                    "label": user_data.get("course", "")
                }
            },
            {
                "data": {
                    "id": "Level",
                    "label": user_data.get("level", "")
                }
            },
            {
                "data": {
                    "id": "Goal",
                    "label": user_data.get("goal", "")
                }
            },
            {
                "data": {
                    "id": "Skills",
                    "label": user_data.get("skills", "")
                }
            }
        ]

        edges = [
            {
                "data": {
                    "id": f"{username}_to_Course",
                    "source": "User",
                    "target": "Course"
                }
            },
            {
                "data": {
                    "id": f"{username}_to_Level",
                    "source": "User",
                    "target": "Level"
                }
            },
            {
                "data": {
                    "id": f"{username}_to_Goal",
                    "source": "User",
                    "target": "Goal"
                }
            },
            {
                "data": {
                    "id": f"{username}_to_Skills",
                    "source": "User",
                    "target": "Skills"
                }
            }
        ]

        return jsonify({
            "nodes": nodes,
            "edges": edges
        })
    else:
        return jsonify({'error': 'User not found'}), 404


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
