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
print("YOUTUBE MONITOR - FINAL WORKING VERSION")
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

def get_transcript_ytdlp_fixed(video_id, video_title):
    """Get transcript using yt-dlp with fixed command."""
    print(f"\n🎬 Getting transcript with yt-dlp: {video_title[:60]}...")
    
    # Create temporary directory
    temp_dir = tempfile.mkdtemp()
    
    try:
        # FIXED: Use simpler command that works without JavaScript runtime
        cmd = [
            'yt-dlp',
            '--skip-download',
            '--write-auto-sub',
            '--sub-lang', 'en',
            '--convert-subs', 'srt',
            '--output', f'{temp_dir}/%(id)s',
            f'https://www.youtube.com/watch?v={video_id}'
        ]
        
        print(f"   Running yt-dlp...")
        
        # Run yt-dlp
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=45
        )
        
        if result.returncode == 0:
            # Look for generated subtitle files
            import glob
            subtitle_files = glob.glob(f'{temp_dir}/{video_id}*.srt') + glob.glob(f'{temp_dir}/{video_id}*.vtt')
            
            if subtitle_files:
                # Read the first subtitle file
                with open(subtitle_files[0], 'r', encoding='utf-8') as f:
                    subtitle_content = f.read()
                
                # Parse subtitles
                transcript = parse_subtitle_content(subtitle_content)
                if transcript:
                    print(f"   ✓ Got transcript via yt-dlp ({len(transcript)} chars)")
                    return transcript
                else:
                    print(f"   ✗ Could not parse subtitle content")
            else:
                # Check if yt-dlp created any files
                all_files = glob.glob(f'{temp_dir}/*')
                print(f"   ✗ No subtitle files found. Files in temp dir: {all_files}")
                
        else:
            # Try alternative command without conversion
            print(f"   Trying alternative method...")
            cmd2 = [
                'yt-dlp',
                '--skip-download',
                '--write-auto-sub',
                '--sub-lang', 'en',
                '--output', f'{temp_dir}/%(id)s',
                f'https://www.youtube.com/watch?v={video_id}'
            ]
            
            result2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=45)
            
            if result2.returncode == 0:
                # Look for JSON subtitle files
                json_files = glob.glob(f'{temp_dir}/{video_id}*.json*')
                if json_files:
                    try:
                        with open(json_files[0], 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            transcript = ' '.join([event.get('segs', [{}])[0].get('utf8', '') for event in data.get('events', []) if event.get('segs')])
                            if transcript:
                                print(f"   ✓ Got transcript from JSON ({len(transcript)} chars)")
                                return transcript
                    except:
                        pass
            
            print(f"   ✗ yt-dlp failed (return code: {result.returncode})")
            
    except subprocess.TimeoutExpired:
        print(f"   ✗ yt-dlp timeout")
    except Exception as e:
        print(f"   ✗ yt-dlp error: {type(e).__name__}: {str(e)[:100]}")
    finally:
        # Clean up
        try:
            shutil.rmtree(temp_dir)
        except:
            pass
    
    return None

def parse_subtitle_content(content):
    """Parse subtitle content (SRT or VTT format)."""
    lines = content.split('\n')
    text_lines = []
    
    for line in lines:
        line = line.strip()
        # Skip timestamp lines and empty lines
        if not line or '-->' in line or line.isdigit() or line.startswith('WEBVTT'):
            continue
        # Remove HTML tags
        line = re.sub(r'<[^>]+>', '', line)
        if line:
            text_lines.append(line)
    
    return ' '.join(text_lines)

def get_transcript_youtube_api_simple(video_id):
    """Simple youtube-transcript-api fallback."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return ' '.join([t['text'] for t in transcript])
    except:
        return None

def get_transcript_all_methods(video_id, video_title):
    """Try all methods to get transcript."""
    print(f"\n🎬 Getting transcript for: {video_title[:60]}...")
    
    # Method 1: yt-dlp (most reliable)
    transcript = get_transcript_ytdlp_fixed(video_id, video_title)
    
    # Method 2: youtube-transcript-api
    if not transcript:
        print(f"   Trying youtube-transcript-api...")
        transcript = get_transcript_youtube_api_simple(video_id)
        if transcript:
            print(f"   ✓ Got transcript via youtube-transcript-api")
    
    # Method 3: Try to get from video description/page
    if not transcript:
        transcript = get_transcript_from_page(video_id)
    
    return transcript

def get_transcript_from_page(video_id):
    """Try to extract transcript from video page."""
    try:
        url = f"https://www.youtube.com/watch?v={video_id}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            # Look for captions data in the page
            html = response.text
            
            # Try to find caption tracks
            import re
            # Look for captionTracks JSON
            pattern = r'"captionTracks":(\[.*?\])'
            match = re.search(pattern, html)
            
            if match:
                try:
                    captions = json.loads(match.group(1))
                    if captions:
                        # Get English caption URL if available
                        for caption in captions:
                            if caption.get('languageCode', '').startswith('en'):
                                caption_url = caption.get('baseUrl')
                                if caption_url:
                                    # Fetch caption data
                                    caption_response = requests.get(caption_url, timeout=15)
                                    if caption_response.status_code == 200:
                                        # Parse XML captions
                                        from xml.etree import ElementTree
                                        root = ElementTree.fromstring(caption_response.content)
                                        texts = [elem.text for elem in root.iter() if elem.text]
                                        return ' '.join(filter(None, texts))
                except:
                    pass
            
            # Alternative: Look for ytInitialData
            pattern2 = r'ytInitialData\s*=\s*({.*?});'
            match2 = re.search(pattern2, html, re.DOTALL)
            if match2:
                try:
                    data = json.loads(match2.group(1))
                    # Navigate through the complex JSON to find captions
                    # This is simplified - actual structure is complex
                    import json
                    # Try to find playerCaptionsTracklistRenderer
                    def find_captions(obj):
                        if isinstance(obj, dict):
                            if 'playerCaptionsTracklistRenderer' in obj:
                                return obj['playerCaptionsTracklistRenderer']
                            for value in obj.values():
                                result = find_captions(value)
                                if result:
                                    return result
                        elif isinstance(obj, list):
                            for item in obj:
                                result = find_captions(item)
                                if result:
                                    return result
                        return None
                    
                    captions_data = find_captions(data)
                    if captions_data:
                        print(f"   Found caption data in page")
                except:
                    pass
    except:
        pass
    
    return None

def analyze_with_gemini(transcript, keywords, video_title):
    """Analyze content with Gemini."""
    if not GEMINI_API_KEY:
        print("ERROR: Gemini API Key missing.")
        return False

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        keyword_list = ", ".join(keywords)
        
        # Limit transcript length
        transcript_short = transcript[:5000] if len(transcript) > 5000 else transcript
        
        prompt = f"""
        VIDEO TITLE: {video_title}
        
        TRANSCRIPT:
        {transcript_short}
        
        QUESTION: Is this video related to ANY of these topics?
        Topics: {keyword_list}
        
        Respond with ONLY: {{"relevant": true}} or {{"relevant": false}}
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
        
        if '"relevant": true' in response_text or "'relevant': true" in response_text:
            print("   ✅ RELEVANT")
            return True
        else:
            print("   ❌ NOT RELEVANT")
            return False

    except Exception as e:
        print(f"   🚨 Gemini analysis failed: {e}")
        return False

def check_title_relevance(video_title, keywords):
    """Check if title suggests relevance."""
    title_lower = video_title.lower()
    
    # Direct keyword matches
    for keyword in keywords:
        if keyword.lower() in title_lower:
            return True
    
    # Common variations
    variations = [
        'budget', 'economy', 'economic', 'gdp', 'inflation', 'tax', 
        'trade', 'fta', 'india-eu', 'india eu', 'de-dollar',
        'rbi', 'reserve bank', 'monetary', 'fiscal', 'scheme',
        'yojana', 'policy', 'government', 'survey'
    ]
    
    for term in variations:
        if term in title_lower:
            return True
    
    return False

def get_latest_videos(channel_id):
    """Fetch latest videos from RSS feed."""
    feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(feed_url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            feed = feedparser.parse(response.content)
            videos = []
            
            for entry in feed.entries[:15]:  # Limit to 15
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
                    
            return videos
            
    except Exception as e:
        print(f"   ✗ Error fetching videos: {e}")
    
    return []

def main():
    """Main execution function."""
    print("\n" + "=" * 80)
    print("STARTING YOUTUBE MONITOR")
    print("=" * 80)
    
    # Test yt-dlp installation
    print("Checking yt-dlp installation...")
    try:
        result = subprocess.run(['yt-dlp', '--version'], capture_output=True, text=True)
        print(f"✓ yt-dlp version: {result.stdout.strip()}")
    except:
        print("✗ yt-dlp not found or not working")
    
    send_telegram_message("🔍 YouTube Monitor Started")
    
    relevant_videos = []
    
    for channel_name, config in CHANNELS_TO_WATCH.items():
        print(f"\n🔍 Checking: {channel_name}")
        
        videos = get_latest_videos(config["id"])
        
        if not videos:
            print(f"   No videos found")
            continue
            
        print(f"   Processing {len(videos)} videos...")
        
        for i, video in enumerate(videos):
            print(f"\n{'─'*60}")
            print(f"📺 [{i+1}/{len(videos)}] {video['title']}")
            print(f"   Published: {video['published']}")
            
            # Try to get transcript
            transcript = get_transcript_all_methods(video['id'], video['title'])
            
            if transcript and len(transcript) > 100:  # Need reasonable length
                print(f"   ✓ Got transcript ({len(transcript)} chars)")
                
                # Analyze with Gemini
                is_relevant = analyze_with_gemini(transcript, config["keywords"], video['title'])
                
                if is_relevant:
                    relevant_videos.append(f"• [{video['title']}]({video['link']}) - {channel_name}")
                    print(f"   ✅ ADDED (Transcript analyzed)")
                else:
                    print(f"   ❌ NOT RELEVANT")
            else:
                # Fallback to title check
                title_relevant = check_title_relevance(video['title'], config["keywords"])
                
                if title_relevant:
                    print(f"   ⚠️ No transcript, but title suggests relevance")
                    relevant_videos.append(f"• [{video['title']}]({video['link']}) - {channel_name} [Title]")
                    print(f"   ✅ ADDED (Title only)")
                else:
                    print(f"   ❌ NOT RELEVANT (no transcript, title doesn't match)")
    
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print(f"Total relevant videos found: {len(relevant_videos)}")
    
    # Send results
    if relevant_videos:
        if len(relevant_videos) > 10:
            message = f"🚨 **{len(relevant_videos)} Relevant Videos Found:**\n\n"
            message += "\n".join(relevant_videos[:10])
            message += f"\n\n... and {len(relevant_videos) - 10} more"
        else:
            message = f"🚨 **{len(relevant_videos)} Relevant Videos Found:**\n\n"
            message += "\n".join(relevant_videos)
        
        send_telegram_message(message)
        print(f"\n✅ Sent notification with {len(relevant_videos)} videos")
    else:
        message = "✅ **Daily Check:** No relevant videos found in the last 24 hours."
        send_telegram_message(message)
        print(f"\n✅ Sent 'no videos' notification")

if __name__ == "__main__":
    main()
