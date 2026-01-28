import os
import requests
import feedparser
import time
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled
from google import genai
from google.genai import types

# --- Configuration Section ---
# Let's test with just Mint channel first for debugging
CHANNELS_TO_WATCH = {
    "Mint": {
        "id": "UCUI9vm69ZbAqRK3q3vKLWCQ",
        "keywords": ["Indian economy", "economics", "india international trade", "india government schemes", "tax", "gdp", "inflation", "budget", "economic survey", "rbi", "trade agreement", "FTA", "free trade agreement", "international trade"]
    }
}

# --- Environment Variables ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

print("=" * 80)
print("DEBUG MODE: YouTube Monitor with Detailed Logging")
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

def analyze_transcript_with_gemini(transcript, keywords, video_title):
    """Uses Gemini to determine if transcript is relevant to AT LEAST ONE keyword."""
    if not GEMINI_API_KEY:
        print("ERROR: Gemini API Key missing.")
        return False

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        keyword_list = ", ".join(keywords)
        
        # Show what we're sending to Gemini
        print(f"\n📋 SENDING TO GEMINI FOR ANALYSIS:")
        print(f"   Video Title: {video_title}")
        print(f"   Looking for ANY of: {keyword_list}")
        print(f"   Transcript length: {len(transcript)} characters")
        print(f"   First 500 chars of transcript: {transcript[:500]}...")
        
        # Limit transcript length
        transcript_short = transcript[:10000] if len(transcript) > 10000 else transcript
        
        prompt = f"""
        VIDEO TITLE: {video_title}
        
        TRANSCRIPT:
        {transcript_short}
        
        QUESTION: Is this video about ANY of these topics? (Answer YES if it's about at least one):
        {keyword_list}
        
        IMPORTANT: Consider partial matches and related concepts. For example:
        - "India-EU FTA" matches "international trade", "trade agreement", "FTA"
        - "Economic partnership" matches "economics", "Indian economy"
        - "Budget discussion" matches "budget", "Indian economy"
        
        Respond with ONLY this JSON format: {{"relevant": true}} or {{"relevant": false}}
        No other text.
        """
        
        print(f"\n🤖 SENDING PROMPT TO GEMINI...")
        
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=100
            )
        )
        
        # Show raw response
        response_text = response.text.strip()
        print(f"\n📝 GEMINI RAW RESPONSE: {response_text}")
        print(f"   Response length: {len(response_text)} characters")
        
        # More robust parsing
        response_lower = response_text.lower()
        if '"relevant": true' in response_lower or "'relevant': true" in response_lower or 'true' in response_lower:
            print("✅ GEMINI DECISION: RELEVANT (matches at least one topic)")
            return True
        elif '"relevant": false' in response_lower or "'relevant': false" in response_lower or 'false' in response_lower:
            print("❌ GEMINI DECISION: NOT RELEVANT")
            return False
        else:
            print("⚠️ GEMINI DECISION: Could not parse response, defaulting to false")
            print(f"   Unusual response: {response_text}")
            return False

    except Exception as e:
        print(f"🚨 GEMINI ANALYSIS FAILED: {type(e).__name__}: {e}")
        return False

def get_latest_videos(channel_id, channel_name):
    """Fetches ALL videos from the last 24 hours with detailed debugging."""
    feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    
    print(f"\n📡 FETCHING VIDEOS FOR: {channel_name}")
    print(f"   RSS URL: {feed_url}")
    
    try:
        # Add timeout and user-agent
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(feed_url, headers=headers, timeout=30)
        print(f"   RSS HTTP Status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"   ⚠️ Failed to fetch RSS: HTTP {response.status_code}")
            return []
            
        feed = feedparser.parse(response.content)
        
        print(f"   Feed title: {feed.feed.get('title', 'Unknown')}")
        print(f"   Total entries in feed: {len(feed.entries)}")
        
        videos = []
        video_count = 0
        
        current_time = time.time()
        print(f"   Current time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(current_time))}")
        
        for i, entry in enumerate(feed.entries):
            try:
                print(f"\n   Entry #{i+1}: {entry.get('title', 'No title')[:60]}...")
                
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    published_timestamp = time.mktime(entry.published_parsed)
                    published_str = time.strftime('%Y-%m-%d %H:%M:%S', entry.published_parsed)
                    
                    time_diff = current_time - published_timestamp
                    hours_diff = time_diff / 3600
                    
                    print(f"     Published: {published_str} ({hours_diff:.1f} hours ago)")
                    
                    # Check if video from last 24 hours
                    if time_diff < 86400:
                        # Extract video ID from URL
                        video_link = entry.link
                        print(f"     Link: {video_link}")
                        
                        if 'v=' in video_link:
                            video_id = video_link.split('v=')[1].split('&')[0]
                            video_title = entry.title
                            
                            print(f"     Video ID: {video_id}")
                            print(f"     ✅ WITHIN 24 HOURS - Adding to check list")
                            
                            videos.append({
                                'title': video_title,
                                'link': video_link,
                                'id': video_id,
                                'published': published_str,
                                'hours_ago': hours_diff
                            })
                            video_count += 1
                        else:
                            print(f"     ⚠️ Could not extract video ID from link")
                    else:
                        print(f"     ⚫ OLDER THAN 24 HOURS - Skipping")
                else:
                    print(f"     ⚠️ No publish date found")
                    
            except Exception as e:
                print(f"     🚨 Error parsing entry: {e}")
                continue
                
        print(f"\n   ✓ Found {video_count} videos from last 24 hours")
        return videos
        
    except Exception as e:
        print(f"   🚨 Failed to fetch RSS feed: {type(e).__name__}: {e}")
        return []

def test_video_transcript(video_id, video_title):
    """Test if we can get transcript for a specific video."""
    print(f"\n🎬 TESTING TRANSCRIPT FOR: {video_title[:60]}...")
    print(f"   Video ID: {video_id}")
    
    try:
        # Try multiple language options
        languages_to_try = ['en', 'hi', 'en-US', 'en-IN', 'en-GB']
        
        for lang in languages_to_try:
            try:
                print(f"   Trying language: {lang}")
                transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=[lang])
                transcript_text = ' '.join([t['text'] for t in transcript_list])
                
                print(f"   ✅ SUCCESS: Found transcript in {lang}")
                print(f"   Transcript length: {len(transcript_text)} characters")
                print(f"   Sample: {transcript_text[:300]}...")
                
                return transcript_text
                
            except Exception as lang_error:
                print(f"   ⚠️ No transcript in {lang}: {type(lang_error).__name__}")
                continue
        
        print("   ❌ No transcript found in any language")
        return None
        
    except TranscriptsDisabled:
        print("   ❌ Transcripts disabled for this video")
        return None
    except Exception as e:
        print(f"   🚨 Error getting transcript: {type(e).__name__}: {e}")
        return None

