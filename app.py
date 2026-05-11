from flask import Flask, jsonify, request, send_from_directory
from supabase import create_client
import random
import os
import json
import requests
import re
import time
import logging
import sys

# Set up logging to see errors in Render
logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='public', static_url_path='')

# Supabase credentials
SUPABASE_URL = "https://kwuidjidzeehevigvgwb.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imt3dWlkamlkemVlaGV2aWd2Z3diIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzY3MjMxNzMsImV4cCI6MjA5MjI5OTE3M30.1HRlRYVgc4-Br_T70-SwlVGGluUtLZLi6-9h7SWxpb0"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# OpenRouter API key from environment variable
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

logger.info(f"API Key loaded: {'YES' if OPENROUTER_API_KEY else 'NO'}")

# Updated system prompt for families, couples, and solo travelers
VOYAGER_SYSTEM_PROMPT = """You are Voyager, a travel assistant for families, couples, and solo travelers planning trips to Orlando theme parks, cruises, and romantic getaways.

First, detect the traveler type from the user's first message:
- If they mention kids or "family" → Family trip
- If they mention "honeymoon", "anniversary", "couple", "romantic" → Couples trip
- If they mention "alone", "solo", "by myself" → Solo trip

Then ask questions based on traveler type:

FOR FAMILY: family size & kids ages, budget, travel month, must-do experiences, park preference.
FOR COUPLES: number of adults, budget, travel month, romantic must-haves (fine dining, spas, adult pools), preferred vibe (luxury, adventure, relaxation).
FOR SOLO: budget, travel month, interests (thrill rides, shows, relaxation), desired pace.

After 5 answers, output ONLY this JSON, nothing else:
{"recommendation_ready":true,"traveler_type":"family","park":"Universal","summary":"2 sentences tailored to traveler type","savings":"Save $X","best_deal":"Tip","affiliate_category":"universal_tickets"}

One question at a time. Keep responses short. Detect language automatically."""


@app.route('/')
def index():
    return app.send_static_file('index.html')


@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)


@app.route('/privacy.html')
def privacy():
    return app.send_static_file('privacy.html')


@app.route('/chat.html')
def chat():
    return app.send_static_file('chat.html')


@app.route('/blog/<path:filename>')
def serve_blog(filename):
    return app.send_static_file(f'blog/{filename}')


@app.route('/<path:filename>.html')
def serve_html(filename):
    return app.send_static_file(f'{filename}.html')


@app.route('/sitemap.xml')
def sitemap():
    base_url = "https://voyager-flask.onrender.com"
    pages = [
        "/",
        "/chat.html",
        "/universal-vs-disney.html",
        "/family-cruise-guide-2026.html",
        "/couples-cruise-guide-2026.html",
        "/celebrate-mom.html",
        "/privacy.html"
    ]
    today = time.strftime('%Y-%m-%d')
    sitemap_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
    sitemap_content += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for page in pages:
        sitemap_content += '  <url>\n'
        sitemap_content += f'    <loc>{base_url}{page}</loc>\n'
        sitemap_content += f'    <lastmod>{today}</lastmod>\n'
        if page == "/":
            sitemap_content += '    <priority>1.0</priority>\n'
        elif page in ["/universal-vs-disney.html", "/family-cruise-guide-2026.html", "/couples-cruise-guide-2026.html"]:
            sitemap_content += '    <priority>0.9</priority>\n'
        else:
            sitemap_content += '    <priority>0.8</priority>\n'
        sitemap_content += '  </url>\n'
    sitemap_content += '</urlset>'
    return app.response_class(sitemap_content, mimetype='application/xml')


@app.route('/robots.txt')
def robots():
    robots_content = 'User-agent: *\n'
    robots_content += 'Allow: /\n'
    robots_content += 'Sitemap: https://voyager-flask.onrender.com/sitemap.xml\n'
    return app.response_class(robots_content, mimetype='text/plain')


# ========== TEST ENDPOINTS ==========

@app.route('/api/test-db')
def test_db():
    try:
        response = supabase.table('affiliate_links').select('*', count='exact').execute()
        return jsonify({'connected': True, 'count': response.count})
    except Exception as e:
        return jsonify({'connected': False, 'error': str(e)}), 500


