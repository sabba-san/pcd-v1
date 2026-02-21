# Microservices Architecture Testing Guide

This guide provides step-by-step instructions on how to deploy and test the Microservices architecture for this project.

## Prerequisites
- **Docker Desktop**: Ensure Docker Desktop is installed and running on your system.

## Step 1: Setup
1. In the root directory of the project, you will find a file named `.env.example`.
2. Rename `.env.example` to `.env`.
3. Open `.env` and insert your actual Groq API key:
   ```env
   GROQ_API_KEY=your_actual_api_key_here
   ```
   *(Note: The `.env` file is safely excluded from version control via `.gitignore` to keep your credentials secure).*

## Step 2: Build & Run
Open your terminal in the root directory and start the services using Docker Compose:
```bash
docker compose up -d --build
```
This command will build the necessary images and start all the microservices in the background.

## Step 3: Database Initialization
Once the containers are running, initialize the database by executing the following command:
```bash
docker compose exec web_service python setup_db.py
```

## Step 4: Access
Open your web browser and navigate to the application:
[http://localhost:5000](http://localhost:5000)

## Step 5: Test Credentials
You can use the following test accounts to log in and test different roles in the system.

**Homeowner:**
- **Email:** `abbas@student.uum.edu.my`
- **Password:** `password123`
*(Alternative Homeowner: `salman@dummy.com` / `salman123`)*

**Developer:**
- **Email:** `developer@ecoworld.com`
- **Password:** `dev123`

**Lawyer:**
- **Email:** `lawyer@firm.com`
- **Password:** `law123`

**Admin:**
- **Email:** `admin@uum.edu.my`
- **Password:** `admin123`

## Step 6: Testing Flow
We recommend the following user journey to thoroughly test the application's capabilities:

1. **Log in as Homeowner** (`abbas@student.uum.edu.my`).
2. **Add Defect with 3D/Image**: Navigate to your project and add a new defect, utilizing the 3D visualization or image upload feature.
3. **Use Legal AI Chatbot**: Interact with the legal AI chatbot to get smart responses regarding your defect or general inquiries.
4. **Download Form 1 PDF**: Generate and download the Tribunal Form 1 PDF from the reporting microservice.
5. **Log out**.
6. **Log in as Developer** (`developer@ecoworld.com`).
7. **View Defect**: Check the dashboard for the defect submitted by the homeowner.
8. **Download Compliance PDF**: Generate and download the DLP Compliance PDF.
