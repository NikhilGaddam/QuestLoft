import uuid
import datetime
import json
import logging
from config.db_config import get_db_connection
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from config.json_schema import Feedback

logging.basicConfig(level=logging.INFO)

def start_quiz(user_id, grade, llm, redis_client):
    # Generate 10 questions based on the student's grade
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

def generate_quiz_questions(grade, llm):
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful assistant that generates quiz questions."),
        ("human", "Generate 10 quiz questions with answers for a student in grade {grade}. "
                  "The questions should be appropriate for their difficulty level. "
                  "Provide only the questions and the correct answers in a valid JSON format as a list of dictionaries. "
                  "Each dictionary should have 'question' and 'answer' keys.")
    ])
    
    chain = prompt | llm
    res = chain.invoke({"grade": grade})
    ai_response = res.content
    print("AI Response:", ai_response)
    
    try:
        questions = json.loads(ai_response)
        if len(questions) != 10:
            logging.error(f"Expected 10 questions, but received {len(questions)}")
            return []
        return questions
    except json.JSONDecodeError:
        logging.error("Failed to decode AI response for questions")
        return []

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

def calculate_score_and_feedback(answers, llm):
    score = 0
    total_questions = len(answers)
    correct_answers = 0
    incorrect_answers = 0
    correct_questions = []
    incorrect_questions = []
    
    for item in answers:
        correctness = evaluate_answer(item['question'], item['student_answer'], item['correct_answer'], llm)
        if correctness:
            score += 1
            correct_answers += 1
            correct_questions.append(item['question'])
        else:
            incorrect_answers += 1
            incorrect_questions.append(item['question'])
    
    feedback = get_summary_from_llm(correct_questions, incorrect_questions, llm)
    
    return score, total_questions, correct_answers, incorrect_answers, feedback

def get_summary_from_llm(correct_questions, incorrect_questions, llm):
    if not correct_questions and not incorrect_questions:
        logging.info("No correct or incorrect questions to summarize.")
        return {
            'areas_well_done': "None",
            'areas_to_improve': "None"
        }
    
    correct_part = ', '.join(correct_questions) if correct_questions else "None"
    incorrect_part = ', '.join(incorrect_questions) if incorrect_questions else "None"

    prompt_text = (f"Here is the student's quiz performance.\n\n"
                   f"Correctly answered questions: {correct_part}.\n\n"
                   f"Incorrectly answered questions: {incorrect_part}.\n\n"
                   f"Summarize the areas well done and areas to improve in the following JSON format: "
                   f"Do not include any other text or explanations.")

    structured_llm = llm.with_structured_output(Feedback, method="json_mode")
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful assistant that provides structured feedback in JSON."),
        ("human", prompt_text)
    ])
    
    chain = prompt | structured_llm

    try:
        res = chain.invoke({})
        feedback = res.dict() 
        
        feedback['areas_well_done'] = '\n'.join(feedback['areas_well_done'])
        feedback['areas_to_improve'] = '\n'.join(feedback['areas_to_improve'])
        
        return feedback

    except Exception as e:
        logging.error(f"Error parsing LLM response: {e}")
        return {
            'areas_well_done': "None",
            'areas_to_improve': "None"
        }

def evaluate_answer(question, student_answer, correct_answer, llm):
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an assistant that evaluates quiz answers."),
        ("human", "Question: {question}\nStudent's Answer: {student_answer}\nCorrect Answer: {correct_answer}\nIs the student's answer correct? Reply with 'True' or 'False'.")
    ])

    chain = prompt | llm

    res = chain.invoke({
        "question": question,
        "student_answer": student_answer,
        "correct_answer": correct_answer
    })

    ai_response = res.content.strip().lower()
    return ai_response == 'true'

def store_test_scores(user_id, quiz_id, start_time, score, total_questions, correct_answers, incorrect_answers, areas_well_done, areas_to_improve):
    connection = get_db_connection()
    cursor = connection.cursor()

    insert_query = """
    INSERT INTO TestScores (UserID, TestDate, Score, TotalQuestions, CorrectAnswers, IncorrectAnswers, AreasWellDone, AreasToImprove)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    cursor.execute(insert_query, (
        user_id,
        start_time, 
        score,
        total_questions,
        correct_answers,
        incorrect_answers,
        areas_well_done,
        areas_to_improve
    ))
    connection.commit()
    cursor.close()
    connection.close()
    logging.info(f"Stored test score for user {user_id} in database.")
