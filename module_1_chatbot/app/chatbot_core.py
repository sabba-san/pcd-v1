from groq import Groq
from .dlp_knowledge_base import load_pdf_knowledge

# ⚠️ Paste your actual Groq API key here
GROQ_API_KEY = "YOUR_GROQ_API_KEY_HERE"

try:
    client = Groq(api_key=GROQ_API_KEY)
except Exception as e:
    print(f"Groq Initialization Error: {e}")
    client = None

# Load the PDF text when the app starts
PDF_CONTEXT = load_pdf_knowledge()

def process_query(user_query):
    if not client:
        return "Error: AI Client not initialized. Check your API key."

    # Groq's Llama model can read huge amounts of text. 
    # We pass the first 50,000 characters to keep it fast and safe.
    safe_context = PDF_CONTEXT[:50000] if PDF_CONTEXT else "No documents available."

    prompt = f"""You are a specialized legal assistant for Malaysian Property Law.
    Read the following official legal documents carefully.
    
    1. Answer the user's question using ONLY the provided Document Text.
    2. If the Document Text does not contain the answer, strictly reply: "I don't have sufficient information from the uploaded legal documents to answer this."
    3. End every response with: "This is not legal advice. Please consult a qualified lawyer."

    Document Text:
    {safe_context}
    
    User Question: {user_query}
    """

    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.1
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"AI Error: {str(e)}"

def analyze_legal_text(document_text):
    if not client: return "Error: AI Client not initialized."
    try:
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": f"Analyze this legal text briefly:\n\n{document_text}"}],
            model="llama-3.3-70b-versatile",
            temperature=0.1
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Analysis Error: {str(e)}"