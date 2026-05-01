from flask import Flask, jsonify, request
from supabase import create_client
import random
import os
import json
import requests
import re

app = Flask(__name__, static_folder='public', static_url_path='')

# Supabase credentials
SUPABASE_URL = "https://kwuidjidzeehevigvgwb.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imt3dWlkamlkemVlaGV2aWd2Z3diIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzY3MjMxNzMsImV4cCI6MjA5MjI5OTE3M30.1HRlRYVgc4-Br_T70-SwlVGGluUtLZLi6-9h7SWxpb0"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

# Ultra-short system prompt
VOYAGER_SYSTEM_PROMPT = """You are Voyager. Ask for: family size, budget, travel month, must-do experiences, park preference.

After 5 answers, output ONLY this JSON, nothing else:
{"recommendation_ready":true,"park":"Universal","summary":"2 sentences","savings":"Save $X","best_deal":"Tip","affiliate_category":"universal_tickets"}

One question at a time. Keep responses very short."""


@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/privacy.html')
def privacy():
    return app.send_static_file('privacy.html')

@app.route('/blog/<path:filename>')
def serve_blog(filename):
    return app.send_static_file(f'blog/{filename}')

@app.route('/<path:filename>.html')
def serve_html(filename):
    return app.send_static_file(f'{filename}.html')


@app.route('/api/get_link')
def get_link():
    try:
        response = supabase.table('links').select('*').execute()
        links = response.data
        if not links:
            return jsonify({'affiliate_link': 'https://example.com/no-links'})
        selected = random.choice(links)
        return jsonify({'affiliate_link': selected['url'], 'link_id': selected['id']})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


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
                    # Look for JSON pattern
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