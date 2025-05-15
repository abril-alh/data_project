import streamlit as st
import requests
from datetime import datetime
import pytz
import time

# Set page config for a cleaner appearance
st.set_page_config(
    page_title="Courier Zone Briefing",
    page_icon="🚚",
    layout="centered"
)

# API keys
OPENWEATHER_API_KEY = "bc76588823fc2b0ff58485ed9196da3c"
NEWS_API_KEY = "0d9c613f7217408782b7b6e6d9ec6dc5"

# App title and description with styling
st.title("📍 Courier Zone Briefing")
st.markdown(
    """
    <style>
    /* Use supported selectors and hide Streamlit exceptions container elegantly */
    .stException {display: none !important;}
    .stApp {
        background-color: #f5f7fa;
    }
    </style>
    """, unsafe_allow_html=True
)
st.write("Get real-time weather, news, and delivery information when entering a new zone.")

# User inputs
col1, col2 = st.columns(2)
with col1:
    location = st.text_input("City or postal code:", "Barcelona")
with col2:
    country = st.selectbox(
        "Country:",
        options=["es", "us", "gb", "fr", "de", "it"],
        format_func=lambda x: {
            "es": "Spain", "us": "United States", "gb": "United Kingdom",
            "fr": "France", "de": "Germany", "it": "Italy"
        }.get(x, x.upper())
    )

# Timezone mapping
def get_local_time(city):
    tz_name = {
        "new york": "America/New_York",
        "barcelona": "Europe/Madrid",
        "madrid": "Europe/Madrid",
        "london": "Europe/London",
        "paris": "Europe/Paris",
        "rome": "Europe/Rome",
        "berlin": "Europe/Berlin",
    }.get(city.lower(), "UTC")
    local_tz = pytz.timezone(tz_name)
    return datetime.now(local_tz).strftime("%H:%M")

# ... [other functions unchanged] ...

def generate_briefing(location, country):
    with st.spinner("Generating briefing..."):
        weather_success, (weather_data, temp_val) = get_weather(location)
        news_success, news_data = get_news(country, location)
        load_level, load_details = estimate_delivery_load(location)

        st.subheader(f"Zone: {location.title()}")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("### 🌤️ Weather")
            st.info(weather_data) if weather_success else st.error(weather_data)
        with col2:
            st.markdown("### 📦 Delivery Load")
            if load_level == "High":
                st.error(f"**{load_level}**\n{load_details}")
            elif load_level == "Medium":
                st.warning(f"**{load_level}**\n{load_details}")
            else:
                st.success(f"**{load_level}**\n{load_details}")
        with col3:
            st.markdown("### ⏰ Current Time")
            st.info(f"{get_local_time(location)} local time")

        st.markdown("### 📰 Local News")
        if news_success:
            for i, headline in enumerate(news_data):
                st.write(f"{i+1}. {headline}")
        else:
            st.error(news_data[0])

        provide_safety_tips(temp_val)

# Corrected button without invalid 'type' argument
if st.button("Generate Delivery Briefing", key="generate_btn"):
    generate_briefing(location, country)

with st.expander("Show location on map"):
    st.write("Map visualization will be shown here in a future update.")

st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: gray; font-size: 12px;">
        Courier Zone Briefing App | Real-time delivery intelligence
    </div>
    """, unsafe_allow_html=True
)


 
