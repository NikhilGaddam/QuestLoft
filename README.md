Prerequisites
Before you begin, ensure you have met the following requirements:

Python 3.x installed on your machine.
pip (Python package manager) is also installed.
Installation
Clone the repository:

git clone git@gitlab.com:wallfacers1/questloft.git
cd backend
Create a virtual environment:

It is recommended to use a virtual environment to manage dependencies.

python -m venv venv
Activate the virtual environment:

On Windows:

venv\Scripts\activate
On macOS/Linux:

source venv/bin/activate
Install the required packages:

pip install -r requirements.txt
Usage
To run the application, execute the following command:

python main.py
After starting the server, you can access the application by navigating to http://127.0.0.1:5000 in your web browser.



-------
PSQL schema
CREATE TABLE users (
  id SERIAL PRIMARY KEY,
  auth0_user_id VARCHAR(255),
  user_role VARCHAR(50),
  is_approved BOOLEAN DEFAULT FALSE
);




