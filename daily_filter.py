import os
import sys
import requests
import feedparser
import time
import re
import json
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
print("CORRECTED: MAIN APPROACH + FALLBACKS")
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

# --- MAIN APPROACH: Get transcript and analyze with keywords ---
def get_transcript_web_scraping(video_id, video_title):
    """Get transcript by scraping YouTube page."""
    print(f"\n🎬 Getting transcript for: {video_title[:60]}...")
    
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
            print(f"   ✗ Failed to fetch page: {response.status_code}")
            return None
        
        html = response.text
        
        # Method 1: Look for captionTracks
        import re
        
        # Pattern for captionTracks in JSON
        pattern = r'"captionTracks":\s*(\[.*?\]),'
        match = re.search(pattern, html, re.DOTALL)
        
        if match:
            try:
                caption_tracks = json.loads(match.group(1))
                
                # Find English captions
                for track in caption_tracks:
                    lang = track.get('languageCode', '')
                    if lang.startswith('en'):
                        caption_url = track.get('baseUrl')
                        if caption_url:
                            print(f"   Found English captions, fetching...")
                            
                            # Add query parameters for better format
                            if 'fmt=json3' not in caption_url and 'fmt=srv3' not in caption_url:
                                caption_url += '&fmt=json3'
                            
                            caption_response = requests.get(caption_url, timeout=30)
                            if caption_response.status_code == 200:
                                # Parse JSON captions
                                try:
                                    caption_data = json.loads(caption_response.text)
                                    # Extract text from events
                                    transcript_parts = []
                                    for event in caption_data.get('events', []):
                                        if 'segs' in event:
                                            for seg in event['segs']:
                                                if 'utf8' in seg:
                                                    transcript_parts.append(seg['utf8'])
                                    
                                    transcript = ' '.join(transcript_parts)
                                    if len(transcript) > 100:
                                        print(f"   ✓ Got transcript ({len(transcript)} chars)")
                                        return transcript
                                except json.JSONDecodeError:
                                    # Try XML parsing
                                    text_pattern = r'<text[^>]*>([^<]+)</text>'
                                    text_matches = re.findall(text_pattern, caption_response.text)
                                    if text_matches:
                                        transcript = ' '.join(text_matches)
                                        if len(transcript) > 100:
                                            print(f"   ✓ Got transcript via XML ({len(transcript)} chars)")
                                            return transcript
            except Exception as e:
                print(f"   ✗ Error parsing captions: {type(e).__name__}")
        
        # Method 2: Try to get description
        desc_pattern = r'"description":{"simpleText":"(.*?)"}'
        desc_match = re.search(desc_pattern, html)
        
        if desc_match:
            description = desc_match.group(1)
            try:
                import json
                description = json.loads(f'"{description}"')
                if len(description) > 200:
                    print(f"   ✓ Got description ({len(description)} chars)")
                    # Use description as fallback content
                    return f"DESCRIPTION: {description}"
            except:
                pass
        
        print(f"   ✗ No transcript/description found")
        return None
        
    except Exception as e:
        print(f"   ✗ Error: {type(e).__name__}: {str(e)[:100]}")
        return None

