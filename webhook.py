import requests
import base64
import os
from flask import Flask, request

app = Flask(__name__)

# Load environment variables
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHANNEL_ID = os.getenv('CHANNEL_ID')
TARGET_MESSAGE_ID = int(os.getenv('TARGET_MESSAGE_ID'))

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
        return f"{track_name} by {artist}"
    elif response.status_code == 204:
        return "No song currently playing"
    else:
        print("Error fetching current track:", response.json())
        return None

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    if 'event' in data and data['event'] == 'track_changed':
        token = get_spotify_token()
        if token:
            current_track = get_current_playing_track(token)
            if current_track:
                # Update the message in the channel
                update_channel_message(current_track)
    return '', 200

def update_channel_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/editMessageText"
    payload = {
        "chat_id": CHANNEL_ID,
        "message_id": TARGET_MESSAGE_ID,
        "text": text
    }
    requests.post(url, json=payload)

if __name__ == "__main__":
    app.run(port=5000)
