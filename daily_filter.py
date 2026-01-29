import os
import requests
import feedparser
import time
from google import genai

# --- Configuration Section (ONLY 2 CHANNELS FOR TESTING) ---
CHANNELS_TO_WATCH = {
    "Mint": {
        "id": "UCUI9vm69ZbAqRK3q3vKLWCQ",
        "keywords": ["Indian economy", "economics", "india international trade", "india government schemes", "tax", "gdp", "inflation", "budget", "economic survey", "rbi"]
    },
    "DrishtiIAS English": {
        "id": "UCafpueX9hFLls24ed6UddEQ",
        "keywords": ["Indian economy", "economics", "india international trade", "india government schemes", "tax", "gdp", "inflation", "budget", "economic survey", "rbi", "economics concept explainer"]
    }
}

# --- Environment Variables ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# --- DEBUGGING LINES ---
if GEMINI_API_KEY:
    print("✓ Gemini API Key found.")
else:
    print("✗ Gemini API Key MISSING.")
if TELEGRAM_BOT_TOKEN:
    print(f"✓ Telegram Token found.")
else:
    print("✗ Telegram Token MISSING.")
if TELEGRAM_CHAT_ID:
    print("✓ Telegram Chat ID found.")
else:
    print("✗ Telegram Chat ID MISSING.")

def send_telegram_message(message_text):
    """Sends a notification message via Telegram bot."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram credentials missing, cannot send message.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message_text,
        'parse_mode': 'Markdown',
        'disable_web_page_preview': True
    }
    
    try:
        response = requests.post(url, data=payload, timeout=30)
        
        if response.status_code == 200:
            print("✓ Telegram message sent successfully.")
        else:
            print(f"✗ Failed to send Telegram message: {response.text[:200]}")
    except Exception as e:
        print(f"✗ Telegram API error: {e}")

def analyze_video_with_retry(youtube_url, video_title, keywords, channel_name, max_retries=3):
    """Analyze YouTube video link using Gemini with retry logic - NUMERICAL RESPONSE."""
    if not GEMINI_API_KEY:
        print("  ✗ Gemini API Key not set")
        return False

    client = genai.Client(api_key=GEMINI_API_KEY)
    
    # Prepare keywords string
    keywords_str = ", ".join(keywords[:6])
    
    # PROMPT: Ask for numerical response (1 or 0)
    prompt = f"""
    Acting as a strict IES (Indian Economic Service)/IAS Exam Economics mentor.
    
    Analyze if this YouTube video is specifically about ECONOMICS for exam preparation.
    
    VIDEO: {video_title}
    URL: {youtube_url}
    CHANNEL: {channel_name}
    
    RELEVANT TOPICS: {keywords_str}
    
    STRICT RULES:
    1. Only mark as relevant if video is PRIMARILY about Indian economy, economics, or economic policy
    2. Must be educational content for IES/UPSC Economics preparation
    3. Must cover specific economic topics from the list above
    4. REJECT general news, ceremonies, cultural events, shorts, entertainment
    
    Respond with ONLY a single digit: 
    1 if RELEVANT
    0 if NOT_RELEVANT
    """

    for attempt in range(max_retries):
        try:
            print(f"  🤖 Attempt {attempt + 1}: Analyzing with Gemini...")
            
            response = client.models.generate_content(
                model="gemini-2.0-flash", 
                contents=prompt,
                generation_config={
                    "temperature": 0.1,
                    "max_output_tokens": 5,  # Very short response
                }
            )
            
            response_text = response.text.strip()
            print(f"  Raw Gemini response: '{response_text}'")
            
            # Parse numerical response
            # Look for "1" in the response (could be "1", "1.", "Answer: 1", etc.)
            if "1" in response_text:
                print("  ✅ Parsed as: RELEVANT (found '1' in response)")
                return True
            else:
                print("  ❌ Parsed as: NOT RELEVANT (no '1' found)")
                return False

        except Exception as e:
            error_msg = str(e)
            
            # Check for Rate Limit (429) or Quota errors
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                if attempt < max_retries - 1:
                    print(f"  ⚠️ Rate limit hit. Waiting 65 seconds...")
                    time.sleep(65)
                else:
                    print(f"  ✗ Still hitting rate limits after 3 attempts.")
                    return False
            
            # Check for model errors
            elif "404" in error_msg or "NOT_FOUND" in error_msg:
                print(f"  ✗ Model error: {error_msg[:100]}")
                return False
            
            else:
                print(f"  ✗ Gemini error: {error_msg[:100]}")
                return False
    
    return False

def get_latest_videos(channel_id, max_videos=3):
    """Fetch latest videos from RSS feed (limited to 3 for testing)."""
    feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(feed_url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            feed = feedparser.parse(response.text)
            videos = []
            
            for entry in feed.entries[:max_videos]:  # Limit to 3 videos for testing
                try:
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        published_timestamp = time.mktime(entry.published_parsed)
                        # Check if from last 24 hours
                        if time.time() - published_timestamp < 86400:
                            videos.append({
                                'title': entry.title,
                                'link': entry.link,
                                'published': time.strftime('%Y-%m-%d %H:%M', entry.published_parsed)
                            })
                except Exception:
                    continue
                    
            return videos
            
    except Exception as e:
        print(f"  ✗ Error fetching videos: {e}")
    
    return []

def main():
    """Main execution function."""
    print("\n" + "="*60)
    print("YOUTUBE MONITOR - GEMINI NUMERICAL ANALYSIS (1/0)")
    print("="*60)
    
    relevant_videos_summary = []
    
    for channel_name, config in CHANNELS_TO_WATCH.items():
        print(f"\n🔍 Checking: {channel_name}")
        latest_videos = get_latest_videos(config["id"], max_videos=3)
        
        if not latest_videos:
            print(f"  No recent videos found")
            continue
            
        print(f"  Found {len(latest_videos)} recent videos")
        
        for video in latest_videos:
            print(f"\n  📺 {video['title'][:70]}...")
            print(f"  📅 Published: {video['published']}")
            
            # Analyze with Gemini (NUMERICAL RESPONSE VERSION)
            if analyze_video_with_retry(video['link'], video['title'], config["keywords"], channel_name):
                # Format: • [Video Title](YouTube Link) - Channel Name
                relevant_videos_summary.append(f"• [{video['title']}]({video['link']}) - {channel_name}")
                print(f"  ✅ RELEVANT - Added to list")
            else:
                print(f"  ❌ NOT RELEVANT")

    print(f"\n{'='*60}")
    print("DAILY SUMMARY")
    print(f"{'='*60}")
    
    if relevant_videos_summary:
        message = "🚨 **Relevant YouTube Videos Found:**\n\n" + "\n".join(relevant_videos_summary)
        message += f"\n\n🕒 *Checked at:* {time.strftime('%Y-%m-%d %H:%M IST')}"
        send_telegram_message(message)
        print(f"✅ Sent notification with {len(relevant_videos_summary)} videos")
    else:
        message = f"""
✅ **Daily YouTube Check Complete**

*Status:* No relevant videos found in the last 24 hours.

*Channels checked:* {', '.join(CHANNELS_TO_WATCH.keys())}

*Time:* {time.strftime('%Y-%m-%d %H:%M IST')}
        """
        send_telegram_message(message)
        print("✅ Sent 'no videos' notification")

if __name__ == "__main__":
    main()
