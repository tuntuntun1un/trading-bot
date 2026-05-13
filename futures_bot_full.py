import ccxt
import json
import threading
import time
from datetime import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)

SYMBOL = "XRP/USDT"
USE_TESTNET = True

RISK_PERCENT = 1.0
STOP_LOSS_PERCENT = 1.5
TRAILING_ACTIVATE_PERCENT = 2.0
TRAILING_DISTANCE_PERCENT = 0.8
PARTIAL_CLOSE_LEVEL_1 = 3.0
PARTIAL_CLOSE_PERCENT_1 = 30
PARTIAL_CLOSE_LEVEL_2 = 5.0
PARTIAL_CLOSE_PERCENT_2 = 30

SECRET = "my_secret_2025"

def get_exchange():
    if USE_TESTNET:
        return ccxt.bybit({
            'apiKey': 'твой_тестнет_api_ключ',
            'secret': 'твой_тестнет_секрет',
            'enableRateLimit': True,
            'options': {'defaultType': 'future', 'leverage': 1},
            'urls': {
                'api': {
                    'public': 'https://api-testnet.bybit.com',
                    'private': 'https://api-testnet.bybit.com',
                }
            }
        })
    else:
        return ccxt.bybit({
            'apiKey': 'твой_api_ключ',
            'secret': 'твой_секрет',
            'enableRateLimit': True,
            'options': {'defaultType': 'future', 'leverage': 1}
        })

exchange = get_exchange()

active_trade = {
    'side': None,
    'entry_price': 0,
    'amount': 0,
    'remaining_amount': 0,
    'best_price': 0,
    'trailing_active': False,
    'partial_closed_1': False,
    'partial_closed_2': False,
    'stop_order_id': None
}

def get_position_size(price):
    try:
        balance = exchange.fetch_balance()
        usdt = balance['USDT']['free']
        risk_usdt = usdt * (RISK_PERCENT / 100)
        stop_distance = price * (STOP_LOSS_PERCENT / 100)
        size = risk_usdt / stop_distance
        return round(size, 1)
    except:
        return 10.0

def close_partial(percent, reason):
    if active_trade['remaining_amount'] <= 0:
        return
    amount = round(active_trade['remaining_amount'] * (percent / 100), 1)
    if amount < 1:
        return
    if active_trade['side'] == 'long':
        exchange.create_market_sell_order(SYMBOL, amount)
    else:
        exchange.create_market_buy_order(SYMBOL, amount)
    active_trade['remaining_amount'] -= amount
    print(f"💰 {reason}: закрыто {amount} XRP. Осталось {active_trade['remaining_amount']}")

def update_stop_loss(new_stop):
    if active_trade['stop_order_id']:
        try:
            exchange.cancel_order(active_trade['stop_order_id'], SYMBOL)
        except:
            pass
    if active_trade['side'] == 'long':
        order = exchange.create_order(SYMBOL, 'stop_market', 'sell', active_trade['remaining_amount'], None, {'stopPrice': round(new_stop, 4)})
    else:
        order = exchange.create_order(SYMBOL, 'stop_market', 'buy', active_trade['remaining_amount'], None, {'stopPrice': round(new_stop, 4)})
    active_trade['stop_order_id'] = order['id']

def get_current_stop():
    try:
        orders = exchange.fetch_open_orders(SYMBOL)
        for order in orders:
            if order['side'] == ('sell' if active_trade['side'] == 'long' else 'buy') and order['type'] == 'stop_market':
                return order['stopPrice']
        return 0
    except:
        return 0

