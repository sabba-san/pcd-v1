# Automated Compliance Report Generation

An AI-powered Flask web application for generating **Tribunal Defect Liability Period (DLP)** compliance and support reports using **Groq LLM**.  
The system supports role-based access for **Homeowner, Developer, and Legal/Tribunal** users.


## 🚀 Features
- AI-generated tribunal-style compliance reports
- Role-based dashboards: Homeowner, Developer, Legal/Tribunal
- Bahasa Malaysia & English support
- PDF report generation (Borang 1 format)
- Secure backend with defect status tracking

## 🛠️ Tech Stack
- Python
- Flask
- Groq API
- ReportLab


## ⚙️ Setup & Run


### 1. Navigate to project folder
```bash
cd C:\Users\user\Automated-Compliance-Report-Generation\app\module3
```

---

### 2. Install dependencies

```bash
pip install groq
```

```bash
pip install flask reportlab groq
```

---

### 3. Set up Groq API key

1.	Create an API key at:

```text
https://console.groq.com/keys
```

2.	Add the key in `groqai_client.py`:

```phyton
# app/module3/groqai_client.py
# Groq AI API key (replace with your own api)
GROQ_API_KEY = "replace _here"
```

**⚠️ Do not expose real API keys in public repositories.**

---

### 4. Run application

```bash
python app.py
```

Open in a browser:
```text
http://127.0.0.1:5000
```

---

## 🌐 Role Access

Homeowner:
 http://127.0.0.1:5000/?role=Homeowner

Developer:
http://127.0.0.1:5000/?role=Developer

Legal / Tribunal:
http://127.0.0.1:5000/?role=Legal


## 📌 Disclaimer

This project is developed for academic and demonstration purposes only.
AI-generated reports assist in information organisation and do not constitute legal advice.


Author: N. Nabilah

Automated Compliance Report Generation (Academic Project)
