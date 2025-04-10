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
        

        # ✅ Handle Messages
        entry = data.get("entry", [])[0]
        changes = entry.get("changes", [])[0]
        value = changes.get("value", {})

        if "messages" in value:
            message = value["messages"][0]
            sender = message["from"]
            text = message.get("text", {}).get("body", "").strip().lower()

            print(f"📥 Received Message: {text} from {sender}")

            handle_message(sender, text)

        return "OK", 200


def handle_message(sender, text):
    """Process incoming message & send appropriate reply"""
    if text in ["Hi", "hello", "hii"]:
        send_template_message(sender, "hello_world")

    elif text == "menu":
        send_menu(sender)

    elif text == "contact support":
        send_message(sender, "📞 *Support:* +91XXXXXXXXXX")

    else:
        send_message(sender, "❌ Invalid option. Type 'Hi' to start! 😊")


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


def send_template_message(to, template_name):
    """Send a pre-approved template message"""
    url = f"https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": "en_US"}
        }
    }

    response = requests.post(url, headers=headers, json=payload)
    print(f"📤 Sent Template Message Response: {response.json()}")


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
