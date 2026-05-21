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

# ========== SUPABASE CREDENTIALS ==========
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')

if not SUPABASE_URL:
    logger.error("SUPABASE_URL not found in environment variables!")
if not SUPABASE_KEY:
    logger.error("SUPABASE_KEY not found in environment variables!")

if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    logger.info("Supabase client initialized successfully")
else:
    supabase = None
    logger.error("Supabase client NOT initialized - missing credentials")

# ========== OPENROUTER API KEY ==========
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

# ========== SERVICE STATUS LOGGING ==========
logger.info("=" * 50)
logger.info("VOYAGER API STARTING")
logger.info(f"Supabase URL: {'YES' if SUPABASE_URL else 'NO'}")
logger.info(f"Supabase Key: {'YES' if SUPABASE_KEY else 'NO'}")
logger.info(f"OpenRouter Key: {'YES' if OPENROUTER_API_KEY else 'NO'}")
logger.info("=" * 50)


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
    if not supabase:
        return jsonify({'connected': False, 'error': 'Supabase client not initialized'}), 500
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


# ========== AFFILIATE API ENDPOINTS ==========

@app.route('/api/affiliate/links')
def get_all_affiliate_links():
    if not supabase:
        return jsonify({'error': 'Supabase client not initialized'}), 500
    try:
        response = supabase.table('affiliate_links').select('*').eq('active', True).order('sort_order').execute()
        return jsonify(response.data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/affiliate/links/page/<page_name>')
def get_links_by_page(page_name):
    if not supabase:
        return jsonify({'error': 'Supabase client not initialized'}), 500
    try:
        response = supabase.table('affiliate_links').select('*').eq('page', page_name).eq('active', True).order('sort_order').execute()
        return jsonify(response.data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/affiliate/links/category/<category>')
def get_links_by_category(category):
    if not supabase:
        return jsonify({'error': 'Supabase client not initialized'}), 500
    try:
        response = supabase.table('affiliate_links').select('*').eq('category', category).eq('active', True).order('sort_order').execute()
        return jsonify(response.data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/affiliate/click', methods=['POST'])
def track_affiliate_click():
    if not supabase:
        return jsonify({'error': 'Supabase client not initialized'}), 500
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
    if not supabase:
        return jsonify({'error': 'Supabase client not initialized'}), 500
    try:
        response = supabase.table('affiliate_links').select('*').eq('active', True).limit(6).order('sort_order').execute()
        return jsonify(response.data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ========== LEGACY AFFILIATE ENDPOINTS ==========

@app.route('/api/get_link')
def get_link():
    if not supabase:
        return jsonify({'affiliate_link': 'https://example.com/no-links', 'error': 'Supabase not initialized'}), 500
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
    if not supabase:
        return jsonify({'affiliate_link': 'https://example.com/no-links', 'error': 'Supabase not initialized'}), 500
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
    if not supabase:
        return jsonify({'error': 'Supabase not initialized'}), 500
    try:
        response = supabase.table('affiliate_links').select('*').eq('page', page).eq('active', True).execute()
        return jsonify(response.data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/amazon/<page>')
def get_amazon_links(page):
    if not supabase:
        return jsonify({'error': 'Supabase not initialized'}), 500
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


# ========== AI CHAT ENDPOINT ==========

@app.route('/api/voyager-chat', methods=['POST'])
def voyager_chat():
    try:
        data = request.get_json()
        messages = data.get('messages', [])
        
        if not messages:
            return jsonify({'error': 'No messages provided'}), 400
        
        user_messages = [m for m in messages if m['role'] == 'user']
        user_message_count = len(user_messages)
        
        family_info = "your family"
        budget_info = "a reasonable budget"
        
        for msg in user_messages:
            content = msg['content'].lower()
            if 'budget' in content or '$' in content:
                budget_info = msg['content']
            if 'family' in content or 'kids' in content or 'people' in content:
                family_info = msg['content']
        
        system_prompt = """You are Voyager, a friendly travel assistant. Keep responses short (2-3 sentences). 
        Never ask for email or personal info. Recommend Universal over Disney for budget concerns. 
        Mention Epic Universe opens May 22, 2026."""
        
        openrouter_messages = [{"role": "system", "content": system_prompt}]
        for msg in messages[-8:]:
            openrouter_messages.append(msg)
        
        if not OPENROUTER_API_KEY:
            logger.error("OPENROUTER_API_KEY not found")
            if user_message_count <= 1:
                fallback_reply = "Hey there! How many people in your group and what are their ages?"
            else:
                fallback_reply = f"Based on {family_info} with {budget_info}, I recommend Universal Orlando Resort!"
            return jsonify({'reply': fallback_reply})
        
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "openai/gpt-3.5-turbo",
                "messages": openrouter_messages,
                "max_tokens": 250,
                "temperature": 0.8,
            },
            timeout=10
        )
        
        result = response.json()
        
        if "error" in result:
            logger.error(f"OpenRouter error: {result}")
            return jsonify({'reply': "I'm having a moment. Can you tell me more about what you're looking for?"})
        
        ai_reply = result['choices'][0]['message']['content']
        show_deal = user_message_count >= 3
        
        response_data = {'reply': ai_reply, 'showDeal': show_deal}
        
        if show_deal:
            response_data['deal'] = {
                'park': 'Universal Orlando Resort',
                'summary': f'Based on {family_info} with {budget_info}, this is the best value for 2026.',
                'savings': 'Save ~$1,500 vs Disney packages',
                'best_deal': 'Premier hotels include FREE Express Pass'
            }
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error in chat: {str(e)}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
