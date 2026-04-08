from flask import Flask, request
import requests
import os
import time
import threading
import json

app = Flask(__name__)

# تنظیمات - از Environment Variables میخونه
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
CHANNEL_USERNAME = os.environ.get("CHANNEL_USERNAME", "@bitcashcryptofaucet")

# URL پایه ربات
BOT_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

def check_membership(user_id):
    """بررسی می‌کند کاربر عضو چنل است یا نه"""
    url = f"{BOT_API_URL}/getChatMember"
    params = {
        "chat_id": CHANNEL_USERNAME,
        "user_id": user_id
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if data.get("ok"):
            status = data["result"].get("status")
            print(f"User {user_id} status in channel: {status}")
            if status in ["member", "administrator", "creator"]:
                return True
        return False
    except Exception as e:
        print(f"Error checking membership: {e}")
        return False

def reward_user(user_id):
    """به کاربر جایزه می‌دهد و task_join_channel رو true میکنه"""
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    
    # اول اطلاعات کاربر رو بگیر
    get_url = f"{SUPABASE_URL}/rest/v1/users?telegram_id=eq.{user_id}&select=*"
    
    try:
        get_response = requests.get(get_url, headers=headers)
        
        if get_response.status_code == 200:
            users = get_response.json()
            if users and len(users) > 0:
                user = users[0]
                
                # اگه قبلاً تسک رو انجام نداده
                if not user.get("task_join_channel", False):
                    # به‌روزرسانی کاربر
                    update_url = f"{SUPABASE_URL}/rest/v1/users?telegram_id=eq.{user_id}"
                    new_coins = user.get("total_coins", 0) + 20
                    
                    update_data = {
                        "task_join_channel": True,
                        "total_coins": new_coins
                    }
                    
                    update_response = requests.patch(update_url, headers=headers, json=update_data)
                    
                    if update_response.status_code == 200:
                        print(f"User {user_id} rewarded successfully! New coins: {new_coins}")
                        return True
                    else:
                        print(f"Failed to update user: {update_response.text}")
                else:
                    print(f"User {user_id} already completed task")
                    return False
        else:
            print(f"Failed to get user: {get_response.text}")
        return False
    except Exception as e:
        print(f"Error rewarding user: {e}")
        return False

def send_message(chat_id, text):
    """پیام می‌فرستد"""
    url = f"{BOT_API_URL}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text
    }
    try:
        response = requests.post(url, json=data)
        print(f"Message sent to {chat_id}: {response.status_code}")
    except Exception as e:
        print(f"Error sending message: {e}")

def handle_message(message):
    """پردازش پیام دریافتی"""
    text = message.get("text", "")
    user_id = message["from"]["id"]
    chat_id = message["chat"]["id"]
    username = message["from"].get("username", "No username")
    
    print(f"Received message from {user_id} (@{username}): {text}")
    
    if text == "/start":
        send_message(chat_id, "👋 Welcome to Bitcash Crypto Faucet!\n\nUse the mini app to watch ads and earn DOGE coins!\n\nCommands:\n/verify - Verify channel membership and get 20 coins bonus")
    
    elif text == "/verify":
        send_message(chat_id, "🔍 Checking your channel membership... Please wait.")
        
        if check_membership(user_id):
            if reward_user(user_id):
                send_message(chat_id, "✅ Congratulations! You have been verified and received 20 bonus coins!")
            else:
                send_message(chat_id, "❌ You have already claimed your bonus or there was an error. Please contact support.")
        else:
            send_message(chat_id, f"❌ You are not a member of {CHANNEL_USERNAME} yet.\n\nPlease join the channel first, then send /verify again.")
    
    else:
        send_message(chat_id, "Unknown command. Please use /start or /verify")

def get_updates(offset=None):
    """دریافت آپدیت‌های جدید از تلگرام"""
    url = f"{BOT_API_URL}/getUpdates"
    params = {"timeout": 30, "offset": offset}
    try:
        response = requests.get(url, params=params, timeout=35)
        result = response.json()
        return result.get("result", [])
    except Exception as e:
        print(f"Error getting updates: {e}")
        return []

def polling_loop():
    """حلقه اصلی دریافت پیام‌ها"""
    print("Polling loop started...")
    last_update_id = 0
    
    while True:
        try:
            updates = get_updates(offset=last_update_id + 1)
            for update in updates:
                last_update_id = update["update_id"]
                if "message" in update:
                    handle_message(update["message"])
        except Exception as e:
            print(f"Error in polling loop: {e}")
        time.sleep(1)

@app.route("/")
def index():
    return "Bot is running with polling method! Bot username: @Bitcashcryptofaucet_bot"

@app.route("/webhook", methods=["POST"])
def webhook():
    """Webhook endpoint for Telegram"""
    try:
        update = request.get_json()
        if update and "message" in update:
            handle_message(update["message"])
        return "ok", 200
    except Exception as e:
        print(f"Webhook error: {e}")
        return "error", 500

if __name__ == "__main__":
    # راه‌اندازی حلقه Polling در یک ترد جداگانه
    polling_thread = threading.Thread(target=polling_loop, daemon=True)
    polling_thread.start()
    
    # راه‌اندازی سرور Flask
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
