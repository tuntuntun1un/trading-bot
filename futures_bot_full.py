import ccxt
import json
from flask import Flask, request, jsonify

app = Flask(__name__)

SYMBOL = "XRP/USDT"
USE_TESTNET = True
SECRET = "my_secret_2025"
RISK_PERCENT = 1.0
STOP_LOSS_PERCENT = 1.5

def get_exchange():
    if USE_TESTNET:
        return ccxt.bybit({
            'apiKey': '0NGmuZYb5Bescwkahq',          # твой API Key
            'secret': 'T1P10T4BHCMWppS7GGGdSOVJajNja1iDiIsUO',  # твой Secret
            'enableRateLimit': True,
            'options': {
                'defaultType': 'linear',  # для USDT-фьючерсов
            }
        })
    else:
        return ccxt.bybit({
            'apiKey': 'твой_api_ключ',
            'secret': 'твой_секрет',
            'enableRateLimit': True,
            'options': {
                'defaultType': 'linear',
            }
        })

exchange = get_exchange()

# Принудительно установим режим фьючерсов (линейных)
exchange.load_markets()
exchange.set_sandbox_mode(True)  # для тестнета

def get_position_size(price):
    try:
        balance = exchange.fetch_balance()
        usdt = balance['USDT']['free']
        risk_usdt = usdt * (RISK_PERCENT / 100)
        stop_distance = price * (STOP_LOSS_PERCENT / 100)
        size = risk_usdt / stop_distance
        return round(size, 1)
    except Exception as e:
        print(f"Ошибка расчета размера: {e}")
        return 10.0

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        print(f"📡 Получен сигнал: {data}")
        
        if data.get('secret') != SECRET:
            return jsonify({"error": "Unauthorized"}), 401
        
        signal = data.get('signal')
        price = float(data.get('price', 0))
        
        if signal not in ['buy', 'sell']:
            return jsonify({"error": "Invalid signal"}), 400
        
        amount = get_position_size(price)
        if amount < 1:
            return jsonify({"error": f"Amount {amount} too small"}), 400
        
        print(f"🚀 ОТКРЫТИЕ {signal.upper()} {amount} XRP по {price}")
        
        if signal == 'buy':
            # Открываем длинную позицию (лонг)
            order = exchange.create_market_buy_order(SYMBOL, amount)
            stop_price = round(price * (1 - STOP_LOSS_PERCENT / 100), 4)
            # Устанавливаем стоп-лосс
            exchange.create_order(SYMBOL, 'stop_market', 'sell', amount, None, {'stopPrice': stop_price})
        else:
            # Открываем короткую позицию (шорт)
            order = exchange.create_market_sell_order(SYMBOL, amount)
            stop_price = round(price * (1 + STOP_LOSS_PERCENT / 100), 4)
            exchange.create_order(SYMBOL, 'stop_market', 'buy', amount, None, {'stopPrice': stop_price})
        
        print(f"✅ Сделка исполнена. Стоп: {stop_price}")
        return jsonify({"status": "ok"}), 200
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    print(f"🚀 БОТ ЗАПУЩЕН. Режим: {'ТЕСТНЕТ' if USE_TESTNET else 'РЕАЛ'}")
    app.run(host='0.0.0.0', port=5002)
