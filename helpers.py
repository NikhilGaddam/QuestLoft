from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import MessagesPlaceholder
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

chat_histories = {}

embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

vector_store = FAISS.load_local(
    "faiss_index", embeddings, allow_dangerous_deserialization=True
)


def get_answer_from_question(llm, question, chat_id):
    context = get_close_vector_text(question)
    chat_history = chat_histories.setdefault(chat_id, [])
    template = ChatPromptTemplate.from_messages([
        ("system", "You are limited to 2 sentences. If the context is relevant to the question, only use that and do not add extra things. Here is some information for you to answer question {context}"),
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


def get_close_vector_text(question):
    
    results = vector_store.similarity_search_with_score(
        question, k=1
    )

    if results[0][1] < 1.5:
        return results[0][0].page_content