from flask import Flask, request, Response
import hmac
import hashlib
import json
import requests

app = Flask(__name__)

# Telegram and Paystack credentials (will move to env vars later)
TELEGRAM_TOKEN = '6954369228:AAGvH6t20CjdWJJVx1Idxf0mRuZpfQuAWl8'
PAYSTACK_SECRET_KEY = 'sk_test_2ab162c82e50d96fa701b593bc72689be1d17456'
TELEGRAM_API_URL = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
ADMIN_USER_ID = 6009484587

# Verify Paystack webhook signature
def verify_signature(payload, signature):
    secret = PAYSTACK_SECRET_KEY.encode('utf-8')
    computed = hmac.new(secret, payload, hashlib.sha512).hexdigest()
    return computed == signature

@app.route('/webhook', methods=['POST'])
def webhook():
    # Get Paystack signature from header
    signature = request.headers.get('x-paystack-signature')
    if not signature:
        return Response('Missing signature', status=403)
    
    # Verify the request
    payload = request.get_data()
    if not verify_signature(payload, signature):
        return Response('Invalid signature', status=403)
    
    # Parse the event
    event = request.get_json()
    if event['event'] == 'charge.success':
        data = event['data']
        reference = data['reference']
        user_id = int(reference.split('_')[1])  # Extract user_id from reference (e.g., order_<user_id>_<timestamp>)
        amount = data['amount'] / 100  # Convert pesewas to GHS
        
        # Simulate order completion (normally, you'd update your DB here)
        order_msg = f"Payment of ₵{amount} successful!\nOrder #{reference} completed (Status: Pending)"
        send_telegram_message(user_id, order_msg)
        send_telegram_message(ADMIN_USER_ID, f"*New Order from {user_id}:*\n{order_msg}")
    
    return Response('Webhook received', status=200)

def send_telegram_message(chat_id, text):
    payload = {'chat_id': chat_id, 'text': text, 'parse_mode': 'Markdown'}
    requests.post(TELEGRAM_API_URL, json=payload)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
