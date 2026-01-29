import os
import requests
import feedparser
import time
from google import genai
from google.genai import types

# --- Configuration Section (ALL 8 CHANNELS) ---
CHANNELS_TO_WATCH = {
    "Mint": {
        "id": "UCUI9vm69ZbAqRK3q3vKLWCQ",
        "keywords": ["Indian economy", "economics", "india international trade", "india government schemes", "tax", "gdp", "inflation", "budget", "economic survey", "rbi"]
    },
    "Mrunal Unacedmy": {
        "id": "UCwDfgcUkKKTxPozU9UnQ8Pw",
        "keywords": ["Indian government schemes", "government policy", "monthly economy", "scheme", "yojana", "policies", "government initiative"]
    },
    "OnlyIAS Ext.": {
        "id": "UCAidhU356a0ej2MtFEylvBA",
        "keywords": ["Monthly government schemes", "Important government scheme in news", "scheme", "yojana", "government initiative", "policy", "current affairs"]
    },
    "Vajiram Ravi": {
        "id": "UCzelA5kqD9v6k6drK44l4_g",
        "keywords": ["Indian economy", "economics", "india international trade", "india government schemes", "tax", "gdp", "inflation", "budget", "economic survey", "rbi"]
    },
    "DrishtiIAS Hindi": {
        "id": "UCzLqOSZPtUKrmSEnlH4LAvw",
        "keywords": ["Indian economy", "economics", "india international trade", "india government schemes", "tax", "gdp", "inflation", "budget", "economic survey", "rbi", "आर्थिक सर्वेक्षण", "बजट", "जीडीपी", "मुद्रास्फीति", "वित्त", "अर्थव्यवस्था", "कर", "व्यापार"]
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
        "keywords": ["Indian economy", "economics", "india international trade", "india government schemes", "tax", "gdp", "inflation", "budget", "economic survey", "rbi", "economics concept explainer", "US dollar", "dollar", "currency", "IMF", "global economy", "forex"]
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
        return False

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
            print("✓ Telegram message sent.")
            return True
        else:
            print(f"✗ Failed to send Telegram message: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"✗ Telegram API error: {e}")
        return False

def analyze_video_with_retry(youtube_url, video_title, keywords, channel_name, max_retries=3):
    """Analyze YouTube video link using Gemini with retry logic."""
    if not GEMINI_API_KEY:
        print("  ✗ Gemini API Key not set")
        return "ERROR", "API Key missing"

    client = genai.Client(api_key=GEMINI_API_KEY)
    
    # Prepare keywords string
    keywords_str = ", ".join(keywords[:8])  # Take first 8 keywords
    
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
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=5,
                )
            )
            
            response_text = response.text.strip()
            print(f"  Raw Gemini response: '{response_text}'")
            
            # Parse numerical response
            if "1" in response_text:
                return "RELEVANT", response_text
            else:
                return "NOT_RELEVANT", response_text

        except Exception as e:
            error_msg = str(e)
            
            # Check for Rate Limit (429) or Quota errors
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                if attempt < max_retries - 1:
                    wait_time = 65
                    print(f"  ⚠️ Rate limit hit. Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    return "ERROR", "Rate limit exceeded after retries"
            
            # Check for model errors
            elif "404" in error_msg or "NOT_FOUND" in error_msg:
                return "ERROR", f"Model error: {error_msg[:100]}"
            
            else:
                return "ERROR", f"Gemini error: {error_msg[:100]}"
    
    return "ERROR", "Max retries exceeded"

def get_latest_videos(channel_id, max_videos=15):
    """Fetch latest videos from RSS feed (up to 15 within last 24 hours)."""
    feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(feed_url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            feed = feedparser.parse(response.text)
            videos = []
            
            for entry in feed.entries[:max_videos * 2]:  # Get more to filter by time
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
                            
                            if len(videos) >= max_videos:
                                break
                except Exception:
                    continue
                    
            return videos
            
    except Exception as e:
        print(f"  ✗ Error fetching videos: {e}")
    
    return []

def main():
    """Main execution function."""
    print("\n" + "="*60)
    print("YOUTUBE MONITOR - ALL CHANNELS - SINGLE FINAL REPORT")
    print("="*60)
    
    total_videos_processed = 0
    relevant_videos = []
    failed_videos = []
    
    for channel_name, config in CHANNELS_TO_WATCH.items():
        print(f"\n🔍 Checking: {channel_name}")
        latest_videos = get_latest_videos(config["id"], max_videos=15)
        
        if not latest_videos:
            print(f"  No recent videos found in last 24 hours")
            continue
            
        print(f"  Found {len(latest_videos)} recent videos")
        
        for i, video in enumerate(latest_videos):
            total_videos_processed += 1
            print(f"\n  📺 [{i+1}/{len(latest_videos)}] {video['title'][:70]}...")
            print(f"  📅 Published: {video['published']}")
            
            # Analyze with Gemini
            status, gemini_response = analyze_video_with_retry(
                video['link'], 
                video['title'], 
                config["keywords"], 
                channel_name
            )
            
            # Store results (NO individual Telegram messages)
            if status == "RELEVANT":
                relevant_videos.append(f"• [{video['title']}]({video['link']}) - {channel_name}")
                print(f"  ✅ RELEVANT")
            elif status == "NOT_RELEVANT":
                print(f"  ❌ NOT RELEVANT")
            elif status == "ERROR":
                failed_videos.append(f"• {video['title']} - {channel_name} (Error: {gemini_response})")
                print(f"  ⚠️ ANALYSIS FAILED")
            
            # Add 2-minute delay between videos (except after the last one)
            if i < len(latest_videos) - 1:
                delay_seconds = 120  # 2 minutes
                print(f"  ⏳ Waiting {delay_seconds} seconds before next video...")
                time.sleep(delay_seconds)
    
    print(f"\n{'='*60}")
    print("ANALYSIS COMPLETE - GENERATING FINAL REPORT")
    print(f"{'='*60}")
    print(f"Total videos processed: {total_videos_processed}")
    print(f"Relevant videos found: {len(relevant_videos)}")
    print(f"Failed analyses: {len(failed_videos)}")
    
    # Generate and send ONE FINAL Telegram message
    if relevant_videos:
        message = f"🚨 **RELEVANT YOUTUBE VIDEOS FOUND**\n\n"
        message += "\n".join(relevant_videos)
        
        # Add statistics
        message += f"\n\n📊 *Statistics:*"
        message += f"\n• Channels checked: {len(CHANNELS_TO_WATCH)}"
        message += f"\n• Videos analyzed: {total_videos_processed}"
        message += f"\n• Relevant found: {len(relevant_videos)}"
        message += f"\n• Failed analyses: {len(failed_videos)}"
        
        # Add failed videos if any
        if failed_videos:
            message += f"\n\n❌ *Failed Analyses ({len(failed_videos)}):*"
            for failed in failed_videos[:3]:  # Show first 3 only
                message += f"\n{failed}"
            if len(failed_videos) > 3:
                message += f"\n... and {len(failed_videos) - 3} more"
        
        message += f"\n\n🕒 *Analysis completed at:* {time.strftime('%Y-%m-%d %H:%M IST')}"
        
    else:
        message = f"""
✅ **DAILY YOUTUBE MONITORING COMPLETE**

*Status:* No relevant videos found in the last 24 hours.

📊 *Statistics:*
• Channels checked: {len(CHANNELS_TO_WATCH)}
• Videos analyzed: {total_videos_processed}
• Relevant found: 0
• Failed analyses: {len(failed_videos)}

🕒 *Analysis completed at:* {time.strftime('%Y-%m-%d %H:%M IST')}
"""
        
        # Add failed videos if any (even when no relevant videos found)
        if failed_videos:
            message += f"\n\n❌ *Failed Analyses ({len(failed_videos)}):*"
            for failed in failed_videos[:3]:  # Show first 3 only
                message += f"\n{failed}"
            if len(failed_videos) > 3:
                message += f"\n... and {len(failed_videos) - 3} more"
    
    # Send the SINGLE FINAL message
    send_telegram_message(message)
    print("✅ Final report sent to Telegram")

if __name__ == "__main__":
    main()
