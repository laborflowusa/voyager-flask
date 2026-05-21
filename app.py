from flask import Flask, jsonify, request, send_from_directory
from supabase import create_client
import random
import os
import requests
import time
import logging
import sys

logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='public', static_url_path='')

# Supabase
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
supabase = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

# OpenRouter
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

logger.info("=" * 50)
logger.info("VOYAGER API STARTING")
logger.info(f"Supabase: {'YES' if SUPABASE_URL else 'NO'}")
logger.info(f"OpenRouter: {'YES' if OPENROUTER_API_KEY else 'NO'}")
logger.info("=" * 50)

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/<path:filename>.html')
def serve_html(filename):
    return app.send_static_file(f'{filename}.html')

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

@app.route('/privacy.html')
def privacy():
    return app.send_static_file('privacy.html')

@app.route('/chat.html')
def chat():
    return app.send_static_file('chat.html')

@app.route('/api/test-db')
def test_db():
    if not supabase:
        return jsonify({'connected': False, 'error': 'No Supabase'}), 500
    response = supabase.table('affiliate_links').select('*', count='exact').execute()
    return jsonify({'connected': True, 'count': response.count})

@app.route('/api/test-key')
def test_key():
    return jsonify({'status': 'ok', 'key_prefix': (OPENROUTER_API_KEY or '')[:20] + '...'})

@app.route('/api/affiliate/links')
def get_all_affiliate_links():
    if not supabase:
        return jsonify({'error': 'Supabase not ready'}), 500
    response = supabase.table('affiliate_links').select('*').eq('active', True).order('sort_order').execute()
    return jsonify(response.data)

@app.route('/api/affiliate/links/category/<category>')
def get_links_by_category(category):
    if not supabase:
        return jsonify({'error': 'Supabase not ready'}), 500
    response = supabase.table('affiliate_links').select('*').eq('category', category).eq('active', True).order('sort_order').execute()
    return jsonify(response.data)

@app.route('/api/affiliate/featured')
def get_featured_deals():
    if not supabase:
        return jsonify({'error': 'Supabase not ready'}), 500
    response = supabase.table('affiliate_links').select('*').eq('active', True).limit(6).order('sort_order').execute()
    return jsonify(response.data)

@app.route('/api/affiliate/click', methods=['POST'])
def track_affiliate_click():
    return jsonify({'success': True})

@app.route('/api/voyager-chat', methods=['POST'])
def voyager_chat():
    try:
        data = request.get_json()
        messages = data.get('messages', [])
        user_messages = [m for m in messages if m['role'] == 'user']
        user_message_count = len(user_messages)
        
        if user_message_count == 1:
            reply = "Great! What's your budget for the trip?"
        elif user_message_count == 2:
            reply = "When are you planning to travel?"
        elif user_message_count == 3:
            reply = "What kind of experiences do you want? Thrill rides, shows, or character meet-and-greets?"
        else:
            reply = "Based on your family's needs, I recommend Universal Orlando Resort! It saves families $1,500+ compared to Disney. Epic Universe opens May 22, 2026!"
        
        show_deal = user_message_count >= 3
        response_data = {'reply': reply, 'showDeal': show_deal}
        
        if show_deal:
            response_data['deal'] = {
                'park': 'Universal Orlando Resort',
                'summary': 'Best value for your family in 2026',
                'savings': 'Save ~$1,500 vs Disney',
                'best_deal': 'Free Express Pass with Premier Hotels'
            }
        
        return jsonify(response_data)
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/sitemap.xml')
def sitemap():
    base_url = "https://voyager-flask.onrender.com"
    pages = ["/", "/chat.html", "/universal-vs-disney.html", "/family-cruise-guide-2026.html", "/couples-cruise-guide-2026.html", "/celebrate-mom.html", "/dorney-park.html", "/luxury-safaris.html", "/privacy.html"]
    today = time.strftime('%Y-%m-%d')
    content = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for page in pages:
        content += f'  <url>\n    <loc>{base_url}{page}</loc>\n    <lastmod>{today}</lastmod>\n    <priority>{1.0 if page == "/" else 0.8}</priority>\n  </url>\n'
    content += '</urlset>'
    return app.response_class(content, mimetype='application/xml')

@app.route('/robots.txt')
def robots():
    return app.response_class('User-agent: *\nAllow: /\nSitemap: https://voyager-flask.onrender.com/sitemap.xml\n', mimetype='text/plain')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