@app.route('/api/test-key')
def test_key():
    key = os.environ.get("OPENROUTER_API_KEY")
    if key:
        return jsonify({'status': 'ok', 'key_prefix': key[:20] + '...'})
    else:
        return jsonify({'status': 'error', 'message': 'OPENROUTER_API_KEY not found'}), 500


# ========== AFFILIATE LINK API ENDPOINTS ==========

@app.route('/api/get_link')
def get_link():
    try:
        response = supabase.table('affiliate_links').select('*').eq('is_active', True).execute()
        links = response.data
        if not links:
            return jsonify({'affiliate_link': 'https://example.com/no-links', 'error': 'No links found'})
        selected = random.choice(links)
        supabase.table('affiliate_links').update({'clicks': selected['clicks'] + 1}).eq('id', selected['id']).execute()
        return jsonify({'affiliate_link': selected['url'], 'name': selected['name']})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/get_link/<category>')
def get_link_by_category(category):
    try:
        response = supabase.table('affiliate_links').select('*').eq('category', category).eq('is_active', True).execute()
        links = response.data
        if not links:
            return jsonify({'affiliate_link': 'https://example.com/no-links', 'error': f'No links found for category: {category}'}), 404
        selected = random.choice(links)
        supabase.table('affiliate_links').update({'clicks': selected['clicks'] + 1}).eq('id', selected['id']).execute()
        return jsonify({'affiliate_link': selected['url'], 'name': selected['name'], 'category': category})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/links/<page>')
def get_links_for_page(page):
    try:
        response = supabase.table('affiliate_links').select('*').eq('page_location', page).eq('is_active', True).execute()
        return jsonify(response.data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/amazon/<page>')
def get_amazon_links(page):
    try:
        response = supabase.table('affiliate_links').select('*').eq('category', 'amazon').eq('page_location', page).eq('is_active', True).execute()
        return jsonify(response.data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/click/<int:link_id>', methods=['POST'])
def track_click(link_id):
    try:
        response = supabase.table('affiliate_links').select('clicks').eq('id', link_id).execute()
        if response.data:
            current_clicks = response.data[0]['clicks']
            supabase.table('affiliate_links').update({'clicks': current_clicks + 1}).eq('id', link_id).execute()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ========== AI CHAT ENDPOINT - RULE-BASED FALLBACK (WORKS 100%) ==========

@app.route('/api/voyager-chat', methods=['POST'])
def voyager_chat():
    try:
        data = request.get_json()
        messages = data.get('messages', [])
        
        if not messages:
            return jsonify({'error': 'No messages provided'}), 400
        
        # Get the last user message
        last_message = messages[-1]['content'].lower()
        
        # Simple rule-based responses that always work
        if any(word in last_message for word in ["family", "kids", "children", "ages", "old"]):
            reply = "Great! How many people are in your family, and what are the ages of the kids?"
        elif any(word in last_message for word in ["budget", "$", "money", "dollar", "spend"]):
            reply = "What's your approximate budget for the trip? (Example: $3,000)"
        elif any(word in last_message for word in ["month", "summer", "spring", "fall", "winter", "june", "july", "august", "may", "april", "march", "february", "january", "december", "november", "october", "september"]):
            reply = "Which travel month works best for your family?"
        elif any(word in last_message for word in ["harry potter", "thrill", "ride", "coaster", "universal", "disney", "potion", "wand", "magic"]):
            reply = "Universal Orlando has amazing thrill rides and the Wizarding World of Harry Potter. Would you like me to show you some ticket options and deals?"
        elif any(word in last_message for word in ["cruise", "ship", "boat", "sailing"]):
            reply = "Cruises are a great option for families! I can help you find the best family cruise deals. Which departure port works best for you?"
        elif any(word in last_message for word in ["hotel", "stay", "room", "resort", "accommodation"]):
            reply = "I can help you find hotels near the parks. What's your nightly budget?"
        elif "recommendation" in last_message or "deal" in last_message:
            reply = "Based on what you've shared, I recommend Universal Orlando for the best value. A family of 4 can save over $1,500 compared to Disney. Would you like to see current ticket prices?"
        else:
            reply = "Thanks for sharing! Let me help you plan your trip. First, could you tell me how many people are in your family and the ages of any children?"
        
        return jsonify({'reply': reply})
        
    except Exception as e:
        logger.error(f"Error in chat: {str(e)}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)