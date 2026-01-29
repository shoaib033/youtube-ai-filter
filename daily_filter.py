import os
import requests
import feedparser
import time
from google import genai
from google.genai import types

# --- Configuration Section ---
CHANNELS_TO_WATCH = {
    "Mint": {
        "id": "UCUI9vm69ZbAqRK3q3vKLWCQ",
        "keywords": ["Indian economy", "economics", "india international trade", "india government schemes", "tax", "gdp", "inflation", "budget", "economic survey", "rbi"]
    },
    "Mrunal Unacedmy": {
        "id": "UCwDfgcUkKKTxPozU9UnQ8Pw",
        "keywords": ["Indian government schemes", "government policy", "monthly economy"]
    },
    "OnlyIAS Ext.": {
        "id": "UCAidhU356a0ej2MtFEylvBA",
        "keywords": ["Monthly government schemes", "Important government scheme in news"]
    },
    "Vajiram Ravi": {
        "id": "UCzelA5kqD9v6k6drK44l4_g",
        "keywords": ["Indian economy", "economics", "india international trade", "india government schemes", "tax", "gdp", "inflation", "budget", "economic survey", "rbi"]
    },
    "DrishtiIAS Hindi": {
        "id": "UCzLqOSZPtUKrmSEnlH4LAvw",
        "keywords": ["Indian economy", "economics", "india international trade", "india government schemes", "tax", "gdp", "inflation", "budget", "economic survey", "rbi"]
    },
    "DrishtiIAS English": {
        "id": "UCafpueX9hFLls24ed6UddEQ",
        "keywords": ["Indian economy", "economics", "india international trade", "india government schemes", "tax", "gdp", "inflation", "budget", "economic survey", "rbi", "economics concept explainer"]
    },
    "Sleepy Classes": {
        "id": "UCgRf62bnK3uX4N-YEhG4Jog",
        "keywords": ["Indian economy", "economics", "india international trade", "india government schemes", "tax", "gdp", "inflation", "budget", "economic survey", "rbi", "economics concept explainer"]
    },
    "CareerWill": {
        "id": "UCmS9VpdkUNhyOKtKQrtFV1Q",
        "keywords": ["Indian economy", "economics", "india international trade", "india government schemes", "tax", "gdp", "inflation", "budget", "economic survey", "rbi", "economics concept explainer"]
    }
}

# --- Environment Variables ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# --- DEBUGGING LINES ---
if GEMINI_API_KEY:
    print("DEBUG: Gemini API Key found.")
else:
    print("DEBUG: Gemini API Key MISSING.")
if TELEGRAM_BOT_TOKEN:
    print(f"DEBUG: Telegram Token found (Length: {len(TELEGRAM_BOT_TOKEN)}).")
    print(f"DEBUG: Token preview: {TELEGRAM_BOT_TOKEN[:20]}...")
else:
    print("DEBUG: Telegram Token MISSING.")
if TELEGRAM_CHAT_ID:
    print("DEBUG: Telegram Chat ID found.")
else:
    print("DEBUG: Telegram Chat ID MISSING.")

def send_telegram_message(message_text):
    """Sends a notification message via Telegram bot."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram credentials missing, cannot send message.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    print(f"DEBUG: Telegram URL being used: https://api.telegram.org/bot[...hidden...]/sendMessage")
    
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message_text,
        'parse_mode': 'Markdown',
        'disable_web_page_preview': True
    }
    
    try:
        response = requests.post(url, data=payload, timeout=30)
        print(f"DEBUG: Telegram response status: {response.status_code}")
        
        if response.status_code == 200:
            print("Telegram message sent successfully.")
        else:
            print(f"Failed to send Telegram message: {response.text[:200]}")
    except Exception as e:
        print(f"Telegram API error: {e}")

def analyze_youtube_link_with_gemini(youtube_url, video_title, keywords, channel_name):
    """Uses Gemini to analyze YouTube video directly from URL."""
    if not GEMINI_API_KEY:
        print("GEMINI_API_KEY not set, skipping analysis")
        return False

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        keyword_list = ", ".join(keywords)
        
        prompt = f"""
        Analyze this YouTube video for relevance to Indian Economic Service (IES) and UPSC Economics preparation.
        
        VIDEO TITLE: "{video_title}"
        CHANNEL: {channel_name}
        YOUTUBE URL: {youtube_url}
        
        Check if this video discusses ANY of these topics:
        {keyword_list}
        
        IMPORTANT: Consider the video's title, description, content, and context. 
        This is for exam preparation, so focus on educational content about:
        - Indian economy and economics
        - Government schemes and policies
        - Budget, trade, RBI, fiscal/monetary policy
        - Economic concepts and explanations
        
        Respond with ONLY: RELEVANT or NOT_RELEVANT
        """
        
        # Try different model names
        model_names = [
            'gemini-2.0-flash',  # Newest model
            'gemini-1.5-flash-latest',
            'gemini-1.5-pro-latest',
            'gemini-pro'
        ]
        
        for model_name in model_names:
            try:
                print(f"  Trying model: {model_name}")
                response = client.models.generate_content(
                    model=model_name,
                    contents=[prompt],
                    config=types.GenerateContentConfig(
                        temperature=0.1,
                        max_output_tokens=20
                    )
                )
                
                response_text = response.text.strip().upper()
                print(f"  Gemini response: {response_text}")
                
                return "RELEVANT" in response_text
                
            except Exception as model_error:
                if "404" in str(model_error) or "not found" in str(model_error).lower():
                    continue  # Try next model
                else:
                    print(f"  Model {model_name} error: {type(model_error).__name__}")
                    break
        
        print("  All Gemini models failed")
        return False

    except Exception as e:
        print(f"  Gemini analysis failed: {e}")
        return False

def get_latest_videos(channel_id):
    """Fetches latest videos from RSS feed."""
    feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    feed = feedparser.parse(feed_url)
    videos = []
    
    for entry in feed.entries[:5]:  # Check latest 5 videos
        try:
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                published_timestamp = time.mktime(entry.published_parsed)
                # Check if from last 24 hours
                if time.time() - published_timestamp < 86400:
                    videos.append({
                        'title': entry.title,
                        'link': entry.link,
                        'id': entry.link.split('v=')[1].split('&')[0] if 'v=' in entry.link else None
                    })
        except Exception as e:
            print(f"Error parsing video: {e}")
            continue
            
    return videos

def main():
    """Main execution function."""
    relevant_videos_summary = []

    for channel_name, config in CHANNELS_TO_WATCH.items():
        print(f"\nLOG: Checking {channel_name}...")
        latest_videos = get_latest_videos(config["id"])
        
        for video in latest_videos:
            try:
                print(f"\n  Processing: {video['title'][:60]}...")
                
                if analyze_youtube_link_with_gemini(video['link'], video['title'], config["keywords"], channel_name):
                    relevant_videos_summary.append(f"* [{video['title']}]({video['link']}) (Channel: {channel_name})")
                    print(f"  ✅ Matched: {video['title']}")
                else:
                    print(f"  ❌ Not relevant: {video['title']}")

            except Exception as e:
                print(f"  ⚠️ Error processing video: {type(e).__name__}")

    if relevant_videos_summary:
        message = "🚨 **New Relevant YouTube Videos Found:**\n\n" + "\n".join(relevant_videos_summary)
        send_telegram_message(message)
    else:
        print("\nNo new relevant videos found in the last 24 hours.")
        send_telegram_message("✅ No new relevant videos found in the last 24 hours.")

if __name__ == "__main__":
    main()
