import requests
import os
from dotenv import load_dotenv
from telegram import Bot
from telegram.ext import CommandHandler, CallbackContext, ApplicationBuilder
from telegram import Update
from spotdl import download
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
import asyncio

# Load environment variables from .env file
load_dotenv()

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
    redirect_uri='http://localhost:8889/callback',  # تغییر پورت به 8889
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
            return track_name, artist  # Returning both track name and artist
        else:
            return None, None
    except Exception as e:
        print("Error fetching current track:", e)
        return None, None

# Async function to update the target message in the channel
async def update_channel_message(bot: Bot, text: str):
    try:
        await bot.edit_message_text(chat_id=CHANNEL_ID, message_id=TARGET_MESSAGE_ID, text=text)
        print("Channel message updated.")
    except Exception as e:
        print("Error updating message:", e)

# Async function to track song changes
async def track_current_song(bot: Bot):
    global check_current_song
    last_track = None
    while check_current_song:
        track_name, artist = get_current_playing_track()
        if track_name and artist:
            current_track = f"{track_name} by {artist}"
            if current_track != last_track:
                await update_channel_message(bot, f"🎶 Currently playing: {current_track}\nDownload here: {BOT_URL}/download?track={track_name}&artist={artist}")
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
async def send_downloaded_file(update: Update, context: CallbackContext, track_name: str, artist: str):
    result = download_song(track_name, artist)
    if "با موفقیت دانلود شد." in result:
        # فرض کنید نام فایل دانلود شده با فرمت مشخصی ذخیره می‌شود
        file_path = f"{track_name} - {artist}.mp3"  # نام فایل دانلود شده
        await context.bot.send_audio(chat_id=update.effective_chat.id, audio=open(file_path, 'rb'))
    else:
        await update.message.reply_text(result)

# Function to handle the /download command
def download_track(update: Update, context: CallbackContext):
    if len(context.args) < 2:
        update.message.reply_text("لطفاً نام آهنگ و هنرمند را وارد کنید.")
        return
    
    track_name = context.args[0]
    artist = context.args[1]
    
    # فراخوانی تابع ارسال فایل
    asyncio.create_task(send_downloaded_file(update, context, track_name, artist))

# Function to start the OAuth process
def start_auth():
    auth_url = sp_oauth.get_authorize_url()
    print("Visit this URL to authorize the application:", auth_url)
    
    #  گرفتن کد دستی
    code = input("Enter the code from the URL: ")  # اضافه کردن این خط
    token_info = sp_oauth.get_access_token(code)  # از کد استفاده کن

    return token_info

# Setting up and running the bot
async def main():
    # Get Spotify token at the start
    token_info = start_auth()

    if token_info is None or 'access_token' not in token_info:
        print("Failed to obtain access token.")
        return

    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler('download', download_track))

    # Start tracking song changes in the background
    asyncio.create_task(track_current_song(application.bot))

    await application.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
