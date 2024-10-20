# Questloft Backend

Questloft is a comprehensive learning platform that combines interactive tools, AI-powered conversational interfaces, and dynamic content management. It aims to create an engaging environment for students, support teachers with better management tools, and help students develop critical STEM skills required for the future workforce.

## Prerequisites

Before you begin, ensure you have met the following requirements:

- **Python 3.x**: Ensure Python 3.x is installed on your machine.
- **pip**: Make sure pip (Python package manager) is also installed.

## Installation

Follow these steps to set up the Questloft backend on your local machine.

### Clone the Repository

First, clone the repository from GitLab:

```bash
git clone git@gitlab.com:wallfacers1/questloft.git
cd questloft/backend
```

### Create a Virtual Environment
It is recommended to use a virtual environment to manage dependencies. Run the following command to create one:
bash
```bash
python -m venv venv
```
### Activate the Virtual Environment
Activate the virtual environment using the command appropriate for your operating system.

On Windows:
```bash
venv\Scripts\activate
```

On macOS/Linux:
```bash
source venv/bin/activate
```

### Install Required Packages
Install the necessary packages using pip:
```bash
pip install -r requirements.txt
```


### Run the application
Before running the application, make sure you have the environment variables defined in .env file
```
OPENAI_API_KEY=""

OPENAI_MODEL_NAME=""

SPEECH_KEY=""

SERVICE_REGION=""

PORT=""

DB_HOST = ""
DB_PORT = ""
DB_NAME = ""
DB_USER = "" 
DB_PASSWORD = "" 

```


To run the application, execute the following command:

```bash
python main.py
```


After starting the server, you can access the application by navigating to http://127.0.0.1:5000 in your web browser.


### Contributing

To contribute to Questloft, please follow these guidelines:

- Fork the repository.
- Create a new branch: `git checkout -b feat/<feature-name>` or `fix/<fix-name>`.
- Push to the branch.
- Open a pull request.



-------
PSQL schema
CREATE TABLE users (
  id SERIAL PRIMARY KEY,
  auth0_user_id VARCHAR(255),
  user_role VARCHAR(50),
  is_approved BOOLEAN DEFAULT FALSE
);




