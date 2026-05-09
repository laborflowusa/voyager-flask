from flask import Flask, jsonify, request, send_from_directory
from supabase import create_client
import random
import os
import json
import requests
import re
import time

app = Flask(__name__, static_folder='public', static_url_path='')

# Supabase credentials
SUPABASE_URL = "https://kwuidjidzeehevigvgwb.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imt3dWlkamlkemVlaGV2aWd2Z3diIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzY3MjMxNzMsImV4cCI6MjA5MjI5OTE3M30.1HRlRYVgc4-Br_T70-SwlVGGluUtLZLi6-9h7SWxpb0"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# OpenRouter API key from environment variable
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

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
    """Serve static files (images, CSS, etc.) from the static folder"""
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


# Updated Sitemap route
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


# Robots.txt route
@app.route('/robots.txt')
def robots():
    robots_content = 'User-agent: *\n'
    robots_content += 'Allow: /\n'
    robots_content += 'Sitemap: https://voyager-flask.onrender.com/sitemap.xml\n'
    return app.response_class(robots_content, mimetype='text/plain')


# ========== AFFILIATE LINK API ENDPOINTS ==========

# Get random affiliate link (original)
@app.route('/api/get_link')
def get_link():
    try:
        response = supabase.table('affiliate_links').select('*').eq('is_active', True).execute()
        links = response.data
        if not links:
            return jsonify({'affiliate_link': 'https://example.com/no-links'})
        selected = random.choice(links)
        # Increment click count
        supabase.table('affiliate_links').update({'clicks': selected['clicks'] + 1}).eq('id', selected['id']).execute()
        return jsonify({'affiliate_link': selected['url'], 'name': selected['name']})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Get link by category (e.g., /api/get_link/amazon)
@app.route('/api/get_link/<category>')
def get_link_by_category(category):
    try:
        response = supabase.table('affiliate_links').select('*').eq('category', category).eq('is_active', True).execute()
        links = response.data
        if not links:
            return jsonify({'affiliate_link': 'https://example.com/no-links', 'error': 'No links found'}), 404
        selected = random.choice(links)
        supabase.table('affiliate_links').update({'clicks': selected['clicks'] + 1}).eq('id', selected['id']).execute()
        return jsonify({'affiliate_link': selected['url'], 'name': selected['name'], 'category': category})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Get all links for a specific page (e.g., /api/links/family-cruise)
@app.route('/api/links/<page>')
def get_links_for_page(page):
    try:
        response = supabase.table('affiliate_links').select('*').eq('page_location', page).eq('is_active', True).execute()
        links = response.data
        return jsonify(links)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Get Amazon links for a specific page
@app.route('/api/amazon/<page>')
def get_amazon_links(page):
    try:
        response = supabase.table('affiliate_links').select('*').eq('category', 'amazon').eq('page_location', page).eq('is_active', True).execute()
        links = response.data
        return jsonify(links)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Track click on a specific link
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


# ========== AI CHAT ENDPOINT ==========

@app.route('/api/voyager-chat', methods=['POST'])
def voyager_chat():
    try:
        data = request.get_json()
        messages = data.get('messages', [])

        if not messages:
            return jsonify({'error': 'No messages provided'}), 400

        if not OPENROUTER_API_KEY:
            return jsonify({'error': 'OpenRouter API key not configured'}), 500

        models = ["openai/gpt-oss-20b:free", "google/gemma-4-31b:free"]

        for model in models:
            try:
                resp = requests.post(
                    url="https://openrouter.ai/api/v1/chat/completions",
                    headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"},
                    json={
                        "model": model,
                        "messages": [{"role": "system", "content": VOYAGER_SYSTEM_PROMPT}] + messages,
                        "max_tokens": 1000,
                        "temperature": 0.7
                    },
                    timeout=15
                )

                if resp.status_code == 200:
                    result = resp.json()
                    reply = result['choices'][0]['message']['content']
                    
                    # Try to extract JSON
                    recommendation = None
                    json_match = re.search(r'\{[^{}]*"recommendation_ready"[^{}]*\}', reply)
                    if json_match:
                        try:
                            recommendation = json.loads(json_match.group())
                        except:
                            pass
                    
                    # Clean reply: remove the JSON part
                    clean_reply = reply
                    if json_match:
                        clean_reply = reply.replace(json_match.group(), '').strip()
                        if not clean_reply:
                            clean_reply = "Here's your personalized recommendation!"
                    
                    return jsonify({'reply': clean_reply, 'recommendation': recommendation})
            except:
                continue

        return jsonify({'error': 'All models failed'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)