import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv, find_dotenv
from openai import OpenAI
import logging
import uuid

from helpers import speech_to_text, get_answer_from_question

logging.basicConfig(level=logging.DEBUG)

load_dotenv(find_dotenv())

app = Flask(__name__)

CORS(app, resources={r"/chat/*": {
    "origins": "http://localhost:3000",
    "methods": ["GET", "POST", "OPTIONS"],
    "allow_headers": ["Content-Type", "Authorization"]
}})

client = OpenAI()
llm = ChatOpenAI(api_key=os.environ.get("OPENAI_API_KEY"),
                 model=os.environ.get("OPENAI_MODEL_NAME"))


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


if __name__ == '__main__':
    app.run(debug=True)
