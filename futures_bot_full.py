import requests
import json
import time
import hashlib
import hmac
from flask import Flask, request, jsonify

app = Flask(__name__)

# ========== НАСТРОЙКИ ==========
SECRET_KEY = "my_secret_2025"
SYMBOL = "XRPUSDT"

# ========== ВАШ API-КЛЮЧ (СОЗДАННЫЙ СИСТЕМОЙ) ==========
API_KEY = "bwd7nW3S4L868hLd67"
API_SECRET = "79yRETq6nAo2dEeKptxghAxz7utdCdIYrqUf"

BASE_URL = "https://api-testnet.bybit.com"

def generate_signature(params, secret):
    """Генерация подписи строго по документации Bybit."""
    # 1. Отфильтровать пустые значения и отсортировать по ключу
    filtered_params = {k: v for k, v in params.items() if v is not None and v != ""}
    sorted_params = sorted(filtered_params.items())
    # 2. Объединить в строку "key=value&key2=value2"
    param_str = '&'.join([f"{k}={v}" for k, v in sorted_params])
    # 3. Сгенерировать HMAC-SHA256 подпись
    signature = hmac.new(
        bytes(secret, 'utf-8'),
        bytes(param_str, 'utf-8'),
        hashlib.sha256
    ).hexdigest()
    return signature, param_str

def place_order(side):
    """Отправка ордера на Bybit Testnet."""
    timestamp = int(time.time() * 1000)
    
    # Параметры ордера
    order_params = {
        'category': 'linear',
        'symbol': SYMBOL,
        'side': side,
        'orderType': 'Market',
        'qty': '10',
        'timeInForce': 'GTC',
        'recv_window': 5000  # Цифрой, не строкой!
    }
    
    # Параметры для подписи (добавляем api_key и timestamp)
    sign_params = {
        'api_key': API_KEY,
        'timestamp': timestamp,  # Цифрой, не строкой!
        **order_params
    }
    
    # Генерация подписи и получение строки для отладки
    sign, param_str = generate_signature(sign_params, API_SECRET)
    print(f"DEBUG param_str: {param_str}")
    print(f"DEBUG sign: {sign}")
    
    # Подготовка данных для отправки
    sign_params['sign'] = sign
    
    # Отправка запроса
    response = requests.post(f"{BASE_URL}/v5/order/create", data=sign_params)
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
        
        result = place_order(side)
        print(f"✅ Ответ Bybit: {result}")

        if result.get('retCode') == 0:
            return jsonify({"status": "ok", "orderId": result['result']['orderId']}), 200
        else:
            return jsonify({"error": result}), 500

    except Exception as e:
        print(f"❌ ОШИБКА: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    print("🚀 БОТ (FINAL) ЗАПУЩЕН!")
    app.run(host='0.0.0.0', port=5002)
