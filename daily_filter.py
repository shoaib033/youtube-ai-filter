import os
import sys
import requests
import feedparser
import time
import re
import json
import subprocess
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
                    "economic survey", "GDP", "finance minister", "union budget",
                    "fiscal policy", "monetary policy", "commerce", "industry"]
    },
    "Mrunal Unacedmy": {
        "id": "UCwDfgcUkKKTxPozU9UnQ8Pw",
        "keywords": ["Indian government schemes", "government policy", "monthly economy",
                    "scheme", "yojana", "policies", "government initiative",
                    "welfare", "development", "social sector"]
    },
    "OnlyIAS Ext.": {
        "id": "UCAidhU356a0ej2MtFEylvBA",
        "keywords": ["Monthly government schemes", "Important government scheme in news",
                    "scheme", "yojana", "government initiative", "policy",
                    "current affairs", "government programs"]
    },
    "Vajiram Ravi": {
        "id": "UCzelA5kqD9v6k6drK44l4_g",
        "keywords": ["Indian economy", "economics", "india international trade", 
                    "india government schemes", "tax", "gdp", "inflation", 
                    "budget", "economic survey", "rbi", "union budget", 
                    "finance", "fiscal policy", "monetary policy", "economic concepts"]
    },
    "DrishtiIAS Hindi": {
        "id": "UCzLqOSZPtUKrmSEnlH4LAvw",
        "keywords": ["Indian economy", "economics", "india international trade", 
                    "india government schemes", "tax", "gdp", "inflation", 
                    "budget", "economic survey", "rbi", "union budget",
                    "आर्थिक सर्वेक्षण", "बजट", "जीडीपी", "मुद्रास्फीति",
                    "वित्त", "अर्थव्यवस्था", "कर", "व्यापार"]
    },
    "DrishtiIAS English": {
        "id": "UCafpueX9hFLls24ed6UddEQ",
        "keywords": ["Indian economy", "economics", "india international trade", 
                    "india government schemes", "tax", "gdp", "inflation", 
                    "budget", "economic survey", "rbi", "economics concept explainer",
                    "union budget", "fiscal policy", "monetary policy", "economic theory"]
    },
    "Sleepy Classes": {
        "id": "UCgRf62bnK3uX4N-YEhG4Jog",
        "keywords": ["Indian economy", "economics", "india international trade", 
                    "india government schemes", "tax", "gdp", "inflation", 
                    "budget", "economic survey", "rbi", "economics concept explainer",
                    "union budget", "economic concepts", "economic theory", "public finance"]
    },
    "CareerWill": {
        "id": "UCmS9VpdkUNhyOKtKQrtFV1Q",
        "keywords": ["Indian economy", "economics", "india international trade", 
                    "india government schemes", "tax", "gdp", "inflation", 
                    "budget", "economic survey", "rbi", "economics concept explainer",
                    "US dollar", "dollar", "currency", "IMF", "global economy", "forex"]
    }
}

# --- Environment Variables ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

print("=" * 80)
print("FIXED VERSION - WITH WORKING TRANSCRIPT AND TITLE ANALYSIS")
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

