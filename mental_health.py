import streamlit as st
import requests
import os
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="MindEase: AI Mental Health Journal", layout="centered")

API_KEY = os.getenv("CLAUDE_API_KEY")
CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"

st.title("📔 MindEase: AI Mental Health Journal")
st.write("Start your daily check-in:")

# User inputs
mood_input = st.text_area("🧠 How are you feeling today?", placeholder="e.g., a little anxious, but hopeful")
journal_input = st.text_area("📅 What happened today?", placeholder="e.g., Had a tough class, argued with a friend, but also got good news...")

if st.button("Reflect with AI") and (mood_input or journal_input):
    with st.spinner("MindEase is reflecting with you..."):

        headers = {
            "x-api-key": API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        user_message = f"""
You are a compassionate mental health assistant.

The user provided a mood check-in and a short journal entry.

Mood: {mood_input}
Journal Entry: {journal_input}

Please respond in a caring, empathetic tone. Reflect on their emotional state and events, and suggest simple well-being strategies if needed.
"""

        payload = {
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": 600,
            "messages": [
                {"role": "user", "content": user_message}
            ]
        }

        response = requests.post(CLAUDE_API_URL, headers=headers, json=payload)

        if response.status_code == 200:
            reply = response.json()["content"][0]["text"]
            st.markdown(f"**MindEase:** {reply}")
        else:
            st.error("Something went wrong. Check your API key or input.")
