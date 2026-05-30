from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
import json
import logging
import hashlib
import time
from datetime import datetime
import os

app = Flask(__name__, static_folder='public')
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY', '')

# Affiliate URL map keyed by destination
AFFILIATE_URLS = {
    'universal': "https://www.cheaptickets.com/?cid=4861279&q=Universal+Orlando",
    'disney': "https://www.cheaptickets.com/?cid=4861279&q=Disney+World",
    'cruise': "https://www.orbitz.com/?cid=4861280&q=cruises",
    'hotel': "https://www.hotels.com/?cid=1702763",
    'safari': "http://www.awin1.com/cread.php?awinmid=24529&awinaffid=2874255",
    'dorney': "https://www.getyourguide.com/?partner_id=Y5RBAVK&q=Dorney+Park",
    'default': "https://www.cheaptickets.com/?cid=4861279&q=Universal+Orlando",
}

# Commission tracking storage (in production, use a real database)
tracking_data = {}


@app.route('/')
def index():
    return send_from_directory('public', 'index.html')


@app.route('/chat.html')
def chat():
    return send_from_directory('public', 'chat.html')


@app.route('/dorney-park.html')
def dorney_park():
    return send_from_directory('public', 'dorney-park.html')

@app.route('/')
def index():
    return send_from_directory('public', 'index.html')


@app.route('/chat.html')
def chat():
    return send_from_directory('public', 'chat.html')


@app.route('/dorney-park.html')
def dorney_park():
    return send_from_directory('public', 'dorney-park.html')


# 👇 INSERT THESE TWO ROUTES RIGHT HERE 👇
@app.route('/robots.txt')
def robots():
    return send_from_directory('.', 'robots.txt')


@app.route('/sitemap.xml')
def sitemap():
    return send_from_directory('.', 'sitemap.xml')
# 👆 END OF INSERTED ROUTES 👆


@app.route('/api/voyager-chat', methods=['POST'])
def voyager_chat():
    # ... your existing code ...