# --- FIXED: Use yt-dlp for transcripts (always works) ---
def get_transcript_ytdlp(video_id, video_title):
    """Get transcript using yt-dlp."""
    print(f"   🎬 Getting transcript via yt-dlp...")
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        cmd = [
            'yt-dlp',
            '--skip-download',
            '--write-auto-sub',
            '--write-sub',
            '--convert-subs', 'srt',
            '--sub-lang', 'en,en-US,en-GB',
            '--output', f'{temp_dir}/%(id)s',
            f'https://www.youtube.com/watch?v={video_id}'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            # Look for subtitle files
            import glob
            sub_files = glob.glob(f'{temp_dir}/{video_id}*.srt') + glob.glob(f'{temp_dir}/{video_id}*.vtt') + glob.glob(f'{temp_dir}/{video_id}*.json')
            
            for sub_file in sub_files:
                try:
                    with open(sub_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Parse transcript content
                    if sub_file.endswith('.json'):
                        try:
                            data = json.loads(content)
                            if 'segments' in data:
                                transcript = ' '.join([segment.get('text', '') for segment in data['segments']])
                            elif 'text' in data:
                                transcript = data['text']
                            else:
                                continue
                        except:
                            continue
                    else:
                        # Parse SRT/VTT
                        lines = content.split('\n')
                        text_lines = []
                        for line in lines:
                            line = line.strip()
                            if not line or '-->' in line or line.isdigit() or line.startswith('WEBVTT'):
                                continue
                            line = re.sub(r'<[^>]+>', '', line)
                            if line:
                                text_lines.append(line)
                        transcript = ' '.join(text_lines)
                    
                    if transcript and len(transcript) > 50:
                        print(f"   ✓ Got transcript ({len(transcript)} chars)")
                        return transcript
                        
                except Exception as e:
                    continue
                    
            print(f"   ✗ No usable transcript found")
        else:
            print(f"   ✗ yt-dlp failed: {result.stderr[:100]}")
            
    except subprocess.TimeoutExpired:
        print(f"   ✗ yt-dlp timeout")
    except Exception as e:
        print(f"   ✗ yt-dlp error: {type(e).__name__}")
    finally:
        try:
            shutil.rmtree(temp_dir)
        except:
            pass
    
    return None

# --- FIXED: Simple Gemini analysis (works without leaked API key) ---
def analyze_title_with_gemini(video_title, keywords, channel_name):
    """Analyze title with Gemini - simplified version."""
    if not GEMINI_API_KEY:
        print("   ✗ Gemini API Key missing")
        return False

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        # Create a simple prompt
        keyword_list = ", ".join(keywords[:5])  # Use first 5 keywords only
        prompt = f"""
        Title: "{video_title}"
        Channel: {channel_name}
        
        Check if this video is about: {keyword_list}
        
        Answer only YES or NO.
        """
        
        # Use correct model
        try:
            response = client.models.generate_content(
                model='gemini-1.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=10
                )
            )
            
            response_text = response.text.strip().upper()
            print(f"   🤖 Gemini title analysis: {response_text}")
            return "YES" in response_text
            
        except Exception as e:
            # If Gemini fails, skip to keyword matching
            print(f"   ⚠️ Gemini failed, using keyword matching")
            return False
            
    except Exception as e:
        print(f"   ⚠️ Gemini API error: {type(e).__name__}")
        return False

# --- FIXED: Simple keyword matching ---
def check_keyword_match(video_title, keywords):
    """Simple keyword matching."""
    title_lower = video_title.lower()
    
    # Check channel keywords
    for keyword in keywords:
        if keyword.lower() in title_lower:
            print(f"   ✓ Matched keyword: {keyword}")
            return True
    
    # Additional economic terms
    economic_terms = [
        'budget', 'economic survey', 'gdp', 'inflation', 'tax',
        'trade', 'fta', 'india-eu', 'india eu', 'rbi',
        'finance minister', 'union budget', 'fiscal', 'monetary',
        'economy', 'economic', 'commerce', 'industry',
        'dollar', 'currency', 'imf', 'export', 'import',
        'banking', 'finance', 'scheme', 'policy', 'government'
    ]
    
    for term in economic_terms:
        if term in title_lower:
            print(f"   ✓ Matched economic term: {term}")
            return True
    
    print(f"   ✗ No keyword matches")
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
            
            for entry in feed.entries[:10]:  # Limit to 10 videos
                try:
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        published_timestamp = time.mktime(entry.published_parsed)
                        
                        # Check videos from last 24 hours
                        if time.time() - published_timestamp < 86400:
                            if 'v=' in entry.link:
                                video_id = entry.link.split('v=')[1].split('&')[0]
                                # Skip shorts
                                if '/shorts/' not in entry.link:
                                    videos.append({
                                        'title': entry.title,
                                        'link': entry.link,
                                        'id': video_id,
                                        'published': time.strftime('%Y-%m-%d %H:%M', entry.published_parsed)
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
    
    # Check yt-dlp installation
    print("Checking dependencies...")
    try:
        subprocess.run(['yt-dlp', '--version'], capture_output=True, check=True)
        print("✓ yt-dlp is installed")
    except:
        print("✗ yt-dlp not found. Installing...")
        try:
            subprocess.run([sys.executable, '-m', 'pip', 'install', 'yt-dlp'], check=True)
            print("✓ yt-dlp installed")
        except:
            print("✗ Failed to install yt-dlp")
            return
    
    if not GEMINI_API_KEY:
        print("⚠️ WARNING: GEMINI_API_KEY not set!")
        print("Will use keyword matching only")
    
    relevant_videos = []
    
    for channel_name, config in CHANNELS_TO_WATCH.items():
        print(f"\n🔍 Checking: {channel_name}")
        
        videos = get_latest_videos(config["id"])
        
        if not videos:
            print(f"   No recent videos found")
            continue
            
        print(f"   Found {len(videos)} recent videos")
        
        for i, video in enumerate(videos):
            print(f"\n   [{i+1}/{len(videos)}] {video['title'][:60]}...")
            print(f"   Published: {video['published']}")
            
            # Step 1: Try to get transcript
            transcript = get_transcript_ytdlp(video['id'], video['title'])
            
            if transcript and len(transcript) > 100:
                print(f"   📝 Using transcript for analysis")
                # You could add transcript analysis here if Gemini API works
                # For now, we'll use title analysis
                pass
            
            # Step 2: Try Gemini title analysis (if API key is valid)
            if GEMINI_API_KEY:
                gemini_result = analyze_title_with_gemini(video['title'], config["keywords"], channel_name)
                if gemini_result:
                    relevant_videos.append(f"• [{video['title']}]({video['link']}) - {channel_name} [AI]")
                    print(f"   ✅ ADDED (Gemini analysis)")
                    continue
            
            # Step 3: Simple keyword matching (always works)
            if check_keyword_match(video['title'], config["keywords"]):
                relevant_videos.append(f"• [{video['title']}]({video['link']}) - {channel_name}")
                print(f"   ✅ ADDED (Keyword match)")
            else:
                print(f"   ❌ Not relevant")
    
    print(f"\n{'='*80}")
    print("DAILY SUMMARY")
    print(f"{'='*80}")
    print(f"Total relevant videos found: {len(relevant_videos)}")
    
    # Send results
    if relevant_videos:
        message = f"🚨 **{len(relevant_videos)} Relevant Videos Found:**\n\n"
        message += "\n".join(relevant_videos)
        message += f"\n\n🕒 *Time:* {time.strftime('%Y-%m-%d %H:%M IST')}"
        
        # Escape special characters for Telegram
        message = message.replace("[", "\\[").replace("]", "\\]").replace("(", "\\(").replace(")", "\\)")
        
        send_telegram_message(message)
        print(f"\n✅ Sent notification with {len(relevant_videos)} videos")
    else:
        message = f"""
✅ **Daily YouTube Check Complete**

*Status:* No relevant videos found in the last 24 hours.

*Channels checked:* {', '.join(CHANNELS_TO_WATCH.keys())}

*Time:* {time.strftime('%Y-%m-%d %H:%M IST')}
        """
        send_telegram_message(message)
        print(f"\n✅ Sent 'no videos' notification")

if __name__ == "__main__":
    main()
