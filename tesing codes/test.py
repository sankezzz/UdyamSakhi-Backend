from flask import Flask, request, jsonify
import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
WHATSAPP_ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")

app = Flask(__name__)

# Temporary storage for user selections
user_selections = {}
user_states = {}  # Track user state

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

        # Handle Messages
        entry = data.get("entry", [])[0]
        changes = entry.get("changes", [])[0]
        value = changes.get("value", {})

        if "messages" in value:
            message = value["messages"][0]
            sender = message["from"]
            
            # Check for text message
            if "text" in message:
                text = message["text"]["body"].lower()
                if sender in user_states and user_states[sender] == "waiting_for_confirm":
                    if text == "confirm":
                        generate_bill(sender)
                        user_states.pop(sender)  # Reset state
                    elif text == "menu":
                        send_menu(sender)
                        user_states.pop(sender)  # Reset state
                    else:
                        send_message(sender, "Invalid input. Please reply with 'menu' or 'confirm'.")
                else:
                    send_welcome_message(sender)

            elif "interactive" in message:
                interactive_data = message["interactive"]
                if "button_reply" in interactive_data:
                    button_id = interactive_data["button_reply"]["id"]

                    if button_id == "menu_button":
                        send_menu(sender)
                    elif button_id == "payment_done":
                        send_message(sender, "*Payment Confirmed!* Thank you for your order!")
                elif "list_reply" in interactive_data:
                    item_id = interactive_data["list_reply"]["id"]
                    add_to_selection(sender, item_id)
            

        return "OK", 200

def send_welcome_message(to):
    """Send welcome message with interactive buttons"""
    url = f"https://graph.facebook.com/v16.0/{PHONE_NUMBER_ID}/messages"
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
            "body": {"text": "Welcome to our small business! We offer handcrafted goods made with love. How can we assist you?"},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": "menu_button", "title": "📜 View Items"}},
                    {"type": "reply", "reply": {"id": "contact_button", "title": "📞 Contact Us"}}
                ]
            }
        }
    }

    response = requests.post(url, headers=headers, json=payload)
    print(f"📤 Sent Welcome Message Response: {response.json()}")

def send_menu(to):
    """Send an interactive menu"""
    url = f"https://graph.facebook.com/v16.0/{PHONE_NUMBER_ID}/messages"
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
            "body": {"text": "*✨ Our Handmade Collection:*\nSelect items one by one."},
            "action": {
                "button": "Choose Items",
                "sections": [
                    {
                        "title": "🧶 Handknitted Items",
                        "rows": [
                            {"id": "scarf_1", "title": "Wool Scarf - ₹450"},
                            {"id": "beanie_1", "title": "Cozy Beanie - ₹350"}
                        ]
                    },
                    {
                        "title": "🏺 Pottery",
                        "rows": [
                            {"id": "mug_1", "title": "Handcrafted Mug - ₹250"},
                            {"id": "bowl_1", "title": "Decorative Bowl - ₹500"}
                        ]
                    },
                     {
                        "title": "🧵 Embroidery",
                        "rows": [
                            {"id": "hoop_1", "title": "Embroidery Hoop - ₹650"},
                        ]
                    }
                ]
            }
        }
    }

    response = requests.post(url, headers=headers, json=payload)
    print(f"📤 Sent Menu Response: {response.json()}")

def add_to_selection(user_id, item_id):
    """Add selected item to user's order"""
    menu_items = {
        'scarf_1': ("Wool Scarf", 450),
        'beanie_1': ("Cozy Beanie", 350),
        'mug_1': ("Handcrafted Mug", 250),
        'bowl_1': ("Decorative Bowl", 500),
        'hoop_1': ("Embroidery Hoop", 650)
    }

    item_name, item_price = menu_items[item_id]

    if user_id not in user_selections:
        user_selections[user_id] = []

    user_selections[user_id].append((item_name, item_price))

    # Send confirmation message
    send_message(user_id, f"✅ Added *{item_name}* to your cart!")

    # Ask if they want to add more or confirm order
    send_message(user_id, "*Do you want to add more items or confirm your order?*\nReply with 'menu' or 'confirm'.")
    user_states[user_id] = "waiting_for_confirm"  # Set user state

def generate_bill(user_id):
    """Generate and send the bill"""
    if user_id not in user_selections or not user_selections[user_id]:
        send_message(user_id, "*Your cart is empty!* Please select items from the menu.")
        return

    items = user_selections[user_id]
    total_cost = sum(item[1] for item in items)

    bill_message = f"*✨ Your Order Summary:*\n Order id -867654 \n UserName - Sanket \n Address - Bhupeshnagar,Nagpur\n"
    for item_name, item_price in items:
        bill_message += f"- {item_name}: ₹{item_price}\n"
    
    bill_message += f"\n*Total: ₹{total_cost}*\n\nThank you for supporting our small business! 💖"

    # Send the bill
    send_message(user_id, bill_message)

     # Send payment confirmation button
    send_payment_confirmation(user_id)

    # Clear user's selections after generating the bill
    user_selections[user_id] = []


def send_payment_confirmation(to):
    """Send payment confirmation button"""
    url = f"https://graph.facebook.com/v16.0/{PHONE_NUMBER_ID}/messages"
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
            "body": {"text": "Confirm Payment?"},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": "payment_done", "title": "✅ Payment Done"}}
                ]
            }
        }
    }

    response = requests.post(url, headers=headers, json=payload)
    print(f"📤 Sent Payment Confirmation Button: {response.json()}")


def send_message(to, message):
    """Send a simple text message"""
    url = f"https://graph.facebook.com/v16.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        'Authorization': f'Bearer {WHATSAPP_ACCESS_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        'messaging_product': 'whatsapp',
        'to': to,
        'text': {'body': message}
    }

    response = requests.post(url, headers=headers, json=payload)
    print(f"📤 Sent Message Response: {response.json()}")

@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": True, "message": 'WhatsApp Bot is Running 🚀'})

if __name__ == "__main__":
    app.run(debug=True, port=5000)
