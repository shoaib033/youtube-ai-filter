import os
import sys
import requests
import feedparser
import time
import re
import subprocess
import json
import tempfile
import shutil
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
                    "de-dollarisation", "trade deal", "India-EU", "India EU",
                    "economic survey", "GDP", "finance minister", "union budget"]
    },
    "Mrunal Unacedmy": {
        "id": "UCwDfgcUkKKTxPozU9UnQ8Pw",
        "keywords": ["Indian government schemes", "government policy", "monthly economy",
                    "scheme", "yojana", "policies", "government initiative"]
    },
    "OnlyIAS Ext.": {
        "id": "UCAidhU356a0ej2MtFEylvBA",
        "keywords": ["Monthly government schemes", "Important government scheme in news",
                    "scheme", "yojana", "government initiative", "policy"]
    },
    "Vajiram Ravi": {
        "id": "UCzelA5kqD9v6k6drK44l4_g",
        "keywords": ["Indian economy", "economics", "india international trade", 
                    "india government schemes", "tax", "gdp", "inflation", 
                    "budget", "economic survey", "rbi", "union budget", 
                    "finance", "fiscal policy", "monetary policy"]
    },
    "DrishtiIAS Hindi": {
        "id": "UCzLqOSZPtUKrmSEnlH4LAvw",
        "keywords": ["Indian economy", "economics", "india international trade", 
                    "india government schemes", "tax", "gdp", "inflation", 
                    "budget", "economic survey", "rbi", "union budget",
                    "आर्थिक सर्वेक्षण", "बजट", "जीडीपी", "मुद्रास्फीति"]
    },
    "DrishtiIAS English": {
        "id": "UCafpueX9hFLls24ed6UddEQ",
        "keywords": ["Indian economy", "economics", "india international trade", 
                    "india government schemes", "tax", "gdp", "inflation", 
                    "budget", "economic survey", "rbi", "economics concept explainer",
                    "union budget", "fiscal policy", "monetary policy"]
    },
    "Sleepy Classes": {
        "id": "UCgRf62bnK3uX4N-YEhG4Jog",
        "keywords": ["Indian economy", "economics", "india international trade", 
                    "india government schemes", "tax", "gdp", "inflation", 
                    "budget", "economic survey", "rbi", "economics concept explainer",
                    "union budget", "economic concepts", "economic theory"]
    },
    "CareerWill": {
        "id": "UCmS9VpdkUNhyOKtKQrtFV1Q",
        "keywords": ["Indian economy", "economics", "india international trade", 
                    "india government schemes", "tax", "gdp", "inflation", 
                    "budget", "economic survey", "rbi", "economics concept explainer",
                    "US dollar", "dollar", "currency", "IMF", "global economy"]
    }
}

# --- Environment Variables ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

print("=" * 80)
print("YOUTUBE MONITOR WITH YT-DLP FALLBACK")
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

def get_transcript_ytdlp(video_id, video_title):
    """Get transcript using yt-dlp (most reliable method)."""
    print(f"\n🎬 Getting transcript with yt-dlp: {video_title[:60]}...")
    print(f"   Video ID: {video_id}")
    
    # Create temporary directory
    temp_dir = tempfile.mkdtemp()
    output_template = os.path.join(temp_dir, f"%(id)s.%(ext)s")
    
    try:
        # Build yt-dlp command
        cmd = [
            'yt-dlp',
            '--write-auto-sub',           # Write auto-generated subtitles
            '--convert-subs', 'srt',      # Convert to SRT format
            '--skip-download',            # Don't download video
            '--sub-lang', 'en,en-US,en-GB,hi',  # Preferred languages
            '--output', output_template,
            f'https://www.youtube.com/watch?v={video_id}'
        ]
        
        print(f"   Running: {' '.join(cmd[:5])}...")
        
        # Run yt-dlp
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60  # 60 second timeout
        )
        
        if result.returncode == 0:
            # Look for subtitle files
            srt_files = []
            for ext in ['srt', 'vtt', 'ttml', 'json3']:
                pattern = os.path.join(temp_dir, f"{video_id}*.{ext}")
                import glob
                srt_files.extend(glob.glob(pattern))
            
            if srt_files:
                # Read the first subtitle file
                srt_file = srt_files[0]
                with open(srt_file, 'r', encoding='utf-8') as f:
                    srt_content = f.read()
                
                # Parse SRT (simplified)
                transcript = parse_srt_content(srt_content)
                print(f"   ✓ Got transcript via yt-dlp ({len(transcript)} chars)")
                return transcript
            else:
                print(f"   ✗ No subtitle files generated")
        else:
            print(f"   ✗ yt-dlp failed: {result.stderr[:200]}")
            
    except subprocess.TimeoutExpired:
        print(f"   ✗ yt-dlp timeout")
    except Exception as e:
        print(f"   ✗ yt-dlp error: {type(e).__name__}: {e}")
    finally:
        # Clean up temp directory
        try:
            shutil.rmtree(temp_dir)
        except:
            pass
    
    return None

def parse_srt_content(srt_text):
    """Parse SRT subtitle content to plain text."""
    # Remove SRT timestamps and formatting
    lines = srt_text.split('\n')
    text_lines = []
    
    for line in lines:
        # Skip timestamp lines and empty lines
        if re.match(r'^\d+$', line) or '-->' in line or not line.strip():
            continue
        # Skip HTML tags
        line = re.sub(r'<[^>]+>', '', line)
        text_lines.append(line.strip())
    
    return ' '.join(text_lines)

