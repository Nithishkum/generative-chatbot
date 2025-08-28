import streamlit as st
import json
import os
import time
from html import escape
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.llms import Ollama
from fuzzywuzzy import fuzz

# ========================
# Constants
# ========================
USER_DATA_FILE = "users.json"
HISTORY_FILE = "chat_history.json"
CACHE_FILE = "caches.json"

# ========================
# Helper Functions
# ========================
def load_json(file_path):
    if not os.path.exists(file_path):
        return {}
    with open(file_path, "r") as f:
        return json.load(f)

def load_cache_lines(file_path):
    cache = {}
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    cache[entry["question"]] = entry["answer"]
                except:
                    pass
    return cache

def save_json(file_path, data):
    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)

def append_cache(file_path, question, answer):
    with open(file_path, "a") as f:
        json.dump({"question": question, "answer": answer}, f)
        f.write("\n")

# ========================
# Auth Functions
# ========================
def login(username, password):
    users = load_json(USER_DATA_FILE)
    return username in users and users[username] == password

def register(username, password):
    users = load_json(USER_DATA_FILE)
    if username in users:
        return False
    users[username] = password
    save_json(USER_DATA_FILE, users)
    return True

# ========================
# LangChain setup
# ========================
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant. Your name is Nithish personal assistant. You were created by Nithish."),
    ("user", "user query:{query}")
])
llm = Ollama(model="llama3")
output_parser = StrOutputParser()
chain = prompt | llm | output_parser

# ========================
# Streamlit Config
# ========================
st.set_page_config(page_title="N-GPT", layout="centered")

# ========================
# Session states
# ========================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "cache" not in st.session_state:
    st.session_state.cache = load_cache_lines(CACHE_FILE)
if "typing" not in st.session_state:
    st.session_state.typing = False
if "processing" not in st.session_state:
    st.session_state.processing = False

# ========================
# CSS Styling
# ========================
st.markdown("""
    <style>
        .centered-container {
            display: flex;
            justify-content: center;
            align-items: center;
            height: 10vh;
        }
        .chat-message {
            background-color:black;
            color:white;
            padding: 0.75em;
            border-radius: 10px;
            margin-bottom: 0.5em;
            max-width: 85%;
            text-align: left;
            word-wrap: break-word;
        }
        .chat-container {
            max-height: 70vh;
            overflow-y: auto;
            padding-right: 1em;
            margin-bottom: 80px;
        }
        .fixed-input-container {
            position: fixed;
            bottom: 20px;
            left: 20px;
            right: 20px;
            z-index: 9999;
            background-color: white;
            padding: 0;
            box-shadow: 0 0 8px rgba(0,0,0,0.2);
            border-radius: 10px;
        }
        .stTextInput > div > label {
            display: none;
        }
        .stTextInput {
            margin-bottom: 0 !important;
        }
        pre {
            background-color: #222;
            color: #fff;
            padding: 0.5em;
            border-radius: 5px;
            overflow-x: auto;
        }
    </style>
""", unsafe_allow_html=True)

# ========================
# Login/Register Page
# ========================
if not st.session_state.logged_in:
    st.markdown('<div class="centered-container">', unsafe_allow_html=True)
    with st.container():
        st.title("🔐 Login or Register")
        option = st.radio("Select an option:", ["Login", "Register"])
        username = st.text_input("Username", key="login_user")
        password = st.text_input("Password", type="password", key="login_pass")

        if st.button(option):
            if option == "Login":
                if login(username, password):
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.chat_history = load_json(HISTORY_FILE).get(username, [])
                    st.rerun()
                else:
                    st.error("Invalid credentials.")
            else:
                if register(username, password):
                    st.success("Registration successful. You can now log in.")
                else:
                    st.error("Username already exists.")
    st.markdown('</div>', unsafe_allow_html=True)

