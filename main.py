import streamlit as st
from streamlit_chat import message
from PyPDF2 import PdfReader
from docx import Document
import pandas as pd
import requests
import json
import time
import base64
from pathlib import Path

# Function definitions
def get_image_base64(image_path):
    if image_path.exists():
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return None

def get_avatar_image():
    avatar_path = Path(__file__).parent / "image" / "Bathandwa Picture.jpg"
    return get_image_base64(avatar_path)

def get_logo_image():
    logo_path = Path(__file__).parent / "image" / "Raznet-logo.jpg"
    return get_image_base64(logo_path)

# Function to interact with Ollama API
@st.cache_resource
def initialize_model():
    try:
        response = requests.get('http://localhost:11434/api/tags')
        if response.status_code == 200:
            return True
        return False
    except Exception as e:
        st.error(f"Error connecting to Ollama: {str(e)}")
        return False

def generate_response(prompt, temperature=0.7, max_tokens=500):
    try:
        response = requests.post('http://localhost:11434/api/generate',
            json={
                'model': 'deepseek-r1:1.5b',
                'prompt': prompt,
                'stream': False,
                'temperature': temperature,
                'max_tokens': max_tokens
            })
        if response.status_code == 200:
            return response.json()['response']
        else:
            return f"Error: {response.status_code} - {response.text}"
    except Exception as e:
        return f"Error generating response: {str(e)}"

def get_file_preview(file):
    try:
        if file.type == "application/pdf":
            return "PDF Document Preview"
        elif file.type == "text/plain":
            return file.getvalue().decode()[:1000] + "..."
        elif "excel" in file.type or "csv" in file.type:
            df = pd.read_csv(file) if "csv" in file.type else pd.read_excel(file)
            return df.head().to_html()
        else:
            return "Preview not available for this file type"
    except Exception as e:
        return f"Error generating preview: {str(e)}"

def process_file(uploaded_file):
    if uploaded_file.type == "application/pdf":
        pdf_reader = PdfReader(uploaded_file)
        text = "\n".join(page.extract_text() for page in pdf_reader.pages)
    elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        doc = Document(uploaded_file)
        text = "\n".join(paragraph.text for paragraph in doc.paragraphs)
    elif "excel" in uploaded_file.type or "csv" in uploaded_file.type:
        df = pd.read_csv(uploaded_file) if "csv" in uploaded_file.type else pd.read_excel(uploaded_file)
        text = df.to_string()
    elif uploaded_file.type == "text/plain":
        text = uploaded_file.read().decode("utf-8")
    else:
        text = "Unsupported file type!"
    return text

def deepseek_inference(query, context=""):
    if not initialize_model():
        return "Cannot connect to Ollama. Please make sure the Ollama service is running."

    try:
        temperature = st.session_state.temperature
        max_tokens = st.session_state.max_tokens

        if context:
            prompt = f"""Context: {context}

Question: {query}

Please provide a detailed answer based on the context above. If the answer cannot be found in the context, please say so."""
        else:
            prompt = f"""Question: {query}

Please provide a detailed answer. Feel free to use markdown formatting for better readability."""

        response = generate_response(prompt, temperature, max_tokens)
        return response.strip()
    except Exception as e:
        error_msg = f"Error generating response: {str(e)}"
        st.error(error_msg)
        return error_msg

def handle_send():
    if st.session_state.user_message.strip():  
        context = process_file(uploaded_file) if uploaded_file else ""
        user_message = st.session_state.user_message
        
        # Show thinking process if enabled
        if st.session_state.show_thinking:
            with st.spinner("Thinking..."):
                response = deepseek_inference(user_message, context)
        else:
            response = deepseek_inference(user_message, context)
        
        # Extract only the final response if thinking is hidden
        if not st.session_state.show_thinking and "<think>" in response:
            response = response.split("</think>")[-1].strip()
        
        st.session_state.messages.append({
            "user": user_message,
            "bot": response,
            "timestamp": time.time()
        })
        st.session_state.user_message = ""

