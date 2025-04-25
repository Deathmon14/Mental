import streamlit as st
import requests
import os
import datetime
from dotenv import load_dotenv
import pandas as pd
import matplotlib.pyplot as plt
import time

# Load environment variables
load_dotenv()

# App configuration
st.set_page_config(
    page_title="MindEase: AI Mental Health Companion",
    page_icon="🧠",
    layout="centered",
    initial_sidebar_state="expanded"
)

# Constants
API_KEY = os.getenv("CLAUDE_API_KEY")
CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"

# Initialize session state
if 'history' not in st.session_state:
    st.session_state.history = []
if 'mood_history' not in st.session_state:
    st.session_state.mood_history = {}

# CSS styling
st.markdown("""
    <style>
        .stTextArea textarea {
            min-height: 100px !important;
        }
        .stButton>button {
            background-color: #4CAF50;
            color: white;
            border-radius: 5px;
            padding: 0.5rem 1rem;
            width: 100%;
        }
        .stButton>button:hover {
            background-color: #45a049;
        }
        .sidebar .sidebar-content {
            background-color: #f8f9fa;
        }
        .reportview-container .main .block-container {
            padding-top: 2rem;
        }
        h1 {
            color: #4CAF50;
        }
    </style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3048/3048127.png", width=100)
    st.title("MindEase")
    st.markdown("Your AI-powered mental health companion")
    st.markdown("---")
    
    st.subheader("Quick Resources")
    if st.button("Crisis Hotlines"):
        with st.expander("Emergency Contacts"):
            st.write("""
            - **National Suicide Prevention Lifeline**: 988 (US)
            - **Crisis Text Line**: Text HOME to 741741 (US)
            - **Samaritans**: 116 123 (UK)
            - **Lifeline Australia**: 13 11 14
            """)
    
    st.markdown("---")
    st.subheader("Wellness Tips")
    if st.button("Quick Coping Strategies"):
        with st.expander("Try these techniques"):
            st.write("""
            - **5-4-3-2-1 Grounding**: Notice 5 things you see, 4 you can touch, 3 you hear, 2 you smell, 1 you taste
            - **Box Breathing**: Inhale 4s, hold 4s, exhale 4s, hold 4s
            - **Progressive Muscle Relaxation**: Tense and release muscles from toes to head
            """)
    
    st.markdown("---")
    st.write("© 2023 MindEase | Privacy Policy")

# Main app
st.title("🧠 MindEase: AI Mental Health Journal")
st.caption("Track your mood, reflect on your day, and receive AI-powered support")

# Tab layout
tab1, tab2, tab3 = st.tabs(["Daily Check-In", "Mood History", "Wellness Resources"])

with tab1:
    st.subheader("How are you feeling today?")
    
    # Mood slider
    mood_level = st.select_slider(
        "Rate your overall mood:",
        options=["😭 Terrible", "😞 Poor", "😐 Neutral", "🙂 Good", "😁 Excellent"],
        value="😐 Neutral"
    )
    
    # Journal entry
    mood_input = st.text_area(
        "Describe your mood in more detail:",
        placeholder="e.g., Feeling anxious about work but grateful for my friends..."
    )
    
    journal_input = st.text_area(
        "What's on your mind today?",
        placeholder="e.g., Had a productive morning meeting but feeling overwhelmed by upcoming deadlines..."
    )
    
    # Tags
    tags = st.multiselect(
        "Add relevant tags:",
        ["Work", "School", "Relationships", "Health", "Family", "Finances", "Sleep", "Exercise"],
        help="Select categories that relate to your current state"
    )
    
    # Submit button
    if st.button("Reflect with AI", type="primary"):
        if mood_input or journal_input:
            with st.spinner("MindEase is reflecting with your thoughts..."):
                # Record entry
                entry = {
                    "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "mood": mood_level,
                    "mood_detail": mood_input,
                    "entry": journal_input,
                    "tags": tags
                }
                st.session_state.history.append(entry)
                
                # Track mood for history
                today = datetime.date.today().strftime("%Y-%m-%d")
                mood_value = ["😭 Terrible", "😞 Poor", "😐 Neutral", "🙂 Good", "😁 Excellent"].index(mood_level) + 1
                st.session_state.mood_history[today] = mood_value
                
                # Call Claude API
                headers = {
                    "x-api-key": API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                }

                user_message = f"""
You are a compassionate mental health assistant named MindEase. The user has shared their current emotional state:

Mood Rating: {mood_level}
Mood Description: {mood_input}
Journal Entry: {journal_input}
Relevant Tags: {', '.join(tags) if tags else 'None'}

Respond with:
1. A brief empathetic reflection acknowledging their feelings
2. Analysis of potential patterns or noteworthy aspects
3. 2-3 personalized suggestions for coping or self-care
4. An encouraging closing statement

Keep the tone warm, professional, and supportive. If concerning content appears, gently suggest professional help but don't diagnose.
"""

                payload = {
                    "model": "claude-3-5-sonnet-20241022",
                    "max_tokens": 800,
                    "messages": [
                        {"role": "user", "content": user_message}
                    ]
                }

                try:
                    response = requests.post(CLAUDE_API_URL, headers=headers, json=payload, timeout=10)
                    
                    if response.status_code == 200:
                        reply = response.json()["content"][0]["text"]
                        
                        # Store response
                        entry["ai_response"] = reply
                        
                        # Display response with animation
                        response_container = st.empty()
                        full_response = ""
                        for chunk in reply.split():
                            full_response += chunk + " "
                            time.sleep(0.05)
                            response_container.markdown(f"""
                            <div style='background-color: #f0f2f6; padding: 1rem; border-radius: 10px;'>
                                <strong>MindEase:</strong> {full_response}
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.error(f"API Error: {response.status_code} - {response.text}")
                except Exception as e:
                    st.error(f"Connection error: {str(e)}")
        else:
            st.warning("Please share at least some thoughts about your mood or day")

with tab2:
    st.subheader("Your Mood Over Time")
    
    if st.session_state.mood_history:
        # Convert mood history to DataFrame
        df = pd.DataFrame.from_dict(
            st.session_state.mood_history, 
            orient='index', 
            columns=['Mood Level']
        )
        df.index = pd.to_datetime(df.index)
        df.sort_index(inplace=True)
        
        # Plot
        fig, ax = plt.subplots(figsize=(10, 4))
        df['Mood Level'].plot(
            marker='o',
            linestyle='-',
            color='#4CAF50',
            ax=ax
        )
        ax.set_ylim(0, 6)
        ax.set_yticks([1, 2, 3, 4, 5])
        ax.set_yticklabels(["Terrible", "Poor", "Neutral", "Good", "Excellent"])
        ax.set_title("Your Mood Trend")
        ax.grid(True, linestyle='--', alpha=0.7)
        st.pyplot(fig)
        
        # Show recent entries
        st.subheader("Recent Journal Entries")
        for entry in reversed(st.session_state.history[-5:]):
            with st.expander(f"{entry['date']} - {entry['mood']}"):
                st.write(f"**Mood Details:** {entry.get('mood_detail', '')}")
                st.write(f"**Journal Entry:** {entry.get('entry', '')}")
                if entry.get('ai_response'):
                    st.markdown(f"""
                    <div style='background-color: #f0f2f6; padding: 1rem; border-radius: 10px; margin-top: 1rem;'>
                        <strong>MindEase Response:</strong> {entry['ai_response']}
                    </div>
                    """, unsafe_allow_html=True)
    else:
        st.info("No mood history yet. Complete your first check-in to see your trends.")

with tab3:
    st.subheader("Personalized Wellness Resources")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🧘 Meditation Guides")
        st.video("https://www.youtube.com/watch?v=inpok4MKVLM")
        st.write("5-minute mindfulness meditation")
        
        st.markdown("### 📚 Recommended Reading")
        st.write("- *The Happiness Trap* by Russ Harris")
        st.write("- *Atomic Habits* by James Clear")
    
    with col2:
        st.markdown("### 🏋️‍♀️ Physical Wellness")
        st.write("**Movement Breaks**")
        st.video("https://www.youtube.com/watch?v=UItWltVZZmE")
        
        st.markdown("### 🎧 Relaxation Sounds")
        st.audio("https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3")
        st.write("White noise for focus or sleep")

# Footer
st.markdown("---")
st.caption("MindEase is an AI companion, not a substitute for professional mental health care. If you're in crisis, please contact a licensed professional.")