# --- MAIN ANALYSIS: Gemini checks transcript against channel keywords ---
def analyze_transcript_with_keywords(transcript, keywords, video_title, channel_name):
    """MAIN APPROACH: Check if transcript is relevant to channel keywords."""
    if not GEMINI_API_KEY:
        print("ERROR: Gemini API Key missing.")
        return False

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        keyword_list = ", ".join(keywords)
        
        # Limit transcript length
        transcript_short = transcript[:4000] if len(transcript) > 4000 else transcript
        
        prompt = f"""
        VIDEO TITLE: {video_title}
        CHANNEL: {channel_name}
        
        CONTENT (transcript/description):
        {transcript_short}
        
        QUESTION: Is the MAIN CONTENT of this video related to ANY of these specific topics?
        
        TOPICS TO CHECK: {keyword_list}
        
        IMPORTANT: 
        1. Check if the video discusses ANY of these topics (even just one)
        2. "India-EU deal" matches "trade agreement", "FTA", "international trade"
        3. "De-dollarisation" matches "Indian economy", "economics", "international trade"
        4. "Budget 2026" matches "budget", "Indian economy", "tax"
        5. Be liberal - if it's related even indirectly, say YES
        
        Respond with ONLY JSON: {{"relevant": true}} or {{"relevant": false}}
        """
        
        print(f"\n🤖 MAIN ANALYSIS: Checking against {len(keywords)} channel keywords...")
        
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
        
        # Parse JSON response
        try:
            result = json.loads(response_text)
            if result.get("relevant", False):
                print("   ✅ RELEVANT: Matches channel keywords")
                return True
            else:
                print("   ❌ NOT RELEVANT: Doesn't match channel keywords")
                return False
        except json.JSONDecodeError:
            # Fallback parsing
            if '"relevant": true' in response_text or "'relevant': true" in response_text:
                print("   ✅ RELEVANT (fallback parsing)")
                return True
            else:
                print("   ❌ NOT RELEVANT (fallback parsing)")
                return False
        
    except Exception as e:
        print(f"   🚨 Gemini analysis failed: {e}")
        return False

# --- FALLBACK 1: Title analysis for IES/UPSC context ---
def analyze_title_for_exam(video_title, channel_name):
    """FALLBACK 1: Check if title suggests relevance for IES/UPSC preparation."""
    if not GEMINI_API_KEY:
        print("ERROR: Gemini API Key missing.")
        return False

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        prompt = f"""
        CONTEXT: I am preparing for Indian Economic Service (IES) and UPSC Economics.
        
        VIDEO TITLE: "{video_title}"
        CHANNEL: {channel_name}
        
        QUESTION: Based ONLY on the title, is this video likely relevant for IES/UPSC Economics preparation?
        
        CONSIDER RELEVANCE TO:
        - Indian economy, budget, economic survey
        - Government schemes, policies, taxation
        - International trade, agreements
        - RBI, monetary policy, finance
        - Economic concepts with Indian context
        
        IMPORTANT: Be liberal - if title SUGGESTS it MIGHT be relevant, say YES.
        
        Respond with ONLY: YES or NO
        """
        
        print(f"   🤖 FALLBACK 1: Analyzing title for exam relevance...")
        
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=10
            )
        )
        
        response_text = response.text.strip().upper()
        print(f"   Title analysis result: {response_text}")
        
        return response_text == "YES"
        
    except Exception as e:
        print(f"   🚨 Title analysis failed: {e}")
        return False

