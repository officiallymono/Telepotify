import os
import base64
from flask import Flask, request, jsonify
from pyrogram import Client

app = Flask(__name__)

# Load environment variables
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHANNEL_ID = os.getenv('CHANNEL_ID')
TARGET_MESSAGE_ID = int(os.getenv('TARGET_MESSAGE_ID'))

# Global variable to track whether to check the current song
check_current_song = True

# Initialize Pyrogram Client
client = Client("my_bot", bot_token=TELEGRAM_BOT_TOKEN)

# Function to get Spotify token
def get_spotify_token():
    url = "https://accounts.spotify.com/api/token"
    headers = {
        "Authorization": "Basic " + base64.b64encode((SPOTIFY_CLIENT_ID + ":" + SPOTIFY_CLIENT_SECRET).encode()).decode()
    }
    data = {
        "grant_type": "client_credentials"
    }
    response = requests.post(url, headers=headers, data=data)
    if response.status_code == 200:
        return response.json().get("access_token")
    else:
        print("Error fetching Spotify token:", response.json())
        return None

# Function to get currently playing track from Spotify
def get_current_playing_track(token):
    url = "https://api.spotify.com/v1/me/player/currently-playing"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200 and response.json():
        item = response.json().get("item")
        artist = item["artists"][0]["name"]
        track_name = item["name"]
        track_url = item["external_urls"]["spotify"]
        return f"{track_name} by {artist}\nListen here: {track_url}"
    elif response.status_code == 204:
        return "No song currently playing"
    else:
        print("Error fetching current track:", response.json())
        return None

@app.route('/webhook', methods=['POST'])
def webhook():
    global check_current_song
    data = request.json
    
    if 'event' in data and data['event'] == 'track_changed':
        token = get_spotify_token()
        if token:
            current_track = get_current_playing_track(token)
            if current_track:
                # Update the message in the channel
                update_channel_message(current_track)
                check_current_song = False

    return jsonify({"status": "success"}), 200

def update_channel_message(text):
    with client:
        client.edit_message_text(chat_id=CHANNEL_ID, message_id=TARGET_MESSAGE_ID, text=text)

if __name__ == "__main__":
    app.run(port=5000)