def get_transcript_youtube_api(video_id, video_title):
    """Try youtube-transcript-api as secondary method."""
    print(f"   Trying youtube-transcript-api...")
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
        
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        transcript_text = ' '.join([t['text'] for t in transcript_list])
        print(f"   ✓ Got transcript via youtube-transcript-api")
        return transcript_text
        
    except ImportError:
        print(f"   ✗ youtube-transcript-api not installed")
    except (TranscriptsDisabled, NoTranscriptFound):
        print(f"   ✗ No transcript available")
    except Exception as e:
        print(f"   ✗ Error: {type(e).__name__}")
    
    return None

def get_transcript(video_id, video_title):
    """Main function to get transcript - tries multiple methods."""
    print(f"\n🎬 Getting transcript for: {video_title[:60]}...")
    
    # Method 1: Try yt-dlp first (most reliable)
    transcript = get_transcript_ytdlp(video_id, video_title)
    
    # Method 2: Try youtube-transcript-api as fallback
    if not transcript:
        transcript = get_transcript_youtube_api(video_id, video_title)
    
    return transcript

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
        Be liberal in interpretation - if it's related even indirectly, say YES.
        
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

def check_title_relevance(video_title, keywords):
    """Check if title suggests relevance (for fallback)."""
    title_lower = video_title.lower()
    keywords_lower = [k.lower() for k in keywords]
    
    # Check each keyword
    for keyword in keywords_lower:
        if keyword in title_lower:
            return True
    
    # Check for common variations
    variations = {
        'india-eu': ['india-eu', 'india eu', 'india europe', 'eu india'],
        'trade agreement': ['trade agreement', 'trade deal', 'fta', 'free trade', 'trade pact'],
        'budget': ['budget', 'union budget', 'economic survey', 'finance minister', 'fiscal'],
        'economy': ['economy', 'economic', 'gdp', 'inflation', 'monetary', 'fiscal'],
        'de-dollar': ['de-dollar', 'dedollar', 'de dollar', 'dollarisation', 'dollarization'],
        'tax': ['tax', 'taxation', 'gst', 'income tax'],
        'scheme': ['scheme', 'yojana', 'initiative', 'program', 'policy'],
        'rbi': ['rbi', 'reserve bank', 'monetary policy', 'repo rate'],
    }
    
    for base_term, variant_list in variations.items():
        if any(variant in title_lower for variant in variant_list):
            return True
    
    return False

def get_latest_videos(channel_id):
    """Fetch latest videos from RSS feed."""
    feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    
    print(f"\n📡 Fetching videos for channel: {channel_id}")
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(feed_url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            feed = feedparser.parse(response.content)
            videos = []
            
            for entry in feed.entries:
                try:
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        published_timestamp = time.mktime(entry.published_parsed)
                        
                        if time.time() - published_timestamp < 86400:
                            if 'v=' in entry.link:
                                video_id = entry.link.split('v=')[1].split('&')[0]
                                if '/shorts/' not in entry.link:
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
        print(f"   ✗ Error fetching videos: {e}")
    
    return []

def main():
    """Main execution function."""
    print("\n" + "=" * 80)
    print("STARTING DAILY YOUTUBE MONITOR")
    print("=" * 80)
    
    # Check if yt-dlp is installed
    print("Checking dependencies...")
    try:
        subprocess.run(['yt-dlp', '--version'], capture_output=True, check=True)
        print("✓ yt-dlp is installed")
    except:
        print("✗ yt-dlp is NOT installed. Transcripts may not work.")
    
    # Send start notification
    send_telegram_message("🔍 YouTube Daily Monitor Started")
    
    relevant_videos = []
    
    for channel_name, config in CHANNELS_TO_WATCH.items():
        print(f"\n🔍 Checking: {channel_name}")
        
        videos = get_latest_videos(config["id"])
        
        if not videos:
            print(f"   ⚠️ No videos found in last 24 hours")
            continue
            
        print(f"   Processing {len(videos)} videos...")
        
        for i, video in enumerate(videos):
            print(f"\n{'─'*60}")
            print(f"📺 [{i+1}/{len(videos)}] {video['title']}")
            print(f"   Published: {video['published']}")
            
            # Get transcript
            transcript = get_transcript(video['id'], video['title'])
            
            if transcript:
                print(f"   ✓ Got transcript ({len(transcript)} chars)")
                
                # Analyze with Gemini
                is_relevant = analyze_with_gemini(transcript, config["keywords"], video['title'])
                
                if is_relevant:
                    relevant_videos.append(f"• [{video['title']}]({video['link']}) - {channel_name}")
                    print(f"   ✅ ADDED (Gemini confirmed)")
                else:
                    print(f"   ❌ NOT RELEVANT (Gemini)")
            else:
                # No transcript available
                print(f"   ⚠️ No transcript available")
                
                # Check title as last resort
                title_relevant = check_title_relevance(video['title'], config["keywords"])
                
                if title_relevant:
                    print(f"   ⚠️ Title suggests relevance (adding with low confidence)")
                    relevant_videos.append(f"• [{video['title']}]({video['link']}) - {channel_name} [Title match]")
                    print(f"   ✅ ADDED (Title match only - low confidence)")
                else:
                    print(f"   ❌ Title doesn't suggest relevance")
    
    print(f"\n{'='*80}")
    print("DAILY SUMMARY")
    print(f"{'='*80}")
    print(f"Total relevant videos found: {len(relevant_videos)}")
    
    # Send results
    if relevant_videos:
        # Limit message length
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
