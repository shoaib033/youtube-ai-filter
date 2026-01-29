# Add this import at the top
import traceback

# --- GEMINI ANALYSIS FUNCTIONS --- FIXED VERSION
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
            # FALLBACK: Title analysis for IES/UPSC - SIMPLIFIED
            keywords = context["keywords"]
            keyword_list = ", ".join(keywords[:5])  # Just show first 5 for clarity
            
            prompt = f"""
            Analyze this YouTube video title for IES/UPSC Economics preparation:
            
            TITLE: "{video_title}"
            CHANNEL: {channel_name}
            
            RELEVANT TOPICS to look for: {keyword_list}
            
            INSTRUCTIONS:
            1. Is this video about Indian economy, economics, or government schemes?
            2. Does it discuss budget, trade, RBI, or economic policies?
            3. Is it relevant for Indian Economic Service (IES) exam preparation?
            
            Answer with ONLY one word: YES or NO
            
            Example responses:
            - "YES" if relevant
            - "NO" if not relevant
            """
            
            print(f"   🤖 TITLE ANALYSIS: Checking title against channel keywords")
        
        # FIXED: Use correct model name and simpler approach
        try:
            # Use the FLASH model which should be available
            model_name = 'gemini-1.5-flash'
            
            # Simpler API call
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=10,
                    top_p=0.1
                )
            )
            
            # Get response text
            if hasattr(response, 'text'):
                response_text = response.text.strip().upper()
            elif hasattr(response, 'candidates'):
                response_text = response.candidates[0].content.parts[0].text.strip().upper()
            else:
                print(f"   ✗ Unexpected response format")
                return False
            
            print(f"   Gemini response: {response_text}")
            
            # Check for YES
            if "YES" in response_text:
                return True
            return False
            
        except Exception as model_error:
            print(f"   ✗ Model error: {type(model_error).__name__}")
            
            # Alternative: Try a different approach with raw requests
            return analyze_with_gemini_fallback(prompt)
        
    except Exception as e:
        print(f"   🚨 Gemini analysis failed: {type(e).__name__}")
        print(f"   Error details: {str(e)[:100]}")
        return False

def analyze_with_gemini_fallback(prompt):
    """Fallback using direct HTTP request to Gemini API."""
    try:
        import json
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        
        headers = {
            "Content-Type": "application/json"
        }
        
        data = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 10,
                "topP": 0.1
            }
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if 'candidates' in result and len(result['candidates']) > 0:
                text = result['candidates'][0]['content']['parts'][0]['text'].strip().upper()
                print(f"   Fallback Gemini response: {text}")
                return "YES" in text
        
        return False
        
    except Exception as e:
        print(f"   ✗ Fallback also failed: {type(e).__name__}")
        return False

# --- SIMPLE KEYWORD MATCHING (Final fallback) ---
def check_simple_keyword_match(video_title, keywords):
    """Simple keyword matching as last resort."""
    title_lower = video_title.lower()
    
    print(f"   Keywords for matching: {', '.join(keywords[:5])}...")
    
    # Check channel keywords
    for keyword in keywords:
        if keyword.lower() in title_lower:
            print(f"   ✓ Matched keyword: {keyword}")
            return True
    
    # Common economic terms for IES/UPSC
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
            print(f"   ✓ Matched economic term: {term}")
            return True
    
    print(f"   ✗ No keyword matches found")
    return False
