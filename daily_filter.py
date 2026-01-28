import os
import requests
import feedparser
import time
import json
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from google import genai
from google.genai import types

# --- Configuration Section ---
CHANNELS_TO_WATCH = {
    "Mint": {
        "id": "UCUI9vm69ZbAqRK3q3vKLWCQ",
        "keywords": ["Indian economy", "economics", "india international trade", 
                    "india government schemes", "tax", "gdp", "inflation", 
                    "budget", "economic survey", "rbi", "trade agreement", 
                    "FTA", "free trade agreement", "international trade",
                    "de-dollarisation", "trade deal", "India-EU"]
    }
}

# --- Environment Variables ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

print("=" * 80)
print("FIXED VERSION: Using YouTube API for transcripts")
print("=" * 80)

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
            print("✓ Telegram message sent successfully.")
            return True
        else:
            print(f"✗ Failed to send Telegram message. Status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ Telegram API error: {e}")
        return False

def get_transcript_with_retry(video_id, video_title):
    """Try multiple methods to get transcript."""
    print(f"\n🎬 Getting transcript for: {video_title[:60]}...")
    print(f"   Video ID: {video_id}")
    
    methods = [
        # Method 1: Try with specific languages
        lambda: YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'hi']),
        
        # Method 2: Try without language filter (gets any available)
        lambda: YouTubeTranscriptApi.get_transcript(video_id),
        
        # Method 3: Try to list available transcripts first
        lambda: YouTubeTranscriptApi.list_transcripts(video_id),
    ]
    
    for i, method in enumerate(methods):
        try:
            print(f"   Method {i+1}: Trying...")
            result = method()
            
            if i == 2:  # list_transcripts method
                print(f"   Available transcripts: {[t.language_code for t in result]}")
                # Try to get the first available transcript
                if result:
                    transcript = result[0].fetch()
                    print(f"   ✓ Got transcript using list_transcripts method")
                    transcript_text = ' '.join([t['text'] for t in transcript])
                    return transcript_text
            
            else:  # get_transcript methods
                print(f"   ✓ Got transcript using method {i+1}")
                transcript_text = ' '.join([t['text'] for t in result])
                return transcript_text
                
        except (TranscriptsDisabled, NoTranscriptFound) as e:
            print(f"   ✗ No transcript available: {type(e).__name__}")
            return None
        except Exception as e:
            print(f"   ✗ Method {i+1} failed: {type(e).__name__}")
            continue
    
    print("   ❌ All methods failed to get transcript")
    return None

def analyze_transcript_with_gemini(transcript, keywords, video_title):
    """Uses Gemini to determine if transcript is relevant."""
    if not GEMINI_API_KEY:
        print("ERROR: Gemini API Key missing.")
        return False

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        keyword_list = ", ".join(keywords)
        
        print(f"\n📋 ANALYZING WITH GEMINI:")
        print(f"   Video: {video_title}")
        print(f"   Looking for ANY of: {keyword_list}")
        
        # Use a better prompt
        prompt = f"""
        VIDEO TITLE: {video_title}
        
        TRANSCRIPT (partial):
        {transcript[:3000]}
        
        QUESTION: Is this video related to ANY of these topics? (Answer YES if related to at least one):
        {keyword_list}
        
        IMPORTANT CONSIDERATIONS:
        1. "India-EU deal" matches "trade agreement", "FTA", "international trade", "India-EU"
        2. "De-dollarisation" matches "Indian economy", "economics", "international trade"
        3. "Budget 2026" matches "budget", "Indian economy", "tax"
        4. Consider synonyms and related terms
        
        Respond with ONLY: {{"relevant": true}} or {{"relevant": false}}
        """
        
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=50
            )
        )
        
        response_text = response.text.strip()
        print(f"🤖 Gemini response: {response_text}")
        
        # Parse response
        if '"relevant": true' in response_text or "'relevant': true" in response_text:
            print("✅ Gemini: RELEVANT")
            return True
        else:
            print("❌ Gemini: NOT RELEVANT")
            return False

    except Exception as e:
        print(f"🚨 Gemini analysis failed: {e}")
        return False

def get_latest_videos(channel_id):
    """Fetches videos from the last 24 hours."""
    feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    
    print(f"\n📡 Fetching RSS: {feed_url}")
    
    try:
        feed = feedparser.parse(feed_url)
        videos = []
        
        for entry in feed.entries:
            try:
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    published_timestamp = time.mktime(entry.published_parsed)
                    
                    if time.time() - published_timestamp < 86400:
                        if 'v=' in entry.link:
                            video_id = entry.link.split('v=')[1].split('&')[0]
                            videos.append({
                                'title': entry.title,
                                'link': entry.link,
                                'id': video_id,
                                'published': time.strftime('%Y-%m-%d %H:%M:%S', entry.published_parsed)
                            })
            except:
                continue
                
        print(f"✓ Found {len(videos)} videos from last 24 hours")
        return videos
        
    except Exception as e:
        print(f"✗ Failed to fetch RSS: {e}")
        return []

def main():
    """Main execution function."""
    print("\n" + "=" * 80)
    print("STARTING ANALYSIS")
    print("=" * 80)
    
    send_telegram_message("🔍 YouTube Monitor Started - Testing Transcript Methods")
    
    relevant_videos = []
    
    for channel_name, config in CHANNELS_TO_WATCH.items():
        print(f"\n🔍 Checking: {channel_name}")
        
        videos = get_latest_videos(config["id"])
        
        for video in videos:
            print(f"\n{'─'*60}")
            print(f"📺 {video['title']}")
            print(f"   Published: {video['published']}")
            print(f"   Link: {video['link']}")
            
            # Try to get transcript
            transcript = get_transcript_with_retry(video['id'], video['title'])
            
            if transcript:
                print(f"   Transcript length: {len(transcript)} chars")
                
                # Check if it's about Indian economy/trade
                if any(keyword.lower() in video['title'].lower() for keyword in 
                      ['india-eu', 'trade', 'economy', 'budget', 'FTA', 'de-dollar']):
                    print(f"   ⚠️ Title suggests it might be relevant")
                
                # Analyze with Gemini
                is_relevant = analyze_transcript_with_gemini(
                    transcript, 
                    config["keywords"],
                    video['title']
                )
                
                if is_relevant:
                    relevant_videos.append(f"• [{video['title']}]({video['link']})")
                    print(f"   ✅ ADDED TO LIST")
                else:
                    print(f"   ❌ NOT ADDED")
            else:
                print(f"   ⚠️ No transcript available")
                
                # Fallback: Check if title contains keywords
                title_lower = video['title'].lower()
                keywords_lower = [k.lower() for k in config["keywords"]]
                
                if any(keyword in title_lower for keyword in 
                      ['india-eu', 'trade deal', 'fta', 'de-dollar', 'budget', 'economy']):
                    print(f"   ⚠️ Title suggests relevance but no transcript")
                    # We could add a simple title-based check here
                    # For now, let's be conservative and not add without transcript
    
    print(f"\n{'='*80}")
    print("RESULTS SUMMARY")
    print(f"{'='*80}")
    print(f"Relevant videos found: {len(relevant_videos)}")
    
    if relevant_videos:
        message = "🚨 **Relevant YouTube Videos Found:**\n\n" + "\n".join(relevant_videos)
        send_telegram_message(message)
        print(f"\n✅ Sent notification with {len(relevant_videos)} videos")
    else:
        message = "✅ No relevant videos found with available transcripts in last 24 hours."
        send_telegram_message(message)
        print(f"\n✅ Sent 'no videos' notification")

if __name__ == "__main__":
    main()
