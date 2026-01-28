import os
import requests
import feedparser
import time
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled
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
print("=" * 60)
print("DEBUG: Starting YouTube Monitor")
print("=" * 60)

if GEMINI_API_KEY:
    print(f"✓ GEMINI_API_KEY found (first 5 chars: {GEMINI_API_KEY[:5]}...)")
else:
    print("✗ GEMINI_API_KEY MISSING")

if TELEGRAM_BOT_TOKEN:
    print(f"✓ TELEGRAM_BOT_TOKEN found (length: {len(TELEGRAM_BOT_TOKEN)})")
else:
    print("✗ TELEGRAM_BOT_TOKEN MISSING")

if TELEGRAM_CHAT_ID:
    print(f"✓ TELEGRAM_CHAT_ID found: {TELEGRAM_CHAT_ID}")
else:
    print("✗ TELEGRAM_CHAT_ID MISSING")

print("=" * 60)

def send_telegram_message(message_text):
    """Sends a notification message via Telegram bot."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("ERROR: Telegram credentials missing.")
        return False

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message_text,
            'parse_mode': 'Markdown',
            'disable_web_page_preview': True
        }
        
        response = requests.post(url, data=payload, timeout=30)
        
        if response.status_code == 200:
            print("LOG: Telegram message sent successfully.")
            return True
        else:
            print(f"ERROR: Failed to send Telegram message. Status: {response.status_code}")
            print(f"Response: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"ERROR: Telegram API error: {e}")
        return False

def analyze_transcript_with_gemini(transcript, keywords):
    """Uses Gemini to determine if transcript is relevant to AT LEAST ONE keyword."""
    if not GEMINI_API_KEY:
        print("ERROR: Gemini API Key missing.")
        return False

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        keyword_list = ", ".join(keywords)
        
        # Limit transcript length to avoid token limits (keep it reasonable)
        transcript_short = transcript[:15000] if len(transcript) > 15000 else transcript
        
        # CRITICAL: Ask if relevant to ANY (at least one) of the keywords
        prompt = f"""
        Analyze this YouTube video transcript. Determine if the main topic is related to AT LEAST ONE of these topics:
        
        Topics: {keyword_list}
        
        IMPORTANT: Return {{"relevant": true}} if the video is about ANY ONE of these topics (even just one).
        Return {{"relevant": false}} only if it's NOT about ANY of these topics.
        
        Respond with ONLY the JSON object, no other text.
        
        Transcript: {transcript_short}
        """
        
        print(f"LOG: Asking Gemini if video is relevant to ANY of: {keyword_list}")
        
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=50
            )
        )
        
        # Parse response
        response_text = response.text.strip()
        print(f"LOG: Gemini raw response: {response_text}")
        
        # Check for true/false in the response
        if '"relevant": true' in response_text or "'relevant': true" in response_text:
            print("LOG: Gemini analysis: RELEVANT (matches at least one topic)")
            return True
        else:
            print("LOG: Gemini analysis: NOT RELEVANT (doesn't match any topic)")
            return False

    except Exception as e:
        print(f"ERROR: Gemini analysis failed: {e}")
        return False

def get_latest_videos(channel_id):
    """Fetches ALL videos from the last 24 hours."""
    feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    
    print(f"  Fetching RSS feed: {feed_url}")
    
    try:
        feed = feedparser.parse(feed_url)
        videos = []
        
        if not feed.entries:
            print(f"  No videos found in RSS feed")
            return videos
        
        video_count = 0
        for entry in feed.entries:  # Check ALL entries
            try:
                # Parse published time
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    published_timestamp = time.mktime(entry.published_parsed)
                    
                    # Check if video from last 24 hours
                    if time.time() - published_timestamp < 86400:
                        # Extract video ID from URL
                        video_link = entry.link
                        if 'v=' in video_link:
                            video_id = video_link.split('v=')[1].split('&')[0]
                            videos.append({
                                'title': entry.title,
                                'link': entry.link,
                                'id': video_id,
                                'published': time.strftime('%Y-%m-%d %H:%M:%S', entry.published_parsed)
                            })
                            video_count += 1
                            print(f"    Found ({video_count}): {entry.title[:60]}...")
            except Exception as e:
                print(f"    Error parsing video: {e}")
                continue
                
        print(f"  Total videos from last 24 hours: {video_count}")
        return videos
        
    except Exception as e:
        print(f"  ERROR: Failed to fetch RSS feed: {e}")
        return []

def main():
    """Main execution function."""
    relevant_videos_summary = []
    total_videos_checked = 0
    
    print("\n" + "=" * 60)
    print("STARTING CHANNEL CHECKS")
    print("=" * 60)

    for channel_name, config in CHANNELS_TO_WATCH.items():
        print(f"\n🔍 Checking: {channel_name}")
        print(f"   Channel ID: {config['id']}")
        print(f"   Looking for ANY of these topics: {', '.join(config['keywords'])}")
        
        latest_videos = get_latest_videos(config["id"])
        
        for video in latest_videos:
            total_videos_checked += 1
            print(f"\n  📺 Video {total_videos_checked}: {video['title'][:70]}...")
            print(f"     Published: {video.get('published', 'Unknown')}")
            print(f"     Video ID: {video['id']}")
            
            try:
                # Try multiple language options
                transcript_list = YouTubeTranscriptApi.get_transcript(
                    video['id'], 
                    languages=['en', 'hi', 'en-US', 'en-IN']
                )
                transcript_text = ' '.join([t['text'] for t in transcript_list])
                print(f"     Transcript length: {len(transcript_text)} chars")
                
                # Check if relevant to ANY keyword
                if analyze_transcript_with_gemini(transcript_text, config["keywords"]):
                    relevant_videos_summary.append(f"• [{video['title']}]({video['link']}) - {channel_name}")
                    print(f"     ✅ RELEVANT - Matches at least one topic")
                else:
                    print(f"     ❌ Not relevant to any specified topic")

            except TranscriptsDisabled:
                print(f"     ⚠️ Transcripts disabled for this video")
            except Exception as e:
                print(f"     ⚠️ Error processing transcript: {type(e).__name__}: {str(e)[:80]}")

    print(f"\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Channels checked: {len(CHANNELS_TO_WATCH)}")
    print(f"Total videos checked (last 24h): {total_videos_checked}")
    print(f"Relevant videos found (matches ANY topic): {len(relevant_videos_summary)}")
    
    if relevant_videos_summary:
        # If many videos, limit message length
        if len(relevant_videos_summary) > 15:
            message = f"🚨 **{len(relevant_videos_summary)} New Relevant YouTube Videos Found:**\n\n"
            message += "\n".join(relevant_videos_summary[:15])
            message += f"\n\n... and {len(relevant_videos_summary) - 15} more videos"
        else:
            message = f"🚨 **{len(relevant_videos_summary)} New Relevant YouTube Videos Found:**\n\n"
            message += "\n".join(relevant_videos_summary)
        
        send_telegram_message(message)
    else:
        message = "✅ **Daily YouTube Check:** No relevant videos found in the last 24 hours matching your criteria."
        send_telegram_message(message)
    
    print("\n" + "=" * 60)
    print("SCRIPT COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    main()