# --- FALLBACK 2: Simple keyword matching ---
def check_simple_keyword_match(video_title, keywords):
    """FALLBACK 2: Simple keyword matching in title."""
    title_lower = video_title.lower()
    
    for keyword in keywords:
        if keyword.lower() in title_lower:
            return True
    
    # Common variations
    variations = [
        'budget', 'economic survey', 'gdp', 'inflation', 'tax',
        'trade', 'fta', 'india-eu', 'india eu', 'rbi',
        'finance minister', 'union budget', 'fiscal', 'monetary',
        'economy', 'economic', 'commerce', 'industry',
        'de-dollar', 'dollar', 'currency', 'imf'
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
    """Main execution function with CORRECT priority order."""
    print("\n" + "=" * 80)
    print("STARTING WITH CORRECT PRIORITY ORDER")
    print("=" * 80)
    
    if not GEMINI_API_KEY:
        print("ERROR: GEMINI_API_KEY not set!")
        return
    
    print(f"✓ Gemini API key is set")
    send_telegram_message("🔍 YouTube Monitor Started - Main + Fallback Approach")
    
    relevant_videos = []
    
    for channel_name, config in CHANNELS_TO_WATCH.items():
        print(f"\n🔍 Checking: {channel_name}")
        print(f"   Keywords: {len(config['keywords'])} topics")
        
        videos = get_latest_videos(config["id"])
        
        if not videos:
            print(f"   No videos found")
            continue
            
        print(f"   Processing {len(videos)} videos...")
        
        for i, video in enumerate(videos):
            print(f"\n{'─'*60}")
            print(f"📺 [{i+1}/{len(videos)}] {video['title']}")
            print(f"   Published: {video['published']}")
            
            # --- STEP 1: MAIN APPROACH ---
            # Try to get transcript/description
            content = get_transcript_web_scraping(video['id'], video['title'])
            
            if content and len(content) > 200:
                print(f"   ✓ Got content for main analysis")
                
                # MAIN ANALYSIS: Check against channel keywords
                is_relevant = analyze_transcript_with_keywords(
                    content, 
                    config["keywords"], 
                    video['title'],
                    channel_name
                )
                
                if is_relevant:
                    relevant_videos.append(f"• [{video['title']}]({video['link']}) - {channel_name}")
                    print(f"   ✅ ADDED (Main analysis - matches keywords)")
                    continue  # Skip fallbacks since main analysis succeeded
                else:
                    print(f"   ❌ Main analysis: Not relevant to keywords")
                    # Continue to fallbacks since main analysis said no
            
            else:
                print(f"   ⚠️ No content for main analysis")
            
            # --- STEP 2: FALLBACK 1 ---
            # Title analysis for exam context
            print(f"   ⚠️ Trying Fallback 1: Title analysis for IES/UPSC...")
            title_relevant = analyze_title_for_exam(video['title'], channel_name)
            
            if title_relevant:
                relevant_videos.append(f"• [{video['title']}]({video['link']}) - {channel_name} [Title analysis]")
                print(f"   ✅ ADDED (Fallback 1 - title suggests exam relevance)")
                continue  # Skip further fallbacks
            
            # --- STEP 3: FALLBACK 2 ---
            # Simple keyword matching
            print(f"   ⚠️ Trying Fallback 2: Simple keyword match...")
            keyword_match = check_simple_keyword_match(video['title'], config["keywords"])
            
            if keyword_match:
                relevant_videos.append(f"• [{video['title']}]({video['link']}) - {channel_name} [Keyword match]")
                print(f"   ✅ ADDED (Fallback 2 - keyword match)")
            else:
                print(f"   ❌ All checks failed - Not relevant")
    
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print(f"Total relevant videos found: {len(relevant_videos)}")
    
    # Send results
    if relevant_videos:
        # Add analysis method tags
        methods_summary = {
            "Main": 0,
            "Title": 0,
            "Keyword": 0
        }
        
        for video in relevant_videos:
            if "[Title analysis]" in video:
                methods_summary["Title"] += 1
            elif "[Keyword match]" in video:
                methods_summary["Keyword"] += 1
            else:
                methods_summary["Main"] += 1
        
        if len(relevant_videos) > 10:
            message = f"🚨 **{len(relevant_videos)} Relevant Videos Found:**\n\n"
            message += "\n".join(relevant_videos[:10])
            message += f"\n\n... and {len(relevant_videos) - 10} more"
        else:
            message = f"🚨 **{len(relevant_videos)} Relevant Videos Found:**\n\n"
            message += "\n".join(relevant_videos)
        
        # Add summary
        message += f"\n\n📊 *Analysis Methods:*"
        message += f"\n• Main (transcript analysis): {methods_summary['Main']}"
        message += f"\n• Title analysis: {methods_summary['Title']}"
        message += f"\n• Keyword match: {methods_summary['Keyword']}"
        
        send_telegram_message(message)
        print(f"\n✅ Sent notification with {len(relevant_videos)} videos")
    else:
        message = "✅ **Daily Check:** No relevant videos found in the last 24 hours."
        send_telegram_message(message)
        print(f"\n✅ Sent 'no videos' notification")

if __name__ == "__main__":
    main()
