import os
from dotenv import load_dotenv
from pyrogram import Client, filters
from spotdl import download
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
import asyncio
import logging

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Get variables
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHANNEL_ID = os.getenv('CHANNEL_ID')
TARGET_MESSAGE_ID = os.getenv('TARGET_MESSAGE_ID')
BOT_URL = os.getenv('BOT_URL')
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
REDIRECT_URI = os.getenv('REDIRECT_URI')

# Check for missing environment variables
if not all([SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, TELEGRAM_BOT_TOKEN, CHANNEL_ID, TARGET_MESSAGE_ID, BOT_URL, API_ID, API_HASH, REDIRECT_URI]):
    logging.error("Missing one or more environment variables.")
    exit(1)

# Initialize Spotify client with OAuth
sp_oauth = SpotifyOAuth(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope='user-read-currently-playing user-read-playback-state'
)

# Initialize Spotify variable
spotify = None

# Function to get the currently playing track
def get_current_playing_track():
    global spotify
    try:
        current_track = spotify.current_playback()
        if current_track and current_track.get('is_playing'):
            track_name = current_track['item']['name']
            artist = current_track['item']['artists'][0]['name']
            return track_name, artist
    except Exception as e:
        logging.error("Error fetching current track: %s", e)
    return None, None

# Async function to update the target message in the channel
async def update_channel_message(app: Client, text: str):
    try:
        await app.edit_message_text(chat_id=CHANNEL_ID, message_id=TARGET_MESSAGE_ID, text=text)
        logging.info("Channel message updated.")
    except Exception as e:
        logging.error("Error updating message: %s", e)
        await app.send_message(chat_id=CHANNEL_ID, text=f"خطا در به‌روزرسانی پیام: {str(e)}")

# Async function to track song changes
async def track_current_song(app: Client):
    last_track = None
    while True:
        track_name, artist = get_current_playing_track()
        if track_name and artist:
            current_track = f"{track_name} by {artist}"
            if current_track != last_track:
                # Create download link
                download_link = f"{BOT_URL}/download?track={track_name}&artist={artist}"
                await update_channel_message(app, f"🎶 Currently playing: {current_track}\nDownload here: {download_link}")
                last_track = current_track
        await asyncio.sleep(10)

# Function to download the currently playing track
def download_song(track_name: str, artist: str):
    search_query = f"{track_name} {artist}"
    try:
        download([search_query])
        return f"{track_name} از {artist} با موفقیت دانلود شد."
    except Exception as e:
        return f"خطا در دانلود آهنگ: {str(e)}"

# Function to handle the /download command
@Client.on_message(filters.command("download"))
async def download_track(client: Client, message):
    args = message.command[1:]
    if len(args) < 2:
        await message.reply_text("لطفاً نام آهنگ و هنرمند را وارد کنید.")
        return
    
    track_name = args[0]
    artist = " ".join(args[1:])  # Join the remaining args for artist name
    
    # Call the download function and send the response
    response_message = download_song(track_name, artist)
    await message.reply_text(response_message)

# Function to start the OAuth process
async def start_auth():
    auth_url = sp_oauth.get_authorize_url()
    print("Visit this URL to authorize the application:", auth_url)
    
    code = input("Enter the code from the URL: ")
    
    # Exchange the authorization code for an access token
    token_info = sp_oauth.get_access_token(code)
    
    if not token_info:
        logging.error("Failed to obtain access token.")
        print("Failed to obtain access token.")
        return None
    
    return token_info

# Setting up and running the bot
async def main():
    logging.info("Starting the bot...")
    global spotify  # Declare that we're using the global variable
    token_info = await start_auth()
    
    if token_info is None or 'access_token' not in token_info:
        logging.error("Failed to obtain access token.")
        return

    # Initialize Spotify client with the new access token
    spotify = Spotify(auth=token_info['access_token'])

    app = Client("my_bot", bot_token=TELEGRAM_BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)
    
    # Start the app only if not already connected
    if not app.is_connected:
        async with app:
            asyncio.create_task(track_current_song(app))
            await app.start()  # Start the app
            await app.idle()   # Keep the bot running

if __name__ == "__main__":
    asyncio.run(main())