def trailing_loop():
    while True:
        try:
            if active_trade['side'] is not None and active_trade['remaining_amount'] > 0:
                ticker = exchange.fetch_ticker(SYMBOL)
                price = ticker['last']
                if active_trade['side'] == 'long':
                    profit = (price - active_trade['entry_price']) / active_trade['entry_price'] * 100
                    if not active_trade['partial_closed_1'] and profit >= PARTIAL_CLOSE_LEVEL_1:
                        close_partial(PARTIAL_CLOSE_PERCENT_1, f"Тейк +{PARTIAL_CLOSE_LEVEL_1}%")
                        active_trade['partial_closed_1'] = True
                    if not active_trade['partial_closed_2'] and profit >= PARTIAL_CLOSE_LEVEL_2:
                        close_partial(PARTIAL_CLOSE_PERCENT_2, f"Тейк +{PARTIAL_CLOSE_LEVEL_2}%")
                        active_trade['partial_closed_2'] = True
                    if price > active_trade['best_price']:
                        active_trade['best_price'] = price
                        if not active_trade['trailing_active'] and profit >= TRAILING_ACTIVATE_PERCENT:
                            active_trade['trailing_active'] = True
                            print(f"🔊 Трейлинг активирован при +{profit:.2f}%")
                        if active_trade['trailing_active']:
                            new_stop = active_trade['best_price'] * (1 - TRAILING_DISTANCE_PERCENT / 100)
                            current_stop = get_current_stop()
                            if new_stop > current_stop:
                                update_stop_loss(new_stop)
                else:
                    profit = (active_trade['entry_price'] - price) / active_trade['entry_price'] * 100
                    if not active_trade['partial_closed_1'] and profit >= PARTIAL_CLOSE_LEVEL_1:
                        close_partial(PARTIAL_CLOSE_PERCENT_1, f"Тейк +{PARTIAL_CLOSE_LEVEL_1}%")
                        active_trade['partial_closed_1'] = True
                    if not active_trade['partial_closed_2'] and profit >= PARTIAL_CLOSE_LEVEL_2:
                        close_partial(PARTIAL_CLOSE_PERCENT_2, f"Тейк +{PARTIAL_CLOSE_LEVEL_2}%")
                        active_trade['partial_closed_2'] = True
                    if price < active_trade['best_price']:
                        active_trade['best_price'] = price
                        if not active_trade['trailing_active'] and profit >= TRAILING_ACTIVATE_PERCENT:
                            active_trade['trailing_active'] = True
                            print(f"🔊 Трейлинг активирован при +{profit:.2f}%")
                        if active_trade['trailing_active']:
                            new_stop = active_trade['best_price'] * (1 + TRAILING_DISTANCE_PERCENT / 100)
                            current_stop = get_current_stop()
                            if new_stop < current_stop:
                                update_stop_loss(new_stop)
        except Exception as e:
            print(f"Ошибка трейлинга: {e}")
        time.sleep(10)

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
            exchange.create_market_buy_order(SYMBOL, amount)
            stop_price = round(price * (1 - STOP_LOSS_PERCENT / 100), 4)
            stop_order = exchange.create_order(SYMBOL, 'stop_market', 'sell', amount, None, {'stopPrice': stop_price})
            active_trade.update({
                'side': 'long', 'entry_price': price, 'amount': amount, 'remaining_amount': amount,
                'best_price': price, 'trailing_active': False, 'partial_closed_1': False,
                'partial_closed_2': False, 'stop_order_id': stop_order['id']
            })
        else:
            exchange.create_market_sell_order(SYMBOL, amount)
            stop_price = round(price * (1 + STOP_LOSS_PERCENT / 100), 4)
            stop_order = exchange.create_order(SYMBOL, 'stop_market', 'buy', amount, None, {'stopPrice': stop_price})
            active_trade.update({
                'side': 'short', 'entry_price': price, 'amount': amount, 'remaining_amount': amount,
                'best_price': price, 'trailing_active': False, 'partial_closed_1': False,
                'partial_closed_2': False, 'stop_order_id': stop_order['id']
            })
        print(f"✅ Сделка исполнена. Стоп: {stop_price}")
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    print(f"🚀 БОТ ЗАПУЩЕН. Режим: {'ТЕСТНЕТ' if USE_TESTNET else 'РЕАЛ'}")
    threading.Thread(target=trailing_loop, daemon=True).start()
    app.run(host='0.0.0.0', port=5002)