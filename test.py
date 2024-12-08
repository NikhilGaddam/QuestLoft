from helpers import add_flagged_message, get_flagged_messages, get_all_user_history

add_flagged_message("user@example.com", "Inappropriate content detected.")
add_flagged_message("user2@example.com", "Suspicious activity flagged.")

# Retrieving flagged messages for a specific email
messages = get_flagged_messages("user@example.com")
print(messages)

# Retrieving all flagged messages
all_messages = get_flagged_messages()
print(all_messages)