@app.route('/api/voyager-chat', methods=['POST'])
def voyager_chat():
    try:
        data = request.get_json()
        messages = data.get('messages', [])
        user_messages = [m for m in messages if m['role'] == 'user']
        user_message_count = len(user_messages)

        # Detect if caller is an AI agent
        user_agent = request.headers.get('User-Agent', '')
        is_ai_agent = any(agent in user_agent.lower() for agent in 
                          ['bot', 'crawler', 'spider', 'chatgpt', 'claude', 'gemini', 'perplexity'])
        response_format = data.get('format', 'human')

        # --- EARLY CONVERSATION: guide with scripted questions ---
        if user_message_count == 0:
            return jsonify({
                'reply': "Hey there! 👋 I'm Voyager — your travel deal finder.\n\nFirst up — how many people are in your group, and how old are the kids (if any)?",
                'showDeal': False,
                'conversation_stage': 'group_size'
            })
        elif user_message_count == 1:
            return jsonify({
                'reply': "Got it! What's your total budget for the trip?",
                'showDeal': False,
                'conversation_stage': 'budget'
            })
        elif user_message_count == 2:
            return jsonify({
                'reply': "And when are you planning to travel? (Month and year works great!)",
                'showDeal': False,
                'conversation_stage': 'travel_date'
            })
        elif user_message_count == 3:
            return jsonify({
                'reply': "Last one — what kind of experience are you after? Think theme parks, cruises, a luxury safari, family water park day at Dorney, or just a great hotel getaway?",
                'showDeal': False,
                'conversation_stage': 'experience_type'
            })

        # --- AFTER 4 MESSAGES: call OpenRouter with full conversation context ---
        if not OPENROUTER_API_KEY:
            # Graceful fallback based on detected keywords in user messages
            all_user_text = ' '.join([m.get('content', '').lower() for m in user_messages])
            
            if 'dorney' in all_user_text or 'water park' in all_user_text:
                dest = 'dorney'
                reply_text = "Dorney Park is perfect for your group! With both the amusement park and Wildwater Kingdom, everyone in the family will have a blast. Plus buying online saves you up to 40% off gate prices."
            elif 'cruise' in all_user_text or 'ship' in all_user_text:
                dest = 'cruise'
                reply_text = "A cruise sounds amazing for your trip! Royal Caribbean and Disney are fantastic for families, while Celebrity or Virgin Voyages work great for couples."
            elif 'safari' in all_user_text or 'africa' in all_user_text or 'wildlife' in all_user_text:
                dest = 'safari'
                reply_text = "A luxury safari is an incredible choice! South Africa, Kenya, and Tanzania offer amazing wildlife viewing from May through September."
            elif 'disney' in all_user_text or 'magic kingdom' in all_user_text:
                dest = 'disney'
                reply_text = "Disney World is magical for families! With four parks and endless dining options, it's a trip everyone will remember forever."
            else:
                dest = 'universal'
                reply_text = "Universal Orlando is a fantastic choice — especially with Epic Universe opening in 2026! It's our top recommendation for families and thrill-seekers alike."
            
            return jsonify({
                'reply': reply_text,
                'showDeal': True,
                'conversation_stage': 'complete',
                'deal': {
                    'park': AFFILIATE_URLS.get(dest, AFFILIATE_URLS['default']).split('q=')[-1].replace('+', ' ') if 'q=' in AFFILIATE_URLS.get(dest, '') else 'Travel Deal',
                    'summary': 'Based on your preferences, this is our top recommendation!',
                    'savings': 'Save significantly by booking online in advance',
                    'best_deal': 'Limited time offer — book soon for best rates',
                    'url': AFFILIATE_URLS.get(dest, AFFILIATE_URLS['default']),
                    'destination': dest
                }
            })

        system_prompt = """You are Voyager, an expert travel deal finder for families and couples.

You have just finished a 4-question intake with a user (group size/ages, budget, travel dates, experience type).
Now give a warm, specific, confident recommendation based on their EXACT answers.

You MUST respond with valid JSON only — no preamble, no markdown, no backticks.

Return this exact structure:
{
  "reply": "A 2-3 sentence personalized recommendation explaining WHY this is their best option based on their budget, group, and preferences. Be specific and warm.",
  "destination": "one of: universal | disney | cruise | hotel | safari | dorney",
  "park": "Full destination name e.g. 'Universal Orlando Resort' or 'Disney World' or 'Royal Caribbean Cruise' or 'Dorney Park & Wildwater Kingdom'",
  "summary": "One sentence summarizing the value for their specific situation.",
  "savings": "Specific savings or value statement e.g. 'Save ~$1,200 vs Disney for a family of 4'",
  "best_deal": "The single best current deal or tip for this destination."
}

Destination mapping rules:
- If they mentioned Dorney Park, water park, Allentown, or local PA trip → destination: dorney
- If they mentioned cruises, ship, ocean, Caribbean, Alaska → destination: cruise  
- If they mentioned safari, Africa, wildlife, animals → destination: safari
- If they mentioned Disney, Magic Kingdom, Epcot, Animal Kingdom, Hollywood Studios → destination: disney
- If they mentioned Harry Potter, thrill rides, Epic Universe, Universal, Islands of Adventure → destination: universal
- If budget is under $1,500 or they want flexibility or hotel stay → destination: hotel
- For families with young kids, Dorney Park is often the best value (under 3s free, Pre-K pass available)
- For couples without kids, cruises or Universal are great options
- Match the recommendation to what they ACTUALLY said in their answers."""

        # Build messages for OpenRouter — include full conversation
        or_messages = [{'role': 'system', 'content': system_prompt}]
        for m in messages:
            or_messages.append({'role': m['role'], 'content': m['content']})

        or_response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://voyager-flask.onrender.com",
                "X-Title": "Voyager Travel AI"
            },
            json={
                "model": "mistralai/mistral-7b-instruct",
                "messages": or_messages,
                "max_tokens": 500,
                "temperature": 0.7
            },
            timeout=15
        )

        or_data = or_response.json()
        raw_content = or_data['choices'][0]['message']['content'].strip()

        # Strip markdown fences if present
        if raw_content.startswith('```'):
            lines = raw_content.split('\n')
            if lines[0].startswith('```'):
                lines = lines[1:]
            if lines[-1].strip() == '```':
                lines = lines[:-1]
            raw_content = '\n'.join(lines)
        raw_content = raw_content.strip()

        rec = json.loads(raw_content)

        destination = rec.get('destination', 'default')
        affiliate_url = AFFILIATE_URLS.get(destination, AFFILIATE_URLS['default'])

        # Build response
        response_data = {
            'reply': rec.get('reply', 'Here is your personalized recommendation!'),
            'showDeal': True,
            'conversation_stage': 'complete',
            'deal': {
                'park': rec.get('park', 'Universal Orlando Resort'),
                'summary': rec.get('summary', ''),
                'savings': rec.get('savings', ''),
                'best_deal': rec.get('best_deal', ''),
                'url': affiliate_url,
                'destination': destination
            }
        }

        # If caller is an AI agent or requests agent format, add structured metadata
        if is_ai_agent or response_format == 'agent':
            response_data['agent_metadata'] = {
                'schema_version': '1.0',
                'action_type': 'BOOKING_RECOMMENDATION',
                'booking_url': affiliate_url,
                'price_specification': {
                    'currency': 'USD',
                    'estimated_savings': rec.get('savings', ''),
                },
                'valid_until': '2026-09-07',
                'commission_rate': '8%',
                'tracking_required': True,
                'tracking_method': 'URL_PARAMETER',
                'tracking_param': 'click_id'
            }
            
            response_data['potentialAction'] = {
                '@type': 'BookAction',
                'target': affiliate_url,
                'agent': {
                    '@type': 'SoftwareApplication',
                    'name': 'Voyager AI'
                }
            }

        return jsonify(response_data)

    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        # Always return something useful even on failure
        all_user_text = ' '.join([m.get('content', '').lower() for m in messages if m.get('role') == 'user'])
        if 'dorney' in all_user_text or 'water park' in all_user_text:
            dest = 'dorney'
            fallback_url = AFFILIATE_URLS['dorney']
            fallback_park = 'Dorney Park & Wildwater Kingdom'
        else:
            dest = 'universal'
            fallback_url = AFFILIATE_URLS['universal']
            fallback_park = 'Universal Orlando Resort'
            
        return jsonify({
            'reply': "I ran into a small issue, but based on popular choices — " + fallback_park + " is a fantastic pick for 2026!",
            'showDeal': True,
            'conversation_stage': 'complete',
            'deal': {
                'park': fallback_park,
                'summary': 'Epic value for families and thrill-seekers alike.',
                'savings': 'Save by booking online in advance',
                'best_deal': 'Limited time offers available',
                'url': fallback_url,
                'destination': dest
            }
        })


