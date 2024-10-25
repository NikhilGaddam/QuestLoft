import uuid
import datetime
import json
from config.db_config import get_db_connection
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from config.json_schema import Feedback
quiz_sessions = {}

def start_quiz(user_id, grade, llm):
    # Generate 10 questions based on the student's grade
    questions = generate_quiz_questions(grade, llm)
    if not questions:
        return "Sorry, I couldn't generate quiz questions at this time."
    # Initialize quiz session
    quiz_id = str(uuid.uuid4())
    quiz_sessions[user_id] = {
        'quiz_id': quiz_id,
        'questions': questions,
        'current_question': 0,
        'answers': [],
        'grade': grade,
        'start_time': datetime.datetime.now()
    }
    # Return the first question
    return questions[0]['question']

def generate_quiz_questions(grade, llm):
    # Define the prompt template
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful assistant that generates quiz questions."),
        ("human", "Generate 10 quiz questions with answers for a student in grade {grade}. "
                  "The questions should be appropriate for their difficulty level. "
                  "Provide only the questions and the correct answers in a valid JSON format as a list of dictionaries. "
                  "Do not include any other text or explanations or ``` code blocks. "
                  "Each dictionary should have 'question' and 'answer' keys. Example: "
                  "[{{\"question\": \"What is 2 + 2?\", \"answer\": \"4\"}}, "
                  "{{\"question\": \"What is the capital of France?\", \"answer\": \"Paris\"}}]")
    ])

    # Create the chain
    chain = prompt | llm

    # Invoke the chain, passing 'grade' as input
    res = chain.invoke({"grade": grade})

    # Extract the AI's response
    ai_response = res.content
    print("AI Response:", ai_response)  
    try:
        questions = json.loads(ai_response)
        # Ensure we have 10 questions
        if len(questions) != 10:
            print("Error: Expected 10 questions, but received", len(questions))
            return []
        return questions
    except json.JSONDecodeError:
        return []


def handle_quiz_answer(user_id, answer, llm):
    session = quiz_sessions.get(user_id)
    if not session:
        return "You are not currently in a quiz session. Please type /quiz to start a new quiz."
    
    current_question_index = session['current_question']
    current_question = session['questions'][current_question_index]
    
    session['answers'].append({
        'question': current_question['question'],
        'student_answer': answer,
        'correct_answer': current_question['answer']
    })
    
    session['current_question'] += 1
    
    if session['current_question'] >= len(session['questions']):
        # Quiz is finished
        score, total_questions, correct_answers, incorrect_answers, feedback = calculate_score_and_feedback(session['answers'], llm)
        
        # Store test data in the database
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
        
        del quiz_sessions[user_id]
        
        return (f"Quiz completed! Your score is {score}/{total_questions}.\n\n"
                f"Areas well done:\n{feedback['areas_well_done']}\n\n"
                f"Areas to improve:\n{feedback['areas_to_improve']}")
    else:
        next_question = session['questions'][session['current_question']]['question']
        return next_question

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
        print(f"Error parsing LLM response: {e}")
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

    # Insert into TestScores table without TestID as it is auto-generated
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
