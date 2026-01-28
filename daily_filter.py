import os
import requests
import feedparser
import time
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
                    "de-dollarisation", "trade deal", "India-EU", "India EU"]
    }
    # Add other channels as needed
}

# --- Environment Variables ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

print("=" * 80)
print("FIXED: Proper Transcript Handling")
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

def get_transcript_proper(video_id, video_title):
    """Proper transcript fetching with all available methods."""
    print(f"\n🎬 Getting transcript for: {video_title[:60]}...")
    print(f"   Video ID: {video_id}")
    
    methods_to_try = [
        # Method 1: Try with language list
        {"func": lambda: YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'hi']), "name": "get_transcript with languages"},
        
        # Method 2: Try without language specification
        {"func": lambda: YouTubeTranscriptApi.get_transcript(video_id), "name": "get_transcript default"},
        
        # Method 3: List transcripts first, then fetch
        {"func": lambda: YouTubeTranscriptApi.list_transcripts(video_id), "name": "list_transcripts"},
        
        # Method 4: Try with manual transcript ID (if we can find it)
        {"func": lambda: YouTubeTranscriptApi.get_transcript(video_id, languages=['en-US']), "name": "get_transcript en-US"},
        
        # Method 5: Try with auto-generated transcripts
        {"func": lambda: YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'hi'], preserve_formatting=True), "name": "get_transcript preserve_formatting"},
    ]
    
    for method in methods_to_try:
        try:
            print(f"   Trying: {method['name']}...")
            result = method['func']()
            
            if method['name'] == "list_transcripts":
                # Handle list_transcripts result
                print(f"   Available transcripts: {[f'{t.language_code} ({t.is_generated})' for t in result]}")
                
                # Try to fetch each available transcript
                for transcript in result:
                    try:
                        print(f"   Fetching {transcript.language_code} ({'auto' if transcript.is_generated else 'manual'})...")
                        transcript_data = transcript.fetch()
                        transcript_text = ' '.join([t['text'] for t in transcript_data])
                        print(f"   ✓ Success with {transcript.language_code}")
                        return transcript_text
                    except Exception as e:
                        print(f"   ✗ Failed to fetch {transcript.language_code}: {type(e).__name__}")
                        continue
            else:
                # Handle get_transcript result
                transcript_text = ' '.join([t['text'] for t in result])
                print(f"   ✓ Success with {method['name']}")
                return transcript_text
                
        except (TranscriptsDisabled, NoTranscriptFound) as e:
            print(f"   ✗ No transcript: {type(e).__name__}")
            return None
        except Exception as e:
            print(f"   ✗ {method['name']} failed: {type(e).__name__}: {str(e)[:100]}")
            continue
    
    print("   ❌ All methods failed")
    return None

def analyze_with_gemini(transcript, keywords, video_title):
    """Analyze transcript with Gemini."""
    if not GEMINI_API_KEY:
        print("ERROR: Gemini API Key missing.")
        return False

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        keyword_list = ", ".join(keywords)
        
        # Prepare prompt
        prompt = f"""
        VIDEO TITLE: {video_title}
        
        TRANSCRIPT:
        {transcript[:4000]}
        
        QUESTION: Is the MAIN CONTENT of this video related to ANY of these topics?
        Topics: {keyword_list}
        
        IMPORTANT: 
        1. Consider the overall topic and main discussion points
        2. If it mentions any of these topics as a significant part, say YES
        3. "De-dollarisation" relates to "Indian economy", "economics", "international trade"
        4. "India-EU deal" relates to "trade agreement", "FTA", "international trade"
        5. "Budget 2026" relates to "budget", "Indian economy", "tax"
        
        Respond with ONLY: {{"relevant": true}} or {{"relevant": false}}
        No other text.
        """
        
        print(f"\n🤖 Analyzing with Gemini...")
        
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=50
            )
        )
        
        response_text = response.text.strip()
        print(f"   Gemini response: {response_text}")
        
        # Parse response
        if '"relevant": true' in response_text or "'relevant': true" in response_text:
            print("   ✅ Gemini: RELEVANT")
            return True
        else:
            print("   ❌ Gemini: NOT RELEVANT")
            return False

    except Exception as e:
        print(f"   🚨 Gemini analysis failed: {e}")
        return False

