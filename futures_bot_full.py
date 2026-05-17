from flask import Flask, request, jsonify
from pybit.unified_trading import HTTP

app = Flask(__name__)

# ========== НАСТРОЙКИ ==========
SECRET_KEY = "my_secret_2025"
SYMBOL = "XRPUSDT"

# ========== НОВЫЕ API-КЛЮЧИ (С НОВОГО АККАУНТА) ==========
API_KEY = "wsWxEmJdArETIiHtPO"
API_SECRET = "obd6q8YdyCyBw7OLKz2xpmgwS7aJyMNnifi"

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
    print("🚀 БОТ (НОВЫЙ АККАУНТ) ЗАПУЩЕН!")
    app.run(host='0.0.0.0', port=5002)
