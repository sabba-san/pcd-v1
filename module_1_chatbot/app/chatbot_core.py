from groq import Groq
from .dlp_knowledge_base import get_dlp_info, DLP_RULES

# =====================================================
# 1. CONFIGURATION (GROQ SETUP)
# =====================================================

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# =====================================================
# 1. CONFIGURATION (GROQ SETUP)
# =====================================================

# ⚠️ IMPORTANT: The API Key is now loaded from the .env file
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

try:
    if not GROQ_API_KEY:
        print("Error: GROQ_API_KEY not found in environment variables.")
        client = None
    else:
        client = Groq(api_key=GROQ_API_KEY)
except Exception as e:
    print(f"Groq Client Error: {e}")
    client = None

# Using the new supported model
MODEL_NAME = "llama-3.3-70b-versatile"

# =====================================================
# 2. SYSTEM PROMPTS
# =====================================================

# Strict prompt to ensure it only answers property law questions
SYSTEM_INSTRUCTION = """
You are a specialized legal assistant for Malaysian Property Law.

1.  **Role:** You are an AI expert in Malaysian housing acts, strata management, and defect liability.
2.  **Context:** You will be provided with some "Retrieved Context" from our local database.
    - **PRIORITIZE** this context if it is relevant.
    - If the context is empty or irrelevant, **USE YOUR GENERAL KNOWLEDGE** of Malaysian law to answer helpfuly.
3.  **Scope:**
    - **Allowed:** HDA, Strata Title, Defect Liability, Tenancy, SPA, Homeownership.
    - **Not Allowed:** Criminal law, family law, international law, or non-legal topics.
4.  **Tone:** Professional, helpful, and concise.
5.  **Disclaimer:** ALWAYS end with: "This is not legal advice. Please consult a qualified Malaysian lawyer for your specific situation."

If the user asks about something off-topic, politely refuse.
"""

def process_query(user_query, context=None):
    if not client:
        print("DEBUG: Client not initialized")
        return "Error: AI Client not initialized. Check API Key."

    print(f"DEBUG: Processing query: {user_query}")
    lower_query = user_query.lower()
    retrieved_context = []
    
    # Simple Keyword Search (RAG)
    for key in DLP_RULES.keys():
        if key in lower_query:
            info = get_dlp_info(key)
            retrieved_context.append(f"--- Info regarding '{key}' ---\n{info}")

    if retrieved_context:
        full_context_text = "\n\n".join(retrieved_context)
    else:
        full_context_text = "No specific documents found in internal database. Please rely on your general knowledge."

    # Format Context String
    context_str = ""
    if context:
        project = context.get('project_name', 'Unknown')
        count = context.get('defect_count', '0')
        context_str = f"USER CONTEXT: The user has {count} defect(s) pending at project '{project}'."

    try:
        # Construct the final prompt
        user_prompt = f"""
        {context_str}

        Retrieved Context:
        {full_context_text}

        User Question:
        {user_query}
        """
        
        print(f"DEBUG: Using new context: {context}")
        
        # Send to Groq
        print("DEBUG: Sending to Groq...")
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_INSTRUCTION},
                {"role": "user", "content": user_prompt}
            ],
            model=MODEL_NAME,
            temperature=0.3, # Low temperature = strict and factual
        )
        print("DEBUG: Groq returned response")
        return chat_completion.choices[0].message.content
        
    except Exception as e:
        print(f"DEBUG: AI Error: {e}")
        return f"AI Error: {str(e)}"

def analyze_legal_text(document_text):
    if not client:
        return "Error: AI Client not initialized."

    # Detailed prompt for document analysis
    ANALYSIS_PROMPT = f"""
    You are a Malaysian Property Law Analyst.
    
    TASK: Analyze the following legal text snippet.
    
    DOCUMENT TEXT:
    "{document_text}"
    
    INSTRUCTIONS:
    1. First, determine if this is related to Malaysian Property (SPA, Loan, Title, Tenancy).
    2. If NOT related, strictly say: "I can only analyze Malaysian property documents."
    3. If related, summarize the key point in 1 sentence.
    4. Highlight any potential risks or "gotchas" (e.g., late interest, strict deadlines).
    5. Explain any legal jargon in simple English.
    6. END WITH: "This is a general explanation. Please have a lawyer review your actual document."
    """
    
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a helpful legal analyst."},
                {"role": "user", "content": ANALYSIS_PROMPT}
            ],
            model=MODEL_NAME,
            temperature=0.3,
        )
        return chat_completion.choices[0].message.content
        
    except Exception as e:
        return f"Analysis Error: {str(e)}"