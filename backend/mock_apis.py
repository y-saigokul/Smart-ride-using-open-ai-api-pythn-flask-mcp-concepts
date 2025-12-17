from flask import Flask, jsonify, request
from flask_cors import CORS
import random
import time

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend

@app.route('/api/uber/rides')
def uber_rides():
    """Mock Uber API - returns ride options with prices and ETA"""
    from_loc = request.args.get('from', 'Home')
    to_loc = request.args.get('to', 'Office')
    
    # Base prices vary by route
    base_prices = {
        'Home->Office': 16,
        'Office->Home': 19,
        'Home->Airport': 45,
        'Office->Airport': 42
    }
    
    route_key = f"{from_loc}->{to_loc}"
    base_price = base_prices.get(route_key, 20)
    
    # Add some randomness for realistic pricing
    surge_multiplier = random.uniform(1.0, 1.8)
    
    return jsonify({
        'service': 'Uber',
        'rides': [
            {
                'type': 'UberX',
                'price': round(base_price * surge_multiplier, 2),
                'eta': random.randint(13, 32),
                'surge_multiplier': round(surge_multiplier, 1)
            },
            {
                'type': 'UberPool',
                'price': round(base_price * 0.7 * surge_multiplier, 2),
                'eta': random.randint(8, 25),
                'surge_multiplier': round(surge_multiplier, 1)
            }
        ],
        'timestamp': int(time.time())
    })

@app.route('/api/lyft/rides')
def lyft_rides():
    """Mock Lyft API - returns ride options with prices and ETA"""
    from_loc = request.args.get('from', 'Home')
    to_loc = request.args.get('to', 'Office')
    
    # Base prices (slightly different from Uber)
    base_prices = {
        'Home->Office': 14,
        'Office->Home': 17,
        'Home->Airport': 42,
        'Office->Airport': 38
    }
    
    route_key = f"{from_loc}->{to_loc}"
    base_price = base_prices.get(route_key, 18)
    
    # Different surge pattern than Uber
    surge_multiplier = random.uniform(0.9, 1.6)
    
    return jsonify({
        'service': 'Lyft',
        'rides': [
            {
                'type': 'Lyft',
                'price': round(base_price * surge_multiplier, 2),
                'eta': random.randint(15, 30),
                'surge_multiplier': round(surge_multiplier, 1)
            },
            {
                'type': 'Lyft Shared',
                'price': round(base_price * 0.65 * surge_multiplier, 2),
                'eta': random.randint(8, 23),
                'surge_multiplier': round(surge_multiplier, 1)
            }
        ],
        'timestamp': int(time.time())
    })

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': int(time.time()),
        'services': ['uber', 'lyft']
    })

if __name__ == '__main__':
    print("Starting Mock APIs server...")
    print("Uber API: http://localhost:3001/api/uber/rides")
    print("Lyft API: http://localhost:3001/api/lyft/rides")
    app.run(debug=True, port=3001)