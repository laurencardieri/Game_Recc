import streamlit as st
import requests
import os
from dotenv import load_dotenv
import datetime
from openai import OpenAI

# Load environment variables
load_dotenv()

# Load API keys
rawg_key = os.getenv("API_KEY")
openai_key = os.getenv("OPENAI_API_KEY")

# Check keys
if not rawg_key:
    st.warning("RAWG API_KEY environment variable not set")
if not openai_key:
    st.warning("OPENAI_API_KEY environment variable not set")

# Initialize OpenAI client
client = OpenAI(api_key=openai_key)

# Mood/Genre dictionary
mood_to_genres = {
    "Relaxed": ["indie", "adventure"],
    "Energetic": ["shooter", "action"],
    "Emotional": ["rpg", "adventure"],
    "Tense": ["horror"],
    "Thoughtful": ["puzzle", "strategy"]
}

# Gaming style to genre mapping
gaming_style_to_genres = {
    "Casual": ["puzzle", "indie", "simulation"],
    "Competitive": ["shooter", "fighting", "moba"],
    "Explorative": ["rpg", "adventure"],
    "Strategic": ["strategy", "turn-based", "card"],
    "Story-driven": ["rpg", "story-rich", "adventure"],
    "Social": ["mmo", "co-op", "party"]
}

# Age groups by release date
today = datetime.date.today()
release_ranges = {
    "New (< 1 year old)": (today.replace(year=today.year - 1), today),
    "Recent (1-5 years old)": (today.replace(year=today.year - 5), today.replace(year=today.year - 1)),
    "Aged (5-10 years old)": (today.replace(year=today.year - 10), today.replace(year=today.year - 5)),
    "Older (> 10 years old)": (datetime.date(1970, 1, 1), today.replace(year=today.year - 10))
}

# Streamlit display setup
st.set_page_config(page_title="Game Recommender", layout="wide", page_icon="🎮")

st.markdown("""
<style>
    .main-header {
        text-align: center;
        color: black;  
        font-size: 3rem;
        font-weight: bold;
        margin-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-header"> 🎮 Mood-Based Game Recommender 🎮</h1>', unsafe_allow_html=True)

selected_mood = st.selectbox("🫥 What mood are you in? 🫥", list(mood_to_genres.keys()))
selected_style = st.selectbox("🎮 Choose your gaming style 🎮", list(gaming_style_to_genres.keys()))
selected_age = st.selectbox("🗓️ Game Release Age 🗓️", list(release_ranges.keys()))

# Genre logic
mood_genres = set(mood_to_genres[selected_mood])
style_genres = set(gaming_style_to_genres[selected_style])
combined_genres = mood_genres.intersection(style_genres)
if not combined_genres:
    combined_genres = mood_genres.union(style_genres)
combined_genres = list(combined_genres)

start_date, end_date = release_ranges[selected_age]

if st.button("Find Games"):
    all_games = []

    for genre in combined_genres:
        url = "https://api.rawg.io/api/games"
        params = {
            'genres': genre,
            'ordering': '-rating',
            'page_size': 100,
            'key': rawg_key,
            'dates': f'{start_date},{end_date}'
        }

        response = requests.get(url, params=params)

        if response.status_code == 200:
            data = response.json()
            all_games.extend(data['results'])
        else:
            st.error(f"Failed to load games for genre: {genre}")

    unique_games = {game['id']: game for game in all_games}
    st.session_state.games = list(unique_games.values())
    if st.session_state.games:
        st.session_state.selected_game = st.session_state.games[0]['name']
        st.session_state.review_text = ""  
    else:
        st.session_state.selected_game = None
        st.session_state.review_text = ""

# Display games
if "games" in st.session_state and st.session_state.games:
    game_names = [game['name'] for game in st.session_state.games]

    col1, col2, col3 = st.columns([1, 2, 2])

    with col1:
        selected_game_name = st.radio("Select a game", game_names, index=game_names.index(st.session_state.selected_game))
        if selected_game_name != st.session_state.selected_game:
            st.session_state.selected_game = selected_game_name
            st.session_state.review_text = ""  

    with col2:
        selected_game_data = next((g for g in st.session_state.games if g['name'] == st.session_state.selected_game), None)

        if selected_game_data:
            st.subheader(selected_game_data['name'])
            st.write(f"Rating: {selected_game_data['rating']}")

            genres_str = ', '.join(g['name'] for g in selected_game_data.get('genres', []))
            st.write(f"Genres: {genres_str}")

            release_date = selected_game_data.get('released')
            if release_date:
                formatted_date = datetime.datetime.strptime(release_date, "%Y-%m-%d").strftime("%B %d, %Y")
                st.write(f"Released: {formatted_date}")
            else:
                st.write("Released: N/A")

            clip_info = selected_game_data.get("clip")
            trailer_url = clip_info.get("clip") if clip_info else None

            if trailer_url:
                st.video(trailer_url)
            else:
                game_name = selected_game_data['name']
                yt_search_url = f"https://www.youtube.com/results?search_query={game_name.replace(' ', '+')}+trailer"
                st.markdown(f"[Search for '{game_name}' Trailer on YouTube]({yt_search_url})", unsafe_allow_html=True)

            if selected_game_data.get('background_image'):
                st.image(selected_game_data['background_image'], width=700)

    with col3:
        if selected_game_data:
            game_name = selected_game_data['name']
            genres_str = ', '.join(g['name'] for g in selected_game_data.get('genres', []))
            rating = selected_game_data['rating']

            st.header("Why this game?")

            if "review_text" not in st.session_state:
                st.session_state.review_text = ""

            if st.button("Generate Review"):
                with st.spinner("Generating review..."):
                    prompt = (
                        f"Provide a short review and explain why the game '{game_name}' "
                        f"with genres {genres_str} and rating {rating} is recommended for players."
                    )
                    try:
                        response = client.chat.completions.create(
                            model="gpt-4.1-nano",  
                            messages=[{"role": "user", "content": prompt}],
                            max_tokens=150,
                            temperature=0.7
                        )
                        st.session_state.review_text = response.choices[0].message.content
                    except Exception as e:
                        st.session_state.review_text = f"Error generating review: {e}"

            if st.session_state.review_text:
                st.write(st.session_state.review_text)

else:
    st.info("Choose mood, gaming style, and release age, then click 'Find Games' to get recommendations.")
