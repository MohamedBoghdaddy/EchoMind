from pymongo import MongoClient
from datetime import datetime, timezone
from dotenv import load_dotenv
import os
import tkinter as tk
from tkinter import scrolledtext
import re
import requests

# Suppress warnings and load environment variables
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
load_dotenv()

# Connect to MongoDB
try:
    mongo_uri = os.getenv("MONGODB_URI")
    client = MongoClient(mongo_uri)
    client.server_info()  # Test connection
    print("Connected to MongoDB successfully!")
except Exception as e:
    print("Failed to connect to MongoDB:", e)
    client = None

# Define database and collection if MongoDB connection is successful
if client:
    db = client["chatbot_database"]
    history_collection = db["conversation_history"]

# API Functions
def get_cheapest_gpt4_response(message):
    url = "https://cheapest-gpt-4-turbo-gpt-4-vision-chatgpt-openai-ai-api.p.rapidapi.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "x-rapidapi-key": os.getenv("RAPIDAPI_KEY"),
        "x-rapidapi-host": "cheapest-gpt-4-turbo-gpt-4-vision-chatgpt-openai-ai-api.p.rapidapi.com",
    }
    data = {
        "messages": [{"role": "user", "content": message}],
        "model": "gpt-4o",
        "max_tokens": 100,
        "temperature": 0.9,
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json().get("choices", [{}])[0].get("message", {}).get("content", "No response.")
    except requests.exceptions.HTTPError as e:
        return f"HTTP Error: {e.response.status_code} - {e.response.text}"
    except Exception as e:
        return f"Unexpected error: {e}"

def get_numbers_fact(month, day):
    url = f"https://numbersapi.p.rapidapi.com/{month}/{day}/date"
    headers = {
        "x-rapidapi-key": os.getenv("RAPIDAPI_KEY"),
        "x-rapidapi-host": "numbersapi.p.rapidapi.com",
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.text
    except Exception as e:
        return f"Error fetching number fact: {e}"

def get_math_equation(difficulty="veryhard"):
    url = f"https://math-equations-api.p.rapidapi.com/{difficulty}"
    headers = {
        "x-rapidapi-key": os.getenv("RAPIDAPI_KEY"),
        "x-rapidapi-host": "math-equations-api.p.rapidapi.com",
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.text
    except Exception as e:
        return f"Error fetching math equation: {e}"

def get_proposal_rewrite(text, linkedin=""):
    url = "https://personalized-proposals-ai-rewriting-tool.p.rapidapi.com/"
    headers = {
        "Content-Type": "application/json",
        "x-rapidapi-key": os.getenv("RAPIDAPI_KEY"),
        "x-rapidapi-host": "personalized-proposals-ai-rewriting-tool.p.rapidapi.com",
    }
    data = {
        "text": text,
        "linkedin": linkedin,
        "language": "En",
        "postback_url": "",
        "id": "unique-id-123",
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json().get("rewritten", "No rewritten proposal available.")
    except Exception as e:
        return f"Error rewriting proposal: {e}"

def get_personality_analysis(text):
    url = "https://nlp-nlu.p.rapidapi.com/superstring/"
    headers = {
        "x-rapidapi-key": os.getenv("RAPIDAPI_KEY"),
        "x-rapidapi-host": "nlp-nlu.p.rapidapi.com",
    }
    data = {"q": text, "m": "tokencount,composition"}
    try:
        response = requests.post(url, headers=headers, files=data)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return f"Error analyzing personality: {e}"

def teach_jeannie(data):
    url = "https://jeannie.p.rapidapi.com/teach"
    headers = {
        "Content-Type": "application/json",
        "x-rapidapi-key": os.getenv("RAPIDAPI_KEY"),
        "x-rapidapi-host": "jeannie.p.rapidapi.com",
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return f"Error interacting with Jeannie: {e}"

# Save conversation history to MongoDB
def save_history(user_id, user_input, bot_response):
    if client:
        conversation_entry = {
            "user_id": user_id,
            "user_input": user_input,
            "bot_response": bot_response,
            "timestamp": datetime.now(timezone.utc),
        }
        history_collection.insert_one(conversation_entry)

# Retrieve the last 5 messages to maintain context
def load_history(user_id, limit=5):
    if not client:
        return ""
    user_history = history_collection.find({"user_id": user_id}).sort("timestamp", -1).limit(limit)
    history = ""
    for entry in reversed(list(user_history)):
        history += f"User: {entry['user_input']}\nBot: {entry['bot_response']}\n"
    return history

# Chat function to handle various inputs
def chat(user_input, user_id):
    # Help Command
    if "help" in user_input.lower():
        return (
            "I can do the following:\n"
            "- Perform simple math calculations (e.g., '2*10+7').\n"
            "- Fetch interesting number facts (e.g., 'number fact: 6 21').\n"
            "- Solve challenging math equations (e.g., 'math equation').\n"
            "- Rewrite proposals (e.g., 'rewrite proposal: your text').\n"
            "- Analyze personality (e.g., 'analyze personality: your text').\n"
            "- Use GPT-4 for advanced queries (e.g., 'gpt4: your question').\n"
            "- Teach commands via Jeannie API (e.g., 'jeannie: your command')."
        )

    # Math Calculation
    if re.match(r"^\d+[\+\-\*\/]\d+", user_input):
        return calculate_math(user_input)

    # Number Fact
    if user_input.lower().startswith("number fact"):
        try:
            parts = user_input.split(":")[1].strip().split()
            month, day = parts[0], parts[1]
            return get_numbers_fact(month, day)
        except Exception:
            return "Please provide a valid month and day (e.g., 'number fact: 6 21')."

    # Math Equation
    if "math equation" in user_input.lower():
        return get_math_equation()

    # Rewrite Proposal
    if "rewrite proposal" in user_input.lower():
        text = user_input.split(":")[1].strip()
        return get_proposal_rewrite(text)

    # Personality Analysis
    if "analyze personality" in user_input.lower():
        text = user_input.split(":")[1].strip()
        return get_personality_analysis(text)

    # GPT-4 Query
    if user_input.lower().startswith("gpt4"):
        query = user_input.split(":")[1].strip()
        return get_cheapest_gpt4_response(query)

    # Jeannie
    if user_input.lower().startswith("jeannie"):
        command = user_input.split(":")[1].strip()
        return teach_jeannie({"input": command})

    # Default Response
    return "I didn't understand your query. Type 'help' for a list of commands."

# GUI Implementation
def send_message(event=None):
    user_message = user_input.get()
    if user_message.lower() == "exit":
        root.quit()
    else:
        chat_display.config(state="normal")
        chat_display.insert(tk.END, f"👤 You: {user_message}\n", "user")
        response = chat(user_message, user_id="user123")
        chat_display.insert(tk.END, f"🤖 Chatbot: {response}\n\n", "bot")
        chat_display.config(state="disabled")
        user_input.delete(0, tk.END)

# Set up the main GUI window
root = tk.Tk()
root.title("EchoMind - Interactive Chatbot")
root.geometry("700x500")
root.configure(bg="#282C34")

# Chat Display
chat_display = scrolledtext.ScrolledText(
    root, wrap=tk.WORD, width=70, height=20, bg="#1E1E1E", fg="#FFFFFF", font=("Helvetica", 12)
)
chat_display.pack(pady=10, padx=10)
chat_display.insert(tk.END, "🤖 Chatbot: Hello! I'm here to chat. Type 'exit' to stop.\n\n", "bot")
chat_display.config(state="disabled")

# Style tags for chat
chat_display.tag_config("user", foreground="#ADD8E6", font=("Helvetica", 12, "bold"))
chat_display.tag_config("bot", foreground="#90EE90", font=("Helvetica", 12, "italic"))

# Input field
user_input = tk.Entry(root, width=60, font=("Helvetica", 12))
user_input.pack(pady=5, padx=10, side=tk.LEFT)

# Bind Enter key to send message
user_input.bind("<Return>", send_message)

# Send button
send_button = tk.Button(root, text="Send 💬", command=send_message, bg="#4CAF50", fg="#ffffff", font=("Helvetica", 12, "bold"))
send_button.pack(pady=5, padx=10, side=tk.LEFT)

# Run the GUI application
print("Starting the GUI...")
root.mainloop()
