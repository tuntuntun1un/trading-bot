import requests
import json
import time
import hashlib
import hmac
from flask import Flask, request, jsonify

app = Flask(__name__)

# ========== НАСТРОЙКИ ==========
SECRET = "my_secret_2025"
RISK_PERCENT = 1.0
STOP_LOSS_PERCENT = 1.5

# ========== API-КЛЮЧИ ДЛЯ ТЕСТНЕТА ==========
API_KEY = "0NGmuZYb5Bescwkahq"
API_SECRET = "T1P10T4BHCMWppS7GGGdSOVJajNja1iDiIsUO"

# Базовый URL для тестовой сети Bybit
BASE_URL = "https://api-testnet.bybit.com"

# Параметры торговли
SYMBOL = "XRPUSDT"  # Без слеша для API Bybit
SIDE = "Buy"        # Buy или Sell
ORDER_TYPE = "Market"

def generate_signature(params, secret):
    """Генерация подписи для Bybit"""
    param_str = '&'.join([f"{k}={v}" for k, v in sorted(params.items())])
    signature = hmac.new(bytes(secret, 'utf-8'), bytes(param_str, 'utf-8'), hashlib.sha256).hexdigest()
    return signature

def get_position_size():
    """Получение размера позиции (фиксированный для теста)"""
    return 10  # 10 XRP для теста

@app.route('/webhook', methods=['POST'])
def webhook():
    print("🔥 Webhook вызван!")
    try:
        data = request.get_json()
        print(f"📡 Данные: {data}")

        if data.get('secret') != SECRET:
            return jsonify({"error": "Unauthorized"}), 401

        signal = data.get('signal')
        price = float(data.get('price', 0))

        if signal not in ['buy', 'sell']:
            return jsonify({"error": "Invalid signal"}), 400

        # Определяем сторону сделки
        side = "Buy" if signal == 'buy' else "Sell"
        
        amount = get_position_size()
        print(f"🚀 Открываем {side} {amount} XRP по цене {price}")

        # --- Формируем запрос к Bybit ---
        timestamp = int(time.time() * 1000)
        params = {
            'category': 'linear',
            'symbol': SYMBOL,
            'side': side,
            'orderType': 'Market',
            'qty': str(amount),
            'timeInForce': 'GTC',
            'timestamp': timestamp,
            'api_key': API_KEY,
        }

        # Добавляем подпись
        params['sign'] = generate_signature(params, API_SECRET)

        # Отправляем запрос
        response = requests.post(f"{BASE_URL}/v5/order/create", data=params)
        result = response.json()

        print(f"Ответ Bybit: {result}")

        if result.get('retCode') == 0:
            print(f"✅ Сделка исполнена! Order ID: {result['result']['orderId']}")
            
            # Устанавливаем стоп-лосс
            stop_price = round(price * (1 - STOP_LOSS_PERCENT / 100), 4) if signal == 'buy' else round(price * (1 + STOP_LOSS_PERCENT / 100), 4)
            stop_params = {
                'category': 'linear',
                'symbol': SYMBOL,
                'side': 'Sell' if signal == 'buy' else 'Buy',
                'orderType': 'Market',
                'qty': str(amount),
                'stopPx': str(stop_price),
                'timestamp': int(time.time() * 1000),
                'api_key': API_KEY,
            }
            stop_params['sign'] = generate_signature(stop_params, API_SECRET)
            stop_response = requests.post(f"{BASE_URL}/v5/order/create", data=stop_params)
            print(f"Стоп-лосс: {stop_response.json()}")
            
            return jsonify({"status": "ok"}), 200
        else:
            print(f"❌ Ошибка Bybit: {result}")
            return jsonify({"error": result}), 500

    except Exception as e:
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    print("🚀 ТОРГОВЫЙ БОТ (ПРЯМОЙ API) ЗАПУЩЕН!")
    app.run(host='0.0.0.0', port=5002)
