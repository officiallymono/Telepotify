import requests
import base64
import time
import os
from dotenv import load_dotenv
from telegram import Bot
from telegram.ext import CommandHandler, CallbackContext, ApplicationBuilder
from telegram import Update
from spotdl import download

# Load environment variables from .env file
load_dotenv()

# Get variables
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHANNEL_ID = os.getenv('CHANNEL_ID')
TARGET_MESSAGE_ID = int(os.getenv('TARGET_MESSAGE_ID'))
BOT_URL = os.getenv('BOT_URL')
SPOTIFY_USERNAME = os.getenv('SPOTIFY_USERNAME')  # Load the Spotify username variable

# Global variable to track whether to check the current song
check_current_song = True

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
    url = f"https://api.spotify.com/v1/users/{SPOTIFY_USERNAME}/player/currently-playing"  # Updated to include username
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

# Function to update the target message in the channel
def update_channel_message(bot: Bot, text: str):
    try:
        bot.edit_message_text(chat_id=CHANNEL_ID, message_id=TARGET_MESSAGE_ID, text=text)
        print("Channel message updated.")
    except Exception as e:
        print("Error updating message:", e)

# Function to track song changes
def track_current_song(bot: Bot):
    global check_current_song  # Use the global variable
    last_track = None
    while True:
        if not check_current_song:  # Check if we should continue
            time.sleep(30)  # Wait before checking again
            continue
        
        token = get_spotify_token()
        if token:
            current_track = get_current_playing_track(token)
            if current_track and current_track != last_track:
                update_channel_message(bot, f"🎶 Currently playing: {current_track}\nDownload here: {BOT_URL}/download?track={current_track}")
                last_track = current_track
        time.sleep(30)  # Check every 30 seconds

# Function to download the currently playing track
def download_song(track_name: str, artist: str):
    search_query = f"{track_name} {artist}"
    try:
        # دانلود با استفاده از تابع download
        download([search_query])
        return f"{track_name} از {artist} با موفقیت دانلود شد."
    except Exception as e:
        return f"خطا در دانلود آهنگ: {str(e)}"

# Function to handle the download command
def download_track(update: Update, context: CallbackContext):
    if len(context.args) < 2:
        update.message.reply_text("لطفاً نام آهنگ و هنرمند را وارد کنید.")
        return
    
    track_name = context.args[0]
    artist = context.args[1]
    
    # Call the download function
    result = download_song(track_name, artist)
    
    # Send the result to the user
    update.message.reply_text(result)

# Setting up and running the bot
def main():
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()  # استفاده از ApplicationBuilder

    # Command handler for downloading track
    application.add_handler(CommandHandler('download', download_track))
    
    # Start tracking song changes
    application.job_queue.run_once(lambda context: track_current_song(application.bot), 0)

    # Start the Telegram bot
    application.run_polling()

if __name__ == "__main__":
    main()
