import streamlit as st
import requests
from datetime import datetime
import json
import pandas as pd
import pydeck as pdk
import time

# Set page configuration
st.set_page_config(
    page_title="Courier Zone Briefing",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply custom CSS for styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 1rem;
    }
    .section-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #333;
        margin-top: 1rem;
        margin-bottom: 0.5rem;
    }
    .info-box {
        background-color: #f8f9fa;
        border-radius: 0.5rem;
        padding: 1rem;
        margin-bottom: 1rem;
        border-left: 4px solid #1E88E5;
    }
    .warning {
        border-left: 4px solid #FFC107;
    }
    .danger {
        border-left: 4px solid #F44336;
    }
    .success {
        border-left: 4px solid #4CAF50;
    }
</style>
""", unsafe_allow_html=True)

# Functions from original script
def get_weather(city, api_key):
    """Get weather information for a city"""
    with st.spinner(f"Fetching weather data for {city}..."):
        api_key = api_key.strip()
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
        
        try:
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                weather = data["weather"][0]["description"].capitalize()
                temp = data["main"]["temp"]
                icon = data["weather"][0]["icon"]
                humidity = data["main"]["humidity"]
                wind_speed = data["wind"]["speed"]
                
                # Get coordinates for map
                lat = data["coord"]["lat"]
                lon = data["coord"]["lon"]
                
                weather_details = {
                    "description": weather,
                    "temp": temp,
                    "icon": icon,
                    "humidity": humidity,
                    "wind_speed": wind_speed,
                    "lat": lat,
                    "lon": lon
                }
                
                return True, weather_details
            elif response.status_code == 401:
                return False, "API key error. Please check your OpenWeatherMap API key."
            elif response.status_code == 404:
                return False, f"City '{city}' not found. Please check spelling."
            
            return False, f"Weather API error (Status: {response.status_code})"
        
        except requests.exceptions.RequestException as e:
            return False, f"Network error while fetching weather data: {str(e)}"

def get_news(country_code, city, api_key):
    """Get news headlines for a location"""
    with st.spinner(f"Fetching local news for {city}, {country_code.upper()}..."):
        api_key = api_key.strip()
        url = f"https://www.newsapi.ai/api/top-headlines?country={country_code}&q={city}&apiKey={api_key}"
        
        try:
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                articles = data.get("articles", [])
                
                if not articles:
                    # Fallback to general news
                    url = f"https://www.newsapi.ai/api/top-headlines?country={country_code}&category=general&apiKey={api_key}"
                    response = requests.get(url, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        articles = data.get("articles", [])
                
                relevant_articles = []
                for article in articles[:10]:
                    title = article.get("title", "").lower()
                    if any(keyword in title for keyword in ["traffic", "road", "accident", "protest", "closure"]):
                        relevant_articles.append(article)
                
                display_articles = relevant_articles[:5] if relevant_articles else articles[:5]
                
                if display_articles:
                    news_items = []
                    for article in display_articles:
                        news_items.append({
                            "title": article.get("title"),
                            "url": article.get("url", "#"),
                            "source": article.get("source", {}).get("name", "Unknown")
                        })
                    return True, news_items
                else:
                    return True, [{"title": "No significant news affecting deliveries at this time", "url": "#", "source": "System"}]
            
            else:
                # Try alternative approach if the API structure is different
                return True, [{"title": "No significant news affecting deliveries at this time", "url": "#", "source": "System"}]
        
        except Exception as e:
            return False, [{"title": f"Error fetching news: {str(e)}", "url": "#", "source": "Error"}]

def estimate_delivery_load(location):
    """Estimate delivery load based on time and location"""
    now = datetime.now().hour
    
    # Simple time-based patterns
    if 11 <= now <= 14:  # Lunch rush
        return "High", f"10+ deliveries expected between {11}:00 - {14}:00", "🔴"
    elif 17 <= now <= 20:  # Dinner rush
        return "Medium", f"5-10 deliveries expected between {17}:00 - {20}:00", "🟡"
    elif 8 <= now <= 10:  # Breakfast/morning
        return "Medium", f"5-8 deliveries expected between {8}:00 - {10}:00", "🟡"
    else:
        return "Low", "Less than 5 deliveries expected in the next hour", "🟢"

def get_safety_tips(weather_data):
    """Generate safety tips based on weather conditions"""
    if not isinstance(weather_data, dict):
        return ["No specific weather-related safety concerns. Proceed normally."]
    
    tips = []
    temp = weather_data.get("temp", 20)
    description = weather_data.get("description", "").lower()
    
    if "rain" in description or "shower" in description:
        tips.append("Roads may be slippery. Maintain safe distance and reduce speed.")
    elif "snow" in description:
        tips.append("Snow conditions reported. Use winter equipment and drive cautiously.")
    elif "fog" in description:
        tips.append("Reduced visibility. Use fog lights and reduce speed.")
    elif "storm" in description or "thunder" in description:
        tips.append("Stormy conditions. Seek shelter if lightning intensifies.")
    
    if temp >= 30:
        tips.append("High temperature. Stay hydrated and avoid prolonged sun exposure.")
    elif temp <= 5:
        tips.append("Cold temperature. Wear appropriate clothing and watch for ice.")
        
    if not tips:
        tips.append("No specific weather-related safety concerns. Proceed normally.")
        
    return tips

def generate_map(lat, lon, zoom=12):
    """Generate an interactive 3D map for the location"""
    # Create a layer for the map
    layer = pdk.Layer(
        "HexagonLayer",
        data=pd.DataFrame({
            "lat": [lat],
            "lon": [lon]
        }),
        get_position=["lon", "lat"],
        auto_highlight=True,
        elevation_scale=50,
        pickable=True,
        elevation_range=[0, 300],
        extruded=True,
        coverage=1,
        radius=1000,
    )

    # Set the viewport location
    view_state = pdk.ViewState(
        longitude=lon,
        latitude=lat,
        zoom=zoom,
        min_zoom=5,
        max_zoom=15,
        pitch=40.5,
        bearing=-27.36
    )

    # Combined all of it and render a viewport
    r = pdk.Deck(
        map_style="mapbox://styles/mapbox/light-v9",
        layers=[layer],
        initial_view_state=view_state,
        tooltip={"text": "Delivery Zone Center"},
    )
    
    return r

# Main app
def main():
    # Sidebar configuration
    st.sidebar.markdown("### 🚚 Configuration")
    
    # API Keys
    default_weather_key = "bc76588823fc2b0ff58485ed9196da3c"
    default_news_key = "04b45dc5-16ea-4ae6-a879-1730368ef95b"
    
    weather_key = st.sidebar.text_input("OpenWeatherMap API Key", value=default_weather_key)
    news_key = st.sidebar.text_input("NewsAPI.ai API Key", value=default_news_key)
    
    # Location settings
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📍 Location")
    city = st.sidebar.text_input("City", value="Barcelona")
    country = st.sidebar.text_input("Country Code", value="es", max_chars=2)
    
    # Refresh interval
    st.sidebar.markdown("---")
    refresh_interval = st.sidebar.slider("Auto-refresh interval (minutes)", 0, 60, 15)
    
    # Main content
    st.markdown('<div class="main-header">🚚 COURIER ZONE BRIEFING</div>', unsafe_allow_html=True)
    
    # Current time
    current_time = datetime.now().strftime("%H:%M:%S")
    st.markdown(f"<p style='text-align: center;'>Last updated: {current_time}</p>", unsafe_allow_html=True)
    
    # Initialize session state for auto-refresh
    if 'last_refresh' not in st.session_state:
        st.session_state.last_refresh = datetime.now()
        st.session_state.refresh_counter = 0
    
    # Auto-refresh logic
    if refresh_interval > 0:
        time_since_refresh = (datetime.now() - st.session_state.last_refresh).total_seconds() / 60
        if time_since_refresh >= refresh_interval:
            st.session_state.last_refresh = datetime.now()
            st.session_state.refresh_counter += 1
            st.experimental_rerun()
        
        # Progress bar for next refresh
        progress = min(time_since_refresh / refresh_interval, 1.0)
        if progress < 1.0:
            st.progress(progress)
            next_refresh = refresh_interval - time_since_refresh
            st.caption(f"Next refresh in approximately {int(next_refresh)} minutes")
    
    # Generate data
    weather_success, weather_data = get_weather(city, weather_key)
    news_success, news_data = get_news(country, city, news_key)
    load_level, load_details, load_emoji = estimate_delivery_load(city)
    
    # Create layout with columns
    col1, col2 = st.columns([2, 1])
    
    # Map in the first column
    with col1:
        st.markdown('<div class="section-header">📍 Zone Map</div>', unsafe_allow_html=True)
        
        if weather_success and isinstance(weather_data, dict):
            # Display interactive 3D map
            map_deck = generate_map(weather_data["lat"], weather_data["lon"])
            st.pydeck_chart(map_deck)
            
            # Display coordinates below map
            st.caption(f"Coordinates: {weather_data['lat']:.4f}, {weather_data['lon']:.4f}")
        else:
            st.error("Unable to load map: Weather data unavailable")
    
    # Delivery stats in the second column
    with col2:
        # Weather section
        st.markdown('<div class="section-header">🌤️ Weather</div>', unsafe_allow_html=True)
        
        if weather_success and isinstance(weather_data, dict):
            weather_class = "info-box"
            if "rain" in weather_data["description"].lower() or "snow" in weather_data["description"].lower():
                weather_class += " warning"
            
            st.markdown(f"""
            <div class="{weather_class}">
                <h3>{weather_data["temp"]}°C, {weather_data["description"]}</h3>
                <p>Humidity: {weather_data["humidity"]}%</p>
                <p>Wind Speed: {weather_data["wind_speed"]} m/s</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.error(weather_data if isinstance(weather_data, str) else "Weather data unavailable")
        
        # Delivery load section
        st.markdown('<div class="section-header">📦 Delivery Load</div>', unsafe_allow_html=True)
        
        load_class = "info-box"
        if load_level == "High":
            load_class += " danger"
        elif load_level == "Medium":
            load_class += " warning"
        else:
            load_class += " success"
            
        st.markdown(f"""
        <div class="{load_class}">
            <h3>{load_emoji} {load_level}</h3>
            <p>{load_details}</p>
        </div>
        """, unsafe_allow_html=True)
    
    # News section (full width)
    st.markdown('<div class="section-header">📰 Local News</div>', unsafe_allow_html=True)
    
    if news_success:
        for news_item in news_data:
            title = news_item.get("title", "")
            url = news_item.get("url", "#")
            source = news_item.get("source", "Unknown")
            
            st.markdown(f"""
            <div class="info-box">
                <h3>{title}</h3>
                <p>Source: {source}</p>
                <a href="{url}" target="_blank">Read more</a>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.error("News data unavailable")
    
    # Safety tips section
    st.markdown('<div class="section-header">🛡️ Safety Tips</div>', unsafe_allow_html=True)
    
    if weather_success:
        tips = get_safety_tips(weather_data)
        
        for tip in tips:
            tip_class = "info-box"
            if "caution" in tip.lower() or "reduce speed" in tip.lower():
                tip_class += " warning"
            elif "danger" in tip.lower() or "seek shelter" in tip.lower():
                tip_class += " danger"
                
            st.markdown(f"""
            <div class="{tip_class}">
                <p>• {tip}</p>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.warning("Safety tips unavailable: Weather data not accessible")
    
    # Save data as JSON
    try:
        briefing_data = {
            "zone": city,
            "country": country,
            "timestamp": datetime.now().isoformat(),
            "weather": weather_data if weather_success else None,
            "news": news_data if news_success else None,
            "delivery_load": {
                "level": load_level,
                "details": load_details
            }
        }
        
        if st.button("Save Briefing to JSON"):
            with open("last_briefing.json", "w") as f:
                json.dump(briefing_data, f, indent=2)
            st.success("Briefing data saved to 'last_briefing.json'")
    except Exception as e:
        st.error(f"Error saving data: {str(e)}")

if _name_ == "_main_":
    main()
 