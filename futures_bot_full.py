import requests
import time
import hashlib
import hmac
from flask import Flask, request, jsonify

app = Flask(__name__)

# ========== НАСТРОЙКИ ==========
SECRET_KEY = "my_secret_2025"
SYMBOL = "XRPUSDT"
BASE_URL = "https://api-testnet.bybit.com"

# ========== ТВОЙ НОВЫЙ API-КЛЮЧ ==========
API_KEY = "E5t4L6W2m6xEYnq9oB"
API_SECRET = "tjgXH9VL54blwx2yRIPbAGLnAc6v7ufDq56C"

def bybit_request(endpoint, params):
    """Универсальная функция для подписанных запросов к Bybit Testnet."""
    timestamp = int(time.time() * 1000)
    params['api_key'] = API_KEY
    params['timestamp'] = timestamp
    params['recv_window'] = 5000

    # Сортировка параметров для подписи
    sorted_params = sorted(params.items())
    param_str = '&'.join([f"{k}={v}" for k, v in sorted_params])
    
    # Генерация подписи
    signature = hmac.new(
        bytes(API_SECRET, 'utf-8'),
        bytes(param_str, 'utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    params['sign'] = signature
    response = requests.post(f"{BASE_URL}{endpoint}", data=params)
    return response.json()

@app.route('/webhook', methods=['POST'])
def webhook():
    print("🔥 Webhook вызван!")
    try:
        data = request.get_json()
        print(f"📡 Данные: {data}")

        if data.get('secret') != SECRET_KEY:
            return jsonify({"error": "Unauthorized"}), 401

        signal = data.get('signal')
        price = float(data.get('price', 0))

        if signal not in ['buy', 'sell']:
            return jsonify({"error": "Invalid signal"}), 400

        side = "Buy" if signal == 'buy' else "Sell"
        print(f"🚀 Отправка ордера {side} 10 XRP по цене {price}")
        
        # Параметры ордера
        order_params = {
            'category': 'linear',
            'symbol': SYMBOL,
            'side': side,
            'orderType': 'Market',
            'qty': '10',
            'timeInForce': 'GTC',
        }
        
        result = bybit_request('/v5/order/create', order_params)
        print(f"✅ Ответ Bybit: {result}")

        if result.get('retCode') == 0:
            print(f"✅ Сделка исполнена! Order ID: {result['result']['orderId']}")
            return jsonify({"status": "ok", "orderId": result['result']['orderId']}), 200
        else:
            print(f"❌ Ошибка Bybit: {result}")
            return jsonify({"error": result}), 500

    except Exception as e:
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    print("🚀 ФИНАЛЬНЫЙ БОТ ЗАПУЩЕН!")
    app.run(host='0.0.0.0', port=5002)
