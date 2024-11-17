from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import MessagesPlaceholder
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from dotenv import load_dotenv, find_dotenv
import azure.cognitiveservices.speech as speechsdk
import base64
from datetime import datetime
from config.db_config import get_db_connection

load_dotenv(find_dotenv())
chat_histories = {}

flags = {}

safe_for_kids_prompts = """
Analyze the following message and determine if it is appropriate for children. 
Consider factors such as explicit language, violence, sexual content, or any other harmful or inappropriate material. 
Respond with either 'Safe' or give a description why we should not ask these question, assume the user is a kid and say that I could help with something else
"""

embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

vector_store = FAISS.load_local(
    "faiss_index", embeddings, allow_dangerous_deserialization=True
)

def add_flagged_message(email, message):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Insert the flagged message into the database
            cursor.execute(
                """
                INSERT INTO flags (email, message, timestamp)
                VALUES (%s, %s, %s);
                """,
                (email, message, current_time)
            )
        connection.commit()
    except Exception as e:
        print(f"Error adding flagged message: {e}")
        connection.rollback()
    finally:
        connection.close()
        
def get_flagged_messages(email=None):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Retrieve flagged messages for a specific email or all emails
            if email:
                cursor.execute(
                    """
                    SELECT email, message, timestamp
                    FROM flags
                    WHERE email = %s
                    ORDER BY timestamp DESC;
                    """,
                    (email,)
                )
            else:
                cursor.execute(
                    """
                    SELECT email, message, timestamp
                    FROM flags
                    ORDER BY timestamp DESC;
                    """
                )
            flagged_messages = cursor.fetchall()
        return flagged_messages
    except Exception as e:
        print(f"Error retrieving flagged messages: {e}")
        return []
    finally:
        connection.close()

def get_answer_from_question(llm, question, chat_id, user_email):
    context = get_close_vector_text(question)
    chat_history = chat_histories.setdefault(chat_id, [])
    template = ChatPromptTemplate.from_messages([
        ("system", safe_for_kids_prompts),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{question}")])

    chain = template | llm

    res = chain.invoke({"context": context, "question": question, "chat_history": chat_history})

    if res.content == "Safe":
        return get_answer_from_question_2(llm, question, chat_id)
    
    chat_history.append(HumanMessage(content=question))
    chat_history.append(AIMessage(content=res.content))
    add_flagged_message(user_email, question)
    print(flags)
    return res.content, str(chat_history)

def get_answer_from_question_2(llm, question, chat_id):
    context = get_close_vector_text(question)
    chat_history = chat_histories.setdefault(chat_id, [])
    template = ChatPromptTemplate.from_messages([
        ("system", "You are questy, the AI Chatbot for THINKABIT LABS @ VIRGINIA TECH, If the context is relevant to the question, only use that and do not add extra things. Here is some information for you to answer question {context}"),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{question}")])

    chain = template | llm

    res = chain.invoke({"context": context, "question": question, "chat_history": chat_history})

    chat_history.append(HumanMessage(content=question))
    chat_history.append(AIMessage(content=res.content))
    return res.content, str(chat_history)


def speech_to_text(client, audio_file):
    transcription = client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file
    )
    return transcription.text

def text_to_speech(speech_synthesizer, file_name, text):
    result = speech_synthesizer.speak_text_async(text).get()
    result_audio_data = result.audio_data
    wav_base64 = base64.b64encode(result_audio_data).decode('utf-8')

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        print("Speech synthesized for text [{}], and the audio was saved to [{}]".format(text, file_name))
    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = result.cancellation_details
        print("Speech synthesis canceled: {}".format(cancellation_details.reason))
        if cancellation_details.reason == speechsdk.CancellationReason.Error:
            print("Error details: {}".format(cancellation_details.error_details))
    return wav_base64

def get_close_vector_text(question):
    
    results = vector_store.similarity_search_with_score(
        question, k=1
    )

    if results[0][1] < 1.5:
        return results[0][0].page_content