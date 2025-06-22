from flask import Flask, request, jsonify, render_template
import requests
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv
import os
import json
import redis

load_dotenv()
APIKEY = os.getenv('API')
url = os.getenv('API_URL')
redis_uri = os.getenv('REDIS_URI')

if not APIKEY or not url or not redis_uri:
    raise RuntimeError("Missing environment variables. Check your .env file.")

r = redis.Redis.from_url(redis_uri)

app = Flask(__name__)
limiter = Limiter(get_remote_address, app=app, default_limits=["5 per day", "1 per hour"], storage_uri=redis_uri, strategy="fixed-window",)

@app.route('/weather', methods=['POST'])
@limiter.limit("5 per minute")
def weather():
    location = request.form.get('location')

    if not location:
        return jsonify({"error": "No location provided"}), 400

    if r.exists(location):
        try:
            data = json.loads(r.get(location).decode())
            return jsonify(data)
        except Exception:
            return jsonify({"error": "Failed to parse cached data"}), 500
    
    req = requests.get(f'{url}/{location}?key={APIKEY}')

    if req.status_code != 200:
        return jsonify({"error": "Failed to get weather data"}), req.status_code
    
    try:
        data = req.json()
    except (KeyError, ValueError):
        return jsonify({"error": "Unexpected response format"}), 500


    r.set(location, json.dumps(data), ex=3600)

    return jsonify(data)

app.run(port=5500)