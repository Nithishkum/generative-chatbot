import streamlit as st
import json
import os
import time
from html import escape
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.llms import Ollama
from fuzzywuzzy import fuzz
import speech_recognition as sr
import uuid
import logging
import base64
import requests
import io
from PIL import Image

#==========================
# Set up logging
#==========================

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

USER_DATA_FILE = "users.json"
HISTORY_FILE = "chat_history.json"
CACHE_FILE = "caches.json"
IMAGE_FOLDER = "generated_images"

def load_json(file_path):
    if not os.path.exists(file_path):
        logger.debug(f"File {file_path} does not exist, returning empty dict.")
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
                except Exception as e:
                    logger.warning(f"Failed to parse cache line: {e}")
    return cache

def save_json(file_path, data):
    try:
        with open(file_path, "w") as f:
            json.dump(data, f, indent=4)
        logger.debug(f"Saved data to {file_path}")
    except Exception as e:
        logger.error(f"Failed to save JSON to {file_path}: {e}")

def append_cache(file_path, question, answer):
    try:
        with open(file_path, "a") as f:
            json.dump({"question": question, "answer": answer}, f)
            f.write("\n")
        logger.debug(f"Appended cache to {file_path}")
    except Exception as e:
        logger.error(f"Failed to append cache to {file_path}: {e}")

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

#==========================
# LangChain setup
#==========================

prompt_template = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant. Your name is Nithish personal assistant. You were created by Nithish. Your favourite mam is emmimal epsiba from st josephs college"),
    ("user", "user query:{query}")
])
llm = Ollama(model="llama3")
output_parser = StrOutputParser()
chain = prompt_template | llm | output_parser

def generate_and_save_image(prompt):
    try:
        logger.debug("Starting Stability AI image generation for prompt: %s", prompt)
        api_key = os.getenv("STABILITY_API_KEY", "YOUR-API-HERE")
        if not api_key or not api_key.startswith("sk-"):
            error_msg = "Invalid or missing Stability AI API key. Please set STABILITY_API_KEY."
            st.error(error_msg)
            logger.error(error_msg)
            return None
        url = "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
        }
        payload = {
            "text_prompts": [
                {"text": prompt},
                {"text": "low quality, blurry", "weight": -1.0}
            ],
            "cfg_scale": 7.5,
            "steps": 30,
            "samples": 1,
            "width": 1024,
            "height": 1024
        }
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code != 200:
            error_msg = f"Stability API error {response.status_code}: {response.text}"
            st.error(error_msg)
            logger.error(error_msg)
            return None
        data = response.json()
        image_base64 = data["artifacts"][0]["base64"]
        image_bytes = io.BytesIO(base64.b64decode(image_base64))
        image = Image.open(image_bytes)
        os.makedirs(IMAGE_FOLDER, exist_ok=True)
        filename = f"{uuid.uuid4()}.png"
        file_path = os.path.join(IMAGE_FOLDER, filename)
        image.save(file_path)
        logger.debug("Image saved to: %s", file_path)
        return file_path
    except Exception as e:
        st.error(f"Image generation failed: {str(e)}")
        logger.exception("Image generation error: %s", str(e))
        return None
#==========================
# Streamlit Config and State
#==========================

st.set_page_config(page_title="N-GPT", layout="centered",page_icon="assets/gen.png")

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
if "image_processing" not in st.session_state:
    st.session_state.image_processing = False
if "prompt" not in st.session_state:
    st.session_state.prompt = ""
if "show_image_dialog" not in st.session_state:
    st.session_state.show_image_dialog = False
if "image_prompt" not in st.session_state:
    st.session_state.image_prompt = ""

