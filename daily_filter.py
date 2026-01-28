import os
import requests
import feedparser
import time
import json
# CORRECT import for youtube-transcript-api
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
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

print("=" * 80)
print("FINAL FIXED VERSION")
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

def get_transcript_correct(video_id, video_title):
    """CORRECT way to get transcript with current library."""
    print(f"\n🎬 Getting transcript for: {video_title[:60]}...")
    print(f"   Video ID: {video_id}")
    print(f"   Video URL: https://www.youtube.com/watch?v={video_id}")
    
    try:
        # Method 1: Try to get transcript directly
        print("   Method 1: Getting transcript with auto-generated...")
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        transcript_text = ' '.join([t['text'] for t in transcript_list])
        print(f"   ✓ Success! Got {len(transcript_list)} segments")
        print(f"   Sample: {transcript_text[:200]}...")
        return transcript_text
        
    except TranscriptsDisabled:
        print("   ✗ Transcripts disabled for this video")
        return None
    except NoTranscriptFound:
        print("   ✗ No transcript found")
        return None
    except Exception as e:
        print(f"   ✗ Error getting transcript: {type(e).__name__}: {e}")
        return None

def analyze_with_gemini(transcript, keywords, video_title):
    """Analyze content with Gemini."""
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
        
        IMPORTANT: Answer YES if the video discusses ANY of these topics significantly.
        
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

def get_latest_videos_enhanced(channel_id):
    """Enhanced method to get videos - tries multiple approaches."""
    print(f"\n📡 Fetching videos for channel: {channel_id}")
    
    videos = []
    
    # Method 1: Standard RSS feed (limited to 15)
    feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    try:
        response = requests.get(feed_url, timeout=30)
        if response.status_code == 200:
            feed = feedparser.parse(response.content)
            for entry in feed.entries:
                try:
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        published_timestamp = time.mktime(entry.published_parsed)
                        if time.time() - published_timestamp < 86400:
                            if 'v=' in entry.link:
                                video_id = entry.link.split('v=')[1].split('&')[0]
                                if '/shorts/' not in entry.link:  # Skip shorts
                                    videos.append({
                                        'title': entry.title,
                                        'link': entry.link,
                                        'id': video_id,
                                        'published': time.strftime('%Y-%m-%d %H:%M:%S', entry.published_parsed),
                                        'source': 'RSS'
                                    })
                except:
                    continue
            print(f"   ✓ RSS feed: Found {len(videos)} videos")
    except Exception as e:
        print(f"   ✗ RSS feed error: {e}")
    
    # If RSS shows few videos, try alternative methods
    if len(videos) < 5:  # If RSS shows very few videos
        print("   ⚠️ RSS shows few videos, checking if more exist...")
        # We could add YouTube API here if you get an API key
    
    return videos

def simple_title_check(video_title, keywords):
    """Simple but effective title matching."""
    title_lower = video_title.lower()
    keywords_lower = [k.lower() for k in keywords]
    
    # Check each keyword
    for keyword in keywords_lower:
        if keyword in title_lower:
            return True
    
    # Check for common variations
    variations = {
        'india-eu': ['india-eu', 'india eu', 'india europe'],
        'trade agreement': ['trade agreement', 'trade deal', 'fta', 'free trade'],
        'budget': ['budget', 'union budget'],
        'economy': ['economy', 'economic', 'gdp', 'inflation'],
        'de-dollar': ['de-dollar', 'dedollar', 'de dollar'],
    }
    
    for base_term, variant_list in variations.items():
        if any(variant in title_lower for variant in variant_list):
            return True
    
    return False

def main():
    """Main execution function."""
    print("\n" + "=" * 80)
    print("STARTING ANALYSIS")
    print("=" * 80)
    
    send_telegram_message("🔍 YouTube Monitor Started")
    
    relevant_videos = []
    
    for channel_name, config in CHANNELS_TO_WATCH.items():
        print(f"\n🔍 Checking: {channel_name}")
        print(f"   Keywords: {', '.join(config['keywords'][:5])}...")
        
        videos = get_latest_videos_enhanced(config["id"])
        
        if not videos:
            print(f"   ⚠️ No videos found for {channel_name}")
            continue
            
        print(f"   Processing {len(videos)} videos...")
        
        for i, video in enumerate(videos):
            print(f"\n{'─'*60}")
            print(f"📺 [{i+1}/{len(videos)}] {video['title']}")
            print(f"   Published: {video['published']}")
            
            # Step 1: Check title first (quick filter)
            title_match = simple_title_check(video['title'], config["keywords"])
            
            if not title_match:
                print(f"   ❌ Title doesn't suggest relevance - skipping")
                continue
            
            print(f"   ✅ Title suggests relevance")
            
            # Step 2: Try to get transcript
            transcript = get_transcript_correct(video['id'], video['title'])
            
            if transcript:
                print(f"   ✓ Got transcript ({len(transcript)} chars)")
                
                # Step 3: Analyze with Gemini
                is_relevant = analyze_with_gemini(transcript, config["keywords"], video['title'])
                
                if is_relevant:
                    relevant_videos.append(f"• [{video['title']}]({video['link']}) - {channel_name}")
                    print(f"   ✅ ADDED (Gemini confirmed)")
                else:
                    print(f"   ❌ Gemini says not relevant")
            else:
                # No transcript, but title matched
                print(f"   ⚠️ No transcript but title matched - adding based on title")
                relevant_videos.append(f"• [{video['title']}]({video['link']}) - {channel_name} [Title match]")
                print(f"   ✅ ADDED (Title match only)")
    
    print(f"\n{'='*80}")
    print("RESULTS SUMMARY")
    print(f"{'='*80}")
    print(f"Total relevant videos found: {len(relevant_videos)}")
    
    # Send results
    if relevant_videos:
        if len(relevant_videos) > 15:
            message = f"🚨 **{len(relevant_videos)} Relevant YouTube Videos Found:**\n\n"
            message += "\n".join(relevant_videos[:15])
            message += f"\n\n... and {len(relevant_videos) - 15} more"
        else:
            message = f"🚨 **{len(relevant_videos)} Relevant YouTube Videos Found:**\n\n"
            message += "\n".join(relevant_videos)
        
        send_telegram_message(message)
        print(f"\n✅ Sent notification with {len(relevant_videos)} videos")
    else:
        message = "✅ **Daily Check:** No relevant videos found in the last 24 hours."
        send_telegram_message(message)
        print(f"\n✅ Sent 'no videos' notification")

if __name__ == "__main__":
    main()
