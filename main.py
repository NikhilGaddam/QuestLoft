import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv, find_dotenv
from openai import OpenAI
import logging
import redis
import azure.cognitiveservices.speech as speechsdk
import psycopg2
from psycopg2 import sql
from authentication.auth_routes import auth_bp
from services.quiz import start_quiz, handle_quiz_answer
from services.quiz_analysis import quiz_analysis_bp
from config.db_config import get_db_connection
from cms import cms

from helpers import speech_to_text, get_answer_from_question, text_to_speech
from chat_history_helpers import get_chatid_from_database, get_all_user_history, get_history_of_chat_id


logging.basicConfig(level=logging.DEBUG)

load_dotenv(override=True)

app = Flask(__name__)
CORS(app)
app.register_blueprint(quiz_analysis_bp)
app.register_blueprint(cms, url_prefix='/api')

redis_host = os.getenv("REDISHOST", "localhost")
redis_port = os.getenv("REDISPORT", 6379)
redis_user = os.getenv("REDISUSER", None)
redis_password = os.getenv("REDISPASSWORD", None)
redis_url = os.getenv("REDIS_URL", None)

user_messages = {}

# Connect to Redis using the environment variables
if redis_url:
    redis_client = redis.StrictRedis.from_url(redis_url)
else:
    redis_client = redis.StrictRedis(host=redis_host, port=redis_port, db=0)

CORS(app, resources={
    r"/*": {  # This will cover all routes
        "origins": ["http://localhost:3000"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

app.register_blueprint(auth_bp)

client = OpenAI()
llm = ChatOpenAI(api_key=os.environ.get("OPENAI_API_KEY"),
                 model=os.environ.get("OPENAI_MODEL_NAME"))

# For text to speech  ---------------------------
UPLOAD_FOLDER = './uploads'
speech_key = os.environ.get("SPEECH_KEY")
service_region = os.environ.get("SERVICE_REGION")

speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
speech_config.speech_synthesis_voice_name = "en-US-AvaMultilingualNeural"

file_name = f"{UPLOAD_FOLDER}/output.wav"
file_config = speechsdk.audio.AudioOutputConfig(filename=file_name)
speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=file_config)
# ------------------------------------------------

@app.route('/', methods=['GET'])
def get_status():
    return "Server Running", 200

@app.route('/flags', methods=['GET'])
def get_flagged_messages_api():
    search_term = request.args.get('search', None)
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        if search_term:
            query = sql.SQL("""
                SELECT email, message, timestamp
                FROM flags
                WHERE email ILIKE %s OR message ILIKE %s OR CAST(timestamp AS TEXT) ILIKE %s
                ORDER BY timestamp DESC;
            """)
            cursor.execute(query, (f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"))
        else:
            cursor.execute("""
                SELECT email, message, timestamp
                FROM flags
                ORDER BY timestamp DESC;
            """)
        flagged_messages = cursor.fetchall()
        cursor.close()
    except Exception as e:
        print(f"Error retrieving flagged messages: {e}")
        return jsonify({'error': 'Unable to retrieve flagged messages.'}), 500
    finally:
        connection.close()
    result = [
        {"email": row[0], "message": row[1], "timestamp": row[2].strftime("%Y-%m-%d %H:%M:%S")}
        for row in flagged_messages
    ]
    return jsonify(result), 200

@app.route('/chat/history', methods=['GET'])
def get_chat_history_for_user():
    user_email = request.args.get('userEmail')
    chat_histories = get_all_user_history(user_email)
    print(chat_histories)
    result = chat_histories
    return jsonify(result), 200

@app.route('/chat/history/<chat_id>', methods=["GET"])
def get_chat_history_for_chat_id(chat_id):
    chat_history = get_history_of_chat_id(chat_id)
    result = chat_history
    return jsonify(result), 200

@app.route('/chat/text', methods=['POST'])
def chat_text():
    data = request.get_json()
    user_message = data.get('userMessage')
    user_email = data.get('userEmail')
    print("User Message:", user_message)
    user_id = "12345" # Need to modify it later
    chat_id = data.get('chat_id')
    chat_id_exists = bool(chat_id)
    if not chat_id:
        chat_id = get_chatid_from_database(user_email)

    if not user_id:
        return jsonify({'error': 'User ID is required.'}), 400

    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT user_role FROM Users WHERE UserID = %s", (user_id,))
    result = cursor.fetchone()
    cursor.close()
    connection.close()
    if result:
        user_role = result[0]
    else:
        user_role = None

    if user_message.strip() == "/quiz":
        print("User started a quiz")
        if user_role != "Student":
            return jsonify({'error': 'Only students can start a quiz.'}), 403
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT Grade FROM Students WHERE UserID = %s", (user_id,))
        result = cursor.fetchone()
        cursor.close()
        connection.close()
        if result:
            grade = result[0]
            question = start_quiz(user_id, grade, llm,redis_client)
            return jsonify({"reply": question}), 200
        else:
            return jsonify({'error': 'Student grade not found.'}), 404
    else:
        session_data = redis_client.get(user_id)

        if session_data:
            # Handle quiz answer
            reply = handle_quiz_answer(user_id, user_message,llm,redis_client)
            return jsonify({"reply": reply}), 200
        else:
            answer = "Unable to get answers"
            if user_message:
                answer, chat_history = get_answer_from_question(llm, user_message, chat_id, user_email)
            response = {"reply": answer, "chat_history": chat_history}
            if not chat_id_exists:
                response["chat_id"] = chat_id
            return jsonify(response), 200

@app.route('/chat/voice', methods=['POST'])
def chat_voice():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    audio_file = request.files['file']
    chat_id = request.form.get('chat_id')
    user_email = request.form.get('userEmail')
    chat_id_exists = bool(chat_id)
    if not chat_id:
        chat_id = get_chatid_from_database(user_email)
    answer = "Sorry, I could not get that, please try again"

    try:        
        converted_text = speech_to_text(client=client, audio_file = ('audio.wav', audio_file, 'audio/wav'))
        if converted_text and len(converted_text) > 5:
            answer = get_answer_from_question(llm, converted_text, chat_id, user_email)
        # Use this to test the frontend, to have a sample response without using whisper
        # answer = "Take this sample message to make the UI"
        # converted_text = "hello there"
    except Exception as e:
        print(e)
        return jsonify({'error': str(e)}), 500
    response = {"reply": answer, "voiceToText": converted_text}
    if not chat_id_exists:
        response["chat_id"] = chat_id
    return jsonify(response), 200

@app.route('/chat/fullvoice', methods=['POST'])
def chat_voice_to_voice():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    audio_file = request.files['file']
    user_email = request.form.get('userEmail')
    chat_id = request.form.get('chat_id')
    chat_id_exists = bool(chat_id)
    if not chat_id:
        chat_id = get_chatid_from_database(user_email)
    answer = "Sorry, I could not get that, please try again"
    wav_base64 = ""
    try:
        converted_text = speech_to_text(client=client, audio_file = ('audio.wav', audio_file, 'audio/wav'))
        # The api will only respond if the users says a text that is longer than 5 characters
        if converted_text and len(converted_text) > 5:
            answer, chat_history = get_answer_from_question(llm, converted_text, chat_id, user_email)
            wav_base64 = text_to_speech(speech_synthesizer, file_name, answer)
    except Exception as e:
        print(e)
        return jsonify({'error': str(e)}), 500
    response = {"reply": answer, "voiceToText": converted_text, "wav_base64": wav_base64, "chat_history": chat_history}
    
    if not chat_id_exists:
        response["chat_id"] = chat_id
    return jsonify(response), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8082, debug=True)

