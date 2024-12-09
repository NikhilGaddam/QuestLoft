from helpers import get_answer_from_question, get_close_vector_text
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())


llm = ChatOpenAI(api_key=os.environ.get("OPENAI_API_KEY"),
                 model=os.environ.get("OPENAI_MODEL_NAME"))

ans = get_answer_from_question(llm, "What is the fermi paradox?")
print(ans)