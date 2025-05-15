import streamlit as st
import requests
from datetime import datetime
import time

# Set page config for a cleaner appearance
st.set_page_config(
    page_title="Courier Zone Briefing",
    page_icon="🚚",
    layout="centered"
)

# API keys - Replace with your actual keys
OPENWEATHER_API_KEY = "bc76588823fc2b0ff58485ed9196da3c"  
NEWS_API_KEY = "04b45dc5-16ea-4ae6-a879-1730368ef95b"

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
    </style>
    """, unsafe_allow_html=True)
st.write("Get real-time weather, news, and delivery information when entering a new zone.")

# Create columns for a better layout
col1, col2 = st.columns(2)

# Get user input
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

# Function to fetch weather data with error handling and retries
def get_weather(city):
    # Clean up API key by removing any extra spaces
    api_key = OPENWEATHER_API_KEY.strip()
    
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    
    try:
        for attempt in range(2):  # Try twice in case of temporary failure
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                weather = data["weather"][0]["description"].capitalize()
                temp = data["main"]["temp"]
                return True, f"{temp}°C, {weather}"
            elif response.status_code == 401:
                return False, "API key error. Please check your OpenWeatherMap API key."
            elif response.status_code == 404:
                return False, f"City '{city}' not found. Please check spelling."
            
            if attempt < 1:  # Wait before retrying
                time.sleep(1)
        
        return False, f"Weather API error (Status: {response.status_code})"
    
    except requests.exceptions.RequestException as e:
        return False, f"Network error while fetching weather data: {str(e)}"

# Function to fetch news data with error handling
def get_news(country_code, city):
    # Clean up API key
    api_key = NEWS_API_KEY.strip()
    
    # Use city name in query to get more relevant local news
    url = f"https://www.newsapi.ai/api/top-headlines?country={country_code}&q={city}&apiKey={api_key}"
    
    try:
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            articles = data.get("articles", [])
            
            if not articles:
                # Fallback to country news if no city-specific news found
                url = f"https://newsapi.org/v2/top-headlines?country={country_code}&category=general&apiKey={api_key}"
                response = requests.get(url, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    articles = data.get("articles", [])
            
            # Filter for relevant news (traffic, events, etc.)
            relevant_keywords = ["traffic", "road", "accident", "protest", 
                                "event", "closure", "strike", "demonstration"]
            
            filtered_articles = []
            for article in articles[:10]:  # Check first 10 articles
                title = article.get("title", "").lower()
                if any(keyword in title for keyword in relevant_keywords):
                    filtered_articles.append(article)
            
            # Use filtered articles if found, otherwise use first 3 articles
            display_articles = filtered_articles[:3] if filtered_articles else articles[:3]
            
            if display_articles:
                headlines = [article.get("title") for article in display_articles]
                return True, headlines
            else:
                return True, ["No significant news affecting deliveries at this time"]
        
        elif response.status_code == 401:
            return False, ["API key error. Please check your NewsAPI key."]
        else:
            return False, [f"News API error (Status: {response.status_code})"]
    
    except requests.exceptions.RequestException as e:
        return False, [f"Network error while fetching news data: {str(e)}"]

# Function to estimate delivery load based on time of day and historical patterns
def estimate_delivery_load(location):
    # Get current hour (24-hour format)
    now = datetime.now().hour
    
    # You could integrate with your actual delivery database here
    # For now, we'll use time-based patterns that vary by location
    
    # Dictionary of city-specific patterns (add more as needed)
    city_patterns = {
        "barcelona": {
            "morning_peak": (9, 11),   # 9 AM - 11 AM
            "lunch_peak": (12, 15),    # 12 PM - 3 PM
            "evening_peak": (18, 21),  # 6 PM - 9 PM
        },
        "madrid": {
            "morning_peak": (8, 11),
            "lunch_peak": (13, 16),
            "evening_peak": (19, 22),
        }
    }
    
    # Default pattern if city not found
    default_pattern = {
        "morning_peak": (8, 11),
        "lunch_peak": (12, 15),
        "evening_peak": (18, 21),
    }
    
    # Get pattern for current location (case insensitive)
    pattern = city_patterns.get(location.lower(), default_pattern)
    
    # Determine current delivery load based on time patterns
    if pattern["lunch_peak"][0] <= now <= pattern["lunch_peak"][1]:
        return "High", f"{10 + now - pattern['lunch_peak'][0]} deliveries scheduled between {pattern['lunch_peak'][0]} - {pattern['lunch_peak'][1]} PM"
    elif pattern["evening_peak"][0] <= now <= pattern["evening_peak"][1]:
        return "Medium", f"5-10 deliveries scheduled between {pattern['evening_peak'][0] - 12 if pattern['evening_peak'][0] > 12 else pattern['evening_peak'][0]} - {pattern['evening_peak'][1] - 12} PM"
    elif pattern["morning_peak"][0] <= now <= pattern["morning_peak"][1]:
        return "Medium", f"5-8 deliveries scheduled between {pattern['morning_peak'][0]} - {pattern['morning_peak'][1]} AM"
    else:
        return "Low", "Less than 5 deliveries expected in the next hour"

# Function to generate output with emojis and formatting
def generate_briefing(location, country):
    with st.spinner("Generating briefing..."):
        # Fetch weather data
        weather_success, weather_data = get_weather(location)
        
        # Fetch news data
        news_success, news_data = get_news(country, location)
        
        # Estimate delivery load
        load_level, load_details = estimate_delivery_load(location)
        
        # Create styled briefing
        st.subheader(f"Zone: {location.title()}")
        
        # Create three columns for the main data points
        col1, col2, col3 = st.columns(3)
        
        # Display weather with proper styling
        with col1:
            st.markdown("### 🌤️ Weather")
            if weather_success:
                st.info(weather_data)
            else:
                st.error(weather_data)
        
        # Display delivery load with appropriate color
        with col2:
            st.markdown("### 📦 Delivery Load")
            if load_level == "High":
                st.error(f"**{load_level}**\n{load_details}")
            elif load_level == "Medium":
                st.warning(f"**{load_level}**\n{load_details}")
            else:
                st.success(f"**{load_level}**\n{load_details}")
        
        # Current time for reference
        with col3:
            st.markdown("### ⏰ Current Time")
            current_time = datetime.now().strftime("%H:%M")
            st.info(f"{current_time} local time")
        
        # Display news section with expandable details
        st.markdown("### 📰 Local News")
        if news_success:
            for i, headline in enumerate(news_data):
                st.write(f"{i+1}. {headline}")
        else:
            st.error(news_data[0])
            
        # Additional safety tips based on weather or time of day
        provide_safety_tips(weather_data if weather_success else None)

# Function to provide contextual safety tips
def provide_safety_tips(weather_data):
    if not weather_data:
        return
    
    st.markdown("### 🛡️ Safety Tips")
    
    weather_lower = weather_data.lower()
    
    if "rain" in weather_lower or "shower" in weather_lower:
        st.warning("• Roads may be slippery. Maintain safe distance and reduce speed.")
    elif "snow" in weather_lower:
        st.warning("• Snow conditions reported. Use winter equipment and drive cautiously.")
    elif "fog" in weather_lower:
        st.warning("• Reduced visibility. Use fog lights and reduce speed.")
    elif "storm" in weather_lower or "thunder" in weather_lower:
        st.warning("• Stormy conditions. Seek shelter if lightning intensifies.")
    elif int(weather_lower.split("°")[0]) > 30:  # Temperature above 30°C
        st.warning("• High temperature. Stay hydrated and avoid prolonged sun exposure.")
    elif int(weather_lower.split("°")[0]) < 5:   # Temperature below 5°C
        st.warning("• Cold temperature. Wear appropriate clothing and watch for ice.")
    else:
        st.success("• No specific weather-related safety concerns. Proceed normally.")

# Main button to generate briefing
if st.button("Generate Delivery Briefing", key="generate_btn", type="primary"):
    generate_briefing(location, country)

# Show a map of the location (if Streamlit is upgraded)
expander = st.expander("Show location on map")
with expander:
    st.write("Map visualization will be shown here in a future update.")
    # When implementing, you can use st.map() with geocoded coordinates

# Footer with app information
st.markdown("---")
st.markdown("""
    <div style="text-align: center; color: gray; font-size: 12px;">
        Courier Zone Briefing App | Real-time delivery intelligence
    </div>
    """, unsafe_allow_html=True)