def get_latest_videos(channel_id):
    """Fetches videos from the last 24 hours."""
    feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    
    print(f"\n📡 Fetching RSS: {feed_url}")
    
    try:
        # Add headers to avoid blocking
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(feed_url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            print(f"   ✗ HTTP Error: {response.status_code}")
            return []
            
        feed = feedparser.parse(response.content)
        
        videos = []
        for entry in feed.entries[:10]:  # Check first 10
            try:
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    published_timestamp = time.mktime(entry.published_parsed)
                    
                    # Check if within 24 hours
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
                
        print(f"   ✓ Found {len(videos)} videos from last 24 hours")
        return videos
        
    except Exception as e:
        print(f"   ✗ Failed to fetch RSS: {e}")
        return []

def main():
    """Main execution function."""
    print("\n" + "=" * 80)
    print("STARTING ANALYSIS")
    print("=" * 80)
    
    send_telegram_message("🔍 YouTube Monitor Started - Checking Mint Channel")
    
    relevant_videos = []
    
    for channel_name, config in CHANNELS_TO_WATCH.items():
        print(f"\n🔍 Checking: {channel_name}")
        
        videos = get_latest_videos(config["id"])
        
        for video in videos:
            print(f"\n{'─'*60}")
            print(f"📺 {video['title']}")
            print(f"   Published: {video['published']}")
            print(f"   Link: {video['link']}")
            
            # Get transcript
            transcript = get_transcript_proper(video['id'], video['title'])
            
            if transcript:
                print(f"   ✓ Transcript length: {len(transcript)} characters")
                
                # Quick check for obvious keywords in transcript
                transcript_lower = transcript.lower()
                keywords_lower = [k.lower() for k in config["keywords"]]
                
                found_keywords = []
                for keyword in keywords_lower:
                    if keyword in transcript_lower:
                        found_keywords.append(keyword)
                
                if found_keywords:
                    print(f"   🔍 Found keywords in transcript: {', '.join(found_keywords[:3])}")
                
                # Analyze with Gemini
                is_relevant = analyze_with_gemini(transcript, config["keywords"], video['title'])
                
                if is_relevant:
                    relevant_videos.append(f"• [{video['title']}]({video['link']}) - {channel_name}")
                    print(f"   ✅ ADDED TO LIST")
                else:
                    print(f"   ❌ NOT RELEVANT")
            else:
                print(f"   ⚠️ No transcript available - checking title only")
                
                # Fallback: Check title for obvious keywords
                title_lower = video['title'].lower()
                title_matches = []
                for keyword in config["keywords"]:
                    if keyword.lower() in title_lower:
                        title_matches.append(keyword)
                
                if title_matches:
                    print(f"   🔍 Title matches: {', '.join(title_matches[:3])}")
                    # If title strongly suggests relevance, add it
                    if any(word in title_lower for word in ['india-eu', 'fta', 'trade deal', 'de-dollar', 'budget']):
                        print(f"   ✅ Adding based on strong title match")
                        relevant_videos.append(f"• [{video['title']}]({video['link']}) - {channel_name} [Title Match]")
                    else:
                        print(f"   ❌ Title match not strong enough")
                else:
                    print(f"   ❌ No title matches either")
    
    print(f"\n{'='*80}")
    print("RESULTS SUMMARY")
    print(f"{'='*80}")
    print(f"Relevant videos found: {len(relevant_videos)}")
    
    # Send results
    if relevant_videos:
        message = f"🚨 **{len(relevant_videos)} Relevant YouTube Videos Found:**\n\n" + "\n".join(relevant_videos)
        send_telegram_message(message)
        print(f"\n✅ Sent notification with {len(relevant_videos)} videos")
    else:
        message = "✅ **Daily Check:** No relevant videos found in the last 24 hours."
        send_telegram_message(message)
        print(f"\n✅ Sent 'no videos' notification")

if __name__ == "__main__":
    main()
