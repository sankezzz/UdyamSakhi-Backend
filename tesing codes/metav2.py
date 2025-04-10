import os
import requests
import json
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
WHATSAPP_ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")

app = Flask(__name__)

# ✅ Webhook Verification (For GET Request)
@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        verify_token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        if verify_token == VERIFY_TOKEN:
            return challenge
        return "Invalid verification token", 403

    elif request.method == "POST":
        data = request.get_json()
        print(f"📩 Incoming Webhook Data: {json.dumps(data, indent=2)}")  # Debugging

        # ✅ Handle Messages
        entry = data.get("entry", [])[0]
        changes = entry.get("changes", [])[0]
        value = changes.get("value", {})

        if "messages" in value:
            message = value["messages"][0]
            sender = message["from"]

            # ✅ Check if it's a button click
            if "interactive" in message:
                button_reply = message["interactive"]["button_reply"]
                button_id = button_reply["id"]

                if button_id == "menu_button":
                    send_menu(sender)
                elif button_id == "contact_button":
                    send_message(sender, "📞 *Support:* +91XXXXXXXXXX")

            else:
                send_welcome_message(sender)  # ✅ Send welcome message for normal text input

        return "OK", 200


def send_welcome_message(to):
    """Send welcome message with interactive buttons"""
    url = f"https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": "🍽 Welcome to our restaurant! How can we assist you?"},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": "menu_button", "title": "📜 View Menu"}},
                    {"type": "reply", "reply": {"id": "contact_button", "title": "📞 Contact Us"}}
                ]
            }
        }
    }

    response = requests.post(url, headers=headers, json=payload)
    print(f"📤 Sent Welcome Message Response: {response.json()}")


def send_message(to, message):
    """Send a simple text message"""
    url = f"https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "text": {"body": message}
    }

    response = requests.post(url, headers=headers, json=payload)
    print(f"📤 Sent Message Response: {response.json()}")


def send_menu(to):
    """Send an interactive menu"""
    url = f"https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": "🍽 *Menu:* Choose a category below:"},
            "action": {
                "button": "View Menu",
                "sections": [
                    {
                        "title": "🍔 Burgers",
                        "rows": [
                            {"id": "burger_1", "title": "Classic Burger - ₹99"},
                            {"id": "burger_2", "title": "Cheese Burger - ₹129"}
                        ]
                    },
                    {
                        "title": "🍕 Pizzas",
                        "rows": [
                            {"id": "pizza_1", "title": "Margherita - ₹199"},
                            {"id": "pizza_2", "title": "Pepperoni - ₹249"}
                        ]
                    }
                ]
            }
        }
    }

    response = requests.post(url, headers=headers, json=payload)
    print(f"📤 Sent Menu Response: {response.json()}")


@app.route("/", methods=["GET"])
def home():
    return "WhatsApp Bot is Running! 🚀", 200


if __name__ == "__main__":
    app.run(debug=True, port=5000)
