from flask import Flask, request, Response
import hmac
import hashlib
import json
import requests
import sqlite3

app = Flask(__name__)

TELEGRAM_TOKEN = '6954369228:AAGvH6t20CjdWJJVx1Idxf0mRuZpfQuAWl8'
PAYSTACK_SECRET_KEY = 'sk_test_2ab162c82e50d96fa701b593bc72689be1d17456'
TELEGRAM_API_URL = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
ADMIN_USER_ID = 6009484587

def verify_signature(payload, signature):
    secret = PAYSTACK_SECRET_KEY.encode('utf-8')
    computed = hmac.new(secret, payload, hashlib.sha512).hexdigest()
    return computed == signature

def checkout(user_id):
    conn = sqlite3.connect('store.db')
    c = conn.cursor()
    c.execute("SELECT product_id, quantity FROM cart WHERE user_id = ?", (user_id,))
    cart_items = c.fetchall()
    if not cart_items:
        conn.close()
        return False
    
    order_id = None
    for product_id, quantity in cart_items:
        c.execute("INSERT INTO orders (user_id, product_id, quantity, status) VALUES (?, ?, ?, ?)",
                  (user_id, product_id, quantity, "Pending"))
        order_id = c.lastrowid
    c.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    return order_id

@app.route('/webhook', methods=['POST'])
def webhook():
    signature = request.headers.get('x-paystack-signature')
    if not signature:
        return Response('Missing signature', status=403)
    
    payload = request.get_data()
    if not verify_signature(payload, signature):
        return Response('Invalid signature', status=403)
    
    event = request.get_json()
    if event['event'] == 'charge.success':
        data = event['data']
        reference = data['reference']
        user_id = int(reference.split('_')[1])
        amount = data['amount'] / 100
        
        # Process the order in the database
        order_id = checkout(user_id)
        if order_id:
            conn = sqlite3.connect('store.db')
            c = conn.cursor()
            c.execute("SELECT p.name, o.quantity, p.price FROM orders o JOIN products p ON o.product_id = p.id WHERE o.id = ?", (order_id,))
            order = c.fetchone()
            conn.close()
            
            if order:
                product_name, quantity, price = order
                receipt = (
                    f"🧾 *Order Receipt*\n"
                    f"Order #{order_id}\n"
                    f"Item: {product_name}\n"
                    f"Quantity: {quantity}\n"
                    f"Unit Price: ₵{price}\n"
                    f"Total: ₵{amount}\n"
                    f"Status: Pending\n"
                    f"🎉 Payment successful!"
                )
                send_telegram_message(user_id, receipt)
                send_telegram_message(ADMIN_USER_ID, f"📦 *New Order from {user_id}:*\n{receipt}")
    
    return Response('Webhook received', status=200)

def send_telegram_message(chat_id, text):
    payload = {'chat_id': chat_id, 'text': text, 'parse_mode': 'Markdown'}
    requests.post(TELEGRAM_API_URL, json=payload)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
