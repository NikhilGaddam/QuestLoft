# Questloft Backend

Questloft is a comprehensive learning platform that combines interactive tools, AI-powered conversational interfaces, and dynamic content management. It aims to create an engaging environment for students, support teachers with better management tools, and help students develop critical STEM skills required for the future workforce.

## Prerequisites

Before you begin, ensure you have met the following requirements:

- **Docker**: Download and install Docker Desktop for your operating system:
  - [Docker for Windows](https://www.docker.com/products/docker-desktop/)
  - [Docker for macOS](https://www.docker.com/products/docker-desktop/)
- **Git**: Ensure Git is installed on your machine.

## Installation

Follow these steps to set up the Questloft backend on your local machine.

### Clone the Repository

First, clone the repository from GitLab:

```bash
git clone https://git.cs.vt.edu/wallfacers/questloft-backend.git
cd questloft/backend
```

### Configure Environment Variables

Before running the application, make sure you have the environment variables defined in a `.env` file:

```
OPENAI_API_KEY="<your_openai_api_key>"
OPENAI_MODEL_NAME="gpt-4o"
PORT=8080
DB_HOST = "<your_db_host>"
DB_PORT = "<your_db_port>"
DB_NAME = "<your_db_name>"
DB_USER = "<your_db_user>"
DB_PASSWORD = "<your_db_password>"
SENDGRID_API_KEY="<your_sendgrid_api_key>"
SPEECH_KEY="<your_speech_key>"
SERVICE_REGION="<your_service_region>"
REDISPORT="<your_redis_port>"
REDIS_URL="<your_redis_url>"
REDISHOST="<your_redis_host>"
REDISUSER="<your_redis_user>"
REDISPASS="<your_redis_password>"
AWS_ACCESS_KEY_ID="<your_aws_access_key_id>"
AWS_SECRET_ACCESS_KEY="<your_aws_secret_access_key>"
AWS_REGION="<your_aws_region>"
AWS_BUCKET_NAME="<your_aws_bucket_name>"
```

### Start the Application

Run the following command to build and start the application:

```bash
docker-compose up --build
```

This command will build the Docker containers, start the PostgreSQL database, and launch the backend server. Once running, you can access the application by navigating to [http://127.0.0.1:5000](http://127.0.0.1:5000) in your web browser.

### Database Initialization

The PostgreSQL database is automatically initialized with the necessary schema during the first run of the Docker containers. If you want to reinitialize the database (e.g., in a development environment), follow these steps:

1. Stop the Docker containers:
   ```bash
   docker-compose down
   ```

2. Remove the PostgreSQL volume to force reinitialization (optional):
   ```bash
   docker volume rm questloft-backend_postgres_data
   ```

3. Restart the Docker containers:
   ```bash
   docker-compose up --build
   ```


### Contributing

To contribute to Questloft, please follow these guidelines:

- Fork the repository.
- Create a new branch:
  ```bash
  git checkout -b feat/<feature-name>
  ```
  or
  ```bash
  git checkout -b fix/<fix-name>
  ```
- Push your changes to the branch:
  ```bash
  git push origin <branch-name>
  ```
- Open a pull request.
