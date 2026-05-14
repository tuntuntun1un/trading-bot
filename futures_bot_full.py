import ccxt
import json
from flask import Flask, request, jsonify

app = Flask(__name__)

# ========== НАСТРОЙКИ ==========
SYMBOL = "XRP/USDT"
SECRET = "my_secret_2025"
RISK_PERCENT = 1.0
STOP_LOSS_PERCENT = 1.5

# ========== ТВОИ API-КЛЮЧИ ==========
API_KEY = "0NGmuZYb5Bescwkahq"
API_SECRET = "T1P10T4BHCMWppS7GGGdSOVJajNja1iDiIsUO"

def get_exchange():
    exchange = ccxt.bybit({
        'apiKey': API_KEY,
        'secret': API_SECRET,
        'enableRateLimit': True,
        'options': {
            'defaultType': 'linear',  # USDT-фьючерсы
            'adjustForTimeDifference': True,  # <- КЛЮЧЕВОЙ ПАРАМЕТР ДЛЯ ТЕСТНЕТА
        },
    })
    # Принудительно устанавливаем режим тестовой сети
    exchange.set_sandbox_mode(True)
    return exchange

exchange = get_exchange()

# Принудительная синхронизация времени при запуске
try:
    exchange.load_time_difference()
    print(f"✅ Разница во времени синхронизирована: {exchange.time_difference} мс")
except Exception as e:
    print(f"⚠️ Ошибка синхронизации времени: {e}")

def get_position_size(price):
    try:
        balance = exchange.fetch_balance()
        usdt = balance['USDT']['free']
        risk_usdt = usdt * (RISK_PERCENT / 100)
        stop_distance = price * (STOP_LOSS_PERCENT / 100)
        size = risk_usdt / stop_distance
        return round(size, 1)
    except Exception as e:
        print(f"Ошибка расчета: {e}")
        return 10.0

@app.route('/webhook', methods=['POST'])
def webhook():
    print("🔥 Webhook вызван!")  # Важный маркер в логах
    try:
        data = request.get_json()
        print(f"📡 Данные: {data}")

        if data.get('secret') != SECRET:
            return jsonify({"error": "Unauthorized"}), 401

        signal = data.get('signal')
        price = float(data.get('price', 0))

        if signal not in ['buy', 'sell']:
            return jsonify({"error": "Invalid signal"}), 400

        amount = get_position_size(price)
        if amount < 1:
            return jsonify({"error": "Amount too small"}), 400

        print(f"🚀 Открываем {signal.upper()} {amount} XRP по цене {price}")
        
        if signal == 'buy':
            order = exchange.create_market_buy_order(SYMBOL, amount)
            stop_price = round(price * (1 - STOP_LOSS_PERCENT / 100), 4)
            exchange.create_order(SYMBOL, 'stop_market', 'sell', amount, None, {'stopPrice': stop_price})
        else:
            order = exchange.create_market_sell_order(SYMBOL, amount)
            stop_price = round(price * (1 + STOP_LOSS_PERCENT / 100), 4)
            exchange.create_order(SYMBOL, 'stop_market', 'buy', amount, None, {'stopPrice': stop_price})
        
        print(f"✅ Сделка исполнена! Стоп на {stop_price}")
        return jsonify({"status": "ok"}), 200

    except Exception as e:
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    print("🚀 ТОРГОВЫЙ БОТ (TESTNET) ЗАПУЩЕН!")
    app.run(host='0.0.0.0', port=5002)