def main():
    """Main execution function with detailed debugging."""
    print("\n" + "=" * 80)
    print("STARTING DEBUG SESSION")
    print("=" * 80)
    
    # Send start notification
    send_telegram_message("🔍 YouTube Monitor Debug Session Started")
    
    relevant_videos_summary = []
    
    for channel_name, config in CHANNELS_TO_WATCH.items():
        print(f"\n{'='*40}")
        print(f"CHANNEL: {channel_name}")
        print(f"{'='*40}")
        print(f"Channel ID: {config['id']}")
        print(f"Keywords: {config['keywords']}")
        
        # Get videos
        videos = get_latest_videos(config["id"], channel_name)
        
        if not videos:
            print(f"\n❌ NO VIDEOS FOUND in last 24 hours for {channel_name}")
            continue
            
        print(f"\n📊 PROCEEDING TO CHECK {len(videos)} VIDEOS:")
        
        for i, video in enumerate(videos):
            print(f"\n{'─'*60}")
            print(f"VIDEO #{i+1}/{len(videos)}: {video['title']}")
            print(f"{'─'*60}")
            
            # Test transcript retrieval first
            transcript = test_video_transcript(video['id'], video['title'])
            
            if transcript:
                # Analyze with Gemini
                print(f"\n🔍 ANALYZING WITH GEMINI...")
                is_relevant = analyze_transcript_with_gemini(
                    transcript, 
                    config["keywords"],
                    video['title']
                )
                
                if is_relevant:
                    print(f"\n🎯 RESULT: ✅ RELEVANT - Adding to notification")
                    relevant_videos_summary.append(f"• [{video['title']}]({video['link']}) - {channel_name} ({video['hours_ago']:.1f}h ago)")
                else:
                    print(f"\n🎯 RESULT: ❌ NOT RELEVANT")
            else:
                print(f"\n🎯 RESULT: ⚠️ SKIPPED - No transcript available")
    
    print(f"\n{'='*80}")
    print("DEBUG SESSION COMPLETE")
    print(f"{'='*80}")
    
    # Summary
    print(f"\n📈 SUMMARY:")
    print(f"   Channels checked: {len(CHANNELS_TO_WATCH)}")
    print(f"   Videos found in last 24h: {sum(1 for _ in CHANNELS_TO_WATCH for videos in [get_latest_videos(config['id'], name)])}")
    print(f"   Relevant videos found: {len(relevant_videos_summary)}")
    
    # Send results
    if relevant_videos_summary:
        message = "🚨 **DEBUG: Relevant Videos Found:**\n\n" + "\n".join(relevant_videos_summary)
        send_telegram_message(message)
        print(f"\n✅ Sent Telegram notification with {len(relevant_videos_summary)} videos")
    else:
        # Send debug info to Telegram
        debug_info = f"""
🔍 **DEBUG REPORT - No Videos Found**

**Channels Checked:** {len(CHANNELS_TO_WATCH)}
**Time of Check:** {time.strftime('%Y-%m-%d %H:%M:%S %Z')}

**Possible Issues:**
1. No videos uploaded in last 24 hours
2. Transcripts not available
3. Gemini API issues
4. RSS feed not working

**Test Search:**
Check Mint channel manually for India-EU FTA videos.
        """
        send_telegram_message(debug_info)
        print(f"\n⚠️ No relevant videos found. Sent debug report to Telegram.")

if __name__ == "__main__":
    main()
