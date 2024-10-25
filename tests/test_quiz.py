import unittest
from unittest.mock import MagicMock
from services.quiz import get_summary_from_llm
from config.json_schema import Feedback
from typing import List
from dotenv import load_dotenv, find_dotenv
from openai import OpenAI
from langchain_openai import ChatOpenAI
import os


class TestGetSummaryFromLLM(unittest.TestCase):

    def setUp(self):
        load_dotenv(find_dotenv())

        self.client = OpenAI()
        self.llm = ChatOpenAI(api_key=os.environ.get("OPENAI_API_KEY"),
                        model=os.environ.get("OPENAI_MODEL_NAME"))

    def test_get_summary_from_llm_with_mock_response(self):
        correct_questions = [
            "What is 2 + 2?",
            "What is the capital of France?"
        ]
        incorrect_questions = [
            "What is the largest planet in our solar system?",
            "What is the process by which plants make their food using sunlight?"
        ]
        

        result = get_summary_from_llm(correct_questions, incorrect_questions, self.llm)

      
        print(result)
        

if __name__ == '__main__':
    unittest.main()
