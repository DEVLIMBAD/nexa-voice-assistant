from flask import Flask, render_template, request, jsonify
from datetime import datetime
import os
import webbrowser
import requests
import wikipedia
import pywhatkit
import threading
import queue
import time
import subprocess
import re
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from typing import Optional
import sys
import signal

app = Flask(__name__)

# Spotify Configuration
SPOTIFY_CLIENT_ID = 'your_spotify_client_id'
SPOTIFY_CLIENT_SECRET = 'your_spotify_client_secret'
SPOTIFY_REDIRECT_URI = 'http://localhost:5000/callback'

# Initialize Spotify client (with error handling)
try:
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
        redirect_uri=SPOTIFY_REDIRECT_URI,
        scope="user-modify-playback-state,user-read-playback-state"
    ))
except Exception as e:
    print(f"Spotify initialization failed: {e}")
    sp = None

#  Speech Engine (Thread-Safe)
class SpeechEngine:
    def __init__(self):
        self.speech_queue = queue.Queue()
        self._running = True
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()

    def _worker(self):
        while self._running:
            try:
                text = self.speech_queue.get(timeout=1)
                if text is None:  # Sentinel for shutdown
                    break
                self._safe_speak(text)
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Speech error: {e}")

    def _safe_speak(self, text):
        try:
            subprocess.run(
                ['espeak', '-ven+f3', '-k5', '-s150', text],
                check=True,
                stderr=subprocess.DEVNULL
            )
        except Exception as e:
            print(f"Speech synthesis failed: {e}")

    def speak(self, text: str):
        if text and isinstance(text, str):
            self.speech_queue.put(text)

    def shutdown(self):
        self._running = False
        self.speech_queue.put(None)  # Sentinel
        self.thread.join()

speech_engine = SpeechEngine()

def speak(text: str):
    speech_engine.speak(text)

# Command Processing
def system_command(command: str) -> Optional[str]:
    if "shutdown" in command:
        os.system("shutdown now")
        return "Shutting down the system."
    elif "restart" in command:
        os.system("reboot")
        return "Restarting the system."
    elif "open file" in command:
        os.system("xdg-open /home/a/Downloads")
        return "Opening your Downloads folder."
    return None

def open_website(command: str) -> Optional[str]:
    sites = {
        "youtube": "https://www.youtube.com",
        "google": "https://www.google.com",
        "github": "https://www.github.com",
        "whatsapp": "https://web.whatsapp.com",
        "facebook": "https://www.facebook.com",
        "instagram": "https://www.instagram.com",
        "spotify": "https://open.spotify.com"
    }
    
    for site, url in sites.items():
        if site in command:
            webbrowser.open(url)
            return f"Opening {site.capitalize()}."
    return None

def get_datetime(command: str) -> Optional[str]:
    now = datetime.now()
    if "time" in command:
        return f"The current time is {now.strftime('%I:%M %p')}."
    elif "date" in command:
        return f"Today's date is {now.strftime('%B %d, %Y')}."
    return None

def get_weather(city: str = "Rajkot") -> str:
    api_key = "YOUR_OPENWEATHERMAP_API_KEY"
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    
    try:
        res = requests.get(url, timeout=5).json()
        if res.get("main"):
            temp = res["main"]["temp"]
            desc = res["weather"][0]["description"]
            return f"The current temperature in {city} is {temp}°C with {desc}."
    except Exception:
        pass
    
    return "Sorry I couldn't fetch the weather data right now."

def search_wikipedia(query: str) -> str:
    try:
        wikipedia.set_lang("en")
        result = wikipedia.summary(query, sentences=2, auto_suggest=False)
        return result
    except Exception:
        return "I couldn't find anything on Wikipedia."

