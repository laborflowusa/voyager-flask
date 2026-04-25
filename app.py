from flask import Flask, jsonify, request
from supabase import create_client
import random
import os

app = Flask(__name__, static_folder='public', static_url_path='')

# Hardcoded Supabase credentials
SUPABASE_URL = "https://kwuidjidzeehevigvgwb.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imt3dWlkamlkemVlaGV2aWd2Z3diIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzY3MjMxNzMsImV4cCI6MjA5MjI5OTE3M30.1HRlRYVgc4-Br_T70-SwlVGGluUtLZLi6-9h7SWxpb0"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/privacy.html')
def privacy():
    return app.send_static_file('privacy.html')

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)