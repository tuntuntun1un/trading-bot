from flask import Flask, request, jsonify
from pybit.unified_trading import HTTP
import os

app = Flask(__name__)

# ========== НАСТРОЙКИ ==========
SECRET_KEY = "my_secret_2025"
SYMBOL = "XRPUSDT"

# ========== ТВОЙ API-КЛЮЧ ==========
API_KEY = "E5t4L6W2m6xEYnq9oB"
API_SECRET = "tjgXH9VL54blwx2yRIPbAGLnAc6v7ufDq56C"

# Подключение к тестовой сети Bybit
session = HTTP(
    testnet=True,
    api_key=API_KEY,
    api_secret=API_SECRET,
)

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
        qty = "10"

        print(f"🚀 Отправка ордера {side} {qty} XRP по цене {price}")

        # Отправка рыночного ордера через pybit
        order = session.place_order(
            category="linear",
            symbol=SYMBOL,
            side=side,
            orderType="Market",
            qty=qty,
            timeInForce="GTC"
        )

        print(f"✅ Ответ Bybit: {order}")

        if order.get('retCode') == 0:
            print(f"✅ Сделка исполнена! Order ID: {order['result']['orderId']}")
            return jsonify({"status": "ok", "orderId": order['result']['orderId']}), 200
        else:
            print(f"❌ Ошибка Bybit: {order}")
            return jsonify({"error": order}), 500

    except Exception as e:
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    print("🚀 БОТ (PYBIT) ЗАПУЩЕН!")
    app.run(host='0.0.0.0', port=5002)