def play_media(command: str) -> Optional[str]:
    # Extract phone number if present
    phone_match = re.search(r'(\+?\d{10,13})', command)
    phone_number = phone_match.group(1) if phone_match else None
    
    # Spotify song
    if "on spotify" in command:
        song = command.split("on spotify")[0].replace("play", "").strip()
        if song:
            return play_spotify_song(song, phone_number)
    
    # Spotify playlist
    elif "spotify playlist" in command:
        playlist = command.split("spotify playlist")[1].strip()
        if playlist:
            return play_spotify_playlist(playlist)
    
    # YouTube video
    elif "video" in command:
        video = command.replace("play", "").replace("video", "").strip()
        if video:
            pywhatkit.playonyt(video)
            return f"Playing {video} video on YouTube."
    
    # Regular YouTube search
    elif "play" in command:
        media = command.replace("play", "").strip()
        if media:
            pywhatkit.playonyt(media)
            return f"Playing {media} on YouTube."
    
    return None

def play_spotify_song(query: str, phone_number: str = None) -> str:
    try:
        results = sp.search(q=query, limit=1, type='track')
        if results['tracks']['items']:
            track_uri = results['tracks']['items'][0]['uri']
            sp.start_playback(uris=[track_uri])
            track_name = results['tracks']['items'][0]['name']
            artist = results['tracks']['items'][0]['artists'][0]['name']
            
            if phone_number:
                send_whatsapp_message(phone_number, f"Now playing: {track_name} by {artist}")
            
            return f"Playing {track_name} by {artist} on Spotify."
        return "Sorry, I couldn't find that song on Spotify."
    except Exception as e:
        print(f"Spotify error: {e}")
        return "Sorry, I'm having trouble with Spotify right now."

def play_spotify_playlist(query: str) -> str:
    try:
        results = sp.search(q=query, limit=1, type='playlist')
        if results['playlists']['items']:
            playlist_uri = results['playlists']['items'][0]['uri']
            sp.start_playback(context_uri=playlist_uri)
            playlist_name = results['playlists']['items'][0]['name']
            return f"Playing playlist {playlist_name} on Spotify."
        return "Sorry, I couldn't find that playlist on Spotify."
    except Exception as e:
        print(f"Spotify error: {e}")
        return "Sorry, I'm having trouble with Spotify right now."

def send_whatsapp_message(number: str = None, message: str = None) -> str:
    try:
        if not number:
            # Extract phone number from command
            user_input = request.json.get("command", "")
            number_match = re.search(r'(\+?\d{10,13})', user_input)
            if not number_match:
                return "Please provide a phone number with the message."
            number = number_match.group(1)
        
        if not message:
            message = "Hello from NEXA!"
        
        pywhatkit.sendwhatmsg_instantly(number, message, wait_time=15)
        return f"Message sent to {number}."
    except Exception as e:
        return f"Failed to send WhatsApp message: {str(e)}"

# Routes
@app.route("/")
def home():
    return render_template("index.html",show_mic = True)

@app.route("/command", methods=["POST"])
def handle_command():
    user_input = request.json.get("command", "").lower().strip()
    if not user_input:
        return jsonify({"response": "Please provide a command."})
    
    print(f"[User command]: {user_input}")

    response = (
        system_command(user_input)
        or open_website(user_input)
        or get_datetime(user_input)
        or play_media(user_input)
        or ("send message" in user_input and send_whatsapp_message())
        or ("weather" in user_input and get_weather())
        or (("who is" in user_input or "what is" in user_input) and search_wikipedia(user_input))
        or "Sorry, I didn't understand that. Please try something else."
    )

    if response:
        speak(response)
        return jsonify({"response": response})
    
    return jsonify({"response": "I'm still learning. Please try another command."})

@app.route('/callback')
def callback():
    return "Spotify authentication successful. You can close this window."

# Graceful Shutdown Handler
def shutdown_handler(signum, frame):
    print("\nShutting down gracefully...")
    speech_engine.shutdown()
    sys.exit(0)

if __name__ == "__main__":
     # Register signal handlers
    signal.signal(signal.SIGINT, shutdown_handler)  # Ctrl+C
    signal.signal(signal.SIGTERM, shutdown_handler)  # Termination

    # Initial greeting (outside Flask's auto-reloader)
    if not os.environ.get("WERKZEUG_RUN_MAIN"):
        speak("Hello, I am NEXA. How can I help you today?")

    app.run(debug=True)