"""
BanglaTruth Frontend - Streamlit UI
Modern, professional fact-checking interface with jury voting system
"""

import streamlit as st
import requests
import pandas as pd
import json
from datetime import datetime
import os

# ============================================================================
# PAGE CONFIG
# ============================================================================

st.set_page_config(
    page_title="BanglaTruth v2.0",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# CUSTOM CSS
# ============================================================================

st.markdown("""
    <style>
    :root {
        --primary: #007bff;
        --success: #28a745;
        --danger: #dc3545;
        --warning: #ffc107;
        --info: #17a2b8;
    }

    .verdict-box {
        padding: 40px;
        border-radius: 15px;
        border-left: 8px solid;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        margin: 20px 0;
    }

    .verdict-true { border-left-color: #28a745; background: linear-gradient(135deg, #d4edda 0%, #28a745 100%); }
    .verdict-false { border-left-color: #dc3545; background: linear-gradient(135deg, #f8d7da 0%, #dc3545 100%); }
    .verdict-misleading { border-left-color: #ffc107; background: linear-gradient(135deg, #fff3cd 0%, #ffc107 100%); }
    .verdict-contested { border-left-color: #fd7e14; background: linear-gradient(135deg, #ffe5cc 0%, #fd7e14 100%); }

    .stButton>button {
        width: 100%;
        padding: 12px 24px;
        border-radius: 10px;
        font-weight: 700;
        font-size: 16px;
        border: none;
        box-shadow: 0 4px 10px rgba(0,0,0,0.2);
        transition: all 0.3s;
    }

    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 15px rgba(0,0,0,0.3);
    }

    .metric-card {
        background: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.08);
        text-align: center;
    }

    .evidence-for { border-left: 4px solid #28a745; padding-left: 15px; }
    .evidence-against { border-left: 4px solid #dc3545; padding-left: 15px; }
    .evidence-neutral { border-left: 4px solid #17a2b8; padding-left: 15px; }

    .sidebar-content {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
    }

    .history-row:hover {
        background-color: #f5f5f5;
    }

    .loading-text {
        font-size: 18px;
        font-weight: 600;
        color: #007bff;
    }
    </style>
""", unsafe_allow_html=True)

# ============================================================================
# SESSION STATE
# ============================================================================

if "history" not in st.session_state:
    st.session_state.history = []

if "api_url" not in st.session_state:
    st.session_state.api_url = os.getenv("BACKEND_URL", "http://localhost:8000")

if "current_result" not in st.session_state:
    st.session_state.current_result = None

if "current_claim" not in st.session_state:
    st.session_state.current_claim = ""

if "reg_done" not in st.session_state:
    st.session_state.reg_done = False

if "user" not in st.session_state:
    st.session_state.user = None

if "user_email" not in st.session_state:
    st.session_state.user_email = None

if "access_token" not in st.session_state:
    st.session_state.access_token = None

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_api_base():
    return st.session_state.api_url

def call_backend(endpoint, payload):
    try:
        url = f"{get_api_base()}{endpoint}"
        response = requests.post(url, json=payload, timeout=60)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Backend Error {response.status_code}: {response.text}")
            return None
    except requests.exceptions.ConnectionError:
        st.error(f"❌ Cannot connect to backend at {get_api_base()}")
        st.info("Is the backend running? Try: `python backend_api.py`")
        return None
    except requests.exceptions.Timeout:
        st.error("⏱️ Backend request timed out. Please try again.")
        return None
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        return None

def get_verdict_color(verdict):
    colors = {
        "TRUE": "green",
        "FALSE": "red",
        "MISLEADING": "orange",
        "CONTESTED": "orange",
        "UNVERIFIED": "gray",
        "ERROR": "gray"
    }
    return colors.get(verdict, "gray")

def get_verdict_emoji(verdict):
    emojis = {
        "TRUE": "✅",
        "FALSE": "❌",
        "MISLEADING": "⚠️",
        "CONTESTED": "⚖️",
        "UNVERIFIED": "❓",
        "ERROR": "🔴"
    }
    return emojis.get(verdict, "❓")

# ============================================================================
# SIDEBAR
# ============================================================================

st.sidebar.markdown("""
    <div class="sidebar-content">
        <h1>🔍 BanglaTruth v2.0</h1>
        <p><strong>AI-Powered Fact-Checking</strong></p>
        <p style="font-size: 12px; opacity: 0.9;">Multiple LLMs vote on the truth</p>
    </div>
""", unsafe_allow_html=True)

st.sidebar.divider()

page = st.sidebar.radio(
    "🧭 Navigation",
    ["🔍 Fact Check", "📊 Dashboard", "⚙️ Settings"],
    label_visibility="visible"
)
st.sidebar.divider()

# User info + logout
if st.session_state.user_email:
    st.sidebar.markdown(f"👤 **{st.session_state.user_email}**")
    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state.user = None
        st.session_state.user_email = None
        st.session_state.access_token = None
        st.session_state.current_result = None
        st.session_state.history = []
        st.rerun()
st.sidebar.divider()

st.sidebar.markdown("### 🔌 Connection Status")
try:
    health_response = requests.get(f"{get_api_base()}/health", timeout=5)
    if health_response.status_code == 200:
        st.sidebar.success("✅ Backend Online")
        st.sidebar.caption(f"URL: {get_api_base()}")
    else:
        st.sidebar.warning("⚠️ Backend Offline")
except:
    st.sidebar.error("❌ Cannot reach backend")
    st.sidebar.caption(f"Tried: {get_api_base()}")

# ============================================================================
# PAGE: FACT CHECK
# ============================================================================
# ============================================================================
# AUTH GATE — show login if not logged in
# ============================================================================

def show_login_page():
    st.title("🔍 BanglaTruth")
    st.markdown("Bangladesh's AI-powered fact-checking platform | বাংলাদেশের তথ্য যাচাই প্ল্যাটফর্ম")
    st.divider()

    default_tab = 0 if not st.session_state.get("reg_done") else 0
    tab1, tab2 = st.tabs(["🔐 Login", "📝 Register"])

    with tab1:
        st.markdown("### Welcome back")
        email = st.text_input("Email", key="login_email", placeholder="you@example.com")
        password = st.text_input("Password", type="password", key="login_password", placeholder="••••••••")

        if st.button("Login →", key="login_btn", use_container_width=True):
            if not email.strip() or not password.strip():
                st.warning("Please enter email and password.")
            else:
                with st.spinner("Logging in..."):
                    try:
                        response = requests.post(
                            f"{get_api_base()}/auth/login",
                            json={"email": email, "password": password},
                            timeout=10
                        )
                        if response.status_code == 200:
                            data = response.json()
                            st.session_state.user = data["user_id"]
                            st.session_state.user_email = data["email"]
                            st.session_state.access_token = data["access_token"]
                            st.success("✅ Logged in successfully!")
                            st.rerun()
                        else:
                            st.error("❌ Invalid email or password.")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")

    with tab2:
        st.markdown("### Create an account")
        reg_email = st.text_input("Email", key="reg_email", placeholder="you@example.com")
        reg_password = st.text_input("Password", type="password", key="reg_password", placeholder="Min 6 characters")
        reg_password2 = st.text_input("Confirm Password", type="password", key="reg_password2", placeholder="Repeat password")

        if st.button("Register →", key="reg_btn", use_container_width=True):
            if not reg_email.strip() or not reg_password.strip():
                st.warning("Please fill in all fields.")
            elif reg_password != reg_password2:
                st.error("❌ Passwords do not match.")
            elif len(reg_password) < 6:
                st.error("❌ Password must be at least 6 characters.")
            else:
                with st.spinner("Creating account..."):
                    try:
                        response = requests.post(
                            f"{get_api_base()}/auth/register",
                            json={"email": reg_email, "password": reg_password},
                            timeout=10
                        )
                        if response.status_code == 200:
                            st.success(" Account created! Check your email then login.")
                            st.session_state.reg_done = True
                            st.rerun()
                        else:
                            detail = response.json().get("detail", "Registration failed.")
                            st.error(f"❌ {detail}")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")

if st.session_state.user is None:
    show_login_page()
    st.stop()
if page == "🔍 Fact Check":

    st.title("🔍 AI Truth Jury")
    st.markdown("Enter a claim and let multiple AI models vote on its veracity.")
    st.divider()

    col1, col2 = st.columns([3, 1])

    with col1:
        input_mode = st.radio(
            "Input Type",
            ["📝 Paste Claim", "🔗 Extract from URL"],
            horizontal=True,
            label_visibility="collapsed"
        )

    if input_mode == "🔗 Extract from URL":
        url_input = st.text_input(
            "Enter URL",
            placeholder="https://example.com/news/article",
            label_visibility="collapsed"
        )

        if st.button("🔗 Extract Claims", use_container_width=True):
            if not url_input.strip():
                st.warning("Please enter a URL")
            else:
                with st.spinner("📰 Extracting article content..."):
                    response = call_backend("/analyze-article", {"url": url_input})
                    if response:
                        st.success("✅ Article extracted!")
                        st.session_state.extracted_claims = response.get("claims", [])
                        st.info(f"Found {len(response.get('claims', []))} claims in article")

        if hasattr(st.session_state, 'extracted_claims'):
            claim_text = st.selectbox(
                "Select a claim to verify",
                st.session_state.extracted_claims,
                label_visibility="collapsed"
            )
        else:
            claim_text = st.text_area(
                "Or paste a claim manually",
                height=120,
                label_visibility="collapsed",
                placeholder="Enter a claim to fact-check..."
            )
    else:
        claim_text = st.text_area(
            "Enter your claim",
            height=150,
            placeholder="e.g., 'The Earth is flat' or 'Bangladesh has more than 170 million people'",
            label_visibility="collapsed"
        )

    st.divider()

    with st.expander("⚙️ Advanced Settings", expanded=True):
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.markdown("**🤖 AI Model**")
            selected_model = st.selectbox(
                "Choose model",
                ["Both", "Llama 3.3", "Llama 3.1"],
                label_visibility="collapsed",
                key="model_select"
            )

        with col2:
            st.markdown("**🔎 Analysis Mode**")
            deep_mode = st.toggle(
                "Deep Analysis (slower, more accurate)",
                value=False,
                label_visibility="collapsed"
            )

        with col3:
            st.markdown("**📰 Reporter Mode**")
            reporter_mode = st.toggle(
                "Include investigation details",
                value=False,
                label_visibility="collapsed"
            )

        with col4:
            st.markdown("**🔍 Search Engine**")
            search_engine = st.radio(
                "Engine",
                ["DuckDuckGo", "Google"],
                horizontal=True,
                label_visibility="collapsed",
                key="engine_select"
            )

    st.divider()

    if st.button(
            f"{'⚡ Quick Check' if not deep_mode else '🔬 Deep Analysis'} {'📰' if reporter_mode else ''}",
            use_container_width=True,
            type="primary"
    ):
        if not claim_text.strip():
            st.error("❌ Please enter a claim first")
        else:
            st.session_state.current_claim = claim_text

            with st.spinner(f"{'🔬' if deep_mode else '⚡'} Processing claim through jury..."):
                payload = {
                    "claim": claim_text,
                    "deep": deep_mode,
                    "reporter": reporter_mode,
                    "engine": search_engine.lower(),
                    "selected_model": selected_model.lower(),
                    "lang_code": "en"
                }

                result = call_backend("/fact-check", payload)

                if result:
                    st.session_state.current_result = result
                    st.session_state.history.append({
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "claim": claim_text[:80],
                        "verdict": result["final_verdict"],
                        "confidence": result["avg_confidence"]
                    })

    # Display Results
    if st.session_state.current_result:
        result = st.session_state.current_result
        claim_text_display = st.session_state.current_claim

        st.divider()

        # related images — shown first
        with st.spinner("🖼️ Finding related images..."):
            try:
                img_response = requests.get(
                    f"{get_api_base()}/images",
                    params={"q": claim_text_display[:80]},
                    timeout=10
                )
                if img_response.status_code == 200:
                    images = img_response.json().get("images", [])
                    if images:
                        st.markdown("### 🖼️ Related Images")
                        img_cols = st.columns(3)
                        for idx, img in enumerate(images[:3]):
                            with img_cols[idx]:
                                st.image(img, width=200)
                        st.divider()
                    else:
                        st.caption("🖼️ No relevant images found for this claim.")
                        st.divider()
            except Exception:
                pass

        st.markdown("## 📋 Jury Verdict")

        verdict = result["final_verdict"]
        confidence = result["avg_confidence"]
        emoji = get_verdict_emoji(verdict)

        verdict_class = f"verdict-{verdict.lower()}"

        st.markdown(f"""
            <div class="verdict-box {verdict_class}">
                <h1 style="margin: 0; color: white; text-shadow: 0 2px 4px rgba(0,0,0,0.3);">
                    {emoji} <strong>{verdict}</strong>
                </h1>
                <p style="margin: 10px 0 0 0; font-size: 18px; color: white;">
                    <strong>Confidence: {confidence}%</strong>
                </p>
            </div>
        """, unsafe_allow_html=True)

        st.progress(min(confidence / 100, 1.0))

        st.divider()

        # Individual Model Results
        st.markdown("## 🤖 Individual Jury Members")

        cols = st.columns(len(result["individual"]))

        for i, model_result in enumerate(result["individual"]):
            with cols[i]:
                model_name = model_result.get("model_name", "Unknown")
                v = model_result.get("verdict", "UNVERIFIED")
                conf = model_result.get("confidence", 0)
                explanation = model_result.get("explanation", "No explanation")

                st.markdown(f"### {model_name}")

                m_emoji = get_verdict_emoji(v)
                st.markdown(f"**{m_emoji} {v}**")

                st.progress(min(int(conf) / 100, 1.0))
                st.caption(f"Confidence: {conf}%")

                with st.expander("📝 Full Explanation"):
                    st.write(explanation)

                if deep_mode:
                    if model_result.get("for_arguments"):
                        st.markdown("**✅ Arguments For:**")
                        st.write(model_result["for_arguments"][:200])
                    if model_result.get("against_arguments"):
                        st.markdown("**❌ Arguments Against:**")
                        st.write(model_result["against_arguments"][:200])

                if reporter_mode:
                    if model_result.get("follow_up_questions"):
                        st.markdown("**❓ Follow-up Questions:**")
                        for q in model_result.get("follow_up_questions", [])[:2]:
                            st.markdown(f"- {q}")
                    if model_result.get("red_flags"):
                        st.markdown("**🚩 Red Flags:**")
                        st.write(model_result["red_flags"][:150])

        st.divider()

        # Source Links
        if result.get("source_links"):
            st.markdown("## 🔗 Suggested Sources")
            for link in result["source_links"][:3]:
                st.markdown(f"- [{link[:60]}...]({link})")

# ============================================================================
# PAGE: DASHBOARD
# ============================================================================

elif page == "📊 Dashboard":

    st.title("📊 Analysis Dashboard")
    st.markdown("Summary of all fact-checks performed in this session")
    st.divider()

    if not st.session_state.history:
        st.info("📭 No claims checked yet. Start fact-checking to see results here!")
    else:
        df = pd.DataFrame(st.session_state.history)

        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            st.metric("📊 Total Checked", len(df))
        with col2:
            true_count = len(df[df["verdict"] == "TRUE"])
            st.metric("✅ True", true_count)
        with col3:
            false_count = len(df[df["verdict"] == "FALSE"])
            st.metric("❌ False", false_count)
        with col4:
            misleading_count = len(df[df["verdict"].isin(["MISLEADING", "CONTESTED"])])
            st.metric("⚠️ Misleading", misleading_count)
        with col5:
            avg_conf = df["confidence"].mean()
            st.metric("🎯 Avg Confidence", f"{int(avg_conf)}%")

        st.divider()

        filter_verdict = st.selectbox(
            "Filter by verdict",
            ["All", "TRUE", "FALSE", "MISLEADING", "CONTESTED", "UNVERIFIED"]
        )

        filtered_df = df
        if filter_verdict != "All":
            filtered_df = df[df["verdict"] == filter_verdict]

        st.markdown("### 📋 Fact-Check History")

        display_df = filtered_df[["timestamp", "claim", "verdict", "confidence"]].copy()
        display_df.columns = ["Time", "Claim", "Verdict", "Confidence (%)"]

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Confidence (%)": st.column_config.ProgressColumn(
                    "Confidence",
                    min_value=0,
                    max_value=100
                )
            }
        )

        st.divider()

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### Verdict Distribution")
            verdict_counts = df["verdict"].value_counts()
            st.bar_chart(verdict_counts)

        with col2:
            st.markdown("### Confidence Trend")
            if len(df) > 1:
                st.line_chart(df["confidence"].reset_index(drop=True))
            else:
                st.info("Need at least 2 checks to show trend")

