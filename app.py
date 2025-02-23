from flask import Flask, request, Response
import hmac
import hashlib
import json
import requests

app = Flask(__name__)

TELEGRAM_TOKEN = '6954369228:AAGvH6t20CjdWJJVx1Idxf0mRuZpfQuAWl8'
PAYSTACK_SECRET_KEY = 'sk_test_2ab162c82e50d96fa701b593bc72689be1d17456'
TELEGRAM_API_URL = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
ADMIN_USER_ID = 6009484587

def verify_signature(payload, signature):
    secret = PAYSTACK_SECRET_KEY.encode('utf-8')
    computed = hmac.new(secret, payload, hashlib.sha512).hexdigest()
    print(f"Signature verification: Expected={signature}, Computed={computed}")
    return computed == signature

@app.route('/', methods=['GET'])
def home():
    print("Root endpoint accessed")
    return Response("Webhook server is running! Use /webhook for Paystack events.", status=200)

@app.route('/webhook', methods=['POST'])
def webhook():
    print("Webhook endpoint hit")
    signature = request.headers.get('x-paystack-signature')
    if not signature:
        print("Webhook error: Missing signature")
        return Response('Missing signature', status=403)
    
    payload = request.get_data()
    if not verify_signature(payload, signature):
        print("Webhook error: Invalid signature")
        return Response('Invalid signature', status=403)
    
    event = request.get_json()
    print(f"Received webhook event: {json.dumps(event, indent=2)}")
    
    if event['event'] == 'charge.success':
        data = event['data']
        reference = data['reference']
        user_id = int(reference.split('_')[1])
        
        # Notify bot to verify payment
        send_telegram_message(user_id, f"🔗 Verifying payment for reference {reference}", callback_data=f"verify_paymentWebhook_{reference}")
        send_telegram_message(ADMIN_USER_ID, f"📦 Payment event received for user {user_id}, reference {reference}")
    
    return Response('Webhook received', status=200)

def send_telegram_message(chat_id, text, callback_data=None):
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Verify Now ✅", callback_data=callback_data)]]) if callback_data else None
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'Markdown',
        'reply_markup': keyboard.to_dict() if keyboard else None
    }
    response = requests.post(TELEGRAM_API_URL, json=payload)
    print(f"Telegram send response: Chat ID={chat_id}, Status={response.status_code}, Body={response.text}")
    return response.status_code == 200

if __name__ == '__main__':
    print("Starting Flask app...")
    app.run(host='0.0.0.0', port=5000)
