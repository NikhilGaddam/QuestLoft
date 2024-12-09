from helpers import get_close_vector_text

# add_flagged_message("user@example.com", "Inappropriate content detected.")
# add_flagged_message("user2@example.com", "Suspicious activity flagged.")

# # Retrieving flagged messages for a specific email
# messages = get_flagged_messages("user@example.com")
# print(messages)

# # Retrieving all flagged messages
# all_messages = get_flagged_messages()
# print(all_messages)
# embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
# vector_store = Chroma(persist_directory="vector-store-chroma", embedding_function=embeddings)

# def get_close_vector_text(question):
    
#     results = vector_store.similarity_search(question, k=1)
#     content_source_info = results[0].metadata["source"]
#     content_source = content_source_info[5:]
#     return results[0].page_content, content_source

content, source = get_close_vector_text("computer")

print(source)