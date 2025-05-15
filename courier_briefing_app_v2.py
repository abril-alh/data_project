
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
st.markdown("""
    <style>
    .reportview-container .markdown-text-container {
        font-family: monospace;
    }
    .stApp {
        background-color: #f5f7fa;
    }
    .element-container:has(div[data-testid="stException"]) {
        display: none;
    }
    </style>
    """, unsafe_allow_html=True)
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
city_timezone = {
    "new york": "America/New_York",
    "barcelona": "Europe/Madrid",
    "madrid": "Europe/Madrid",
    "london": "Europe/London",
    "paris": "Europe/Paris",
    "rome": "Europe/Rome",
    "berlin": "Europe/Berlin",
}

def get_local_time(city):
    tz_name = city_timezone.get(city.lower(), "UTC")
    local_tz = pytz.timezone(tz_name)
    return datetime.now(local_tz).strftime("%H:%M")

def get_weather(city):
    api_key = OPENWEATHER_API_KEY.strip()
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    try:
        for attempt in range(2):
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                weather = data["weather"][0]["description"].capitalize()
                temp = data["main"]["temp"]
                return True, (f"{temp}°C, {weather}", temp)
            elif response.status_code == 401:
                return False, ("API key error. Please check your OpenWeatherMap API key.", None)
            elif response.status_code == 404:
                return False, (f"City '{city}' not found. Please check spelling.", None)
            time.sleep(1)
        return False, (f"Weather API error (Status: {response.status_code})", None)
    except requests.exceptions.RequestException as e:
        return False, (f"Network error while fetching weather data: {str(e)}", None)

def get_news(country_code, city):
    api_key = NEWS_API_KEY.strip()
    url = f"https://newsapi.org/v2/top-headlines?country={country_code}&q={city}&apiKey={api_key}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            articles = data.get("articles", [])
            if not articles:
                fallback_url = f"https://newsapi.org/v2/top-headlines?country={country_code}&category=general&apiKey={api_key}"
                response = requests.get(fallback_url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    articles = data.get("articles", [])
            relevant_keywords = ["traffic", "road", "accident", "protest", "event", "closure", "strike", "demonstration"]
            filtered_articles = [
                article for article in articles[:10]
                if any(keyword in article.get("title", "").lower() for keyword in relevant_keywords)
            ]
            display_articles = filtered_articles[:3] if filtered_articles else articles[:3]
            headlines = [article.get("title") for article in display_articles]
            return True, headlines if headlines else ["No significant news affecting deliveries at this time"]
        elif response.status_code == 401:
            return False, ["API key error. Please check your NewsAPI key."]
        else:
            return False, [f"News API error (Status: {response.status_code})"]
    except requests.exceptions.RequestException as e:
        return False, [f"Network error while fetching news data: {str(e)}"]

def estimate_delivery_load(location):
    now = datetime.now().hour
    city_patterns = {
        "barcelona": {"morning_peak": (9, 11), "lunch_peak": (12, 15), "evening_peak": (18, 21)},
        "madrid": {"morning_peak": (8, 11), "lunch_peak": (13, 16), "evening_peak": (19, 22)},
    }
    default_pattern = {"morning_peak": (8, 11), "lunch_peak": (12, 15), "evening_peak": (18, 21)}
    pattern = city_patterns.get(location.lower(), default_pattern)
    if pattern["lunch_peak"][0] <= now <= pattern["lunch_peak"][1]:
        return "High", f"{10 + now - pattern['lunch_peak'][0]} deliveries scheduled between {pattern['lunch_peak'][0]} - {pattern['lunch_peak'][1]} PM"
    elif pattern["evening_peak"][0] <= now <= pattern["evening_peak"][1]:
        return "Medium", f"5-10 deliveries scheduled between {pattern['evening_peak'][0]-12} - {pattern['evening_peak'][1]-12} PM"
    elif pattern["morning_peak"][0] <= now <= pattern["morning_peak"][1]:
        return "Medium", f"5-8 deliveries scheduled between {pattern['morning_peak'][0]} - {pattern['morning_peak'][1]} AM"
    else:
        return "Low", "Less than 5 deliveries expected in the next hour"

def provide_safety_tips(temp_value):
    if temp_value is None:
        return
    st.markdown("### 🛡️ Safety Tips")
    if temp_value > 30:
        st.warning("• High temperature. Stay hydrated and avoid prolonged sun exposure.")
    elif temp_value < 5:
        st.warning("• Cold temperature. Wear appropriate clothing and watch for ice.")
    else:
        st.success("• No specific weather-related safety concerns. Proceed normally.")

def generate_briefing(location, country):
    with st.spinner("Generating briefing..."):
        weather_success, (weather_data, temp_val) = get_weather(location)
        news_success, news_data = get_news(country, location)
        load_level, load_details = estimate_delivery_load(location)

        st.subheader(f"Zone: {location.title()}")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("### 🌤️ Weather")
            st.info(weather_data) 
            if weather_success 
            else st.error("write nothing")
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

if st.button("Generate Delivery Briefing", key="generate_btn", type="primary"):
    generate_briefing(location, country)

with st.expander("Show location on map"):
    st.write("Map visualization will be shown here in a future update.")

st.markdown("---")
st.markdown("""
    <div style="text-align: center; color: gray; font-size: 12px;">
        Courier Zone Briefing App | Real-time delivery intelligence
    </div>
    """, unsafe_allow_html=True)
