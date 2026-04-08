from flask import Flask, request
import requests
import os
import json

app = Flask(__name__)

# تنظیمات - از Environment Variables میخونه
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
CHANNEL_USERNAME = os.environ.get("CHANNEL_USERNAME", "@bitcashcryptofaucet")

def check_membership(user_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMember"
    params = {
        "chat_id": CHANNEL_USERNAME,
        "user_id": user_id
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if data.get("ok"):
            status = data["result"].get("status")
            if status in ["member", "administrator", "creator"]:
                return True
        return False
    except Exception as e:
        print(f"Error checking membership: {e}")
        return False

def reward_user(user_id):
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    
    get_url = f"{SUPABASE_URL}/rest/v1/users?telegram_id=eq.{user_id}&select=*"
    
    try:
        get_response = requests.get(get_url, headers=headers)
        
        if get_response.status_code == 200:
            users = get_response.json()
            if users and len(users) > 0:
                user = users[0]
                if not user.get("task_join_channel", False):
                    update_url = f"{SUPABASE_URL}/rest/v1/users?telegram_id=eq.{user_id}"
                    new_coins = user.get("total_coins", 0) + 20
                    
                    update_data = {
                        "task_join_channel": True,
                        "total_coins": new_coins
                    }
                    
                    update_response = requests.patch(update_url, headers=headers, json=update_data)
                    return update_response.status_code == 200
        return False
    except Exception as e:
        print(f"Error rewarding user: {e}")
        return False

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text
    }
    try:
        requests.post(url, json=data)
    except Exception as e:
        print(f"Error sending message: {e}")

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        update = request.get_json()
        
        if "message" in update:
            message = update["message"]
            text = message.get("text", "")
            user_id = message["from"]["id"]
            chat_id = message["chat"]["id"]
            
            if text == "/start":
                send_message(chat_id, "👋 Welcome! Use the mini app to watch ads and earn coins!")
            
            elif text == "/verify":
                if check_membership(user_id):
                    if reward_user(user_id):
                        send_message(chat_id, "✅ عضویت شما تأیید شد! 20 سکه به حساب شما اضافه شد.")
                    else:
                        send_message(chat_id, "❌ خطا در ثبت جایزه. لطفاً با پشتیبانی تماس بگیرید.")
                else:
                    send_message(chat_id, "❌ شما هنوز عضو چنل نشدید. لطفاً ابتدا عضو شوید و سپس دوباره /verify را بفرستید.")
        
        return "ok", 200
    except Exception as e:
        print(f"Error: {e}")
        return "error", 500

@app.route("/")
def index():
    return "Bot is running!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)