import os
import requests
import feedparser
import time
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled
from google import genai
from google.genai import types

# --- Configuration Section (EDIT THIS with your IDs and Keywords) ---
CHANNELS_TO_WATCH = {
    "Mint": {
        "id": "UCUI9vm69ZbAqRK3q3vKLWCQ", # REPLACE THIS with actual channel ID
        "keywords": ["Indian economy", "economics", "india international trade", "india government schemes", "tax", "gdp", "inflation", "budget", "economic survey", "rbi"]
    },
    "Mrunal Unacedmy": {
        "id": "UCwDfgcUkKKTxPozU9UnQ8Pw", # REPLACE THIS with actual channel ID
        "keywords": ["Indian government schemes", "government policy", "monthly economy"]
    },
    "OnlyIAS Ext.": {
        "id": "UCAidhU356a0ej2MtFEylvBA", # REPLACE THIS with actual channel ID
        "keywords": ["Monthly government schemes", "Important government scheme in news"]
    },
    "Vajiram Ravi": {
        "id": "UCzelA5kqD9v6k6drK44l4_g", # REPLACE THIS with actual channel ID
        "keywords": ["Indian economy", "economics", "india international trade", "india government schemes", "tax", "gdp", "inflation", "budget", "economic survey", "rbi"]
    },
    "DrishtiIAS Hindi": {
        "id": "UCzLqOSZPtUKrmSEnlH4LAvw", # REPLACE THIS with actual channel ID
        "keywords": ["Indian economy", "economics", "india international trade", "india government schemes", "tax", "gdp", "inflation", "budget", "economic survey", "rbi"]
    },
    "DrishtiIAS English": {
        "id": "UCafpueX9hFLls24ed6UddEQ", # REPLACE THIS with actual channel ID
        "keywords": ["Indian economy", "economics", "india international trade", "india government schemes", "tax", "gdp", "inflation", "budget", "economic survey", "rbi", "economics concept explainer"]
    },
    "Sleepy Classes": {
        "id": "UCgRf62bnK3uX4N-YEhG4Jog", # REPLACE THIS with actual channel ID
        "keywords": ["Indian economy", "economics", "india international trade", "india government schemes", "tax", "gdp", "inflation", "budget", "economic survey", "rbi", "economics concept explainer"]
    },
    "CareerWill": {
        "id": "UCmS9VpdkUNhyOKtKQrtFV1Q", # REPLACE THIS with actual channel ID
        "keywords": ["Indian economy", "economics", "india international trade", "india government schemes", "tax", "gdp", "inflation", "budget", "economic survey", "rbi", "economics concept explainer"]
    }
}

# --- Environment Variables (Read from GitHub Secrets automatically in Step 6) ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# --- DEBUGGING LINES ---
if GEMINI_API_KEY:
    print("DEBUG: Gemini API Key found.")
else:
    print("DEBUG: Gemini API Key MISSING.")
if TELEGRAM_BOT_TOKEN:
    print("DEBUG: Telegram Token found (Length:", len(TELEGRAM_BOT_TOKEN), ").")
else:
    print("DEBUG: Telegram Token MISSING.")
if TELEGRAM_CHAT_ID:
    print("DEBUG: Telegram Chat ID found.")
else:
    print("DEBUG: Telegram Chat ID MISSING.")
# --- END DEBUGGING LINES ---


def send_telegram_message(message_text):
    """Sends a notification message via Telegram bot."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("ERROR: Telegram credentials missing.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message_text,
        'parse_mode': 'Markdown',
        'disable_web_page_preview': True
    }
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        print("LOG: Telegram message sent successfully.")
    else:
        print(f"ERROR: Failed to send Telegram message. Status Code: {response.status_code}, Response: {response.text}")

def analyze_transcript_with_gemini(transcript, keywords):
    """Uses Gemini to determine if transcript is relevant to keywords."""
    if not GEMINI_API_KEY:
        print("ERROR: Gemini API Key missing.")
        return False

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        keyword_list = ", ".join(keywords)
        
        prompt = f"""
        Analyze the provided YouTube video transcript. Determine if the main topic of the video is directly related to any of the following keywords: 
        "{keyword_list}".

        Respond with a simple JSON object: {{"relevant": true}} if relevant, or {{"relevant": false}} if not. 
        Do not include any other text or explanation.
        """
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[prompt, transcript],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema={"type": "object", "properties": {"relevant": {"type": "boolean"}}}
            )
        )
        
        relevance = response.candidates.content.parts.json["relevant"]
        print(f"LOG: Gemini analysis complete. Result: {relevance}")
        return relevance

    except Exception as e:
        print(f"ERROR: Gemini analysis failed: {e}")
        return False

def get_latest_videos(channel_id):
    """Fetches latest videos from RSS feed."""
    feed_url = f"https://www.youtube.com{channel_id}"
    feed = feedparser.parse(feed_url)
    videos = []
    for entry in feed.entries[:10]:
        published_timestamp = time.mktime(entry.published_parsed)
        if time.time() - published_timestamp < 86400: # Check videos from the last 24 hours
            videos.append({'title': entry.title, 'link': entry.link, 'id': entry.yt_videoid})
    return videos

def main():
    """Main execution function."""
    relevant_videos_summary = []

    for channel_name, config in CHANNELS_TO_WATCH.items():
        print(f"LOG: Checking {channel_name}...")
        latest_videos = get_latest_videos(config["id"])
        
        for video in latest_videos:
            try:
                transcript_list = YouTubeTranscriptApi.get_transcript(video['id'], languages=['en', 'hi', 'en-US'])
                transcript_text = ' '.join([t['text'] for t in transcript_list])
                
                if analyze_transcript_with_gemini(transcript_text, config["keywords"]):
                    relevant_videos_summary.append(f"* [{video['title']}]({video['link']}) (Channel: {channel_name})")
                    print(f"LOG: Matched video: {video['title']}")
                else:
                    print(f"LOG: Not relevant video: {video['title']}")

            except TranscriptsDisabled:
                print(f"WARN: Transcripts disabled for video {video['id']}, skipping analysis.")
            except Exception as e:
                print(f"ERROR: An unexpected error occurred while processing video {video['id']}: {e}")

    if relevant_videos_summary:
        # Send message with list of videos if found
        message = "🚨 **New Relevant YouTube Videos Found:**\n\n" + "\n".join(relevant_videos_summary)
        send_telegram_message(message)
    else:
        # Send a "No videos found" message if list is empty
        message = "✅ **Daily YouTube Check:** No relevant videos found in the last 24 hours matching your criteria."
        send_telegram_message(message)

if __name__ == "__main__":
    main()
