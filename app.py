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

    # List of free models in order of reliability
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

                # Extract recommendation JSON if present
                recommendation = None
                if '"recommendation_ready": true' in reply:
                    try:
                        start = reply.index('{')
                        end = reply.rindex('}') + 1
                        recommendation = json.loads(reply[start:end])
                        # Ensure affiliate_category is set
                        if recommendation.get('recommendation_ready'):
                            if 'affiliate_category' not in recommendation:
                                recommendation['affiliate_category'] = 'universal_tickets'
                    except Exception:
                        pass

                return jsonify({
                    'reply': reply,
                    'recommendation': recommendation
                })
            else:
                last_error = f"Model {model} returned {response.status_code}"
                continue

        except Exception as e:
            last_error = str(e)
            continue

    # If all models fail
    return jsonify({'error': f'All models failed. Last error: {last_error}'}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)