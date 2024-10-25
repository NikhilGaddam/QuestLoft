import uuid
import datetime
import json
import logging
from config.db_config import get_db_connection
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from config.json_schema import Feedback

def start_quiz(user_id, grade, llm, redis_client):
    questions = generate_quiz_questions(grade, llm)
    if not questions:
        return "Sorry, I couldn't generate quiz questions at this time."

    quiz_id = str(uuid.uuid4())
    session_data = {
        'quiz_id': quiz_id,
        'questions': questions,
        'current_question': 0,
        'answers': [],
        'grade': grade,
        'start_time': str(datetime.datetime.now())
    }

    try:
        # Store session data in Redis with an expiration (e.g., 30 minutes)
        redis_client.setex(user_id, 1800, json.dumps(session_data))
        logging.info(f"Quiz session started for user {user_id} with quiz ID {quiz_id}")
    except Exception as e:
        logging.error(f"Failed to store quiz session in Redis: {e}")
        return "An error occurred while starting the quiz."

    return 'Question 1: ' + questions[0]['question']

def handle_quiz_answer(user_id, answer, llm, redis_client):
    try:
        session_data = redis_client.get(user_id)
    except Exception as e:
        logging.error(f"Failed to retrieve quiz session from Redis: {e}")
        return "An error occurred while retrieving the quiz session."

    if not session_data:
        return "Your quiz session has expired or does not exist. Please start a new quiz."

    session = json.loads(session_data)
    current_question_index = session['current_question']
    current_question = session['questions'][current_question_index]

    session['answers'].append({
        'question': current_question['question'],
        'student_answer': answer,
        'correct_answer': current_question['answer']
    })
    
    session['current_question'] += 1

    if session['current_question'] >= len(session['questions']):
        score, total_questions, correct_answers, incorrect_answers, feedback = calculate_score_and_feedback(session['answers'], llm)
        
        store_test_scores(
            user_id, 
            session['quiz_id'], 
            session['start_time'], 
            score, 
            total_questions, 
            correct_answers, 
            incorrect_answers, 
            feedback['areas_well_done'], 
            feedback['areas_to_improve']
        )
        try:
            redis_client.delete(user_id)
        except Exception as e:
            logging.error(f"Failed to delete quiz session from Redis: {e}")

        return (f"Quiz completed! Your score is {score}/{total_questions}.\n\n"
                f"Areas well done:\n{feedback['areas_well_done']}\n\n"
                f"Areas to improve:\n{feedback['areas_to_improve']}")
    else:
        try:
            redis_client.set(user_id, json.dumps(session))
        except Exception as e:
            logging.error(f"Failed to update quiz session in Redis: {e}")
            return "An error occurred while saving your quiz progress."
        
        next_question_index = session['current_question']
        next_question = session['questions'][next_question_index]['question']
        return f"Question {next_question_index + 1}: {next_question}"
