from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import MessagesPlaceholder
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from dotenv import load_dotenv, find_dotenv
import azure.cognitiveservices.speech as speechsdk
import base64

load_dotenv(find_dotenv())
chat_histories = {}

embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

vector_store = FAISS.load_local(
    "faiss_index", embeddings, allow_dangerous_deserialization=True
)


def get_answer_from_question(llm, question, chat_id):
    context = get_close_vector_text(question)
    chat_history = chat_histories.setdefault(chat_id, [])
    template = ChatPromptTemplate.from_messages([
        ("system", "If the context is relevant to the question, only use that and do not add extra things. Here is some information for you to answer question {context}"),
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