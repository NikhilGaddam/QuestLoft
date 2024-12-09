from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import MessagesPlaceholder
from langchain_core.output_parsers import JsonOutputParser
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from dotenv import load_dotenv, find_dotenv
import azure.cognitiveservices.speech as speechsdk
import base64
from datetime import datetime
from config.db_config import get_db_connection
from pydantic import BaseModel, Field
from flask import current_app

load_dotenv(find_dotenv())
chat_histories = {}

class JsonInformation(BaseModel):
    is_unsafe_for_k_12_children: bool = Field(description="Is the message unsafe for K-12 children?")
    response: str = Field(description="Response to the message")
json_parser = JsonOutputParser(pydantic_object=JsonInformation)

embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

vector_store = FAISS.load_local(
    "faiss_index", embeddings, allow_dangerous_deserialization=True
)

def add_flagged_message(auth0_user_id, message):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO flags (auth0_user_id, message, timestamp)
                VALUES (%s, %s, %s);
                """,
                (auth0_user_id, message, current_time)
            )
        connection.commit()
        current_app.logger.debug(f"Flagged message added for auth0_user_id: {auth0_user_id}")
    except Exception as e:
        current_app.logger.debug(f"Error adding flagged message: {e}")
        connection.rollback()
    finally:
        connection.close()

def get_answer_from_question(llm, question, chat_id, auth0_user_id):
    context = get_close_vector_text(question)
    chat_history = chat_histories.setdefault(chat_id, [])
    prompt = """
    You are questy, the AI Chatbot for Thinkabit Labs @ Virginia Tech.

    - Always respond in JSON format.
    - If the message is not safe for K-12 students, analyze the following message and determine if it is appropriate for children. Consider factors such as explicit language, violence, sexual content, or any other harmful or inappropriate material. Respond with a description of why we should not ask these questions, assuming the user is a kid, and say that you could help with something else.
    - If you need clarification, respond in JSON format asking for the specific details required.

    Respond in JSON format with the following keys `is_unsafe_for_k_12_children` and `response`.
    Message to Analyze: "{context}"
    """
    template = ChatPromptTemplate.from_messages([
        ("system", prompt),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{question}")
    ])

    chain = template | llm

    try:
        res = chain.invoke({
            "context": context,
            "question": question,
            "chat_history": chat_history
        })
        parsed_response = json_parser.parse(res.content)
        current_app.logger.debug(f"Parsed response: {parsed_response}")
        if parsed_response['is_unsafe_for_k_12_children']:
            add_flagged_message(auth0_user_id, question)
            return parsed_response['response'], str(chat_history)

        chat_history.append(HumanMessage(content=question))
        chat_history.append(AIMessage(content=parsed_response['response']))
        return parsed_response['response'], str(chat_history)
    except Exception as e:
        current_app.logger.debug(f"Error in get_answer_from_question: {e}")
        return "Error processing the question.", str(chat_history)

def speech_to_text(client, audio_file):
    try:
        transcription = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file
        )
        current_app.logger.debug("Transcription completed successfully.")
        return transcription.text
    except Exception as e:
        current_app.logger.debug(f"Error during speech-to-text: {e}")
        return "Error during speech-to-text."

def text_to_speech(speech_synthesizer, file_name, text):
    try:
        result = speech_synthesizer.speak_text_async(text).get()
        result_audio_data = result.audio_data
        wav_base64 = base64.b64encode(result_audio_data).decode('utf-8')

        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            current_app.logger.debug(f"Speech synthesized for text: {text}")
        elif result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = result.cancellation_details
            current_app.logger.debug(f"Speech synthesis canceled: {cancellation_details.reason}")
            if cancellation_details.reason == speechsdk.CancellationReason.Error:
                current_app.logger.debug(f"Error details: {cancellation_details.error_details}")
        return wav_base64
    except Exception as e:
        current_app.logger.debug(f"Error during text-to-speech: {e}")
        return None

def get_close_vector_text(question):
    try:
        results = vector_store.similarity_search_with_score(question, k=1)
        current_app.logger.debug(f"Vector similarity results: {results}")
        if results[0][1] < 1.5:
            return results[0][0].page_content
    except Exception as e:
        current_app.logger.debug(f"Error retrieving close vector text: {e}")
        return ""
