import requests
import json
from flask import Flask, request, jsonify

app = Flask(__name__)

# ===== НАСТРОЙКИ TELEGRAM (ЗАМЕНИ НА СВОИ) =====
TELEGRAM_BOT_TOKEN = "8120661225:AAFzaTzBrfCqjZA2jMmA0bs9zeoDmA0lObA"
TELEGRAM_CHAT_ID = "8398600924"
SECRET = "my_secret_2025"

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'HTML'}
    try:
        r = requests.post(url, json=payload)
        print(f"Telegram ответ: {r.status_code}")
    except Exception as e:
        print(f"Ошибка отправки в Telegram: {e}")

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        print(f"📡 Получен сигнал: {data}")

        if data.get('secret') != SECRET:
            print("❌ Неверный секрет!")
            return jsonify({"error": "Unauthorized"}), 401

        signal = data.get('signal')
        price = data.get('price')

        if signal in ['buy', 'sell']:
            msg = f"🔔 <b>СИГНАЛ ОТ TRADINGVIEW!</b>\n\n"
            msg += f"Направление: <b>{'ПОКУПКА 🟢' if signal == 'buy' else 'ПРОДАЖА 🔴'}</b>\n"
            msg += f"Цена: <b>{price} USDT</b>\nПара: XRPUSDT"
            send_telegram(msg)
            return jsonify({"status": "ok"}), 200
        else:
            return jsonify({"error": "Invalid signal"}), 400

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    print("🚀 TELEGRAM-БОТ ЗАПУЩЕН!")
    app.run(host='0.0.0.0', port=5002)
