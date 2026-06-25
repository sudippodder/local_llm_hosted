import streamlit as st
import requests
import uuid
import os
from dotenv import load_dotenv
import database as db

# Load configuration from .env file
load_dotenv()

# Set Streamlit Page Configuration
st.set_page_config(
    page_title="NsLLM Chat Studio",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject Custom CSS for premium styling (glassmorphism details, scrollbars, gradients)
st.markdown("""
<style>
    /* Styling scrollbars for webkit browsers */
    ::-webkit-scrollbar {
        width: 6px;
        height: 6px;
    }
    ::-webkit-scrollbar-track {
        background: transparent;
    }
    ::-webkit-scrollbar-thumb {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 10px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: rgba(255, 255, 255, 0.25);
    }

    /* Style the sidebar */
    section[data-testid="stSidebar"] {
        background-color: #0f111a !important;
        border-right: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    /* Sleek container styles for suggestions and feature logs */
    .feature-card {
        padding: 20px;
        border-radius: 12px;
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.06);
        margin-bottom: 20px;
    }

    /* Custom Gradient text */
    .gradient-header {
        background: linear-gradient(135deg, #00f2fe 0%, #4facfe 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
    }
    
    /* Inline action buttons custom look */
    div[data-testid="column"] button {
        padding: 0.25rem 0.5rem !important;
        min-height: auto !important;
    }
</style>
""", unsafe_allow_html=True)

# Initialize the SQLite Database
db.init_db()

# Initialize Streamlit session states for LLM connection overrides
if "api_url" not in st.session_state:
    st.session_state.api_url = os.getenv("LLM_API_URL", "https://webhook.nstechservice.shop/api/generate")
if "api_key" not in st.session_state:
    st.session_state.api_key = os.getenv("LLM_API_KEY", "my_secure_api_key_123")
if "model_name" not in st.session_state:
    st.session_state.model_name = os.getenv("LLM_MODEL", "qwen2.5:7b")

# Session state for tracking the selected thread ID
if "current_thread_id" not in st.session_state:
    st.session_state.current_thread_id = None

# Session state for managing thread rename interactions
if "rename_thread_id" not in st.session_state:
    st.session_state.rename_thread_id = None

def format_chatml_prompt(messages):
    """Formats the list of SQLite message rows into a ChatML string for Qwen-2.5 context parsing."""
    prompt = (
        "<|im_start|>system\n"
        "You are NsLLM, a helpful, respectful, and highly competent AI coding and task assistant. "
        "Provide thorough, formatted, and clear answers. Use markdown formatting for code and math blocks.\n"
        "<|im_end|>\n"
    )
    for msg in messages:
        role = msg["role"]
        content = msg["content"]
        prompt += f"<|im_start|>{role}\n{content}\n<|im_end|>\n"
    
    # Append the prompt completion start token to trigger assistant generation
    prompt += "<|im_start|>assistant\n"
    return prompt

def call_llm_api(prompt_str):
    """Issues a blocking POST request to the custom LLM API endpoint."""
    url = st.session_state.api_url
    api_key = st.session_state.api_key
    model = st.session_state.model_name

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "prompt": prompt_str,
        "stream": False
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        result_json = response.json()
        return result_json.get("response", "Error: The model response field was empty.")
    except requests.exceptions.Timeout:
        return "⚠️ **Connection Error**: The request timed out. The server might be starting up or overloaded. Please try again."
    except requests.exceptions.ConnectionError:
        return "⚠️ **Network Error**: Could not connect to the LLM backend. Please verify your connection URL or server status."
    except Exception as e:
        return f"⚠️ **Error Occurred**: {str(e)}"

# ----------------- Sidebar Structure -----------------
with st.sidebar:
    st.markdown("<h2 style='text-align: center; margin-bottom: 2px;' class='gradient-header'>💬 NsLLM Chat</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #666; font-size: 0.85rem; margin-bottom: 20px;'>Persistent SQLite Chat Interface</p>", unsafe_allow_html=True)

    # New Chat Thread Trigger
    if st.button("➕ New Chat Thread", use_container_width=True, type="primary"):
        new_id = str(uuid.uuid4())
        db.create_thread(new_id, "New Chat")
        st.session_state.current_thread_id = new_id
        st.session_state.rename_thread_id = None
        st.rerun()

    st.write("---")

    # Thread History Listings
    st.markdown("### 🗂️ Conversation Threads")
    threads = db.get_all_threads()

    if not threads:
        st.info("No active threads. Launch a chat to get started.")
    else:
        for t in threads:
            t_id = t["id"]
            t_title = t["title"]
            is_active = (st.session_state.current_thread_id == t_id)

            # Check if this thread is currently selected for renaming
            if st.session_state.rename_thread_id == t_id:
                # Rename Form (inline)
                col_rename, col_save = st.columns([0.75, 0.25])
                with col_rename:
                    new_val = st.text_input(
                        "Rename Title",
                        value=t_title,
                        key=f"ren_input_{t_id}",
                        label_visibility="collapsed"
                    )
                with col_save:
                    if st.button("✔️", key=f"save_btn_{t_id}", help="Apply title"):
                        if new_val.strip():
                            db.rename_thread(t_id, new_val.strip())
                        st.session_state.rename_thread_id = None
                        st.rerun()
            else:
                # Normal Thread Item Row
                # 0.70 width for Thread selection button, 0.15 for edit icon, 0.15 for delete icon
                col_title, col_edit, col_del = st.columns([0.7, 0.15, 0.15])
                
                with col_title:
                    btn_style = "primary" if is_active else "secondary"
                    # Render selection button
                    if st.button(t_title, key=f"sel_{t_id}", use_container_width=True, type=btn_style):
                        st.session_state.current_thread_id = t_id
                        st.session_state.rename_thread_id = None
                        st.rerun()
                
                with col_edit:
                    if st.button("✏️", key=f"edit_{t_id}", help="Rename thread"):
                        st.session_state.rename_thread_id = t_id
                        st.rerun()

                with col_del:
                    if st.button("🗑️", key=f"del_{t_id}", help="Delete thread"):
                        db.delete_thread(t_id)
                        # Reset current thread if the active one was deleted
                        if st.session_state.current_thread_id == t_id:
                            st.session_state.current_thread_id = None
                        st.session_state.rename_thread_id = None
                        st.rerun()

    st.write("---")

    # API Connection Configurations Override Expander
    with st.expander("⚙️ Connection Settings", expanded=False):
        st.text_input("Endpoint URL", key="api_url")
        st.text_input("Authorization Key", key="api_key", type="password")
        st.text_input("Model ID", key="model_name")
        st.caption("Adjust these values to connect to alternate servers or models.")

# ----------------- Main Chat Window -----------------
# 1. Landing Screen if no Thread is Selected
if st.session_state.current_thread_id is None:
    st.markdown("""
        <div style='margin-top: 40px; margin-bottom: 20px;'>
            <h1 class='gradient-header' style='font-size: 2.8rem;'>NsLLM Studio</h1>
            <p style='color: #888; font-size: 1.1rem;'>A premium streamlit chat interface with SQLite database persistence.</p>
        </div>
    """, unsafe_allow_html=True)

    # Feature Grid
    st.markdown("""
        <div class="feature-card">
            <h4 style="margin-top: 0; color: #4facfe;">💡 Feature Overview</h4>
            <ul style="margin-bottom: 0; padding-left: 20px; line-height: 1.6;">
                <li><b>SQLite Session Memory</b>: Conversations are automatically saved to local SQLite tables and mapped to persistent storage volumes.</li>
                <li><b>Context Integration</b>: Previous chat runs are formatted in ChatML structures to provide memory window capabilities.</li>
                <li><b>Thread Tracking Controls</b>: Instantly create, inline rename, or wipe out threads from the sidebar navigator.</li>
                <li><b>Container-ready</b>: Ready to execute inside Docker networks, avoiding system library differences.</li>
            </ul>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("### ⚡ Prompt Suggestions")
    
    # Prompt suggestions list
    suggestions = [
        "Write a short poem about a server",
        "Give me a sample SQLite connection code in Python",
        "Explain how Docker volumes help with database persistence",
        "What are the benefits of Streamlit for AI prototypes?"
    ]

    # Display suggestions as nice clickables
    cols = st.columns(2)
    for index, suggestion in enumerate(suggestions):
        col = cols[index % 2]
        if col.button(suggestion, key=f"sug_{index}", use_container_width=True):
            # When a suggestion is selected, auto-create a thread and trigger the flow
            new_id = str(uuid.uuid4())
            auto_title = suggestion[:25] + "..." if len(suggestion) > 25 else suggestion
            db.create_thread(new_id, auto_title)
            db.add_message(new_id, "user", suggestion)
            st.session_state.current_thread_id = new_id
            
            # Request response from API immediately
            with st.spinner("Generating initial response..."):
                formatted_prompt = format_chatml_prompt([{"role": "user", "content": suggestion}])
                llm_response = call_llm_api(formatted_prompt)
                db.add_message(new_id, "assistant", llm_response)
            
            st.rerun()

else:
    # 2. Chat history rendering for active conversation thread
    active_id = st.session_state.current_thread_id
    
    # Get active thread details to show title
    all_t = db.get_all_threads()
    active_title = next((t["title"] for t in all_t if t["id"] == active_id), "Active Conversation")

    # Layout for main chat area header
    st.markdown(f"<h2 style='margin-bottom: 20px;'>💬 {active_title}</h2>", unsafe_allow_html=True)

    # Retrieve and show all messages belonging to this thread
    chat_history = db.get_messages(active_id)
    for message in chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# 3. Floating input widget
prompt = st.chat_input("Message NsLLM...")

# Handle chat input submissions
if prompt:
    # Create thread on the fly if user messages from landing screen
    if st.session_state.current_thread_id is None:
        active_id = str(uuid.uuid4())
        auto_title = prompt[:25] + "..." if len(prompt) > 25 else prompt
        db.create_thread(active_id, auto_title)
        st.session_state.current_thread_id = active_id
        active_title = auto_title
    else:
        active_id = st.session_state.current_thread_id
        # Retrieve active thread details to see if we should override default name
        all_t = db.get_all_threads()
        active_title = next((t["title"] for t in all_t if t["id"] == active_id), "New Chat")
        if active_title == "New Chat":
            auto_title = prompt[:25] + "..." if len(prompt) > 25 else prompt
            db.rename_thread(active_id, auto_title)
            active_title = auto_title

    # Save user message to SQLite db
    db.add_message(active_id, "user", prompt)

    # Render User Message immediately
    with st.chat_message("user"):
        st.markdown(prompt)

    # Query LLM endpoint and render Assistant Response
    with st.chat_message("assistant"):
        response_box = st.empty()
        with st.spinner("NsLLM is writing..."):
            # Gather all historical messages including the new user prompt
            full_context = db.get_messages(active_id)
            chatml_prompt = format_chatml_prompt(full_context)
            llm_response = call_llm_api(chatml_prompt)
        response_box.markdown(llm_response)

    # Save Assistant Response to SQLite db
    db.add_message(active_id, "assistant", llm_response)
    
    # Rerun to sync database values and reset the chat input widget state
    st.rerun()
