# Module 3: Reporting Microservice

An AI-powered Flask microservice for generating **Tribunal Defect Liability Period (DLP)** compliance and support reports using **Groq LLM**.  
The system operates as an independent backend service that is dynamically queried by the main PCD frontend app.

## 🚀 Features
- AI-generated tribunal-style compliance reports
- Centralized database support (Imports models directly from main application)
- Dynamic Context Injection: Homeowner vs Developer perspectives
- PDF Report generation (Borang 1 format) via ReportLab

## 🛠️ Tech Stack
- Python 3.11
- Flask
- Groq LLM API
- ReportLab
- SQLAlchemy (via app.models injection)
- Docker Compose

## ⚙️ Microservice Architecture
Instead of running as a standalone standalone web app displaying HTML, Module 3 has been converted into a REST API endpoint:
`GET /module3/api/generate_report/<report_type>?user_id=<id>&project_id=<id>`

The **Web Service** acts as a proxy, fetching the PDF blob across the Docker network (`http://module_3_reporting:5003`) and streaming it to the user.

## 🚀 Setup & Run

1. Navigate to the root of the PCD project.
2. Ensure you have your `.env` configured inside the main project directory with:
   ```env
   GROQ_API_KEY=your_secure_api_key_here
   ```
3. Run the Docker Compose stack:
   ```bash
   docker compose up --build
   ```

## 📌 Disclaimer
This project is developed for academic and demonstration purposes only.
AI-generated reports assist in information organisation and do not constitute legal advice.

Author: N. Nabilah & Imran
Automated Compliance Report Generation (Academic Project)
