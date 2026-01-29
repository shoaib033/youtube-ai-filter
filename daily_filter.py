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
print("FINAL FIXED VERSION WITH ALL METHODS")
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

# --- METHOD 1: yt-dlp (Most reliable) ---
def get_transcript_ytdlp(video_id, video_title):
    """Get transcript using yt-dlp."""
    print(f"\n🎬 METHOD 1 (yt-dlp): {video_title[:50]}...")
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Check if yt-dlp is installed
        result = subprocess.run(['which', 'yt-dlp'], capture_output=True, text=True)
        if result.returncode != 0:
            print("   ✗ yt-dlp not installed")
            return None
        
        # Try with deno (JavaScript runtime)
        cmd = [
            'yt-dlp',
            '--skip-download',
            '--write-auto-sub',
            '--convert-subs', 'srt',
            '--sub-lang', 'en,en-US,en-GB',
            '--output', f'{temp_dir}/%(id)s',
            f'https://www.youtube.com/watch?v={video_id}'
        ]
        
        print(f"   Running yt-dlp...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            # Look for subtitle files
            import glob
            sub_files = glob.glob(f'{temp_dir}/{video_id}*.srt') + glob.glob(f'{temp_dir}/{video_id}*.vtt')
            
            if sub_files:
                with open(sub_files[0], 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Parse SRT/VTT
                transcript = parse_subtitle_content(content)
                if transcript and len(transcript) > 100:
                    print(f"   ✓ Got transcript via yt-dlp ({len(transcript)} chars)")
                    return transcript
            else:
                print(f"   ✗ No subtitle files generated")
        else:
            print(f"   ✗ yt-dlp failed: {result.stderr[:200]}")
            
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

def parse_subtitle_content(content):
    """Parse SRT/VTT subtitle content."""
    lines = content.split('\n')
    text_lines = []
    
    for line in lines:
        line = line.strip()
        # Skip timestamp lines, empty lines, and numbering
        if not line or '-->' in line or line.isdigit() or line.startswith('WEBVTT'):
            continue
        # Remove HTML tags
        line = re.sub(r'<[^>]+>', '', line)
        if line:
            text_lines.append(line)
    
    return ' '.join(text_lines)

# --- METHOD 2: YouTube Data API ---
def get_transcript_youtube_api(video_id, video_title):
    """Get transcript using YouTube Data API."""
    print(f"   METHOD 2 (YouTube API): Trying...")
    
    # You would need a YouTube Data API key for this
    # This is a placeholder for future implementation
    return None

# --- METHOD 3: Web Scraping ---
def get_transcript_web_scraping(video_id, video_title):
    """Get transcript via web scraping."""
    print(f"   METHOD 3 (Web scraping): Trying...")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        
        response = requests.get(
            f"https://www.youtube.com/watch?v={video_id}",
            headers=headers,
            timeout=30
        )
        
        if response.status_code != 200:
            return None
        
        html = response.text
        
        # Try multiple patterns
        patterns = [
            r'"captionTracks":\s*(\[.*?\]),',
            r'captionTracks\":\s*(\[.*?\])',
            r'"captions":.*?"captionTracks":\s*(\[.*?\])',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html, re.DOTALL)
            if match:
                try:
                    caption_tracks = json.loads(match.group(1))
                    
                    # Find English captions
                    for track in caption_tracks:
                        lang = track.get('languageCode', '')
                        if lang.startswith('en'):
                            base_url = track.get('baseUrl')
                            if base_url:
                                # Fetch captions
                                caption_response = requests.get(base_url, timeout=30)
                                if caption_response.status_code == 200:
                                    # Try to parse as XML
                                    text_pattern = r'<text[^>]*>([^<]+)</text>'
                                    text_matches = re.findall(text_pattern, caption_response.text)
                                    if text_matches:
                                        transcript = ' '.join(text_matches)
                                        if len(transcript) > 100:
                                            print(f"   ✓ Got transcript via web scraping ({len(transcript)} chars)")
                                            return transcript
                except:
                    continue
        
        # Try to get description
        desc_patterns = [
            r'"description":"(.*?)"',
            r'"description":{"simpleText":"(.*?)"}',
            r'shortDescription":"(.*?)"',
        ]
        
        for pattern in desc_patterns:
            matches = re.findall(pattern, html)
            for match in matches:
                if len(match) > 200:
                    try:
                        import json
                        description = json.loads(f'"{match}"')
                        if len(description) > 200:
                            print(f"   ✓ Got description ({len(description)} chars)")
                            return f"DESCRIPTION: {description}"
                    except:
                        if len(match) > 200:
                            print(f"   ✓ Got description raw ({len(match)} chars)")
                            return f"DESCRIPTION: {match}"
        
    except Exception as e:
        print(f"   ✗ Web scraping error: {type(e).__name__}")
    
    return None

# --- MAIN: Get transcript using all methods ---
def get_transcript(video_id, video_title):
    """Get transcript using multiple methods."""
    print(f"\n🔍 Getting transcript for: {video_title[:60]}...")
    
    # Try yt-dlp first (most reliable)
    transcript = get_transcript_ytdlp(video_id, video_title)
    
    # Try web scraping if yt-dlp failed
    if not transcript:
        transcript = get_transcript_web_scraping(video_id, video_title)
    
    return transcript

# --- GEMINI ANALYSIS FUNCTIONS ---
def analyze_with_gemini(content_type, content, context, video_title, channel_name):
    """Analyze content with Gemini using correct model."""
    if not GEMINI_API_KEY:
        print("ERROR: Gemini API Key missing.")
        return False

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        if content_type == "transcript":
            # MAIN ANALYSIS: Transcript vs channel keywords
            keywords = context["keywords"]
            keyword_list = ", ".join(keywords)
            
            # Limit content length
            content_short = content[:3000] if len(content) > 3000 else content
            
            prompt = f"""
            VIDEO TITLE: {video_title}
            CHANNEL: {channel_name}
            
            CONTENT:
            {content_short}
            
            QUESTION: Is this video about ANY of these specific topics?
            TOPICS: {keyword_list}
            
            IMPORTANT: Answer YES if it discusses ANY of these topics (even just one).
            
            Respond with ONLY: YES or NO
            """
            
            print(f"   🤖 MAIN ANALYSIS: Checking against {len(keywords)} channel keywords")
            
        else:  # title analysis
            # FALLBACK: Title analysis for IES/UPSC
            prompt = f"""
            CONTEXT: Preparing for Indian Economic Service (IES) and UPSC Economics.
            
            VIDEO TITLE: "{video_title}"
            CHANNEL: {channel_name}
            
            QUESTION: Based ONLY on title, is this relevant for IES/UPSC Economics prep?
            
            CONSIDER: Indian economy, budget, trade, government schemes, RBI, fiscal/monetary policy.
            
            Respond with ONLY: YES or NO
            """
            
            print(f"   🤖 FALLBACK: Title analysis for IES/UPSC")
        
        # Use correct model - gemini-1.5-flash may not be available, try alternatives
        models_to_try = ['gemini-1.5-pro', 'gemini-pro', 'models/gemini-pro']
        
        for model_name in models_to_try:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.1,
                        max_output_tokens=10
                    )
                )
                
                response_text = response.text.strip().upper()
                print(f"   Gemini response ({model_name}): {response_text}")
                
                return response_text == "YES"
                
            except Exception as model_error:
                if "404" in str(model_error) or "not found" in str(model_error).lower():
                    continue  # Try next model
                else:
                    print(f"   ✗ Model {model_name} error: {type(model_error).__name__}")
                    break
        
        print(f"   ✗ All Gemini models failed")
        return False
        
    except Exception as e:
        print(f"   🚨 Gemini analysis failed: {type(e).__name__}: {str(e)[:100]}")
        return False