st.markdown("""
    <style>
        .chat-message {
            background-color: black;
            color: white;
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
            margin-bottom: 120px;
        }
        pre {
            background-color: #222;
            color: #fff;
            padding: 0.5em;
            border-radius: 5px;
            overflow-x: auto;
        }
        .generated-image {
            max-width: 100%;
            border-radius: 10px;
            margin-top: 10px;
        }
        .wave-text {
            font-size: 18px;
            font-weight: 200;
            display: inline-flex;
            color: white;
            width: 100%;
            padding: 10px;
        }
        .wave-text span {
            animation: waveFade 1.2s infinite;
            display: inline-block;
            opacity: 0.2;
        }
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

#==========================
# Login / Register UI
#==========================

if not st.session_state.logged_in:
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
    
#==========================
# Main Chat UI
#==========================

else:
    
    st.title("N-GPT")

    # Show logged-in username (Top-Right Corner)
    if st.session_state.username:
        st.markdown(
            f"""
            <style>
                .username-box {{
                    position: absolute;
                    top: -55px;
                    right: 20px;
                    background-color: ;
                    color: white;
                    padding: 8px 15px;
                    border-radius: 12px;
                    font-weight: bold;
                    z-index: 9999;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.2);
                    font-size: 20px;
                    border:1px solid white;
                }}
            </style>
            <div class="username-box">
                 Welcome back !!! {st.session_state.username}
            </div>
            """,
            unsafe_allow_html=True
        )

    st.sidebar.title("History")
    for i, (entry, _) in enumerate(reversed(st.session_state.chat_history), start=1):
        query = entry["query"] if isinstance(entry, dict) else entry
        st.sidebar.markdown(f"**{i}.** {query[:100]}{'...' if len(query) > 100 else ''}")


    st.markdown("<div class='chat-container'>", unsafe_allow_html=True)
    for i, (entry, response) in enumerate(st.session_state.chat_history):
        query = entry["query"] if isinstance(entry, dict) else entry
        display_query = f"<pre style='max-height:200px; overflow:auto;'>{query}</pre>" if len(query) > 500 else query
        st.markdown(f"<div class='chat-message' style='background-color:#2a2a33;margin-left:150px'>{display_query}</div>", unsafe_allow_html=True)
        if isinstance(response, dict) and response.get("type") == "image":
            st.markdown(f"<div class='chat-message' style='background-color:black'>Generated Image:</div>", unsafe_allow_html=True)
            try:
                st.image(response["file_path"], caption="Generated Image", use_container_width=True)
                logger.debug(f"Displayed image: {response['file_path']}")
            except Exception as e:
                st.error(f"Failed to display image: {e}")
                logger.error(f"Failed to display image at {response['file_path']}: {e}")
        elif isinstance(response, str):
            if i == len(st.session_state.chat_history) - 1 and st.session_state.typing:
                placeholder = st.empty()
                typing_response = ""
                for char in response:
                    typing_response += escape(char)
                    placeholder.markdown(
                        f"<div class='chat-message' style='background-color:black'>{typing_response}</div>",
                        unsafe_allow_html=True
                    )
                    time.sleep(0.01)
                st.session_state.typing = False
            else:
                st.markdown(
                    f"<div class='chat-message' style='background-color:black'>{response}</div>",
                    unsafe_allow_html=True
                )
        else:
            logger.warning(f"Unexpected response type: {type(response)}")
            st.markdown(
                f"<div class='chat-message' style='background-color:black'>Error: Invalid response format</div>",
                unsafe_allow_html=True
            )
    st.markdown("</div>", unsafe_allow_html=True)

    #==========================
    # Voice recognition function
    #==========================

    def speech_to_text():
        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            st.info("Listening... Speak now.")
            recognizer.adjust_for_ambient_noise(source)
            try:
                audio = recognizer.listen(source, timeout=5)
                st.info("Processing audio...")
                text = recognizer.recognize_google(audio)
                return text
            except sr.WaitTimeoutError:
                st.error("No speech detected within 5 seconds.")
                return ""
            except sr.UnknownValueError:
                st.error("Could not understand the audio.")
                return ""
            except sr.RequestError as e:
                st.error(f"Speech recognition error: {e}")
                return ""
    
    #==========================
    # Chat input
    #==========================

    prompt = st.chat_input("Type your message...")

    # Buttons row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        voice_button = st.button("🎙️", key="voice_button", help="Record voice input")
    with col2:
        image_button = st.button("🏞️", key="image_button", help="Generate image from prompt")
    with col3:
        delete_button = st.button("🗑️", key="delete_button", help="Delete chat")
    with col4:
        logout_button = st.button("⎋", key="logout_button", help="Log out")

    #==========================
    # Handle chat input submission
    #==========================

    if prompt:
        logger.debug("chat_input submitted: %s", prompt)
        st.session_state.prompt = prompt
        st.session_state.chat_history.append(({"query": prompt, "type": "text"}, ""))
        st.session_state.processing = True
        st.rerun()
    #==========================
    # Handle voice input button
    #==========================

    if voice_button:
        transcribed_text = speech_to_text()
        if transcribed_text:
            logger.debug("Voice input received: %s", transcribed_text)
            st.session_state.prompt = transcribed_text
            st.session_state.chat_history.append(({"query": transcribed_text, "type": "text"}, ""))
            st.session_state.processing = True
            st.rerun()
    #==========================
    # Handle image button - open dialog
    #==========================

    if image_button:
        st.session_state.show_image_dialog = True

    # Image generation modal dialog
    if st.session_state.show_image_dialog:
        with st.container():
            st.subheader("🖼️ Generate Image")
            st.session_state.image_prompt = st.text_input(
                "Enter image prompt for generation:",
                value=st.session_state.image_prompt
            )
            col1, col2 = st.columns(2)
            with col1:
                gen_image = st.button("Generate", key="generate_img_btn")
            with col2:
                cancel_image = st.button("Cancel", key="cancel_img_btn")

            if gen_image:
                if st.session_state.image_prompt.strip() != "":
                    st.session_state.image_processing = True
                    with st.spinner("Generating image..."):
                        file_path = generate_and_save_image(st.session_state.image_prompt)
                    st.session_state.show_image_dialog = False
                    if file_path:
                        response = {"type": "image", "file_path": file_path}
                        all_history = load_json(HISTORY_FILE)
                        user_history = all_history.get(st.session_state.username, [])
                        user_history.append(({"query": st.session_state.image_prompt, "type": "text"}, response))
                        all_history[st.session_state.username] = user_history
                        save_json(HISTORY_FILE, all_history)
                        st.session_state.chat_history = user_history
                        st.image(file_path, caption="Generated Image", use_container_width=True)

                        # Wave animation while generating image
                        st.markdown("""
                            <div class="wave-text">
                                <span>G</span><span>e</span><span>n</span><span>e</span><span>r</span><span>a</span><span>t</span><span>i</span><span>n</span><span>g</span><span> </span><span>I</span><span>m</span><span>a</span><span>g</span><span>e</span><span>...</span>
                            </div>
                        """, unsafe_allow_html=True)

                    else:
                        st.error("Failed to generate or save image.")
                    st.session_state.image_prompt = ""
                    st.session_state.image_processing = False
                else:
                    st.error("Please enter a prompt before generating an image.")

            if cancel_image:
                st.session_state.show_image_dialog = False
                st.session_state.image_prompt = ""
    #==========================
    # Handle delete button
    #==========================

    if delete_button:
        st.session_state.chat_history = []
        all_history = load_json(HISTORY_FILE)
        all_history[st.session_state.username] = []
        save_json(HISTORY_FILE, all_history)
        st.rerun()

    #==========================
    # Handle logout button
    #==========================

    if logout_button:
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.chat_history = []
        st.session_state.prompt = ""
        st.rerun()

    #==========================
    # Main text generation with analyzing animation
    #==========================

    if st.session_state.chat_history and st.session_state.chat_history[-1][1] == "" and st.session_state.processing:
        last_entry = st.session_state.chat_history[-1][0]
        last_query = last_entry["query"] if isinstance(last_entry, dict) else last_entry

        #==========================
        # Show analyzing wave animation
        #==========================

        st.markdown("""
            <div class="wave-text">
                <span>A</span><span>n</span><span>a</span><span>l</span><span>y</span><span>z</span><span>i</span><span>n</span><span>g</span><span>.</span><span>.</span><span>.</span>
            </div>
        """, unsafe_allow_html=True)

        matched_key = None
        for k in st.session_state.cache:
            if fuzz.ratio(k.lower(), last_query.lower()) > 80:
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
        if user_history and user_history[-1][0]["query"] == last_query:
            user_history[-1] = ({"query": last_query, "type": "text"}, response)
        else:
            user_history.append(({"query": last_query, "type": "text"}, response))
        all_history[st.session_state.username] = user_history
        save_json(HISTORY_FILE, all_history)

        st.session_state.chat_history = user_history
        st.session_state.typing = True
        st.session_state.processing = False
        st.session_state.prompt = ""
        st.rerun()