# ========================
# Main Chat UI
# ========================
else:
    col1, col2, col3 = st.columns([9,1,1])
    with col1:
        st.markdown("<h1 style='margin: 0;'>🤖 N-GPT</h1>", unsafe_allow_html=True)
    
    chat_col, history_col = st.columns([3, 1])
    
    with history_col:
        st.sidebar.title(" History")
        for i, (query, _) in enumerate(reversed(st.session_state.chat_history), start=1):
            st.sidebar.markdown(f"**{i}.** {query[:100]}{'...' if len(query) > 100 else ''}")

    with chat_col:
        st.markdown("<div class='chat-container'>", unsafe_allow_html=True)
        for i, (query, answer) in enumerate(st.session_state.chat_history):
            display_query = f"<pre style='max-height:200px; overflow:auto;'>{escape(query)}</pre>" if len(query) > 500 else escape(query)
            st.markdown(f"<div class='chat-message' style='background-color:#2a2a33;margin-left:150px'>{display_query}</div>", unsafe_allow_html=True)
        
            if i == len(st.session_state.chat_history) - 1 and st.session_state.typing:
                placeholder = st.empty()
                typing_response = ""
                for char in answer:
                    typing_response += escape(char)
                    placeholder.markdown(
                        f"<div class='chat-message' style='background-color:black'>{typing_response}</div>",
                        unsafe_allow_html=True
                    )
                    time.sleep(0.01)
                st.session_state.typing = False
            else:
                st.markdown(
                    f"<div class='chat-message' style='background-color:black'>{escape(answer)}</div>",
                    unsafe_allow_html=True
                )
        st.markdown("</div>", unsafe_allow_html=True)

    user_prompt = st.chat_input("Type your message...")

    if user_prompt:
        st.session_state.chat_history.append((user_prompt, ""))
        st.session_state.processing = True
        st.rerun()

    colb1, colb2, colb3 = st.columns([12, 1, 1])
    with colb2:
        if st.button("🗑", help="delete chat", use_container_width=True):
            st.session_state.chat_history = []
            all_history = load_json(HISTORY_FILE)
            all_history[st.session_state.username] = []
            save_json(HISTORY_FILE, all_history)
            st.rerun()
    with colb3:
        if st.button("⎋", help="log out", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.chat_history = []
            st.rerun()

    # ============================================================
    # Show continuous "Analyzing..." animation with rotating clock
    # ============================================================
    if st.session_state.chat_history and st.session_state.chat_history[-1][1] == "":
        last_query = st.session_state.chat_history[-1][0]

        if st.session_state.processing:
            placeholder = st.empty()
           
                
            st.markdown("""
                <div class="wave-text">
                    <span>A</span>
                    <span>n</span>
                    <span>a</span>
                    <span>l</span>
                    <span>y</span>
                    <span>z</span>
                    <span>i</span>
                    <span>n</span>
                    <span>g</span>
                    <span>.</span>
                    <span>.</span>
                    <span>.</span>
                    <span>.</span>
                    <span>.</span>
                </div>

                <style>
                    .wave-text {
                        font-size: 18px;
                        font-weight: 200;
                        isplay: inline-flex;
                        color:white;
                    }

                    .wave-text span {
                        animation: waveFade 1.2s infinite;
                        display: inline-block;
                        opacity: 0.2;
                    }

                    /* Wave + Crossfade Effect */
                    @keyframes waveFade {
                        0%, 100% {
                            transform: translateY(0);
                            opacity: 0.2;
                        }
                        50% {
                            transform: translateY(-3px);
                            opacity: 1;
                        }
                    }

                    /* Delay each letter for wave */
                    .wave-text span:nth-child(1) { animation-delay: 0s; }
                    .wave-text span:nth-child(2) { animation-delay: 0.1s; }
                    .wave-text span:nth-child(3) { animation-delay: 0.2s; }
                    .wave-text span:nth-child(4) { animation-delay: 0.3s; }
                    .wave-text span:nth-child(5) { animation-delay: 0.4s; }
                    .wave-text span:nth-child(6) { animation-delay: 0.5s; }
                    .wave-text span:nth-child(7) { animation-delay: 0.6s; }
                    .wave-text span:nth-child(8) { animation-delay: 0.7s; }
                    .wave-text span:nth-child(9) { animation-delay: 0.8s; }
                    .wave-text span:nth-child(10) { animation-delay: 0.9s; }
                    .wave-text span:nth-child(11) { animation-delay: 1s; }
                    .wave-text span:nth-child(12) { animation-delay: 1.1s; }
                    .wave-text span:nth-child(13) { animation-delay: 1.2s; }
                    .wave-text span:nth-child(14) { animation-delay: 1.3s; }
                </style>
            """, unsafe_allow_html=True)
            time.sleep(0.5)

            # --- Process query ---
            matched_key = None
            
            for k in st.session_state.cache:
                if fuzz.ratio(k.lower(), last_query.lower()) > 75:
                    matched_key = k
                    break

            if matched_key:
                response = st.session_state.cache[matched_key]
            else:
                response = chain.invoke({"query": last_query})
                st.session_state.cache[last_query] = response
                append_cache(CACHE_FILE, last_query, response)


            all_history = load_json(HISTORY_FILE)
            user_history = all_history.get(st.session_state.username, [])
            if user_history and user_history[-1][0] == last_query:
                user_history[-1] = (last_query, response)
            else:
                user_history.append((last_query, response))
            all_history[st.session_state.username] = user_history
            save_json(HISTORY_FILE, all_history)

            st.session_state.chat_history = user_history
            st.session_state.typing = True
            st.session_state.processing = False
            st.rerun()
