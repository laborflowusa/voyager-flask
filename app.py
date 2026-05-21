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
    SUPABASE_KEY = "YOUR_SUPABASE_ANON_KEY_HERE"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# OpenRouter API key from environment variable
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

logger.info(f"Supabase URL: {'YES' if SUPABASE_URL else 'NO'}")
logger.info(f"Supabase Key: {'YES' if SUPABASE_KEY else 'NO'}")
logger.info(f"OpenRouter API Key: {'YES' if OPENROUTER_API_KEY else 'NO'}")


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


# ========== AI CHAT ENDPOINT - WITH OPENROUTER AI ==========

@app.route('/api/voyager-chat', methods=['POST'])
def voyager_chat():
    """AI chat endpoint using OpenRouter"""
    try:
        data = request.get_json()
        messages = data.get('messages', [])
        
        if not messages:
            return jsonify({'error': 'No messages provided'}), 400
        
        # Count user messages to know when to show deal card
        user_messages = [m for m in messages if m['role'] == 'user']
        user_message_count = len(user_messages)
        
        # Extract budget and family info from conversation
        family_info = "your family"
        budget_info = "a reasonable budget"
        destination_info = ""
        
        for msg in user_messages:
            content = msg['content'].lower()
            if 'budget' in content or '$' in content:
                budget_info = msg['content']
            if 'family' in content or 'kids' in content or 'people' in content:
                family_info = msg['content']
            if 'universal' in content:
                destination_info = "Universal Orlando"
            elif 'disney' in content:
                destination_info = "Disney World"
            elif 'cruise' in content:
                destination_info = "a cruise"
        
        # System prompt that guides the AI
        system_prompt = """You are Voyager, a friendly, enthusiastic travel assistant helping families plan trips to Disney World, Universal Orlando, and cruises.

IMPORTANT RULES:
1. Keep responses VERY short (2-3 sentences max)
2. Be warm and helpful, like a friend giving advice
3. When someone mentions budget concerns, recommend Universal over Disney (saves $1,500+)
4. Mention Epic Universe (opens May 22, 2026) for Universal trips
5. NEVER ask for email, phone number, or personal info
6. After 3-4 messages, say something like "I've found a great deal for you!"

CRUISE KNOWLEDGE:
- Disney Cruise Line: Best for kids 3-12, premium pricing
- Royal Caribbean: Best for teens and activities
- Carnival: Best budget option
- Norwegian: Freestyle cruising, no set dining times
- MSC: Best for European itineraries

THEME PARK KNOWLEDGE:
- Universal Orlando: Better value, thrilling rides, Harry Potter
- Disney World: Better for kids under 10, magical atmosphere
- Epic Universe opens May 22, 2026 with Super Nintendo World

Be conversational. Use emojis occasionally. Keep it fun!"""
        
        # Prepare messages for OpenRouter
        openrouter_messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history (last 8 messages to save tokens)
        for msg in messages[-8:]:
            openrouter_messages.append(msg)
        
        # Check if API key exists
        if not OPENROUTER_API_KEY:
            logger.error("OPENROUTER_API_KEY not found in environment")
            # Fallback response
            if user_message_count <= 1:
                fallback_reply = "Hey there! 👋 I'm Voyager — your family travel deal finder.\n\nFirst up — how many people are in your group, and how old are the kids?"
            elif user_message_count == 2:
                fallback_reply = "What's your overall budget for the trip?"
            elif user_message_count == 3:
                fallback_reply = "When are you planning to visit? (Month or season)"
            elif user_message_count == 4:
                fallback_reply = "What are the must-do experiences or attractions for your family?"
            else:
                fallback_reply = f"Based on {family_info} with {budget_info}, I recommend Universal Orlando Resort. It saves families $1,500+ compared to Disney!"
            
            return jsonify({'reply': fallback_reply})
        
        # Call OpenRouter API
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "openai/gpt-3.5-turbo",  # Cheap but good model
                "messages": openrouter_messages,
                "max_tokens": 250,
                "temperature": 0.8,
            },
            timeout=10
        )
        
        result = response.json()
        
        if "error" in result:
            logger.error(f"OpenRouter error: {result}")
            # Fallback response
            fallback_reply = "Sorry, I'm having a moment. Can you tell me more about what you're looking for?"
            return jsonify({'reply': fallback_reply})
        
        ai_reply = result['choices'][0]['message']['content']
        
        # Determine if we should show a deal card (after 3+ user messages)
        show_deal = user_message_count >= 3
        
        response_data = {
            'reply': ai_reply,
            'showDeal': show_deal
        }
        
        # Add deal card if ready
        if show_deal:
            # Determine which park to recommend based on conversation
            park_recommendation = "Universal Orlando Resort"
            savings_text = "Save ~$1,500 vs Disney packages"
            
            if "disney" in str(messages).lower():
                park_recommendation = "Walt Disney World"
                savings_text = "Magical experiences for younger kids"
            elif "cruise" in str(messages).lower():
                park_recommendation = "Royal Caribbean or Disney Cruise Line"
                savings_text = "Kids sail free promotions available"
            
            response_data['deal'] = {
                'park': park_recommendation,
                'summary': f'Based on {family_info} with {budget_info}, this is the best value for your 2026 vacation.',
                'savings': savings_text,
                'best_deal': 'Book through Voyager for exclusive rates'
            }
        
        return jsonify(response_data)
        
    except requests.exceptions.Timeout:
        logger.error("OpenRouter API timeout")
        return jsonify({'reply': "I'm thinking... Tell me more about your family's travel plans!"})
    except Exception as e:
        logger.error(f"Error in chat: {str(e)}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
