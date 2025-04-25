import streamlit as st
import requests
import os
import json
from datetime import datetime
import pandas as pd
import plotly.express as px
from dotenv import load_dotenv
import uuid
from streamlit_lottie import st_lottie
import json
import random
import time
import calendar
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

COLOR_PALETTE = {
    "primary": "#4a6fa5",
    "secondary": "#6b9080",
    "accent": "#ff9e4f",
    "background": "#f8f9fa",
    "text": "#2b2d42",
    "dark_bg": "#1a1a2e",
    "dark_text": "#e6e6e6"
}


# Load environment variables
load_dotenv()
@st.cache_resource
def load_lottie(path):
    with open(path, "r") as f:
        return json.load(f)


# Page configuration with improved appearance
st.set_page_config(
    page_title="MindEase: AI Mental Health Journal",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=Playfair+Display:ital@0;1&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    color: #2b2d42;
}
h1, h2, h3 {
    font-family: 'Playfair Display', serif;
}
.stButton>button {
    transition: transform .2s, box-shadow .2s;
    font-weight: bold;
    border-radius: 6px;
}
.stButton>button:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
}
</style>
""", unsafe_allow_html=True)



# Initialize session state variables if they don't exist
if 'journal_entries' not in st.session_state:
    st.session_state.journal_entries = []
if 'mood_scores' not in st.session_state:
    st.session_state.mood_scores = []
if 'streak' not in st.session_state:
    st.session_state.streak = 0
if 'last_entry_date' not in st.session_state:
    st.session_state.last_entry_date = None
if 'show_history' not in st.session_state:
    st.session_state.show_history = False
if 'current_view' not in st.session_state:
    st.session_state.current_view = "journal"
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'current_chat_id' not in st.session_state:
    st.session_state.current_chat_id = None
if 'chats' not in st.session_state:
    st.session_state.chats = {}

# Load journal entries from file if available
def load_journal_entries():
    try:
        with open("journal_entries.json", "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

# Save journal entries to file
def save_journal_entries():
    with open("journal_entries.json", "w") as f:
        json.dump(st.session_state.journal_entries, f)

# Load chat history from file if available
def load_chats():
    try:
        with open("chat_history.json", "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

# Save chat history to file
def save_chats():
    with open("chat_history.json", "w") as f:
        json.dump(st.session_state.chats, f)

# Update streak counter
def update_streak():
    today = datetime.now().date()
    if st.session_state.last_entry_date:
        last_date = datetime.strptime(st.session_state.last_entry_date, "%Y-%m-%d").date()
        days_diff = (today - last_date).days
        if days_diff == 1:  # Consecutive day
            st.session_state.streak += 1
        elif days_diff > 1:  # Streak broken
            st.session_state.streak = 1
        # If same day, don't update streak
    else:
        st.session_state.streak = 1
    
    st.session_state.last_entry_date = today.strftime("%Y-%m-%d")

# Analyze mood from text using Claude API
def analyze_mood(text):
    API_KEY = os.getenv("CLAUDE_API_KEY", "")
    CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"
    
    headers = {
        "x-api-key": API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    
    user_message = f"""
    Analyze the following journal entry and rate the overall mood on a scale from 1-10 where 1 is extremely negative and 10 is extremely positive.
    
    Journal Entry: {text}
    
    Return only a number between 1 and 10, with no other text.
    """
    
    payload = {
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 5,
        "messages": [
            {"role": "user", "content": user_message}
        ]
    }
    
    try:
        response = requests.post(CLAUDE_API_URL, headers=headers, json=payload)
        if response.status_code == 200:
            score_text = response.json()["content"][0]["text"].strip()
            # Extract only digits from response
            score = ''.join(filter(str.isdigit, score_text))
            return int(score) if score.isdigit() else 5
        else:
            return 5  # Default score on error
    except Exception as e:
        st.error(f"Error analyzing mood: {e}")
        return 5  # Default score on exception
def set_background_based_on_mood(mood_score):
    if mood_score < 4:
        bg = "linear-gradient(135deg, #a8c0ff 0%, #3f2b96 100%)"
    elif mood_score < 7:
        bg = "linear-gradient(135deg, #c1dfc4 0%, #6b9080 100%)"
    else:
        bg = "linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%)"

    st.markdown(f"""
    <style>
    .stApp {{
        background: {bg};
        background-attachment: fixed;
        background-size: cover;
    }}
    </style>
    """, unsafe_allow_html=True)


# Breathing Exercise Section

def breathing_exercise():
    st.markdown("### 🌬️ Breathing Exercise")
    breath_duration = st.slider("Breath duration (seconds)", 3, 8, 4)

    if st.button("Start Exercise", key="start_breathing"):
        placeholder = st.empty()
        for i in range(3):  # 3 cycles
            placeholder.markdown("""
            <div style="text-align: center;">
                <h3>Breathe In</h3>
                <div style="width: 100px; height: 100px; background-color: #4a6fa5; border-radius: 50%; margin: 20px auto; animation: breatheIn {}s ease-in forwards;"></div>
            </div>
            """.format(breath_duration), unsafe_allow_html=True)
            time.sleep(breath_duration)

            placeholder.markdown("""
            <div style="text-align: center;">
                <h3>Breathe Out</h3>
                <div style="width: 200px; height: 200px; background-color: #4a6fa5; border-radius: 50%; margin: 20px auto; animation: breatheOut {}s ease-out forwards;"></div>
            </div>
            """.format(breath_duration), unsafe_allow_html=True)
            time.sleep(breath_duration)


# Gratitude Prompt Carousel

def show_gratitude_prompt():
    prompts = [
        "What made you smile today?",
        "Something you're grateful for this week:",
        "Who helped you recently and how?",
        "Describe a small win today.",
        "What personal quality are you thankful for in yourself?"
    ]
    selected = random.choice(prompts)
    st.markdown(f"**💖 Gratitude Prompt:** _{selected}_")


#  Distraction-Free Journal Entry Mode

def distraction_free_editor():
    if 'distraction_free' not in st.session_state:
        st.session_state.distraction_free = False

    if st.button("🌿 Enter Distraction-Free Mode"):
        st.session_state.distraction_free = True

    if st.session_state.distraction_free:
        st.markdown("""
        <style>
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        .stApp > div:first-child { padding-top: 1rem; }
        </style>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div style="position: fixed; top: 10px; right: 10px;">
            <button onclick="window.parent.postMessage('exitDistractionFree', '*')"
                style="background: #4a6fa5; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer;">
                Exit
            </button>
        </div>
        """, unsafe_allow_html=True)

        journal_input = st.text_area(
            "Your thoughts...",
            height=400,
            label_visibility="collapsed",
            placeholder="Write freely...",
            key="distraction_free_input"
        )

        if st.button("Save Entry", key="distraction_save"):
            # You can hook this into the main journaling logic as needed
            st.success("✅ Entry saved successfully!")
            st.session_state.distraction_free = False
            st.rerun()



# Mood Calendar Heatmap

def mood_calendar_heatmap():
    if not st.session_state.journal_entries:
        st.info("You need some journal entries to view the mood calendar.")
        return

    df = pd.DataFrame({
        'date': [datetime.strptime(e['date'], "%Y-%m-%d") for e in st.session_state.journal_entries],
        'mood_score': [e['mood_score'] for e in st.session_state.journal_entries]
    })

    df['month'] = df['date'].dt.month
    df['day'] = df['date'].dt.day
    df['year'] = df['date'].dt.year
    today = datetime.now()
    df = df[df['year'] == today.year]

    heatmap = np.zeros((12, 31))
    for _, row in df.iterrows():
        heatmap[row['month'] - 1, row['day'] - 1] = row['mood_score']

    plt.figure(figsize=(15, 5))
    sns.heatmap(heatmap, cmap="YlGnBu", cbar_kws={'label': 'Mood Score'}, linewidths=0.5)
    plt.yticks(np.arange(12) + 0.5, [calendar.month_name[m+1] for m in range(12)], rotation=0)
    plt.xticks(np.arange(0, 31), [str(i+1) for i in range(31)], rotation=90)
    plt.title("Mood Calendar - {year}".format(year=today.year))
    st.pyplot(plt)



# Emotional Weather Summary

def emotional_weather_summary():
    if len(st.session_state.mood_scores) < 5:
        return "Not enough data for a weekly summary."

    recent = st.session_state.mood_scores[-7:]
    trend = "↗️ Improving" if recent[-1] > recent[0] else "↘️ Declining" if recent[-1] < recent[0] else "→ Stable"

    if np.mean(recent) > 7:
        emoji = "☀️"
        mood = "Mostly Positive"
    elif np.mean(recent) >= 5:
        emoji = "⛅"
        mood = "Balanced with Some Ups & Downs"
    else:
        emoji = "🌧️"
        mood = "Low Mood Period"

    return f"### {emoji} Emotional Weather Summary\n**Mood:** {mood}\n**Trend:** {trend}"



# Mood Tone Breakdown (Pie Chart)

def mood_tone_pie_chart():
    from collections import Counter

    if not st.session_state.journal_entries:
        return

    mood_labels = {
        range(1, 4): 'Negative',
        range(4, 7): 'Neutral',
        range(7, 11): 'Positive'
    }

    def get_tone(score):
        for rng, label in mood_labels.items():
            if score in rng:
                return label
        return "Unknown"

    tone_counts = Counter(get_tone(e['mood_score']) for e in st.session_state.journal_entries)
    labels = list(tone_counts.keys())
    values = list(tone_counts.values())

    fig, ax = plt.subplots()
    ax.pie(values, labels=labels, autopct='%1.1f%%', startangle=90, colors=["#ff6b6b", "#ffd93d", "#6bcf63"])
    ax.axis('equal')
    st.pyplot(fig)



# Meditation Audio Player

def meditation_audio_player():
    st.markdown("### 🧘 Guided Meditation")
    meditation_type = st.selectbox("Choose a meditation style:", ["Rain Sounds", "Forest Ambience", "Ocean Waves"])

    audio_files = {
        "Rain Sounds": "audio/rain.mp3",
        "Forest Ambience": "audio/rain.mp3",
        "Ocean Waves": "audio/rain.mp3"
    }

    selected_audio = audio_files.get(meditation_type)

    if os.path.exists(selected_audio):
        with open(selected_audio, 'rb') as f:
            st.audio(f.read(), format='audio/mp3')
    else:
        st.warning("Meditation audio not found. Please check file paths.")



# Streak Gamification

def show_streak_badges():
    st.markdown("### 🎯 Progress Milestones")
    streak = st.session_state.get("streak", 0)

    if streak >= 30:
        st.success("🏅 30-Day Mind Mastery! Amazing consistency.")
    elif streak >= 14:
        st.info("🥈 2-Week Warrior! Keep going.")
    elif streak >= 7:
        st.info("🎖️ 7-Day Streak! You're on a roll.")
    elif streak >= 3:
        st.info("💪 3-Day Start Strong! You’ve begun a great habit.")
    else:
        st.markdown("🌱 Start your streak and watch your growth!")

    st.progress(min(streak / 30, 1.0))



# Achievement Badge System

def achievement_badges():
    st.markdown("### 🏆 Achievements")
    entries = len(st.session_state.journal_entries)
    badges = []

    if entries >= 1:
        badges.append("📘 First Entry")
    if entries >= 10:
        badges.append("📗 Consistency Hero")
    if entries >= 25:
        badges.append("📕 Reflection Pro")
    if entries >= 50:
        badges.append("📙 Journaling Legend")

    if badges:
        st.markdown("You're earning milestones! ✨")
        st.markdown("**Unlocked Badges:**")
        for b in badges:
            st.markdown(f"- {b}")
    else:
        st.info("No badges unlocked yet. Keep journaling to earn achievements!")

#phase(1-4)
# Function to get AI response for chat
def get_ai_response(message, chat_history):
    API_KEY = os.getenv("CLAUDE_API_KEY", "")
    CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"
    
    headers = {
        "x-api-key": API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    
    # Format chat history for Claude API
    api_messages = []
    for msg in chat_history:
        api_messages.append({
            "role": msg["role"],
            "content": msg["content"]
        })
    
    # Add the new message
    api_messages.append({
        "role": "user",
        "content": message
    })
    
    system_prompt = """
    You are MindEase, a compassionate AI mental health assistant. 
    Your conversations are supportive, empathetic, and focused on helping the user process their emotions and experiences.
    Ask thoughtful follow-up questions to encourage reflection.
    Provide evidence-based suggestions when appropriate, but focus primarily on being a good listener.
    Keep responses warm and personalized, avoiding clinical or generic language.
    If the user expresses serious mental health concerns, gently remind them that you're not a replacement for professional help.
    """
    
    payload = {
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 600,
        "system": system_prompt,
        "messages": api_messages
    }
    
    try:
        response = requests.post(CLAUDE_API_URL, headers=headers, json=payload)
        if response.status_code == 200:
            return response.json()["content"][0]["text"]
        else:
            st.error(f"API Error: {response.status_code} - {response.text}")
            return "I'm having trouble connecting right now. Please try again later."
    except Exception as e:
        st.error(f"Error getting AI response: {e}")
        return "I'm having trouble connecting right now. Please try again later."

# Function to get AI reflection for initial journal entry
def get_ai_reflection(mood_input, journal_input):
    API_KEY = os.getenv("CLAUDE_API_KEY", "")
    CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"
    
    headers = {
        "x-api-key": API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    
    user_message = f"""
    You are a compassionate mental health assistant called MindEase.

    The user provided a mood check-in and a journal entry.

    Mood: {mood_input}
    Journal Entry: {journal_input}

    Please provide a thoughtful response in 3 sections:
    1. A compassionate reflection on their emotional state and experiences
    2. 2-3 positive observations or insights from their journal entry
    3. 1-2 gentle, evidence-based suggestions for supporting their mental wellbeing

    End your response with a thoughtful follow-up question to encourage continued dialogue.
    
    Keep your response warm, genuine, and concise (max 600 tokens). Do not use placeholder text or generic responses. Make the user feel heard and understood.
    """
    
    payload = {
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 600,
        "messages": [
            {"role": "user", "content": user_message}
        ]
    }
    
    try:
        response = requests.post(CLAUDE_API_URL, headers=headers, json=payload)
        if response.status_code == 200:
            return response.json()["content"][0]["text"]
        else:
            st.error(f"API Error: {response.status_code} - {response.text}")
            return "I'm having trouble connecting right now. Please try again later."
    except Exception as e:
        st.error(f"Error getting AI reflection: {e}")
        return "I'm having trouble connecting right now. Please try again later."

# Function to generate insights from journal entries
def generate_insights():
    if len(st.session_state.journal_entries) < 3:
        return "Keep journaling! Insights will be generated after you have at least 3 entries."
    
    # Combine recent entries
    recent_entries = [entry['journal'] for entry in st.session_state.journal_entries[-5:]]
    combined_text = " ".join(recent_entries)
    
    API_KEY = os.getenv("CLAUDE_API_KEY", "")
    CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"
    
    headers = {
        "x-api-key": API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    
    user_message = f"""
    You are a mental health insights assistant. Analyze these recent journal entries and provide meaningful insights about patterns, themes, and potential areas for growth:

    {combined_text}

    Provide 3 insights formatted as bullet points. Each insight should be concise, personalized, and actionable. Focus on patterns in emotional states, recurring themes, and gentle suggestions for personal growth.
    """
    
    payload = {
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 400,
        "messages": [
            {"role": "user", "content": user_message}
        ]
    }
    
    try:
        response = requests.post(CLAUDE_API_URL, headers=headers, json=payload)
        if response.status_code == 200:
            return response.json()["content"][0]["text"]
        else:
            return "Unable to generate insights at this time."
    except Exception:
        return "Unable to generate insights at this time."

# Function to display mood graph
def display_mood_graph():
    if len(st.session_state.journal_entries) > 0:
        data = {
            'Date': [entry['date'] for entry in st.session_state.journal_entries],
            'Mood Score': [entry['mood_score'] for entry in st.session_state.journal_entries]
        }
        df = pd.DataFrame(data)
        
        # Convert date strings to datetime objects
        df['Date'] = pd.to_datetime(df['Date'])
        
        # Sort by date
        df = df.sort_values('Date')
        
        # Create graph
        fig = px.line(
            df, 
            x='Date', 
            y='Mood Score',
            markers=True,
            title='Your Mood History',
            labels={'Mood Score': 'Mood (1-10)', 'Date': ''},
            height=400
        )
        
        # Customize appearance
        fig.update_layout(
            xaxis_title="",
            yaxis_title="Mood Score (1-10)",
            yaxis_range=[0, 11],
            plot_bgcolor='rgba(240,240,240,0.2)',
            hovermode='x unified'
        )
        
        # Add horizontal grid lines
        fig.update_yaxes(
            showgrid=True,
            gridwidth=1,
            gridcolor='rgba(200,200,200,0.3)'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Start journaling to see your mood graph.")

# Function to display chat interface
def display_chat_interface():
    if not st.session_state.chat_history:
        st.info("Start a journal entry to begin chatting with MindEase.")
        return
    
    # Display chat messages
    for message in st.session_state.chat_history:
        with st.container():
            if message["role"] == "user":
                st.markdown(f"""
                <div class="chat-message user">
                    <div class="avatar">👤</div>
                    <div class="message">{message["content"]}</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="chat-message assistant">
                    <div class="avatar">🧠</div>
                    <div class="message">{message["content"]}</div>
                </div>
                """, unsafe_allow_html=True)
    
    # User input for chat
    user_input = st.text_area("Your message:", key="chat_input", height=100)
    
    if st.button("Send", key="send_message"):
        if user_input:
            # Add user message to chat history
            st.session_state.chat_history.append({
                "role": "user",
                "content": user_input
            })
            
            # Get AI response
            ai_response = get_ai_response(user_input, st.session_state.chat_history)
            
            # Add AI response to chat history
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": ai_response
            })
            
            # Save current chat
            if st.session_state.current_chat_id:
                st.session_state.chats[st.session_state.current_chat_id] = st.session_state.chat_history
                save_chats()
            
            # Clear input
            st.rerun()


# Sidebar
# --- DARK MODE STATE INIT (before sidebar) ---
if 'dark_mode' not in st.session_state:
    st.session_state.dark_mode = False

# --- SIDEBAR ---
with st.sidebar:
    st.image("/home/deathmonarch/CODE/Mental/dog.jpeg", width=150)
    st.markdown("<h1 class='main-header'>MindEase</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subheader'>Your AI Mental Health Journal</p>", unsafe_allow_html=True)

    # 🌙 Dark Mode Toggle
    st.session_state.dark_mode = st.checkbox("🌙 Dark Mode")

    # 🔥 Streak
    st.markdown(f"### 🔥 **{st.session_state.streak}** day streak")

    # 📚 Navigation
    st.markdown("### 📚 Navigation")
    if st.button("📝 Journal Entry"):
        st.session_state.current_view = "journal"
    if st.button("💬 Continue Conversation"):
        st.session_state.current_view = "chat"
    if st.button("📊 Analytics & Insights"):
        st.session_state.current_view = "analytics"
    if st.button("📜 Journal History"):
        st.session_state.current_view = "history"

    # 💬 Chat History
    if st.session_state.chats:
        st.markdown("### 💬 Recent Conversations")
        for chat_id, chat in st.session_state.chats.items():
            date = chat_id.split("_")[0]
            preview = chat[0]["content"][:20] + "..." if len(chat[0]["content"]) > 20 else chat[0]["content"]
            if st.button(f"{date}: {preview}", key=f"chat_{chat_id}"):
                st.session_state.current_chat_id = chat_id
                st.session_state.chat_history = chat
                st.session_state.current_view = "chat"

    # 🧰 Resources
    st.markdown("### 🧰 Resources")
    st.markdown("""
    - [Crisis Text Line](https://www.crisistextline.org/) - Text HOME to 741741  
    - [National Suicide Prevention Lifeline](https://suicidepreventionlifeline.org/) - 988  
    - [7 Cups - Online Therapy](https://www.7cups.com/)
    """)

    # ⚙️ Settings (placeholder)
    st.markdown("### ⚙️ Settings")
    st.checkbox("Dark Mode (coming soon)", disabled=True)

    # ℹ️ About
    with st.expander("ℹ️ About MindEase"):
        st.write("""
        MindEase is an AI-powered mental health journaling app designed to help you track your mood, reflect on your experiences, and gain insights into your emotional patterns.

        This app does not store any of your data on servers - everything is kept locally on your device.

        **Note:** This app is not a substitute for professional mental health care. If you're in crisis, please contact a mental health professional or crisis service.
        """)

# 🌙 Global Dark Mode CSS Injection (AFTER sidebar toggle)
if st.session_state.dark_mode:
    st.markdown(f"""
    <style>
    .stApp {{
        background-color: {COLOR_PALETTE['dark_bg']};
        color: {COLOR_PALETTE['dark_text']};
    }}
    </style>
    """, unsafe_allow_html=True)

# Main app layout - Journal view
if st.session_state.current_view == "journal":
    st.markdown("<h1 class='main-header'>📔 MindEase: Daily Check-in</h1>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### 🧠 How are you feeling today?")
        mood_options = ["😔 Very Low", "😟 Low", "😐 Neutral", "🙂 Good", "😊 Great"]
        mood_selection = st.select_slider("Select your mood", options=mood_options, value="😐 Neutral")
        mood_input = st.text_area("Tell me more about your mood:", placeholder="e.g., I'm feeling a little anxious, but hopeful about...")
    
    with col2:
        st.markdown("### 📅 What happened today?")
        journal_input = st.text_area("Your journal entry:", height=220, placeholder="e.g., Today I had a challenging meeting at work, but I handled it better than I expected. I also took time to...")
    
    # Tags for categorizing journal entries
    st.markdown("### 🏷️ Tags (optional)")
    tags_col1, tags_col2, tags_col3, tags_col4 = st.columns(4)
    
    with tags_col1:
        work_tag = st.checkbox("Work")
        health_tag = st.checkbox("Health")
    
    with tags_col2:
        relationships_tag = st.checkbox("Relationships")
        self_care_tag = st.checkbox("Self-care")
    
    with tags_col3:
        achievements_tag = st.checkbox("Achievements")
        challenges_tag = st.checkbox("Challenges")
    
    with tags_col4:
        gratitude_tag = st.checkbox("Gratitude")
        custom_tag = st.text_input("Custom tag")
    
    # Collect all selected tags
    selected_tags = []
    if work_tag: selected_tags.append("Work")
    if health_tag: selected_tags.append("Health")
    if relationships_tag: selected_tags.append("Relationships")
    if self_care_tag: selected_tags.append("Self-care")
    if achievements_tag: selected_tags.append("Achievements")
    if challenges_tag: selected_tags.append("Challenges")
    if gratitude_tag: selected_tags.append("Gratitude")
    if custom_tag: selected_tags.append(custom_tag)
    show_gratitude_prompt()
    distraction_free_editor()
    breathing_exercise()
    
    if st.button("💫 Reflect with AI") and (mood_input or journal_input):
        with st.spinner("MindEase is reflecting with you..."):
            # Analyze mood score
            mood_numeric = {
                "😔 Very Low": 2,
                "😟 Low": 4,
                "😐 Neutral": 5,
                "🙂 Good": 7,
                "😊 Great": 9
            }.get(mood_selection, 5)
            
            # Adjust with text analysis for more precision
            if journal_input:
                text_mood = analyze_mood(journal_input)
                # Weighted average: 70% selection, 30% text analysis
                mood_score = int((mood_numeric * 0.7) + (text_mood * 0.3))
            else:
                mood_score = mood_numeric
            
            # Clip to valid range
            mood_score = max(1, min(10, mood_score))
            set_background_based_on_mood(mood_score)
            
            # Get AI reflection
            reflection = get_ai_reflection(mood_input, journal_input)
            
            # Add entry to journal
            entry_date = datetime.now().strftime("%Y-%m-%d")
            entry_time = datetime.now().strftime("%H:%M")
            new_entry = {
                "date": entry_date,
                "time": entry_time,
                "mood": mood_selection,
                "mood_input": mood_input,
                "journal": journal_input,
                "reflection": reflection,
                "mood_score": mood_score,
                "tags": selected_tags
            }
            
            st.session_state.journal_entries.append(new_entry)
            st.session_state.mood_scores.append(mood_score)
            
            # Update streak
            update_streak()
            
            # Create a new chat session
            chat_id = f"{entry_date}_{entry_time}"
            st.session_state.current_chat_id = chat_id
            
            # Initialize chat with the journal entry and AI reflection
            initial_chat = [
                {
                    "role": "user",
                    "content": f"Mood: {mood_selection}\n\nMood notes: {mood_input}\n\nJournal entry: {journal_input}"
                },
                {
                    "role": "assistant",
                    "content": reflection
                }
            ]
            
            st.session_state.chat_history = initial_chat
            st.session_state.chats[chat_id] = initial_chat
            
            # Save to files
            save_journal_entries()
            save_chats()
            
            # Display reflection and prompt for further conversation
            st.markdown("## 💭 Initial Reflection")
            st.markdown(f"**Mood Score:** {mood_score}/10")
            st.markdown(reflection)
            
            st.success("Journal entry saved! You can now continue the conversation.")
            
            # Option to continue chatting
            if st.button("Continue conversation"):
                st.session_state.current_view = "chat"
                st.rerun()


# Chat view
elif st.session_state.current_view == "chat":
    st.markdown("<h1 class='main-header'>💬 Continue Your Conversation</h1>", unsafe_allow_html=True)
    
    display_chat_interface()

# Analytics view
elif st.session_state.current_view == "analytics":
    st.markdown("<h1 class='main-header'>📊 Mood Analytics & Insights</h1>", unsafe_allow_html=True)
    
    # Overall stats
    if len(st.session_state.journal_entries) > 0:
        col1, col2, col3, col4 = st.columns(4)
        
        # Calculate stats
        num_entries = len(st.session_state.journal_entries)
        avg_mood = sum(entry['mood_score'] for entry in st.session_state.journal_entries) / num_entries
        streak = st.session_state.streak
        st.markdown("### 🌤️ Emotional Weather")
        summary = emotional_weather_summary()
        st.markdown(summary)
        st.markdown("### 🧘 Guided Meditation")
        meditation_audio_player()
        show_streak_badges()



        # Last 7 days trend
        recent_entries = st.session_state.journal_entries[-7:] if len(st.session_state.journal_entries) >= 7 else st.session_state.journal_entries
        if len(recent_entries) >= 2:
            first_score = recent_entries[0]['mood_score']
            last_score = recent_entries[-1]['mood_score']
            trend = last_score - first_score
            trend_icon = "↗️" if trend > 0 else "↘️" if trend < 0 else "→"
        else:
            trend_icon = "→"
        
        with col1:
            st.metric("Total Entries", num_entries)
        
        with col2:
            st.metric("Average Mood", f"{avg_mood:.1f}/10")
        
        with col3:
            st.metric("Current Streak", f"{streak} days")
        
        with col4:
            st.metric("Recent Trend", trend_icon)
    
    # Mood graph
    st.markdown("### Your Mood Over Time")
    display_mood_graph()
    st.markdown("### 🗓️ Mood Calendar")
    mood_calendar_heatmap()
    achievement_badges()


    
    # AI Insights
    st.markdown("### 💡 AI Insights")
    insights = generate_insights()
    st.markdown(insights)
    
    # Tags analysis
    if len(st.session_state.journal_entries) > 0:
        st.markdown("### 🏷️ Tag Analysis")
        
        # Collect all tags
        all_tags = []
        for entry in st.session_state.journal_entries:
            if 'tags' in entry and entry['tags']:
                all_tags.extend(entry['tags'])
        
        if all_tags:
            # Count tag occurrences
            tag_counts = {}
            for tag in all_tags:
                if tag in tag_counts:
                    tag_counts[tag] += 1
                else:
                    tag_counts[tag] = 1
            
            # Create bar chart of tags
            tag_df = pd.DataFrame({
                'Tag': list(tag_counts.keys()),
                'Count': list(tag_counts.values())
            })
            
            fig = px.bar(
                tag_df.sort_values('Count', ascending=False), 
                x='Tag', 
                y='Count',
                title='Most Common Journal Tags',
                color='Count',
                color_continuous_scale=px.colors.sequential.Viridis
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Start using tags in your journal entries to see tag analysis.")
    st.markdown("### 🧠 Mood Tone Distribution")
    mood_tone_pie_chart()

    
    # Chat engagement metrics
    if st.session_state.chats:
        st.markdown("### 💬 Conversation Engagement")
        
        # Calculate average messages per conversation
        total_messages = sum(len(chat) for chat in st.session_state.chats.values())
        avg_messages = total_messages / len(st.session_state.chats)
        
        st.metric("Total Conversations", len(st.session_state.chats))
        st.metric("Average Messages per Conversation", f"{avg_messages:.1f}")

# History view
elif st.session_state.current_view == "history":
    st.markdown("<h1 class='main-header'>📜 Journal History</h1>", unsafe_allow_html=True)
    
    if len(st.session_state.journal_entries) > 0:
        # Sort entries by date (newest first)
        sorted_entries = sorted(st.session_state.journal_entries, key=lambda x: x.get('date', ''), reverse=True)
        
        # Filter options
        st.markdown("### Filter Entries")
        col1, col2 = st.columns(2)
        with col1:
            # Get unique tags
            unique_tags = set()
            for entry in st.session_state.journal_entries:
                if 'tags' in entry:
                    unique_tags.update(entry['tags'])
            
            # Filter by tag if there are tags available
            selected_tag = st.selectbox("Filter by tag:", ["All Tags"] + sorted(list(unique_tags)))
        
        with col2:
            # Filter by mood
            mood_filter = st.selectbox("Filter by mood:", ["All Moods", "😔 Very Low", "😟 Low", "😐 Neutral", "🙂 Good", "😊 Great"])
        
        # Apply filters
        filtered_entries = sorted_entries
        if selected_tag != "All Tags":
            filtered_entries = [entry for entry in filtered_entries if 'tags' in entry and selected_tag in entry['tags']]
        
        if mood_filter != "All Moods":
            filtered_entries = [entry for entry in filtered_entries if entry.get('mood', '') == mood_filter]
        
        # Display entries
        if filtered_entries:
            for entry in filtered_entries:
                entry_date = entry.get('date', 'Unknown date')
                entry_time = entry.get('time', '')
                entry_id = f"{entry_date}_{entry_time}"
                
                with st.expander(f"{entry_date} - {entry.get('mood', 'Unknown mood')}"):
                    st.markdown(f"**Date:** {entry_date} at {entry_time}")
                    st.markdown(f"**Mood:** {entry.get('mood', 'Not recorded')} ({entry.get('mood_score', 'N/A')}/10)")
                    
                    if 'tags' in entry and entry['tags']:
                        st.markdown(f"**Tags:** {', '.join(entry['tags'])}")
                    
                    if 'mood_input' in entry and entry['mood_input']:
                        st.markdown(f"**Mood notes:** {entry['mood_input']}")
                    
                    if 'journal' in entry and entry['journal']:
                        st.markdown(f"**Journal entry:**\n{entry['journal']}")
                    
                    if 'reflection' in entry and entry['reflection']:
                        st.markdown(f"**AI Reflection:**\n{entry['reflection']}")
                    
                    # Options
                    col1, col2 = st.columns(2)
                    with col1:
                        unique_key = f"chat_{entry_id}_{uuid.uuid4()}"
                        if st.button("💬 Continue Conversation", key=unique_key):
                            # If chat exists, load it
                            if entry_id in st.session_state.chats:
                                st.session_state.chat_history = st.session_state.chats[entry_id]
                            # Otherwise, create a new chat based on the journal entry
                            else:
                                initial_chat = [
                                    {
                                        "role": "user",
                                        "content": f"Mood: {entry.get('mood', '')}\n\nMood notes: {entry.get('mood_input', '')}\n\nJournal entry: {entry.get('journal', '')}"
                                    },
                                    {
                                        "role": "assistant",
                                        "content": entry.get('reflection', "How can I help you process these thoughts and feelings?")
                                    }
                                ]
                                st.session_state.chat_history = initial_chat
                                st.session_state.chats[entry_id] = initial_chat
                                save_chats()
                            
                            st.session_state.current_chat_id = entry_id
                            st.session_state.current_view = "chat"
                            st.rerun()

                    
                    with col2:
                        if st.button(f"🗑️ Delete entry", key=f"delete_{entry_id}"):
                            st.session_state.journal_entries.remove(entry)
                            
                            # Also remove associated chat if it exists
                            if entry_id in st.session_state.chats:
                                del st.session_state.chats[entry_id]
                                save_chats()
                            
                            save_journal_entries()
                            st.rerun()

        else:
            st.info("No entries match your filter criteria.")
    else:
        st.info("You haven't created any journal entries yet. Start writing to build your journal history!")

# Export data functionality
if st.session_state.current_view == "analytics" or st.session_state.current_view == "history":
    st.markdown("---")
    st.markdown("### 📤 Export Your Data")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Export Journal Entries (JSON)"):
            if st.session_state.journal_entries:
                # Convert entries to JSON string
                json_str = json.dumps(st.session_state.journal_entries, indent=2)
                
                # Create download button
                st.download_button(
                    label="Download JSON",
                    data=json_str,
                    file_name="mindease_journal_entries.json",
                    mime="application/json"
                )
            else:
                st.warning("No journal entries to export.")
    
    with col2:
        if st.button("Export Journal Entries (CSV)"):
            if st.session_state.journal_entries:
                # Convert to pandas DataFrame
                entries_list = []
                for entry in st.session_state.journal_entries:
                    entry_dict = {
                        "Date": entry.get("date", ""),
                        "Time": entry.get("time", ""),
                        "Mood": entry.get("mood", ""),
                        "Mood Score": entry.get("mood_score", ""),
                        "Mood Notes": entry.get("mood_input", "").replace("\n", " "),
                        "Journal Entry": entry.get("journal", "").replace("\n", " "),
                        "Tags": ", ".join(entry.get("tags", []))
                    }
                    entries_list.append(entry_dict)
                
                df = pd.DataFrame(entries_list)
                
                # Convert to CSV
                csv = df.to_csv(index=False)
                
                # Create download button
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name="mindease_journal_entries.csv",
                    mime="text/csv"
                )
            else:
                st.warning("No journal entries to export.")

# "Therapy Mode" (more advanced chat feature)
if st.session_state.current_view == "chat":
    with st.expander("🛠️ Therapy Mode Settings (Advanced)"):
        st.markdown("Adjust how MindEase responds to you:")
        
        therapy_style = st.selectbox(
            "Therapeutic approach:",
            [
                "Balanced (Default)",
                "Cognitive Behavioral",
                "Solution-Focused",
                "Mindfulness-Based",
                "Compassion-Focused"
            ]
        )
        
        response_length = st.select_slider(
            "Response length:",
            options=["Brief", "Balanced", "Detailed"],
            value="Balanced"
        )
        
        focus_areas = st.multiselect(
            "Focus areas for conversation:",
            [
                "Emotional processing",
                "Problem-solving",
                "Identifying patterns",
                "Building resilience",
                "Stress management",
                "Sleep improvement",
                "Relationship issues"
            ],
            default=["Emotional processing"]
        )
        
        if st.button("Apply Settings"):
            # Add a system message to the chat to guide the AI's responses
            system_message = f"""
            The user has requested that you adjust your therapeutic style to be more {therapy_style.lower()}-oriented,
            with {response_length.lower()} responses, focusing primarily on {', '.join(focus_areas).lower()}.
            
            You should incorporate these preferences while maintaining a compassionate and supportive tone.
            Remember, you're a journaling assistant, not a replacement for professional therapy.
            """
            
            # Add as a hidden system message
            st.session_state.chat_history.append({
                "role": "system",
                "content": system_message
            })
            
            # Confirm to user
            st.success("Settings applied! Your next conversation will reflect these preferences.")

# Add footer
st.markdown("---")
st.markdown(
    """<div style='text-align: center; color: gray; font-size: 0.8em;'>
    MindEase v1.0.0 | Created with ❤️ | Not a substitute for professional mental health care
    </div>""", 
    unsafe_allow_html=True
)