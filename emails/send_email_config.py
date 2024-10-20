
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from dotenv import load_dotenv, find_dotenv
import logging

# Load environment variables
load_dotenv(find_dotenv())
logging.basicConfig(level=logging.ERROR)

# Function to send emails using SendGrid templates
def send_email(template_id, to_email, dynamic_data):
    message = Mail(
        from_email='nikhilgaddam@vt.edu',
        to_emails=to_email
    )
    message.template_id = template_id
    message.dynamic_template_data = dynamic_data

    try:
        sg = SendGridAPIClient(os.getenv('SENDGRID_API_KEY'))
        response = sg.send(message)
        # print(response.status_code)
        # print(response.body)
        # print(response.headers)
    except Exception as e:
        logging.error(f"Error sending email: {str(e)}")
