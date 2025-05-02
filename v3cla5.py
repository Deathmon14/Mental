import streamlit as st
st.set_page_config(
    page_title="MindEase: AI Mental Health Journal",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

import requests
import os
import json
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
from dotenv import load_dotenv
import uuid
import random
import time
import calendar
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pymongo import MongoClient
from bson import ObjectId
import hashlib
from collections import defaultdict
import base64

# --- CONSTANTS ---
COLOR_PALETTE = {
    "primary": "#4a6fa5",
    "secondary": "#6b9080",
    "accent": "#ff9e4f",
    "background": "#f8f9fa",
    "text": "#2b2d42",
    "dark_bg": "#1a1a2e",
    "dark_text": "#e6e6e6"
}

MOOD_OPTIONS = {
    "😔 Very Low": {"score": 2, "color": "#d64045"},
    "😟 Low": {"score": 4, "color": "#ff9a76"},
    "😐 Neutral": {"score": 5, "color": "#ffd93d"},
    "🙂 Good": {"score": 7, "color": "#6bcf63"},
    "😊 Great": {"score": 9, "color": "#4cc9f0"}
}

# --- INITIALIZATION ---
def initialize_session_state():
    """Initialize all session state variables"""
    defaults = {
        'logged_in': False,
        'current_user': None,
        'journal_entries': [],
        'mood_scores': [],
        'streak': 0,
        'last_entry_date': None,
        'show_history': False,
        'current_view': "journal",
        'chat_history': [],
        'current_chat_id': None,
        'chats': {},
        'dark_mode': True,
        'distraction_free': False,
        'selected_tags': [],
        'therapy_settings': {
            'style': "Balanced (Default)",
            'length': "Balanced",
            'focus_areas': ["Emotional processing"]
        }
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

initialize_session_state()

# --- DATABASE FUNCTIONS ---
@st.cache_resource
def connect_to_mongodb():
    """Establish MongoDB connection"""
    load_dotenv()
    connection_string = os.getenv("MONGODB_URI", "")
    if not connection_string:
        st.error("MongoDB connection string not found. Please set the MONGODB_URI environment variable.")
        return None
    try:
        client = MongoClient(connection_string)
        db = client.mindease
        client.admin.command('ping')
        return db
    except Exception as e:
        st.error(f"Error connecting to MongoDB: {e}")
        return None

db = connect_to_mongodb()

# --- AUTHENTICATION FUNCTIONS ---
def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(username, password, email=None):
    """Create a new user account"""
    if db.users.find_one({"username": username}):
        return False, "Username already exists"
    
    user_data = {
        "username": username,
        "password": hash_password(password),
        "created_at": datetime.now().isoformat(),
        "last_login": datetime.now().isoformat()
    }
    if email:
        user_data["email"] = email
        
    db.users.insert_one(user_data)
    return True, "User created successfully"

def validate_login(username, password):
    """Validate user credentials"""
    user = db.users.find_one({"username": username})
    if user and user.get("password") == hash_password(password):
        # Update last login time
        db.users.update_one(
            {"username": username},
            {"$set": {"last_login": datetime.now().isoformat()}}
        )
        return True
    return False

# --- UTILITY FUNCTIONS ---
def autoplay_audio(file_path):
    """Autoplay audio file (for meditation)"""
    with open(file_path, "rb") as f:
        data = f.read()
        b64 = base64.b64encode(data).decode()
        md = f"""
            <audio controls autoplay="true">
            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
            </audio>
            """
        st.markdown(md, unsafe_allow_html=True)

def set_background_based_on_mood(mood_score):
    """Set dynamic background based on mood score"""
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

def update_streak():
    """Update user's journaling streak"""
    today = datetime.now().date()
    if st.session_state.last_entry_date:
        last_date = datetime.strptime(st.session_state.last_entry_date, "%Y-%m-%d").date()
        days_diff = (today - last_date).days
        if days_diff == 1:  # Consecutive day
            st.session_state.streak += 1
        elif days_diff > 1:  # Streak broken
            st.session_state.streak = 1
    else:
        st.session_state.streak = 1
    
    st.session_state.last_entry_date = today.strftime("%Y-%m-%d")

# --- DATA LOADING/SAVING ---
def load_journal_entries():
    """Load journal entries from database"""
    if db is None:
        return []
    try:
        entries = list(db.journal_entries.find({"username": st.session_state.current_user}))
        for entry in entries:
            entry["_id"] = str(entry["_id"])
        return entries
    except Exception as e:
        st.error(f"Error loading journal entries: {e}")
        return []

def save_journal_entry(entry):
    """Save a single journal entry"""
    if db is not None:
        try:
            db.journal_entries.insert_one(entry)
            return True
        except Exception as e:
            st.error(f"Error saving journal entry: {e}")
            return False
    return False

def load_chats():
    """Load chat history from database"""
    if db is None:
        return {}
    try:
        chats = {}
        for chat in db.chats.find({"username": st.session_state.current_user}):
            chats[chat["chat_id"]] = chat["messages"]
        return chats
    except Exception as e:
        st.error(f"Error loading chats: {e}")
        return {}

def save_chat(chat_id, messages):
    """Save chat messages to database"""
    if db is not None:
        try:
            db.chats.update_one(
                {"chat_id": chat_id, "username": st.session_state.current_user},
                {"$set": {"messages": messages}},
                upsert=True
            )
            return True
        except Exception as e:
            st.error(f"Error saving chat: {e}")
            return False
    return False

# --- AI INTEGRATION ---
def analyze_mood(text):
    """Analyze mood from text using Claude API"""
    API_KEY = os.getenv("CLAUDE_API_KEY", "")
    if not API_KEY:
        st.error("Claude API key not found")
        return 5
    
    headers = {
        "x-api-key": API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    
    user_message = f"""
    Analyze this journal entry and rate the overall mood from 1-10 (1=very negative, 10=very positive).
    Consider emotional tone, word choice, and sentiment.
    
    Journal Entry: {text}
    
    Return ONLY a number between 1 and 10 with no other text.
    """
    
    payload = {
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 5,
        "messages": [{"role": "user", "content": user_message}]
    }
    
    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload
        )
        if response.status_code == 200:
            score_text = response.json()["content"][0]["text"].strip()
            score = ''.join(filter(str.isdigit, score_text))
            return int(score) if score.isdigit() else 5
        return 5
    except Exception as e:
        st.error(f"Error analyzing mood: {e}")
        return 5

def get_ai_response(message, chat_history):
    """Get response from Claude AI"""
    API_KEY = os.getenv("CLAUDE_API_KEY", "")
    if not API_KEY:
        st.error("Claude API key not found")
        return "I'm having trouble connecting right now."
    
    headers = {
        "x-api-key": API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    
    # Format messages for API
    messages = [{"role": msg["role"], "content": msg["content"]} for msg in chat_history]
    messages.append({"role": "user", "content": message})
    
    system_prompt = f"""
    You are MindEase, a compassionate AI mental health assistant. Be supportive, empathetic, and focused on helping the user process emotions.
    
    Therapeutic Style: {st.session_state.therapy_settings['style']}
    Response Length: {st.session_state.therapy_settings['length']}
    Focus Areas: {', '.join(st.session_state.therapy_settings['focus_areas'])}
    
    Ask thoughtful questions to encourage reflection. Provide evidence-based suggestions when appropriate.
    Keep responses warm and personalized. If serious concerns are expressed, gently suggest professional help.
    """
    
    payload = {
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 600,
        "system": system_prompt,
        "messages": messages
    }
    
    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload
        )
        if response.status_code == 200:
            return response.json()["content"][0]["text"]
        return "I'm having trouble connecting right now."
    except Exception as e:
        st.error(f"Error getting AI response: {e}")
        return "I'm having trouble connecting right now."

def get_ai_reflection(mood_input, journal_input):
    """Get AI reflection on journal entry"""
    API_KEY = os.getenv("CLAUDE_API_KEY", "")
    if not API_KEY:
        st.error("Claude API key not found")
        return "Unable to generate reflection right now."
    
    headers = {
        "x-api-key": API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    
    user_message = f"""
    You are MindEase, a compassionate mental health assistant. The user provided:

    Mood: {mood_input}
    Journal Entry: {journal_input}

    Provide a thoughtful response in 3 sections:
    1. Emotional reflection (validate their feelings)
    2. 2-3 positive insights from their entry
    3. 1-2 gentle, evidence-based suggestions
    
    End with a thoughtful follow-up question. Keep it warm, genuine and concise (max 600 tokens).
    """
    
    payload = {
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 600,
        "messages": [{"role": "user", "content": user_message}]
    }
    
    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload
        )
        if response.status_code == 200:
            return response.json()["content"][0]["text"]
        return "Unable to generate reflection right now."
    except Exception as e:
        st.error(f"Error getting AI reflection: {e}")
        return "Unable to generate reflection right now."

def generate_insights():
    """Generate insights from journal entries"""
    if len(st.session_state.journal_entries) < 3:
        return "Keep journaling! Insights will appear after 3 entries."
    
    recent_entries = [e['journal'] for e in st.session_state.journal_entries[-5:]]
    combined_text = " ".join(recent_entries)
    
    API_KEY = os.getenv("CLAUDE_API_KEY", "")
    if not API_KEY:
        return "Unable to generate insights right now."
    
    headers = {
        "x-api-key": API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    
    user_message = f"""
    Analyze these journal entries and provide 3 concise insights about emotional patterns, themes, and growth opportunities:

    {combined_text}

    Format each insight as a bullet point. Be specific and actionable.
    """
    
    payload = {
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 400,
        "messages": [{"role": "user", "content": user_message}]
    }
    
    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload
        )
        if response.status_code == 200:
            return response.json()["content"][0]["text"]
        return "Unable to generate insights right now."
    except Exception:
        return "Unable to generate insights right now."

# --- VISUALIZATION FUNCTIONS ---
def display_mood_graph():
    """Display interactive mood history graph"""
    if not st.session_state.journal_entries:
        st.info("Start journaling to see your mood graph")
        return
    
    df = pd.DataFrame({
        'Date': [datetime.strptime(e['date'], "%Y-%m-%d") for e in st.session_state.journal_entries],
        'Mood Score': [e['mood_score'] for e in st.session_state.journal_entries],
        'Mood': [e['mood'] for e in st.session_state.journal_entries]
    }).sort_values('Date')
    
    fig = px.line(
        df, x='Date', y='Mood Score',
        title='Your Mood Over Time',
        labels={'Mood Score': 'Mood (1-10)'},
        hover_data=['Mood'],
        color_discrete_sequence=[COLOR_PALETTE['primary']],
        height=400
    )
    
    # Add horizontal reference lines
    fig.add_hline(y=5, line_dash="dot", line_color="gray")
    fig.add_hline(y=7.5, line_dash="dot", line_color="green")
    fig.add_hline(y=2.5, line_dash="dot", line_color="red")
    
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        yaxis_range=[0, 10.5],
        hovermode='x unified'
    )
    
    st.plotly_chart(fig, use_container_width=True)

def mood_calendar_heatmap():
    """Display mood calendar heatmap"""
    if not st.session_state.journal_entries:
        st.info("Journal to see your mood calendar")
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

    # Create heatmap data
    heatmap = np.zeros((12, 31))
    for _, row in df.iterrows():
        heatmap[row['month'] - 1, row['day'] - 1] = row['mood_score']

    # Create custom colormap
    cmap = sns.color_palette("YlGnBu", as_cmap=True)
    
    plt.figure(figsize=(15, 5))
    sns.heatmap(
        heatmap, cmap=cmap, 
        cbar_kws={'label': 'Mood Score'}, 
        linewidths=0.5, 
        vmin=1, vmax=10
    )
    
    plt.yticks(
        np.arange(12) + 0.5, 
        [calendar.month_name[m+1] for m in range(12)], 
        rotation=0
    )
    plt.xticks(np.arange(0, 31), [str(i+1) for i in range(31)], rotation=90)
    plt.title(f"Mood Calendar - {today.year}")
    
    st.pyplot(plt)

def mood_tone_pie_chart():
    """Display mood tone distribution pie chart"""
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

    tone_counts = defaultdict(int)
    for entry in st.session_state.journal_entries:
        tone_counts[get_tone(entry['mood_score'])] += 1

    labels = list(tone_counts.keys())
    values = list(tone_counts.values())
    colors = ["#ff6b6b", "#ffd93d", "#6bcf63"]
    
    fig = px.pie(
        names=labels, values=values,
        color=labels, color_discrete_map={
            "Negative": "#ff6b6b",
            "Neutral": "#ffd93d",
            "Positive": "#6bcf63"
        },
        hole=0.3,
        title="Mood Tone Distribution"
    )
    
    st.plotly_chart(fig, use_container_width=True)

def tag_analysis_chart():
    """Display tag frequency analysis"""
    if not st.session_state.journal_entries:
        return
    
    all_tags = []
    for entry in st.session_state.journal_entries:
        if 'tags' in entry:
            all_tags.extend(entry['tags'])
    
    if not all_tags:
        st.info("Tag your entries to see analysis")
        return
    
    tag_counts = pd.Series(all_tags).value_counts().reset_index()
    tag_counts.columns = ['Tag', 'Count']
    
    fig = px.bar(
        tag_counts, x='Tag', y='Count',
        color='Count', color_continuous_scale='Viridis',
        title='Most Frequent Tags'
    )
    
    st.plotly_chart(fig, use_container_width=True)

# --- COMPONENTS ---
def breathing_exercise():
    """Interactive breathing exercise component"""
    with st.expander("🌬️ Breathing Exercise", expanded=False):
        st.markdown("Adjust your breathing pace:")
        
        breath_duration = st.select_slider(
            "Breath duration (seconds)",
            options=[3, 4, 5, 6, 7, 8],
            value=4,
            format_func=lambda x: f"{x}s"
        )
        
        # Visual guide
        st.markdown(f"""
        <div style="text-align: center; margin: 20px 0;">
            <div style="display: inline-block; text-align: center; margin: 0 10px;">
                <div style="width: 30px; height: 30px; background-color: #4a6fa5; 
                    border-radius: 50%; margin: 0 auto 5px;"></div>
                <small>Inhale</small>
            </div>
            <div style="display: inline-block; font-size: 24px;">→</div>
            <div style="display: inline-block; text-align: center; margin: 0 10px;">
                <div style="width: 30px; height: 30px; background-color: #6b9080; 
                    border-radius: 50%; margin: 0 auto 5px;"></div>
                <small>Exhale</small>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("Begin Breathing Exercise", type="primary", use_container_width=True):
            placeholder = st.empty()
            for i in range(3):  # 3 cycles
                # Inhale
                placeholder.markdown(f"""
                <div style="text-align: center; padding: 20px; background-color: rgba(74, 111, 165, 0.1); border-radius: 12px;">
                    <h3 style="color: #4a6fa5;">Breathe In</h3>
                    <div style="width: 100px; height: 100px; background-color: #4a6fa5; 
                        border-radius: 50%; margin: 20px auto; 
                        animation: breatheIn {breath_duration}s ease-in infinite;"></div>
                    <p>Count to {breath_duration}</p>
                </div>
                """, unsafe_allow_html=True)
                time.sleep(breath_duration)
                
                # Exhale
                placeholder.markdown(f"""
                <div style="text-align: center; padding: 20px; background-color: rgba(107, 144, 128, 0.1); border-radius: 12px;">
                    <h3 style="color: #6b9080;">Breathe Out</h3>
                    <div style="width: 100px; height: 100px; background-color: #6b9080; 
                        border-radius: 50%; margin: 20px auto; 
                        animation: breatheOut {breath_duration}s ease-out infinite;"></div>
                    <p>Count to {breath_duration}</p>
                </div>
                """, unsafe_allow_html=True)
                time.sleep(breath_duration)
            
            placeholder.success("Breathing exercise completed! 🎉")

def show_gratitude_prompt():
    """Show random gratitude prompt"""
    prompts = [
        "What small thing brought you joy today?",
        "Who made a positive impact on you recently?",
        "What personal strength are you grateful for?",
        "What opportunity are you thankful for this week?",
        "What beautiful thing did you notice today?"
    ]
    st.markdown(f"**💖 Gratitude Prompt:** _{random.choice(prompts)}_")

def distraction_free_editor():
    """Toggle distraction-free writing mode"""
    if st.button(
        "🌿 Enter Distraction-Free Mode" if not st.session_state.distraction_free else "← Return",
        type="primary" if not st.session_state.distraction_free else "secondary",
        key="distraction_toggle",
        use_container_width=True
    ):
        st.session_state.distraction_free = not st.session_state.distraction_free
        st.rerun()

    if st.session_state.distraction_free:
        st.markdown("""
        <style>
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        .stApp > div:first-child { padding-top: 1rem; }
        .stTextArea textarea { 
            background-color: #f8f9fa;
            border: none;
            box-shadow: none;
            font-size: 1.1em;
            line-height: 1.6;
            padding: 20px;
        }
        </style>
        """, unsafe_allow_html=True)

        journal_input = st.text_area(
            "Your thoughts...",
            height=400,
            label_visibility="collapsed",
            placeholder="Write freely...\n\nThis space is just for you.",
            key="distraction_free_input"
        )

        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("💾 Save", type="primary", use_container_width=True):
                st.session_state.distraction_free = False
                st.rerun()
        with col2:
            if st.button("❌ Discard", type="secondary", use_container_width=True):
                st.session_state.distraction_free = False
                st.rerun()

def meditation_audio_player():
    """Guided meditation audio player"""
    st.markdown("### 🧘 Guided Meditation")
    meditation_type = st.selectbox(
        "Choose a meditation style:", 
        ["Rain Sounds", "Forest Ambience", "Ocean Waves", "Peace"]
    )
    
    # Placeholder - in a real app, you would have actual audio files
    if st.button("Play Sample Meditation", type="primary"):
        #st.info("In a full implementation, this would play the selected meditation audio")
        # Example of how you might implement this:
        autoplay_audio(f"audio/{meditation_type.lower().replace(' ', '_')}.mp3")

def achievement_badges():
    """Display earned achievement badges"""
    entries = len(st.session_state.journal_entries)
    badges = []
    
    if entries >= 1: badges.append("📘 First Entry")
    if entries >= 5: badges.append("📗 Journal Newbie")
    if entries >= 10: badges.append("📕 Consistent Writer")
    if entries >= 25: badges.append("📙 Reflection Pro")
    if entries >= 50: badges.append("📚 Journaling Master")
    if st.session_state.streak >= 7: badges.append("🔥 7-Day Streak")
    if st.session_state.streak >= 30: badges.append("🌟 Monthly Commitment")
    
    if badges:
        st.markdown("### 🏆 Your Badges")
        cols = st.columns(3)
        for i, badge in enumerate(badges):
            cols[i%3].markdown(f"<div style='text-align: center; margin: 10px;'>{badge}</div>", 
                              unsafe_allow_html=True)
    else:
        st.info("Keep journaling to earn badges!")

def show_streak_progress():
    """Display streak progress with gamification"""
    streak = st.session_state.get("streak", 0)
    
    st.markdown("### 🔥 Your Streak")
    st.progress(min(streak / 30, 1.0), text=f"{streak} day streak")
    
    if streak >= 30:
        st.success("🏅 30-Day Mind Mastery! Amazing consistency.")
    elif streak >= 14:
        st.info("🥈 2-Week Warrior! Keep going.")
    elif streak >= 7:
        st.info("🎖️ 7-Day Streak! You're on a roll.")
    elif streak >= 3:
        st.info("💪 Getting Started! Every day counts.")

def emotional_weather_summary():
    """Generate emotional weather summary"""
    if len(st.session_state.mood_scores) < 3:
        return "Not enough data for a summary yet."
    
    recent = st.session_state.mood_scores[-7:] or st.session_state.mood_scores
    avg_mood = np.mean(recent)
    trend = "↗️ Improving" if recent[-1] > recent[0] else "↘️ Declining" if recent[-1] < recent[0] else "→ Stable"

    if avg_mood > 7:
        emoji = "☀️"
        mood = "Mostly Sunny"
    elif avg_mood >= 5:
        emoji = "⛅"
        mood = "Partly Cloudy"
    else:
        emoji = "🌧️"
        mood = "Rainy Period"

    return f"""
    ### {emoji} Emotional Weather
    **Current:** {mood}  
    **Trend:** {trend}  
    **Avg Mood:** {avg_mood:.1f}/10
    """

# --- PAGE LAYOUTS ---
def login_signup_page():
    """Authentication page layout"""
    st.markdown("<h1 class='main-header'>🔐 Welcome to MindEase</h1>", unsafe_allow_html=True)
    st.markdown("Log in or sign up to continue your mental health journey.")

    tab1, tab2 = st.tabs(["Login", "Sign Up"])

    with tab1:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            login_button = st.form_submit_button("Login")

            if login_button:
                if validate_login(username, password):
                    st.session_state.logged_in = True
                    st.session_state.current_user = username
                    st.session_state.journal_entries = load_journal_entries()
                    st.session_state.chats = load_chats()
                    st.success(f"Welcome back, {username}! 🎉")
                    st.balloons()
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Invalid username or password.")

    with tab2:
        with st.form("signup_form"):
            new_username = st.text_input("Choose Username")
            new_password = st.text_input("Choose Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            email = st.text_input("Email (optional)")
            signup_button = st.form_submit_button("Sign Up")

            if signup_button:
                if new_password != confirm_password:
                    st.error("Passwords don't match!")
                elif len(new_password) < 6:
                    st.error("Password must be at least 6 characters")
                else:
                    success, message = create_user(new_username, new_password, email)
                    if success:
                        st.success(f"{message}! Please log in.")
                        st.balloons()
                    else:
                        st.error(message)

def journal_view():
    """Journal entry page layout"""
    st.markdown("<h1 class='main-header'>📔 Daily Check-in</h1>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1], gap="large")
    
    with col1:
        with st.container(border=True):
            st.markdown("### 🧠 Mood Check-in")
            mood_selection = st.select_slider(
                "How are you feeling today?",
                options=list(MOOD_OPTIONS.keys()),
                value="😐 Neutral"
            )
            mood_input = st.text_area(
                "Tell me more about your mood:",
                placeholder="Describe what's contributing to this mood...",
                height=100
            )
    
    with col2:
        with st.container(border=True):
            st.markdown("### 📖 Today's Journal")
            journal_input = st.text_area(
                "What's on your mind today?",
                placeholder="Reflect on your day, thoughts, or feelings...",
                height=220
            )
    
    # Tags section
    with st.container(border=True):
        st.markdown("### 🏷️ Tags")
        st.caption("Select categories that apply to today's entry")
        
        tags_col1, tags_col2 = st.columns(2)
        with tags_col1:
            work_tag = st.checkbox("Work")
            relationships_tag = st.checkbox("Relationships")
            achievements_tag = st.checkbox("Achievements")
        with tags_col2:
            health_tag = st.checkbox("Health")
            self_care_tag = st.checkbox("Self-care")
            challenges_tag = st.checkbox("Challenges")
        gratitude_tag = st.checkbox("🙏 Gratitude")
        custom_tag = st.text_input("Add custom tag", placeholder="e.g., Creativity")
        
        # Collect selected tags
        selected_tags = []
        if work_tag: selected_tags.append("Work")
        if relationships_tag: selected_tags.append("Relationships")
        if achievements_tag: selected_tags.append("Achievements")
        if health_tag: selected_tags.append("Health")
        if self_care_tag: selected_tags.append("Self-care")
        if challenges_tag: selected_tags.append("Challenges")
        if gratitude_tag: selected_tags.append("Gratitude")
        if custom_tag: selected_tags.append(custom_tag.strip())
    
    # Features section
    features_col1, features_col2 = st.columns(2)
    with features_col1:
        show_gratitude_prompt()
        breathing_exercise()
    with features_col2:
        distraction_free_editor()
        meditation_audio_player()
    
    # Submit journal entry
    if st.button("💫 Get AI Reflection", type="primary", use_container_width=True) and (mood_input or journal_input):
        with st.spinner("MindEase is reflecting with you..."):
            # Calculate mood score
            base_score = MOOD_OPTIONS[mood_selection]["score"]
            text_score = analyze_mood(journal_input) if journal_input else base_score
            mood_score = int((base_score * 0.7) + (text_score * 0.3))
            mood_score = max(1, min(10, mood_score))
            
            # Get AI reflection
            reflection = get_ai_reflection(mood_input, journal_input)
            
            # Create and save entry
            entry_date = datetime.now().strftime("%Y-%m-%d")
            entry_time = datetime.now().strftime("%H:%M")
            new_entry = {
                "username": st.session_state.current_user,
                "date": entry_date,
                "time": entry_time,
                "mood": mood_selection,
                "mood_input": mood_input,
                "journal": journal_input,
                "reflection": reflection,
                "mood_score": mood_score,
                "tags": selected_tags
            }
            
            if save_journal_entry(new_entry):
                st.session_state.journal_entries.append(new_entry)
                st.session_state.mood_scores.append(mood_score)
                update_streak()
                
                # Create chat session
                chat_id = f"{entry_date}_{entry_time}"
                initial_chat = [
                    {"role": "user", "content": f"Mood: {mood_selection}\n\nJournal: {journal_input}"},
                    {"role": "assistant", "content": reflection}
                ]
                
                if save_chat(chat_id, initial_chat):
                    st.session_state.current_chat_id = chat_id
                    st.session_state.chat_history = initial_chat
                    st.session_state.chats[chat_id] = initial_chat
                
                set_background_based_on_mood(mood_score)
                
                # Display reflection
                with st.container(border=True):
                    st.markdown("## 💭 Your Reflection")
                    st.markdown(f"**Mood Score:** {mood_score}/10")
                    st.markdown("---")
                    st.markdown(reflection)
                
                st.success("Entry saved successfully!")
                
                if st.button("💬 Continue conversation", type="primary"):
                    st.session_state.current_view = "chat"
                    st.rerun()

def chat_view():
    """Chat interface page layout"""
    st.markdown("<h1 class='main-header'>💬 MindEase Chat</h1>", unsafe_allow_html=True)
    
    # Load chat if not loaded
    if not st.session_state.chat_history and st.session_state.current_chat_id:
        chat_data = db.chats.find_one({
            "chat_id": st.session_state.current_chat_id,
            "username": st.session_state.current_user
        })
        if chat_data:
            st.session_state.chat_history = chat_data["messages"]
    
    # Display chat messages
    chat_container = st.container(height=500, border=False)
    with chat_container:
        for message in st.session_state.chat_history:
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
    
    # Chat input
    with st.form(key="chat_form", clear_on_submit=True):
        user_input = st.text_area(
            "Your message:",
            key="chat_input",
            height=100,
            placeholder="Type your thoughts here..."
        )
        
        col1, col2 = st.columns([3, 1])
        with col1:
            if st.form_submit_button("Send", type="primary", use_container_width=True):
                if user_input.strip():
                    # Add user message
                    st.session_state.chat_history.append({
                        "role": "user",
                        "content": user_input
                    })
                    
                    # Get AI response
                    with st.spinner("MindEase is thinking..."):
                        ai_response = get_ai_response(user_input, st.session_state.chat_history)
                    
                    # Add AI response
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": ai_response
                    })
                    
                    # Save chat
                    if st.session_state.current_chat_id:
                        save_chat(
                            st.session_state.current_chat_id,
                            st.session_state.chat_history
                        )
                    
                    st.rerun()
        
        with col2:
            if st.form_submit_button("Clear", type="secondary", use_container_width=True):
                st.session_state.chat_input = ""
                st.rerun()
    
    # Therapy settings
    with st.expander("⚙️ Conversation Settings"):
        st.markdown("Customize how MindEase responds:")
        
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.therapy_settings['style'] = st.selectbox(
                "Therapeutic approach:",
                [
                    "Balanced (Default)",
                    "Cognitive Behavioral",
                    "Solution-Focused",
                    "Mindfulness-Based",
                    "Compassion-Focused"
                ]
            )
            
            st.session_state.therapy_settings['length'] = st.select_slider(
                "Response length:",
                options=["Brief", "Balanced", "Detailed"],
                value="Balanced"
            )
        
        with col2:
            st.session_state.therapy_settings['focus_areas'] = st.multiselect(
                "Focus areas:",
                [
                    "Emotional processing",
                    "Problem-solving",
                    "Identifying patterns",
                    "Building resilience",
                    "Stress management"
                ],
                default=["Emotional processing"]
            )
        
        if st.button("Apply Settings", type="primary", use_container_width=True):
            st.success("Settings applied to future responses!")

def analytics_view():
    """Analytics dashboard page layout"""
    st.markdown("<h1 class='main-header'>📊 Mood Analytics</h1>", unsafe_allow_html=True)
    
    # Stats cards
    if st.session_state.journal_entries:
        st.markdown("### 📈 Your Stats")
        col1, col2, col3 = st.columns(3)
        
        num_entries = len(st.session_state.journal_entries)
        avg_mood = sum(e['mood_score'] for e in st.session_state.journal_entries) / num_entries
        streak = st.session_state.streak
        
        with col1:
            with st.container(border=True):
                st.metric("Total Entries", num_entries)
        
        with col2:
            with st.container(border=True):
                st.metric("Average Mood", f"{avg_mood:.1f}/10")
        
        with col3:
            with st.container(border=True):
                st.metric("Current Streak", f"{streak} days")
    
    # Main charts
    tab1, tab2, tab3 = st.tabs(["Mood History", "Mood Calendar", "Tag Analysis"])
    
    with tab1:
        with st.container(border=True):
            display_mood_graph()
    
    with tab2:
        with st.container(border=True):
            mood_calendar_heatmap()
    
    with tab3:
        with st.container(border=True):
            tag_analysis_chart()
    
    # Additional insights
    col1, col2 = st.columns(2)
    
    with col1:
        with st.container(border=True):
            st.markdown("### 🌤️ Emotional Weather")
            st.markdown(emotional_weather_summary())
        
        with st.container(border=True):
            st.markdown("### 🧠 Mood Tone")
            mood_tone_pie_chart()
    
    with col2:
        with st.container(border=True):
            achievement_badges()
        
        with st.container(border=True):
            show_streak_progress()
    
    # AI Insights
    with st.container(border=True):
        st.markdown("### 💡 AI Insights")
        insights = generate_insights()
        st.markdown(insights)
    
    # Data export
    with st.container(border=True):
        st.markdown("### 📤 Export Data")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Export as JSON", type="secondary", use_container_width=True):
                if st.session_state.journal_entries:
                    json_str = json.dumps(st.session_state.journal_entries, indent=2)
                    st.download_button(
                        label="Download JSON",
                        data=json_str,
                        file_name="mindease_journal.json",
                        mime="application/json"
                    )
                else:
                    st.warning("No entries to export")
        
        with col2:
            if st.button("Export as CSV", type="secondary", use_container_width=True):
                if st.session_state.journal_entries:
                    df = pd.DataFrame([{
                        "Date": e.get("date"),
                        "Mood": e.get("mood"),
                        "Mood Score": e.get("mood_score"),
                        "Journal": e.get("journal"),
                        "Tags": ", ".join(e.get("tags", []))
                    } for e in st.session_state.journal_entries])
                    
                    st.download_button(
                        label="Download CSV",
                        data=df.to_csv(index=False),
                        file_name="mindease_journal.csv",
                        mime="text/csv"
                    )
                else:
                    st.warning("No entries to export")

def history_view():
    """Journal history page layout"""
    st.markdown("<h1 class='main-header'>📜 Journal History</h1>", unsafe_allow_html=True)
    
    if not st.session_state.journal_entries:
        st.info("No journal entries yet. Start writing!")
        return
    
    # Filters
    with st.container(border=True):
        st.markdown("### 🔍 Filter Entries")
        
        # Get unique tags
        all_tags = set()
        for entry in st.session_state.journal_entries:
            if 'tags' in entry:
                all_tags.update(entry['tags'])
        
        col1, col2 = st.columns(2)
        with col1:
            selected_tag = st.selectbox("By Tag", ["All"] + sorted(list(all_tags)))
        with col2:
            selected_mood = st.selectbox("By Mood", ["All"] + list(MOOD_OPTIONS.keys()))
    
    # Apply filters
    filtered_entries = st.session_state.journal_entries
    if selected_tag != "All":
        filtered_entries = [e for e in filtered_entries if 'tags' in e and selected_tag in e['tags']]
    if selected_mood != "All":
        filtered_entries = [e for e in filtered_entries if e.get('mood') == selected_mood]
    
    # Display filtered entries
    if not filtered_entries:
        st.info("No entries match your filters")
        return
    
    for entry in sorted(filtered_entries, key=lambda x: x['date'], reverse=True):
        with st.container(border=True):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"### {entry['date']} - {entry.get('mood', 'No mood')}")
                st.progress(entry.get('mood_score', 5)/10, text=f"Mood: {entry.get('mood_score', '?')}/10")
                
                if 'tags' in entry and entry['tags']:
                    st.markdown(f"**Tags:** {', '.join(entry['tags'])}")
            
            with col2:
                if st.button("Open", key=f"open_{entry['date']}", use_container_width=True):
                    st.session_state.current_entry = entry
                    st.rerun()
                
                if st.button("Delete", key=f"delete_{entry['date']}", type="secondary", use_container_width=True):
                    db.journal_entries.delete_one({
                        "date": entry['date'],
                        "username": st.session_state.current_user
                    })
                    st.session_state.journal_entries.remove(entry)
                    st.success("Entry deleted")
                    st.rerun()
    
    # Entry detail view if one is selected
    if 'current_entry' in st.session_state:
        entry = st.session_state.current_entry
        with st.container(border=True):
            st.markdown(f"## {entry['date']} - {entry.get('mood', 'No mood')}")
            
            col1, col2 = st.columns(2)
            with col1:
                if entry.get('mood_input'):
                    with st.expander("Mood Notes"):
                        st.write(entry['mood_input'])
            
            with col2:
                if entry.get('journal'):
                    with st.expander("Journal Entry"):
                        st.write(entry['journal'])
            
            if entry.get('reflection'):
                with st.expander("AI Reflection"):
                    st.write(entry['reflection'])
            
            if st.button("Back to History", type="primary"):
                del st.session_state.current_entry
                st.rerun()
            
            chat_id = f"{entry['date']}_{entry.get('time', '00:00')}"
            if st.button("Continue Conversation", type="secondary"):
                if chat_id in st.session_state.chats:
                    st.session_state.chat_history = st.session_state.chats[chat_id]
                else:
                    initial_chat = [
                        {"role": "user", "content": f"Mood: {entry.get('mood', '')}\n\nJournal: {entry.get('journal', '')}"},
                        {"role": "assistant", "content": entry.get('reflection', "Let's continue exploring this.")}
                    ]
                    st.session_state.chat_history = initial_chat
                    st.session_state.chats[chat_id] = initial_chat
                
                st.session_state.current_chat_id = chat_id
                st.session_state.current_view = "chat"
                st.rerun()

# --- SIDEBAR ---
def sidebar():
    """Application sidebar layout"""
    with st.sidebar:
        st.image("dog.jpeg", width=150)
        st.markdown("<h1 style='text-align: center;'>MindEase</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center;'>Your AI Mental Health Journal</p>", unsafe_allow_html=True)
        
        # Dark mode toggle
        #st.session_state.dark_mode = st.toggle("🌙 Dark Mode", st.session_state.dark_mode)
        
        # User stats
        st.markdown("### 📊 Your Stats")
        if st.session_state.journal_entries:
            last_entry = st.session_state.journal_entries[-1]
            st.metric("Last Mood", f"{last_entry.get('mood_score', '?')}/10")
        st.metric("🔥 Streak", f"{st.session_state.streak} days")
        
        # Navigation
        st.markdown("### 🧭 Navigation")
        views = {
            "📝 Journal": "journal",
            "💬 Chat": "chat",
            "📊 Analytics": "analytics",
            "📜 History": "history"
        }
        
        for name, view in views.items():
            if st.button(name, use_container_width=True):
                st.session_state.current_view = view
                st.rerun()
        
        # Recent chats
        if st.session_state.chats:
            st.markdown("### 💬 Recent Chats")
            for chat_id in sorted(st.session_state.chats.keys(), reverse=True)[:3]:
                date = chat_id.split("_")[0]
                if st.button(f"{date}", key=f"sidebar_{chat_id}", use_container_width=True):
                    st.session_state.current_chat_id = chat_id
                    st.session_state.chat_history = st.session_state.chats[chat_id]
                    st.session_state.current_view = "chat"
                    st.rerun()
        
        # Resources
        st.markdown("### 🧰 Resources")
        with st.expander("Crisis Resources"):
            st.markdown("""
            - [7 Cups Online Therapy](https://www.7cups.com/)
            """)
        
        # Logout
        if st.session_state.logged_in:
            if st.button("🚪 Logout", type="secondary", use_container_width=True):
                st.session_state.logged_in = False
                st.session_state.current_user = None
                st.rerun()

# --- MAIN APP ---
# Custom CSS
st.markdown(f"""
<style>
:root {{
    --primary: {COLOR_PALETTE['primary']};
    --secondary: {COLOR_PALETTE['secondary']};
    --accent: {COLOR_PALETTE['accent']};
    --background: {COLOR_PALETTE['background']};
    --text: {COLOR_PALETTE['text']};
    --dark-bg: {COLOR_PALETTE['dark_bg']};
    --dark-text: {COLOR_PALETTE['dark_text']};
}}

body, .stApp {{
    font-family: 'Inter', sans-serif;
    color: var(--text);
    background-color: var(--background);
}}

h1, h2, h3, h4 {{
    font-family: 'Playfair Display', serif;
    color: var(--text);
}}

.stButton>button {{
    border-radius: 12px;
    padding: 10px 20px;
    font-weight: 600;
    border: none;
    background: linear-gradient(to right, var(--secondary), var(--primary));
    color: white;
    transition: 0.3s ease;
}}

.stButton>button:hover {{
    background: linear-gradient(to right, var(--primary), var(--secondary));
    box-shadow: 0 6px 12px rgba(0,0,0,0.1);
    transform: scale(1.02);
}}

.chat-message {{
    padding: 1rem;
    border-radius: 12px;
    margin-bottom: 1rem;
}}

.chat-message.user {{
    background-color: rgba(74, 111, 165, 0.1);
}}

.chat-message.assistant {{
    background-color: rgba(107, 144, 128, 0.1);
}}

[data-theme="dark"] {{
    --text: var(--dark-text);
    --background: var(--dark-bg);
}}

[data-theme="dark"] .stTextInput input,
[data-theme="dark"] .stTextArea textarea {{
    background-color: #2a2a3e;
    color: var(--dark-text);
    border-color: #444;
}}
</style>
""", unsafe_allow_html=True)

# Dark mode application
if st.session_state.dark_mode:
    st.markdown(f"""
    <style>
    .stApp {{
        background-color: {COLOR_PALETTE['dark_bg']};
        color: {COLOR_PALETTE['dark_text']};
    }}
    </style>
    """, unsafe_allow_html=True)

# Authentication check
if not st.session_state.logged_in:
    login_signup_page()
    st.stop()

# Update streak if needed
today_str = datetime.now().strftime("%Y-%m-%d")
if st.session_state.last_entry_date != today_str:
    update_streak()

# Load data if not loaded
if not st.session_state.journal_entries:
    st.session_state.journal_entries = load_journal_entries()
if not st.session_state.chats:
    st.session_state.chats = load_chats()

# Main app layout
sidebar()

# Display current view
if st.session_state.current_view == "journal":
    journal_view()
elif st.session_state.current_view == "chat":
    chat_view()
elif st.session_state.current_view == "analytics":
    analytics_view()
elif st.session_state.current_view == "history":
    history_view()

# Footer
st.markdown("---")
st.markdown(
    """<div style='text-align: center; color: gray;'>
    MindEase v2.0 | Not a substitute for professional care
    </div>""", 
    unsafe_allow_html=True
)