# --- SIMPLE KEYWORD MATCHING (Final fallback) ---
def check_simple_keyword_match(video_title, keywords):
    """Simple keyword matching as last resort."""
    title_lower = video_title.lower()
    
    # Check channel keywords
    for keyword in keywords:
        if keyword.lower() in title_lower:
            return True
    
    # Common economic terms
    economic_terms = [
        'budget', 'economic survey', 'gdp', 'inflation', 'tax',
        'trade', 'fta', 'india-eu', 'india eu', 'rbi',
        'finance minister', 'union budget', 'fiscal', 'monetary',
        'economy', 'economic', 'commerce', 'industry',
        'de-dollar', 'dollar', 'currency', 'imf', 'export', 'import',
        'banking', 'finance', 'scheme', 'policy', 'government'
    ]
    
    for term in economic_terms:
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
            
            for entry in feed.entries[:15]:
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
        print(f"   ✗ Error: {e}")
    
    return []

def main():
    """Main execution function."""
    print("\n" + "=" * 80)
    print("STARTING WITH ALL METHODS")
    print("=" * 80)
    
    # Check yt-dlp installation
    print("Checking dependencies...")
    try:
        subprocess.run(['yt-dlp', '--version'], capture_output=True, check=True)
        print("✓ yt-dlp is installed")
    except:
        print("✗ yt-dlp not found. Installing via pip...")
        try:
            subprocess.run([sys.executable, '-m', 'pip', 'install', 'yt-dlp'], check=True)
            print("✓ yt-dlp installed via pip")
        except:
            print("✗ Failed to install yt-dlp")
    
    if not GEMINI_API_KEY:
        print("ERROR: GEMINI_API_KEY not set!")
        return
    
    print(f"✓ Gemini API key is set")
    send_telegram_message("🔍 YouTube Monitor Started - All Methods Active")
    
    relevant_videos = []
    analysis_methods = {"Main": 0, "Title": 0, "Keyword": 0}
    
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
            
            # --- STEP 1: MAIN APPROACH (Transcript analysis) ---
            transcript = get_transcript(video['id'], video['title'])
            
            if transcript and len(transcript) > 100:
                print(f"   ✓ Got content for main analysis")
                
                # MAIN: Analyze transcript against channel keywords
                is_relevant = analyze_with_gemini(
                    "transcript", 
                    transcript,
                    config,  # channel config with keywords
                    video['title'],
                    channel_name
                )
                
                if is_relevant:
                    relevant_videos.append(f"• [{video['title']}]({video['link']}) - {channel_name}")
                    analysis_methods["Main"] += 1
                    print(f"   ✅ ADDED (Main analysis)")
                    continue
            
            # --- STEP 2: FALLBACK 1 (Title analysis with Gemini) ---
            print(f"   ⚠️ No transcript, trying title analysis...")
            title_relevant = analyze_with_gemini(
                "title",
                video['title'],
                config,
                video['title'],
                channel_name
            )
            
            if title_relevant:
                relevant_videos.append(f"• [{video['title']}]({video['link']}) - {channel_name} [Title]")
                analysis_methods["Title"] += 1
                print(f"   ✅ ADDED (Title analysis)")
                continue
            
            # --- STEP 3: FALLBACK 2 (Simple keyword matching) ---
            print(f"   ⚠️ Gemini failed, trying keyword match...")
            keyword_match = check_simple_keyword_match(video['title'], config["keywords"])
            
            if keyword_match:
                relevant_videos.append(f"• [{video['title']}]({video['link']}) - {channel_name} [Keyword]")
                analysis_methods["Keyword"] += 1
                print(f"   ✅ ADDED (Keyword match)")
            else:
                print(f"   ❌ All checks failed")
    
    print(f"\n{'='*80}")
    print("DAILY SUMMARY")
    print(f"{'='*80}")
    print(f"Total relevant videos found: {len(relevant_videos)}")
    print(f"Analysis methods: Main={analysis_methods['Main']}, Title={analysis_methods['Title']}, Keyword={analysis_methods['Keyword']}")
    
    # Send results
    if relevant_videos:
        if len(relevant_videos) > 10:
            message = f"🚨 **{len(relevant_videos)} Relevant Videos Found:**\n\n"
            message += "\n".join(relevant_videos[:10])
            message += f"\n\n... and {len(relevant_videos) - 10} more"
        else:
            message = f"🚨 **{len(relevant_videos)} Relevant Videos Found:**\n\n"
            message += "\n".join(relevant_videos)
        
        message += f"\n\n📊 *Analysis Summary:*"
        message += f"\n• Transcript analysis: {analysis_methods['Main']}"
        message += f"\n• Title analysis: {analysis_methods['Title']}"
        message += f"\n• Keyword match: {analysis_methods['Keyword']}"
        message += f"\n🕒 *Time:* {time.strftime('%Y-%m-%d %H:%M IST')}"
        
        send_telegram_message(message)
        print(f"\n✅ Sent notification with {len(relevant_videos)} videos")
    else:
        message = f"""
✅ **Daily YouTube Check Complete**

*Status:* No relevant videos found for IES/UPSC Economics preparation.

*Channels checked ({len(CHANNELS_TO_WATCH)}):*
- Mint (Economics & Trade)
- Mrunal Unacedmy (Government Schemes)
- OnlyIAS Ext. (Monthly Schemes)
- Vajiram Ravi (Economics)
- DrishtiIAS Hindi/English (Economics)
- Sleepy Classes (Economics)
- CareerWill (Economics)

*Time:* {time.strftime('%Y-%m-%d %H:%M IST')}
        """
        send_telegram_message(message)
        print(f"\n✅ Sent 'no videos' notification")

if __name__ == "__main__":
    main()
