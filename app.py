from flask import Flask, jsonify, request
from supabase import create_client
import random
import os

app = Flask(__name__, static_folder='public', static_url_path='')

# Supabase configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://kwuidjidzeehevigvgwb.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
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
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))