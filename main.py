import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv, find_dotenv
from openai import OpenAI
import logging
import uuid
import azure.cognitiveservices.speech as speechsdk
import psycopg2
from psycopg2 import sql
from authentication.auth_routes import auth_bp


# # Database connection settings
# DB_HOST = "c-questloft-custer.e4a4to25j6hszu.postgres.cosmos.azure.com"
# DB_PORT = "5432"
# DB_NAME = "questloft"
# DB_USER = "citus" 
# DB_PASSWORD = "Questloft3115" 
# Database connection settings


from helpers import speech_to_text, get_answer_from_question, text_to_speech

logging.basicConfig(level=logging.DEBUG)

load_dotenv(find_dotenv())

app = Flask(__name__)
CORS(app)



CORS(app, resources={r"/chat/*": {
    "origins": "http://localhost:3000",
    "methods": ["GET", "POST", "OPTIONS"],
    "allow_headers": ["Content-Type", "Authorization"]
}
})

app.register_blueprint(auth_bp)

client = OpenAI()
llm = ChatOpenAI(api_key=os.environ.get("OPENAI_API_KEY"),
                 model=os.environ.get("OPENAI_MODEL_NAME"))


# UPLOAD_FOLDER = './uploads'
# # Just for text to speech
# speech_key = os.environ.get("SPEECH_KEY")
# service_region = os.environ.get("SERVICE_REGION")

# speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
# speech_config.speech_synthesis_voice_name = "en-US-AvaMultilingualNeural"

# file_name = f"{UPLOAD_FOLDER}/output.wav"
# file_config = speechsdk.audio.AudioOutputConfig(filename=file_name)
# speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=file_config)

@app.route('/', methods=['GET'])
def get_status():
    return "Server Running", 200


@app.route('/chat/text', methods=['POST'])
def chat_text():
    data = request.get_json()
    user_message = data.get('userMessage')
    chat_id = data.get('chat_id') or str(uuid.uuid4())
    chat_id_exists = bool(data.get('chat_id'))
    
    answer = "Unable to get answers"
    if user_message:
        answer, chat_history = get_answer_from_question(llm, user_message, chat_id)

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
    if not chat_id:
        chat_id = str(uuid.uuid4())
    answer = "Sorry, I could not get that, please try again"

    try:        
        converted_text = speech_to_text(client=client, audio_file = ('audio.wav', audio_file, 'audio/wav'))
        if converted_text and len(converted_text) > 5:
            answer = get_answer_from_question(llm, converted_text, chat_id)
        # Use this to test the frontend, to have a sample response without using whisper
        # answer = "Take this sample message to make the UI"
        # converted_text = "hello there"
    except Exception as e:
        print(e)
        return jsonify({'error': str(e)}), 500

    return jsonify({"reply": answer, "voiceToText": converted_text}), 200

@app.route('/chat/fullvoice', methods=['POST'])
def chat_voice_to_voice():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    audio_file = request.files['file']
    chat_id = request.form.get('chat_id') or str(uuid.uuid4())
    chat_id_exists = bool(request.form.get('chat_id'))
    answer = "Sorry, I could not get that, please try again"
    wav_base64 = ""
    try:
        converted_text = speech_to_text(client=client, audio_file = ('audio.wav', audio_file, 'audio/wav'))
        # The api will only respond if the users says a text that is longer than 5 characters
        if converted_text and len(converted_text) > 5:
            answer, chat_history = get_answer_from_question(llm, converted_text, chat_id)
            wav_base64 = text_to_speech(speech_synthesizer, file_name, answer)
        # wav_base64 = test_test_to_speech_fe(test_file_name)
        # answer = "Take this sample message to make the UI"
        # converted_text = "hello there"
    except Exception as e:
        print(e)
        return jsonify({'error': str(e)}), 500
    response = {"reply": answer, "voiceToText": converted_text, "wav_base64": wav_base64, "chat_history": chat_history}
    
    if not chat_id_exists:
        response["chat_id"] = chat_id
    return jsonify(response), 200



if __name__ == '__main__':
    PORT = int(os.getenv("PORT", 6000))
    app.run(host='0.0.0.0', port=PORT, debug=True)