# Page configuration
st.set_page_config(
    page_title="Raznet Chat",
    page_icon="🤖",
    layout="wide"
)

# Initialize session state variables
if "messages" not in st.session_state:
    st.session_state.messages = []
if "temperature" not in st.session_state:
    st.session_state.temperature = 0.7
if "max_tokens" not in st.session_state:
    st.session_state.max_tokens = 500
if "user_message" not in st.session_state:
    st.session_state.user_message = ""
if "show_thinking" not in st.session_state:
    st.session_state.show_thinking = True

# Get images
avatar_img = get_avatar_image()
logo_img = get_logo_image()

# Custom CSS for modern styling
st.markdown(f"""
    <style>
    /* Main container styling */
    .main {{
        background-color: #1E1E1E;
    }}
    
    /* Avatar styling */
    .avatar-image {{
        width: 40px;
        height: 40px;
        border-radius: 50%;
        object-fit: cover;
        transition: all 0.3s ease;
    }}
    
    .thinking .avatar-image {{
        width: 40px;
        height: 40px;
    }}
    
    /* Chat message styling */
    .chat-message {{
        padding: 1.5rem;
        border-radius: 0.75rem;
        margin-bottom: 1rem;
        display: flex;
        gap: 1rem;
        align-items: flex-start;
    }}
    .chat-message.user {{
        background-color: #2E2E2E;
    }}
    .chat-message.bot {{
        background-color: #1E1E1E;
        border: 1px solid #383838;
    }}
    
    /* Thinking indicator */
    .thinking-dots {{
        display: inline-block;
        margin-left: 4px;
    }}
    .thinking-dots::after {{
        content: '';
        animation: thinking 1.5s infinite;
    }}
    @keyframes thinking {{
        0% {{ content: ''; }}
        25% {{ content: '.'; }}
        50% {{ content: '..'; }}
        75% {{ content: '...'; }}
        100% {{ content: ''; }}
    }}
    
    /* Input field styling */
    .stTextArea>div>div>textarea {{
        background-color: #2E2E2E !important;
        color: white !important;
        border: none !important;
        padding: 12px !important;
        border-radius: 8px !important;
        min-height: 100px !important;
        font-size: 16px !important;
        resize: none !important;
    }}
    
    /* Button styling */
    .stButton>button {{
        background-color: #0E76FD !important;
        color: white !important;
        border: none !important;
        padding: 0.5rem 1rem !important;
        border-radius: 8px !important;
        height: 45px !important;
        width: 120px !important;
        transition: all 0.3s !important;
        margin: 10px auto !important;
        display: block !important;
    }}
    .stButton>button:hover {{
        background-color: #0056D6 !important;
    }}
    
    /* Sidebar styling */
    .css-1d391kg {{
        background-color: #1E1E1E !important;
    }}
    .sidebar .sidebar-content {{
        background-color: #1E1E1E !important;
    }}
    
    /* File uploader styling */
    .uploadedFile {{
        background-color: #2E2E2E;
        padding: 12px;
        border-radius: 8px;
        margin: 10px 0;
    }}
    
    /* Slider styling */
    .stSlider>div>div {{
        background-color: #0E76FD !important;
    }}
    
    /* Footer styling */
    .footer-text {{
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: #1E1E1E;
        color: #888;
        text-align: center;
        padding: 10px;
        font-size: 14px;
        border-top: 1px solid #383838;
        z-index: 1000;
    }}
    
    /* Hide Streamlit branding */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    
    /* Custom container padding */
    .main .block-container {{
        padding-bottom: 100px;
    }}
    </style>
    """, unsafe_allow_html=True)

# Main chat interface
col1, col2, col3 = st.columns([1, 3, 1])

