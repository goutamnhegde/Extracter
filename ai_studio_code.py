import streamlit as st
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
import trafilatura
import re
import requests
import json
from youtube_transcript_api.formatters import TextFormatter

# --- 1. CONFIGURATION & PWA METADATA ---
st.set_page_config(
    page_title="OmniSummarizer AI",
    page_icon="⚡",
    layout="centered",
    initial_sidebar_state="collapsed"
)

def inject_pwa_meta():
    """Injects PWA metadata and mobile optimization CSS."""
    pwa_html = f"""
    <link rel="manifest" href="https://gist.githubusercontent.com/user/manifest.json">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <style>
        /* Hide Streamlit Header/Footer for Native Look */
        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}
        header {{visibility: hidden;}}
        .stDeployButton {{display:none;}}
        
        /* Dark Mode Aesthetic */
        body {{ background-color: #0E1117; color: #FFFFFF; }}
        .stTextArea textarea {{ background-color: #161B22 !important; color: white !important; border: 1px solid #30363D; }}
        .stButton button {{ width: 100%; border-radius: 10px; background-color: #238636; color: white; border: none; font-weight: bold; padding: 12px; }}
        .stTabs [data-baseweb="tab-list"] {{ gap: 10px; }}
        .stTabs [data-baseweb="tab"] {{ border-radius: 8px 8px 0 0; padding: 10px 20px; background-color: #161B22; }}
    </style>
    """
    st.markdown(pwa_html, unsafe_allow_html=True)

inject_pwa_meta()

# --- 2. CORE LOGIC & EXTRACTION ---

def extract_youtube_id(url):
    pattern = r'(?:v=|\/)([0-9A-Za-z_-]{11}).*'
    match = re.search(pattern, url)
    return match.group(1) if match else None

def get_youtube_content(url):
    try:
        video_id = extract_youtube_id(url)
        if not video_id: return None
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        # Try English, then fall back to first available
        try:
            transcript = transcript_list.find_transcript(['en'])
        except:
            transcript = transcript_list.find_manually_created_transcript() or transcript_list.find_generated_transcript(transcript_list._manually_created_transcripts.keys())
        
        data = transcript.fetch()
        return TextFormatter().format_transcript(data)
    except Exception as e:
        return f"Error fetching YouTube transcript: {str(e)}"

def get_web_content(url):
    try:
        downloaded = trafilatura.fetch_url(url)
        return trafilatura.extract(downloaded, include_comments=False, include_tables=True)
    except Exception as e:
        return None

def get_facebook_content(url):
    """Attempt mobile scraping, else prompt manual paste."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1'
    }
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200 and "facebook.com" not in res.url: # Check if redirected to login
             # Basic extraction logic for FB public posts
             result = trafilatura.extract(res.text)
             return result if result and len(result) > 50 else None
        return None
    except:
        return None

def summarize_with_gemini(text, api_key):
    if not api_key:
        st.error("Please provide a Gemini API Key in the sidebar.")
        return None
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    Summarize the following content into a high-impact, mobile-readable format:
    1. **TL;DR**: One punchy sentence.
    2. **Key Insights**: 5 bullet points with emojis.
    3. **Sentiment Analysis**: One word (e.g., Optimistic, Critical, Informative).
    4. **Action Items**: 2-3 next steps or takeaways.

    Content:
    {text[:30000]} 
    """
    # 30k chars is a safe buffer, though Gemini handles more.
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI Error: {str(e)}"

# --- 3. MAIN UI ---

st.title("⚡ OmniSummarizer")
st.caption("Summarize YouTube, FB, or Web Articles instantly.")

with st.sidebar:
    st.header("Settings")
    api_key = st.text_input("Gemini API Key", type="password", help="Get a free key at aistudio.google.com")
    st.info("This app is optimized for mobile. Use 'Add to Home Screen' for the best experience.")

tab_link, tab_manual = st.tabs(["🔗 Paste Link", "📝 Paste Text"])

content_to_summarize = ""

with tab_link:
    url = st.text_input("Enter URL (YouTube, FB, Website):", placeholder="https://...")
    if url:
        with st.spinner("Analyzing source..."):
            if "youtube.com" in url or "youtu.be" in url:
                content_to_summarize = get_youtube_content(url)
            elif "facebook.com" in url or "fb.watch" in url:
                fb_data = get_facebook_content(url)
                if not fb_data:
                    st.warning("⚠️ Meta blocked automated access. Please copy the post text and use the 'Paste Text' tab.")
                else:
                    content_to_summarize = fb_data
            else:
                content_to_summarize = get_web_content(url)

with tab_manual:
    manual_text = st.text_area("Paste long text or FB post here:", height=200)
    if manual_text:
        content_to_summarize = manual_text

if st.button("Summarize Now"):
    if content_to_summarize:
        if "Error" in content_to_summarize:
            st.error(content_to_summarize)
        else:
            with st.spinner("Gemini 1.5 Flash is thinking..."):
                summary = summarize_with_gemini(content_to_summarize, api_key)
                if summary:
                    st.markdown("---")
                    st.markdown(summary)
                    st.balloons()
    else:
        st.warning("Please provide a valid link or paste some text first.")