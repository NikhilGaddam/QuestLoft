import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv, find_dotenv
from openai import OpenAI
import logging
import uuid
import psycopg2
from psycopg2 import sql

# Database connection settings
DB_HOST = "c-questloft-custer.e4a4to25j6hszu.postgres.cosmos.azure.com"
DB_PORT = "5432"
DB_NAME = "questloft"
DB_USER = "citus"  # Change this to your PostgreSQL username
DB_PASSWORD = "Questloft3115"  # Change this to your PostgreSQL password

# Create connection to PostgreSQL
def get_db_connection():
    connection = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    return connection

from helpers import speech_to_text, get_answer_from_question

logging.basicConfig(level=logging.DEBUG)

load_dotenv(find_dotenv())

app = Flask(__name__)

CORS(app, resources={r"/chat/*": {
    "origins": "http://localhost:3000",
    "methods": ["GET", "POST", "OPTIONS"],
    "allow_headers": ["Content-Type", "Authorization"]
}})

CORS(app, resources={r"/documents/*": {
    "origins": "*",
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

@app.route('/documents', methods=['GET'])
def list_all_documents():
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        query = "SELECT id, file_name, document_type, user_id, enabled, upload_time FROM documents"
        cursor.execute(query)
        documents = cursor.fetchall()
        
        response = [{"id": doc[0], "file_name": doc[1], "document_type": doc[2], "user_id": doc[3], "enabled": doc[4], "upload_time": doc[5]} for doc in documents]
        
        cursor.close()
        connection.close()

        return jsonify(response), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/documents/<int:document_id>', methods=['GET'])
def fetch_document(document_id):
    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        # Query to fetch document details based on the document ID
        query = "SELECT file_name, file_data FROM documents WHERE id = %s"
        cursor.execute(query, (document_id,))
        document = cursor.fetchone()

        if document:
            file_name, file_data = document

            # Set up the response with the appropriate headers for file download
            response = app.response_class(
                file_data,
                mimetype='application/pdf',  # Use the correct MIME type for PDF
                direct_passthrough=True
            )
            response.headers.set('Content-Disposition', f'inline; filename={file_name}')
            
            cursor.close()
            connection.close()

            return response
        else:
            cursor.close()
            connection.close()
            return jsonify({'error': 'Document not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/documents/upload', methods=['POST'])
def insert_a_document():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    file_name =  request.form.get('file_name')
    document_type = request.form.get('document_type')
    user_id = request.form.get('user_id')

    if not document_type or not user_id:
        return jsonify({'error': 'Missing document_type or user_id'}), 400
    
    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        query = """
            INSERT INTO documents (file_name, file_data, document_type, user_id) 
            VALUES (%s, %s, %s, %s) RETURNING id
        """
        file_data = file.read()
        cursor.execute(query, (file_name, file_data, document_type, user_id))
        
        document_id = cursor.fetchone()[0]
        connection.commit()
        
        cursor.close()
        connection.close()

        return jsonify({'message': 'Document uploaded successfully', 'document_id': document_id}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)