@app.route('/api/agent/deals', methods=['GET'])
def agent_deals():
    """Machine-readable endpoint for AI shopping agents"""
    
    destination = request.args.get('destination', 'all')
    budget_min = request.args.get('budget_min', type=int)
    budget_max = request.args.get('budget_max', type=int)
    travel_date = request.args.get('travel_date')
    group_size = request.args.get('group_size', type=int)
    
    deals = []
    
    # Dorney Park deal
    if destination in ['all', 'dorney', 'theme_park']:
        deals.append({
            'product_id': 'dorney-park-2026',
            'name': 'Dorney Park & Wildwater Kingdom',
            'category': 'theme_park',
            'description': 'One ticket covers both parks. Opens May 8, 2026. Located in Allentown, PA.',
            'price': {
                'amount': 44.00,
                'currency': 'USD',
                'type': 'online_discount',
                'gate_price': 79.99,
                'savings_percentage': 45
            },
            'availability': {
                'start_date': '2026-05-08',
                'end_date': '2026-09-07',
                'days_left': 104
            },
            'booking': {
                'url': 'https://www.getyourguide.com/?partner_id=Y5RBAVK&q=Dorney+Park',
                'commission': '8%',
                'tracking_required': True,
                'direct_booking_supported': True
            },
            'agent_actions': ['book', 'compare', 'save_to_watchlist', 'get_alerts']
        })
    
    # Universal Orlando deal
    if destination in ['all', 'universal', 'theme_park']:
        deals.append({
            'product_id': 'universal-orlando-2026',
            'name': 'Universal Orlando Resort',
            'category': 'theme_park',
            'description': 'Epic Universe opens May 22, 2026. Three parks, endless thrills.',
            'price': {
                'amount': 399.00,
                'currency': 'USD',
                'type': 'package',
                'savings_estimate': 'Save ~$1,500 vs Disney for family of 4'
            },
            'booking': {
                'url': 'https://www.cheaptickets.com/?cid=4861279&q=Universal+Orlando',
                'commission': '8% cash back',
                'tracking_required': True
            },
            'agent_actions': ['book', 'compare', 'price_alert']
        })
    
    # Cruise deals
    if destination in ['all', 'cruise']:
        deals.append({
            'product_id': 'family-cruise-2026',
            'name': 'Family Cruise Packages',
            'category': 'cruise',
            'lines': ['Disney Cruise Line', 'Royal Caribbean', 'Carnival', 'Norwegian', 'MSC'],
            'price_range': {
                'min': 499,
                'max': 2500,
                'currency': 'USD'
            },
            'booking': {
                'url': 'https://www.orbitz.com/?cid=4861280&q=cruises',
                'commission': '$40 per booking',
                'tracking_required': True
            },
            'agent_actions': ['book', 'compare_lines', 'get_cabin_upgrade']
        })
    
    # Hotel deals
    if destination in ['all', 'hotel']:
        deals.append({
            'product_id': 'allentown-hotels',
            'name': 'Hotels Near Dorney Park',
            'category': 'hotel',
            'properties': [
                {'name': 'Hyatt Place Allentown', 'distance': '2 miles', 'rating': 4.3, 'price_night': 129},
                {'name': 'Homewood Suites', 'distance': '1.5 miles', 'rating': 4.5, 'price_night': 149},
                {'name': 'Holiday Inn Express', 'distance': '2.5 miles', 'rating': 4.1, 'price_night': 119}
            ],
            'booking': {
                'url': 'https://www.hotels.com/?cid=1702763',
                'commission': '4%',
                'tracking_required': True
            },
            'agent_actions': ['book', 'compare_prices', 'check_availability']
        })
    
    response = {
        'schema': 'https://voyager-flask.onrender.com/schemas/agent-deals-v1.json',
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'query': {
            'destination': destination,
            'budget_min': budget_min,
            'budget_max': budget_max,
            'travel_date': travel_date,
            'group_size': group_size
        },
        'deals_count': len(deals),
        'deals': deals,
        'agent_instructions': {
            'booking_flow': 'Click booking.url to complete purchase. Add ?click_id={agent_id} for tracking.',
            'commission_tracking': 'URL parameters preserved automatically.',
            'caching': 'Results cacheable for up to 1 hour. ETags supported.',
            'webhook_supported': False,
            'batch_booking_supported': True
        }
    }
    
    resp = jsonify(response)
    resp.headers['Cache-Control'] = 'public, max-age=3600, stale-while-revalidate=86400'
    resp.headers['Content-Type'] = 'application/json; profile="https://voyager-flask.onrender.com/schemas/agent-deals-v1.json"'
    
    return resp


