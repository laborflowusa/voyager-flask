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


# Get random affiliate link
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


# Get link by category
@app.route('/api/get_link/<category>')
def get_link_by_category(category):
    try:
        response = supabase.table('affiliate_links').select('*').eq('category', category).eq('is_active', True).execute()
        links = response.data
        if not links:
            return jsonify({'affiliate_link': 'https://example.com/no-links', 'error': 'No links found'}), 404
        selected = random.choice(links)
        # Increment click count
        supabase.table('affiliate_links').update({'clicks': selected['clicks'] + 1}).eq('id', selected['id']).execute()
        return jsonify({'affiliate_link': selected['url'], 'name': selected['name'], 'category': category})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Get link by page location (most targeted)
@app.route('/api/get_link/for/<page>')
def get_link_by_page(page):
    try:
        response = supabase.table('affiliate_links').select('*').eq('page_location', page).eq('is_active', True).execute()
        links = response.data
        if not links:
            # Fallback to category-based if no page-specific links
            return get_link_by_category('general')
        selected = random.choice(links)
        supabase.table('affiliate_links').update({'clicks': selected['clicks'] + 1}).eq('id', selected['id']).execute()
        return jsonify({'affiliate_link': selected['url'], 'name': selected['name'], 'page': page})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)