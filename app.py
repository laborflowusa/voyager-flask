from flask import Flask, jsonify, request
from supabase import create_client
import random
import os
import json
import requests

app = Flask(__name__, static_folder='public', static_url_path='')

# Supabase credentials
SUPABASE_URL = "https://kwuidjidzeehevigvgwb.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imt3dWlkamlkemVlaGV2aWd2Z3diIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzY3MjMxNzMsImV4cCI6MjA5MjI5OTE3M30.1HRlRYVgc4-Br_T70-SwlVGGluUtLZLi6-9h7SWxpb0"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# OpenRouter API key from environment variable
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

# Ultra-short system prompt to save tokens
VOYAGER_SYSTEM_PROMPT = """You are Voyager. Ask for: family size, budget, travel month, must-do experiences, park preference.

After 5 answers, output ONLY this JSON, nothing else:
{"recommendation_ready":true,"park":"Universal","summary":"2 sentences","savings":"Save $X","best_deal":"Tip","affiliate_category":"universal_tickets"}

One question at a time. Keep responses very short."""


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/privacy.html')
def privacy():
    return app.send_static_file('privacy.html')

@app.route('/voyager-chat.html')
def voyager_chat_page():
    return app.send_static_file('voyager-chat.html')

@app.route('/blog/<path:filename>')
def serve_blog(filename):
    return app.send_static_file(f'blog/{filename}')

@app.route('/<path:filename>.html')
def serve_html(filename):
    return app.send_static_file(f'{filename}.html')


# ─── API: Random affiliate link from Supabase ─────────────────────────────────

@app.route('/api/get_link')
def get_link():
    user_id = request.args.get('user_id', 'anonymous')
    try:
        response = supabase.table('links').select('*').execute()
        links = response.data
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    if not links:
        return jsonify({'affiliate_link': 'https://example.com/no-links'})
    selected = random.choice(links)
    return jsonify({
        'affiliate_link': selected['url'],
        'link_id': selected['id']
    })


# ─── API: Voyager AI chat (OpenRouter – free) ─────────────────────────────────

@app.route('/api/voyager-chat', methods=['POST'])
def voyager_chat():
    data = request.get_json()
    messages = data.get('messages', [])

    if not messages:
        return jsonify({'error': 'No messages provided'}), 400

    if not OPENROUTER_API_KEY:
        return jsonify({'error': 'OpenRouter API key not configured'}), 500

    models_to_try = [
        "openai/gpt-oss-20b:free",
        "google/gemma-4-31b:free",
        "nvidia/nemotron-3-nano-30b-a3b:free"
    ]

    last_error = None

    for model in models_to_try:
        try:
            response = requests.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": VOYAGER_SYSTEM_PROMPT},
                        *messages
                    ],
                    "max_tokens": 1500,
                    "temperature": 0.7
                },
                timeout=20
            )

            if response.status_code == 200:
                result = response.json()
                reply = result['choices'][0]['message']['content']

                # Improved JSON extraction
                recommendation = None
                try:
                    # Try to find JSON anywhere in the response
                    start = reply.find('{')
                    end = reply.rfind('}') + 1
                    if start != -1 and end > start:
                        json_str = reply[start:end]
                        recommendation = json.loads(json_str)
                        # Validate required fields
                        if recommendation.get('recommendation_ready'):
                            if 'affiliate_category' not in recommendation:
                                recommendation['affiliate_category'] = 'universal_tickets'
                except Exception as e:
                    print(f"JSON parse error: {e}")

                # Clean the reply for display (remove JSON if present)
                display_reply = reply
                if recommendation:
                    # Remove the JSON block from the displayed message
                    json_part = json.dumps(recommendation)
                    display_reply = reply.replace(json_part, '').strip()
                    if not display_reply:
                        display_reply = "Here's your personalized recommendation!"

                return jsonify({
                    'reply': display_reply,
                    'recommendation': recommendation
                })
            else:
                last_error = f"Model {model} returned {response.status_code}"
                continue

        except Exception as e:
            last_error = str(e)
            continue

    return jsonify({'error': f'All models failed. Last error: {last_error}'}), 500