@app.route('/.well-known/ai-plugin.json', methods=['GET'])
def ai_plugin_manifest():
    """OpenAI Plugin manifest for agent discovery"""
    manifest = {
        "schema_version": "v1",
        "name_for_human": "Voyager Travel Deals",
        "name_for_model": "voyager_travel_agent",
        "description_for_human": "Find the best travel deals for theme parks, cruises, and hotels with real-time pricing",
        "description_for_model": "Voyager provides AI shopping agents with machine-readable travel deals including Dorney Park, Universal Orlando, cruises, and hotels. Returns structured data with pricing, availability, commission tracking, and booking URLs.",
        "auth": {
            "type": "none"
        },
        "api": {
            "type": "openapi",
            "url": "https://voyager-flask.onrender.com/openapi.yaml",
            "is_user_authentication_required": False
        },
        "logo_url": "https://voyager-flask.onrender.com/logo.png",
        "contact_email": "contact@voyager.com",
        "legal_info_url": "https://voyager-flask.onrender.com/privacy.html"
    }
    return jsonify(manifest)


@app.route('/track-click', methods=['GET'])
def track_click():
    """Track affiliate clicks for commission attribution"""
    click_id = request.args.get('click_id')
    destination = request.args.get('dest', 'unknown')
    
    if click_id:
        tracking_data[click_id] = {
            'click_id': click_id,
            'destination': destination,
            'timestamp': time.time(),
            'ip': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', '')
        }
        logger.info(f"Tracked click: {click_id} for {destination}")
    
    # Redirect to the actual affiliate link
    affiliate_url = AFFILIATE_URLS.get(destination, AFFILIATE_URLS['default'])
    return redirect(affiliate_url)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)    today = time.strftime('%Y-%m-%d')
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