# ============================================================================
# PAGE: SETTINGS
# ============================================================================

elif page == "⚙️ Settings":

    st.title("⚙️ Settings")
    st.markdown("Configure BanglaTruth for your environment")
    st.divider()

    st.markdown("### 🔗 Backend Configuration")

    new_api_url = st.text_input(
        "Backend API URL",
        value=st.session_state.api_url,
        placeholder="http://localhost:8000"
    )

    if new_api_url != st.session_state.api_url:
        st.session_state.api_url = new_api_url
        st.success(f"✅ Backend URL updated to: {new_api_url}")

    st.divider()

    st.markdown("### 🔑 Environment Variables")

    st.info("""
    Create a `.env` file in your project directory with:
```
    GROQ_API_KEY=your_groq_api_key
    GOOGLE_API_KEY=your_google_api_key (optional)
    GOOGLE_CX=your_google_cx (optional)
    PORT=8000
    BACKEND_URL=http://localhost:8000
```
    """)

    st.divider()

    st.markdown("### 🚀 Deployment Options")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Backend Hosting:**")
        st.markdown("""
        - 💻 **Local**: `python backend_api.py`
        - 🌐 **Render**: https://render.com (free tier)
        - 🚂 **Railway**: https://railway.app (free tier)
        """)

    with col2:
        st.markdown("**Frontend Hosting:**")
        st.markdown("""
        - 🎈 **Streamlit Cloud**: https://streamlit.io/cloud
        - 📦 Connect GitHub repo
        - ⚡ Auto-deploy on push
        """)

    st.divider()

    st.markdown("### 📦 Requirements")

    st.code("""
fastapi==0.104.1
uvicorn==0.24.0
python-dotenv==1.0.0
groq==0.4.2
requests==2.31.0
pydantic==2.5.0
streamlit==1.28.0
ddgs
newspaper3k
langdetect==1.0.9
pandas==2.1.3
    """, language="text")

    st.divider()

    st.markdown("### 🗑️ Session Management")

    if st.button("🗑️ Clear History", use_container_width=True):
        st.session_state.history = []
        st.success("✅ History cleared!")
        st.rerun()

    st.divider()

    st.markdown("### ℹ️ About")
    st.markdown("""
    **BanglaTruth v2.0**

    AI-powered fact-checking platform using multiple LLM jury voting.

    - **Models**: Llama 3.3, Llama 3.1 (via Groq)
    - **Languages**: English, Bangla, and more
    - **Search**: DuckDuckGo (default), Google Custom Search (optional)
    - **Architecture**: FastAPI backend + Streamlit frontend
    """)