-- Drop existing tables
DROP TABLE IF EXISTS TestScores;
DROP TABLE IF EXISTS Parents;
DROP TABLE IF EXISTS Students;
DROP TABLE IF EXISTS Users;

CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    title VARCHAR(100),
    filename VARCHAR(100),
    s3_key VARCHAR(200) UNIQUE,
    size INTEGER,
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tags TEXT[],
    content_type VARCHAR(100),
    description TEXT
);

CREATE TABLE IF NOT EXISTS Users (
  UserID SERIAL PRIMARY KEY,
  auth0_user_id VARCHAR(255),
  first_name VARCHAR(100),
  last_name VARCHAR(100),
  user_role VARCHAR(50) CHECK (user_role IN ('Student', 'Teacher', 'Parent', 'Admin')),
  is_approved BOOLEAN DEFAULT FALSE,
  user_created_time TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  approved_time TIMESTAMP WITHOUT TIME ZONE
);

CREATE TABLE IF NOT EXISTS flags (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS Students (
  StudentID SERIAL PRIMARY KEY,
  UserID INT,
  Grade VARCHAR(10),
  FOREIGN KEY (UserID) REFERENCES Users(UserID) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Parents (
  ParentID SERIAL PRIMARY KEY,
  UserID INT,
  StudentUserID INT,
  FOREIGN KEY (UserID) REFERENCES Users(UserID) ON DELETE CASCADE,
  FOREIGN KEY (StudentUserID) REFERENCES Students(StudentID) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS TestScores (
  TestID SERIAL PRIMARY KEY,
  UserID INT,
  Score INT,
  TotalQuestions INT,
  CorrectAnswers INT,
  IncorrectAnswers INT,
  AreasWellDone TEXT,
  AreasToImprove TEXT,
  TestDate TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (UserID) REFERENCES Users(UserID) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS QuizSessions (
    SessionID SERIAL PRIMARY KEY,
    UserID INT,
    QuizID UUID,
    CurrentQuestionIndex INT,
    Answers JSONB,
    StartTime TIMESTAMP WITHOUT TIME ZONE,
    Grade VARCHAR(10),
    FOREIGN KEY (UserID) REFERENCES Users(UserID) ON DELETE CASCADE
);


INSERT INTO Users (
  UserID, 
  auth0_user_id, 
  first_name, 
  last_name, 
  user_role, 
  is_approved, 
  user_created_time, 
  approved_time
) VALUES (
  12345, 
  'auth0|sample_user_12345', 
  'John', 
  'Doe', 
  'Student', 
  TRUE, 
  CURRENT_TIMESTAMP, 
  CURRENT_TIMESTAMP
);

INSERT INTO Students (
  UserID, 
  Grade
) VALUES (
  12345, 
  '5'
);




