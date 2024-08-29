# Learning Assistant

## Introduction

This project aims to develop an intelligent learning assistant that enhances student interactions with large language models (LLMs) like GPT-4 by leveraging personal knowledge graphs. The system is designed to address common challenges faced by novice students, such as a lack of domain knowledge and difficulty in asking well-structured, precise questions.

### Problem Statement

Novice students often struggle with understanding course material due to their lack of familiarity with the subject and the unstructured nature of their queries. When using LLMs for assistance, they may receive vague or inaccurate responses, leading to confusion and frustration. Without personalized guidance, students may find it challenging to stay on track, increasing the likelihood of giving up.

### Solution

To mitigate these challenges, this project introduces a personal knowledge graph-based system. By constructing a knowledge graph from the student's learning records, course materials, and other relevant sources, the system provides context-aware interactions with the LLM. This ensures that the prompts and responses are more accurate, relevant, and aligned with the student's current knowledge level.

### Features

1. **Personal Knowledge Graph**: As students interact with the system, their knowledge graph is dynamically updated, allowing for personalized learning experiences.
2. **Prompt Generation**: Based on the knowledge graph, the system generates structured prompts that guide the LLM to provide precise and relevant responses.
3. **Verification and Feedback**: The system cross-verifies LLM-generated content with the knowledge graph, reducing the risk of misinformation. Students can provide feedback to refine their knowledge graph further.
4. **Adaptive Learning**: The system generates follow-up questions and adjusts the difficulty level based on the student's progress, promoting active learning.

This project serves as a proof-of-concept for a more reliable and personalized LLM-based tutoring system, with the potential to significantly improve the effectiveness of AI-driven learning tools.


## To start
### Step1
```
    make basic_flask_image
```
user docker
### Step1 
```
    cp web/config/config-template.json web/config/config.json
```
Edit openai_api_key etc.
### Step4
```
    make run
```
### Step5
```
    visit 127.0.0.1:5001
```