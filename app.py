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

# Supabase credentials - Using environment variables for security
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')

# Note: Remove fallback keys in production
if not SUPABASE_URL:
    SUPABASE_URL = "https://asgtixmtfcqpkwzlxihu.supabase.co"
if not SUPABASE_KEY:
    SUPABASE_KEY = "YOUR_ANON_KEY_HERE"  # Replace with your actual anon key

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# OpenRouter API key from environment variable
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

logger.info(f"Supabase URL: {'YES' if SUPABASE_URL else 'NO'}")
logger.info(f"Supabase Key: {'YES' if SUPABASE_KEY else 'NO'}")
logger.info(f"OpenRouter API Key: {'YES' if OPENROUTER_API_KEY else 'NO'}")

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
        "/dorney-park.html",
        "/luxury-safaris.html",
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


# ========== AFFILIATE API ENDPOINTS (SIMPLIFIED - NO JOINS) ==========

@app.route('/api/affiliate/links')
def get_all_affiliate_links():
    """Get all active affiliate links"""
    try:
        response = supabase.table('affiliate_links').select('*').eq('active', True).order('sort_order').execute()
        return jsonify(response.data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/affiliate/links/page/<page_name>')
def get_links_by_page(page_name):
    """Get affiliate links for a specific page"""
    try:
        response = supabase.table('affiliate_links').select('*').eq('page', page_name).eq('active', True).order('sort_order').execute()
        return jsonify(response.data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/affiliate/links/category/<category>')
def get_links_by_category(category):
    """Get affiliate links by category"""
    try:
        response = supabase.table('affiliate_links').select('*').eq('category', category).eq('active', True).order('sort_order').execute()
        return jsonify(response.data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/affiliate/click', methods=['POST'])
def track_affiliate_click():
    """Track affiliate link clicks"""
    try:
        data = request.json
        supabase.table('click_tracking').insert({
            'affiliate_link_id': data.get('link_id'),
            'page': data.get('page'),
            'ip_address': request.remote_addr,
            'user_agent': request.headers.get('User-Agent')
        }).execute()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/affiliate/featured')
def get_featured_deals():
    """Get featured deals for homepage"""
    try:
        response = supabase.table('affiliate_links').select('*').eq('active', True).limit(6).order('sort_order').execute()
        return jsonify(response.data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ========== LEGACY AFFILIATE ENDPOINTS (Keep for compatibility) ==========

@app.route('/api/get_link')
def get_link():
    try:
        response = supabase.table('affiliate_links').select('*').eq('active', True).execute()
        links = response.data
        if not links:
            return jsonify({'affiliate_link': 'https://example.com/no-links', 'error': 'No links found'})
        selected = random.choice(links)
        return jsonify({'affiliate_link': selected['url'], 'name': selected['name']})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/get_link/<category>')
def get_link_by_category(category):
    try:
        response = supabase.table('affiliate_links').select('*').eq('category', category).eq('active', True).execute()
        links = response.data
        if not links:
            return jsonify({'affiliate_link': 'https://example.com/no-links', 'error': f'No links found for category: {category}'}), 404
        selected = random.choice(links)
        return jsonify({'affiliate_link': selected['url'], 'name': selected['name'], 'category': category})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/links/<page>')
def get_links_for_page(page):
    try:
        response = supabase.table('affiliate_links').select('*').eq('page', page).eq('active', True).execute()
        return jsonify(response.data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/amazon/<page>')
def get_amazon_links(page):
    try:
        response = supabase.table('affiliate_links').select('*').eq('category', 'packing').eq('page', page).eq('active', True).execute()
        return jsonify(response.data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/click/<int:link_id>', methods=['POST'])
def track_click(link_id):
    try:
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ========== AI CHAT ENDPOINT - WITH STATE TRACKING ==========

@app.route('/api/voyager-chat', methods=['POST'])
def voyager_chat():
    try:
        data = request.get_json()
        messages = data.get('messages', [])
        
        if not messages:
            return jsonify({'error': 'No messages provided'}), 400
        
        # Count how many user messages have been sent
        user_messages = [m for m in messages if m['role'] == 'user']
        stage = len(user_messages)
        
        # Stage-based responses
        if stage == 0:
            reply = "Hey there! 👋 I'm Voyager — your family travel deal finder.\n\nFirst up — how many people are in your group, and how old are the kids?"
        
        elif stage == 1:
            reply = "What's your overall budget for the trip?"
        
        elif stage == 2:
            reply = "When are you planning to visit? (Month or season)"
        
        elif stage == 3:
            reply = "What are the must-do experiences or attractions for your family? (e.g., thrill rides, characters, shows, Harry Potter)"
        
        elif stage >= 4:
            # Extract info from previous messages
            family_info = user_messages[0]['content'] if len(user_messages) > 0 else "your family"
            budget_info = user_messages[1]['content'] if len(user_messages) > 1 else "a reasonable"
            month_info = user_messages[2]['content'] if len(user_messages) > 2 else "summer"
            
            reply = f"""✨ **Here's your personalized recommendation!** ✨

Based on {family_info} with a budget of {budget_info} traveling in {month_info}, I recommend **Universal Orlando Resort**.

🎢 **Why Universal is your best value:**
• Save $1,500+ compared to Disney World
• Epic Universe opens May 22, 2026 (brand new park!)
• Thrill rides: VelociCoaster, Hagrid's, and more
• The Wizarding World of Harry Potter

💡 **Best deal right now:** Premier hotels include FREE Unlimited Express Pass — the pass alone is worth more than the hotel room.

👉 Click below to see current ticket prices and exclusive deals!"""
        
        else:
            reply = "Tell me about your family — how many people and ages of the kids?"
        
        return jsonify({'reply': reply})
        
    except Exception as e:
        logger.error(f"Error in chat: {str(e)}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
