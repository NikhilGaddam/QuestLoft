from langchain_core.messages import HumanMessage, AIMessage
from config.db_config import get_db_connection
import json

def serialize_chat_history(chat_history):
    return [
        {
            "type": type(message).__name__,
            "content": message.content
        }
        for message in chat_history
    ]


def deserialize_chat_history(serialized_history):
    message_classes = {
        "HumanMessage": HumanMessage,
        "AIMessage": AIMessage,
    }
    chat_history_r = [
        message_classes[message["type"]](content=message["content"])
        for message in serialized_history
    ]
    return chat_history_r

# The chat history row in database is created when we get the chat id
def update_user_history(chat_id, chat_history):
    serialized_history = serialize_chat_history(chat_history)
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            update_query = """
                    UPDATE chathistories
                    SET chathistory = %s, last_message_time = NOW()
                    WHERE chatid = %s;
                    """
            cursor.execute(update_query, (json.dumps(serialized_history), chat_id))
        connection.commit()
    except Exception as e:
        print(f"Error adding chat history: {e}")
        connection.rollback()
    finally:
        connection.close()

def get_chatid_from_database(user_email):
    connection = get_db_connection()
    chatid = ""
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO ChatHistories (Username, ChatHistory)
                VALUES (%s, %s)
                RETURNING chatid;
                """,
                (user_email, json.dumps([]))
            )
            chatid = cursor.fetchone()[0]
        connection.commit()
    except Exception as e:
        print(f"Error adding chat history: {e}")
        connection.rollback()
    finally:
        connection.close()
        return chatid


def retrive_chat_history_db(chat_id):
    connection = get_db_connection()
    des_history = []
    try:
        with connection.cursor() as cursor:
            query = "SELECT chathistory FROM chathistories WHERE chatid = %s;"
            cursor.execute(query, (chat_id,))
            result = cursor.fetchone()
            if result:
                des_history = deserialize_chat_history(result[0])
        connection.commit()
    except Exception as e:
        print(f"Error retrieving chat history: {e}")
        connection.rollback()
    finally:
        connection.close()
        return des_history
    

def get_all_user_history(username):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT chathistory, chatid FROM chathistories WHERE Username = %s ORDER BY last_message_time DESC LIMIT 10;", (username,))
            history = cursor.fetchall()
        return history
    except Exception as e:
        print(f"Error retrieving chathistory messages: {e}")
        return []
    finally:
        connection.close()

def get_history_of_chat_id(chat_id):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT chathistory FROM chathistories WHERE chatid = %s", (chat_id, ))
            history = cursor.fetchone()
        return history
    except Exception as e:
        print(f"Error retrieving chathistory for the given Chat ID: {e}")
        return []
    finally:
        connection.close()