from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
from pymongo import MongoClient
from datetime import datetime, timezone
from dotenv import load_dotenv
import os
import tkinter as tk
from tkinter import scrolledtext
import re
import requests

# Suppress TensorFlow oneDNN warnings
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

# Load environment variables from .env file
load_dotenv()

# Attempt to connect to MongoDB
try:
    mongo_uri = os.getenv("MONGODB_URI")
    client = MongoClient(mongo_uri)
    client.server_info()  # Trigger connection to check if it works
    print("Connected to MongoDB successfully!")
except Exception as e:
    print("Failed to connect to MongoDB:", e)
    client = None

# Define database and collection if connection is successful
if client:
    db = client["chatbot_database"]
    history_collection = db["conversation_history"]

# Load the DialoGPT model and tokenizer
tokenizer = AutoTokenizer.from_pretrained("mistralai/Mistral-7B")
model = AutoModelForCausalLM.from_pretrained("mistralai/Mistral-7B")

# Helper function to calculate simple math expressions
def calculate_math(expression):
    try:
        return str(eval(expression))
    except:
        return "I'm unable to calculate that."

# Function to save conversation history to MongoDB
def save_history(user_id, user_input, bot_response):
    if client:
        conversation_entry = {
            "user_id": user_id,
            "user_input": user_input,
            "bot_response": bot_response,
            "timestamp": datetime.now(timezone.utc)
        }
        history_collection.insert_one(conversation_entry)

# Function to retrieve the last 5 messages to maintain context
def load_history(user_id, limit=5):
    if not client:
        return ""
    user_history = history_collection.find({"user_id": user_id}).sort("timestamp", -1).limit(limit)
    history = ""
    for entry in reversed(list(user_history)):
        history += f"User: {entry['user_input']}\nBot: {entry['bot_response']}\n"
    return history

# Function to get factual data from Wikipedia (simple example)
def get_wikipedia_summary(query):
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{query}"
    try:
        response = requests.get(url).json()
        return response.get("extract", "I couldn't find information on that.")
    except:
        return "There was an error connecting to Wikipedia."

# Function to manage conversation with history and external lookups
def chat(user_input, user_id):
    # Check if input is a math expression
    if re.search(r"\d+[\+\-\*\/]\d+", user_input):
        return calculate_math(user_input)

    # Check if it's a factual question and fetch from Wikipedia
    if "who is" in user_input.lower() or "what is" in user_input.lower():
        query = user_input.replace("who is", "").replace("what is", "").strip()
        return get_wikipedia_summary(query)

    # Retrieve the last few conversation history for context
    conversation_history = load_history(user_id)
    input_text = f"{conversation_history}User: {user_input}\nBot:"

    # Tokenize and encode input
    input_ids = tokenizer.encode(input_text, return_tensors="pt")
    attention_mask = torch.ones_like(input_ids)

    # Generate response from model
    bot_output = model.generate(
        input_ids,
        attention_mask=attention_mask,
        max_length=1000,
        pad_token_id=tokenizer.eos_token_id
    )

    bot_response = tokenizer.decode(bot_output[:, input_ids.shape[-1]:][0], skip_special_tokens=True)

    # Save conversation history
    save_history(user_id, user_input, bot_response)

    return bot_response

# GUI Implementation
def send_message(event=None):
    user_message = user_input.get()
    if user_message.lower() == 'exit':
        root.quit()
    else:
        chat_display.config(state="normal")  # Enable editing to insert messages
        chat_display.insert(tk.END, f"👤 You: {user_message}\n", "user")
        response = chat(user_message, user_id="user123")
        chat_display.insert(tk.END, f"🤖 Chatbot: {response}\n\n", "bot")
        chat_display.config(state="disabled")  # Disable editing after inserting
        user_input.delete(0, tk.END)  # Clear input field after sending

# Set up the main window
root = tk.Tk()
root.title("EchoMind - Interactive Chatbot")
root.geometry("700x500")
root.configure(bg="#282C34")

# Chat Display (Scrollable)
chat_display = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=70, height=20, bg="#1E1E1E", fg="#FFFFFF", font=("Helvetica", 12))
chat_display.pack(pady=10, padx=10)
chat_display.insert(tk.END, "🤖 Chatbot: Hello! I'm here to chat. Type 'exit' to stop.\n\n", "bot")
chat_display.config(state="disabled")  # Disable editing directly in the chat display

# Style tags for user and bot messages
chat_display.tag_config("user", foreground="#ADD8E6", font=("Helvetica", 12, "bold"))
chat_display.tag_config("bot", foreground="#90EE90", font=("Helvetica", 12, "italic"))

# Entry for User Input
user_input = tk.Entry(root, width=60, font=("Helvetica", 12))
user_input.pack(pady=5, padx=10, side=tk.LEFT)

# Bind Enter key to send message
user_input.bind("<Return>", send_message)

# Send Button
send_button = tk.Button(root, text="Send 💬", command=send_message, bg="#4CAF50", fg="#ffffff", font=("Helvetica", 12, "bold"))
send_button.pack(pady=5, padx=10, side=tk.LEFT)

# Run the GUI application
root.mainloop()