with col2:
    # Display welcome message with Raznet logo
    if not st.session_state.messages:
        if logo_img:
            st.markdown(f"""
                <div class="chat-message bot">
                    <img src="data:image/jpeg;base64,{logo_img}" class="avatar-image">
                    <div>Hi, I'm Raznet! How can I assist you today?</div>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.error("Logo image not found. Please check the image path.")

    # Chat container with padding for footer
    chat_container = st.container()
    with chat_container:
        # Add padding at the bottom for footer
        st.markdown('<div style="margin-bottom: 60px;">', unsafe_allow_html=True)
        
        for msg in st.session_state.messages:
            if msg["user"]:
                message(msg["user"], is_user=True, key=f"user_{msg['timestamp']}")
            
            # Process bot message based on thinking toggle
            bot_message = msg["bot"]
            if not st.session_state.show_thinking and "<think>" in bot_message:
                bot_message = bot_message.split("</think>")[-1].strip()
            
            # Use profile picture for bot messages
            if avatar_img:
                thinking_class = "thinking" if st.session_state.show_thinking else ""
                st.markdown(f"""
                    <div class="chat-message bot {thinking_class}">
                        <img src="data:image/jpeg;base64,{avatar_img}" class="avatar-image">
                        <div>{bot_message}</div>
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.error("Profile picture not found for bot message")
        
        st.markdown('</div>', unsafe_allow_html=True)

    # Input container
    input_container = st.container()
    with input_container:
        st.markdown('<div style="margin-bottom: 80px;">', unsafe_allow_html=True)
        st.text_area("", placeholder="Message Raznet...", key="user_message", height=100)
        st.button("Send", on_click=handle_send)
        st.markdown('</div>', unsafe_allow_html=True)

# Sidebar with advanced options
with st.sidebar:
    st.markdown("### Settings")
    st.session_state.temperature = st.slider(
        "Temperature",
        min_value=0.1,
        max_value=1.0,
        value=st.session_state.temperature,
        step=0.1,
        help="Higher values make the output more random, lower values make it more deterministic"
    )
    
    st.session_state.max_tokens = st.slider(
        "Max Tokens",
        min_value=100,
        max_value=2000,
        value=st.session_state.max_tokens,
        step=100,
        help="Maximum number of tokens to generate"
    )
    
    st.session_state.show_thinking = st.toggle(
        "Show Thinking Process",
        value=st.session_state.show_thinking,
        help="Show or hide the model's thinking process"
    )

    # Add chat history section with custom styling
    st.markdown("""
        <style>
        .chat-history {
            margin-top: 20px;
            padding: 10px;
            border-radius: 8px;
            background-color: #2E2E2E;
        }
        .history-item {
            padding: 8px;
            margin: 5px 0;
            border-radius: 4px;
            background-color: #383838;
            font-size: 0.9em;
            word-wrap: break-word;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown("### Chat History")
    if st.session_state.messages:
        st.markdown('<div class="chat-history">', unsafe_allow_html=True)
        for msg in st.session_state.messages:
            # Display only user questions as history items
            if "user" in msg and msg["user"].strip():
                st.markdown(f'<div class="history-item">{msg["user"]}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        if st.button("Clear Chat History", type="primary", help="Delete all chat messages"):
            st.session_state.messages = []
            st.rerun()
    else:
        st.markdown("No chat history yet")

    # File uploader
    st.markdown("### Upload File")
    uploaded_file = st.file_uploader(
        "Upload a document",
        type=["pdf", "txt", "docx", "csv", "xlsx"],
        help="Upload a document to chat about its contents"
    )

    if uploaded_file:
        st.success(f"File uploaded: {uploaded_file.name}")
        with st.expander("File Preview"):
            preview = get_file_preview(uploaded_file)
            st.write(preview)

# Footer with white heart
st.markdown(
    '<p class="footer-text">Built with 🤍 by Raz using Streamlit, Ollama & Deepseek</p>',
    unsafe_allow_html=True
)