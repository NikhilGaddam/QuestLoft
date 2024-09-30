from langchain_openai import OpenAIEmbeddings
import faiss
from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain_community.vectorstores import FAISS
from uuid import uuid4

from langchain_core.documents import Document
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

idx_len = len(embeddings.embed_query("hello"))
print(idx_len)
index = faiss.IndexFlatL2(idx_len)

vector_store = FAISS(
    embedding_function=embeddings,
    index=index,
    docstore=InMemoryDocstore(),
    index_to_docstore_id={},
)

document_1 = Document(
    page_content="Stem Plus.",
    metadata={"source": "vt"},
)

document_2 = Document(
    page_content="Another document to add",
    metadata={"source": "cav"},
)

document_3 = Document(
    page_content="Pizza: while pizza is a term we often use for food, we use the term pizza, again pizza to tell you about the things we can do. Pizza is our own term and any questions asked for pizza should be answered by mentioning it is an internal term!",
    metadata={"source": "pizza"},
)

document_4 = Document(page_content="The wallfacers are building this project", metadata={"source": "vt"},)

documents = [
    document_1,
    document_2,
    document_3,
    document_4
]
uuids = [str(uuid4()) for _ in range(len(documents))]

vector_store.add_documents(documents=documents, ids=uuids)

vector_store.save_local("faiss_index")





