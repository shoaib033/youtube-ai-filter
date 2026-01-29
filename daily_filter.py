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

def analyze_title_with_gemini(video_title, keywords, channel_name):
    """Fallback: Analyze video title with Gemini when transcript fails."""
    if not GEMINI_API_KEY:
        print("ERROR: Gemini API Key missing.")
        return False

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        keyword_list = ", ".join(keywords)
        
        prompt = f"""
        Analyze this YouTube video title. Determine if this video is about ANY of these specific topics:
        
        VIDEO TITLE: "{video_title}"
        CHANNEL: {channel_name}
        TOPICS TO CHECK: {keyword_list}
        
        IMPORTANT: Only consider if it's about Indian economy, economics, government schemes, budget, trade, RBI, or economic policies.
        
        Respond with ONLY one word: YES or NO
        """
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[prompt],
            config=types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=10
            )
        )
        
        # Extract response text
        if hasattr(response, 'text'):
            response_text = response.text.strip().upper()
        else:
            response_text = response.candidates[0].content.parts[0].text.strip().upper()
        
        print(f"LOG: Title analysis result: {response_text}")
        
        return "YES" in response_text

    except Exception as e:
        print(f"ERROR: Gemini title analysis failed: {e}")
        return False

def check_keyword_match(video_title, keywords):
    """Simple keyword matching as final fallback."""
    title_lower = video_title.lower()
    
    for keyword in keywords:
        if keyword.lower() in title_lower:
            print(f"LOG: Matched keyword '{keyword}' in title")
            return True
    
    # Additional economic terms
    economic_terms = ['budget', 'economic', 'economy', 'gdp', 'inflation', 'tax', 'trade', 
                      'rbi', 'finance', 'scheme', 'policy', 'government', 'fiscal', 'monetary']
    
    for term in economic_terms:
        if term in title_lower:
            print(f"LOG: Matched economic term '{term}' in title")
            return True
    
    return False

def get_latest_videos(channel_id):
    """Fetches latest videos from RSS feed."""
    feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    feed = feedparser.parse(feed_url)
    videos = []
    
    for entry in feed.entries[:10]:
        published_timestamp = time.mktime(entry.published_parsed)
        if time.time() - published_timestamp < 86400: # Check videos from the last 24 hours
            # Extract video ID from link
            if 'v=' in entry.link:
                video_id = entry.link.split('v=')[1].split('&')[0]
                videos.append({
                    'title': entry.title, 
                    'link': entry.link, 
                    'id': video_id,
                    'published': time.strftime('%Y-%m-%d %H:%M', entry.published_parsed)
                })
    return videos

def main():
    """Main execution function."""
    relevant_videos_summary = []
    
    # Test Gemini connection first
    print("\n" + "="*60)
    print("STARTING YOUTUBE MONITOR")
    print("="*60)

    for channel_name, config in CHANNELS_TO_WATCH.items():
        print(f"\nLOG: Checking {channel_name}...")
        latest_videos = get_latest_videos(config["id"])
        
        if not latest_videos:
            print(f"LOG: No videos found in last 24 hours for {channel_name}")
            continue
            
        print(f"LOG: Found {len(latest_videos)} recent videos")
        
        for video in latest_videos:
            print(f"\n  Video: {video['title']}")
            print(f"  Published: {video['published']}")
            
            try:
                # Try to get transcript first
                transcript_list = YouTubeTranscriptApi.get_transcript(video['id'], languages=['en', 'hi', 'en-US'])
                transcript_text = ' '.join([t['text'] for t in transcript_list])
                
                # Analyze transcript with Gemini
                if analyze_transcript_with_gemini(transcript_text, config["keywords"]):
                    relevant_videos_summary.append(f"* [{video['title']}]({video['link']}) (Channel: {channel_name})")
                    print(f"  LOG: ✓ ADDED (Transcript analysis)")
                    continue
                else:
                    print(f"  LOG: ✗ Not relevant (Transcript analysis)")
                    
            except TranscriptsDisabled:
                print(f"  WARN: Transcripts disabled, trying title analysis...")
            except Exception as e:
                print(f"  WARN: Could not get transcript: {e}, trying title analysis...")
            
            # Fallback 1: Analyze title with Gemini
            if analyze_title_with_gemini(video['title'], config["keywords"], channel_name):
                relevant_videos_summary.append(f"* [{video['title']}]({video['link']}) (Channel: {channel_name}) [Title Analysis]")
                print(f"  LOG: ✓ ADDED (Title analysis)")
                continue
            
            # Fallback 2: Simple keyword matching
            if check_keyword_match(video['title'], config["keywords"]):
                relevant_videos_summary.append(f"* [{video['title']}]({video['link']}) (Channel: {channel_name}) [Keyword Match]")
                print(f"  LOG: ✓ ADDED (Keyword match)")
            else:
                print(f"  LOG: ✗ Not relevant (All checks failed)")

    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    if relevant_videos_summary:
        message = "🚨 **New Relevant YouTube Videos Found:**\n\n" + "\n".join(relevant_videos_summary)
        message += f"\n\n🕒 *Checked at:* {time.strftime('%Y-%m-%d %H:%M IST')}"
        send_telegram_message(message)
        print(f"LOG: Sent notification with {len(relevant_videos_summary)} videos")
    else:
        message = f"""
✅ **Daily YouTube Check Complete**

*Status:* No relevant videos found in the last 24 hours matching your criteria.

*Channels checked:* {', '.join(CHANNELS_TO_WATCH.keys())}

*Time:* {time.strftime('%Y-%m-%d %H:%M IST')}
        """
        send_telegram_message(message)
        print("LOG: Sent 'no videos found' notification")

if __name__ == "__main__":
    main()
