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
TARGET_MESSAGE_ID = int(os.getenv('TARGET_MESSAGE_ID'))
BOT_URL = os.getenv('BOT_URL')

# Initialize Spotify client with OAuth
sp_oauth = SpotifyOAuth(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET,
    redirect_uri='http://localhost:8889/callback',
    scope='user-read-currently-playing user-read-playback-state'
)
spotify = Spotify(auth_manager=sp_oauth)

# Global variable to track whether to check the current song
check_current_song = True

# Function to get currently playing track from Spotify
def get_current_playing_track():
    try:
        current_song = spotify.current_user_playing_track()
        if current_song and current_song["is_playing"]:
            item = current_song["item"]
            artist = item["artists"][0]["name"]
            track_name = item["name"]
            return track_name, artist
        else:
            return None, None
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
    global check_current_song
    last_track = None
    while check_current_song:
        track_name, artist = get_current_playing_track()
        if track_name and artist:
            current_track = f"{track_name} by {artist}"
            if current_track != last_track:
                await update_channel_message(app, f"🎶 Currently playing: {current_track}\nDownload here: {BOT_URL}/download?track={track_name}&artist={artist}")
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

# Function to handle the download command
async def send_downloaded_file(client: Client, chat_id: int, track_name: str, artist: str):
    result = download_song(track_name, artist)
    if "با موفقیت دانلود شد." in result:
        file_path = f"{track_name} - {artist}.mp3"
        if os.path.exists(file_path):
            await client.send_audio(chat_id=chat_id, audio=file_path)
        else:
            await client.send_message(chat_id=chat_id, text="فایل دانلود شده پیدا نشد.")
    else:
        await client.send_message(chat_id=chat_id, text=result)

# Function to handle the /download command
@Client.on_message(filters.command("download"))
async def download_track(client: Client, message):
    args = message.command[1:]  # Get command arguments
    if len(args) < 2:
        await message.reply_text("لطفاً نام آهنگ و هنرمند را وارد کنید.")
        return
    
    track_name = args[0]
    artist = args[1]
    
    await send_downloaded_file(client, message.chat.id, track_name, artist)

# Function to start the OAuth process
def start_auth():
    auth_url = sp_oauth.get_authorize_url()
    print("Visit this URL to authorize the application:", auth_url)
    
    code = input("Enter the code from the URL: ")
    token_info = sp_oauth.get_access_token(code)

    return token_info

# Setting up and running the bot
if __name__ == "__main__":
    app = Client("my_bot", bot_token=TELEGRAM_BOT_TOKEN)
    
    async def main():
        token_info = start_auth()
        
        if token_info is None or 'access_token' not in token_info:
            print("Failed to obtain access token.")
            return

        async with app:
            asyncio.create_task(track_current_song(app))
            await app.idle()  # This keeps the bot running until you manually stop it.

    asyncio.run(main())
