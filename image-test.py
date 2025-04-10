from flask import Flask, request, jsonify
import os
import requests
import json
from dotenv import load_dotenv
from datetime import datetime
import time  # Already requested

# Load environment variables
load_dotenv()
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
WHATSAPP_ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")

app = Flask(__name__)

# Temporary storage for user selections
user_selections = {}

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
        print(f"📩 Incoming Webhook Data: {json.dumps(data, indent=2)}")

        entry = data.get("entry", [])[0]
        changes = entry.get("changes", [])[0]
        value = changes.get("value", {})

        if "messages" in value:
            message = value["messages"][0]
            sender = message["from"]

            if "interactive" in message:
                interactive_data = message["interactive"]
                if "button_reply" in interactive_data:
                    button_id = interactive_data["button_reply"]["id"]

                    if button_id == "menu_button":
                        send_menu(sender)
                    elif button_id == "contact_button":
                        send_contact_info(sender)
                    elif button_id == "payment_done":
                        send_message(sender, "*✅ Payment Confirmed!* Thank you for your order! 🙏")
                        save_bill_to_json(sender)  # Save bill to file here
                    elif button_id == "confirm_order":
                        generate_bill(sender)
                    elif button_id == "add_more":
                        send_menu(sender)
                elif "list_reply" in interactive_data:
                    item_id = interactive_data["list_reply"]["id"]
                    add_to_selection(sender, item_id)
            else:
                send_welcome_message(sender)

        return "OK", 200
    
def send_contact_info(to):
    message = (
        "*📞 Contact Information:*\n\n"
        "👩‍💼 *Owner:* Aarti Creations\n"
        "📍 *Location:* Bhupeshnagar, Nagpur\n"
        "📱 *Phone:* +91 7719436134\n"
        "📧 *Email:* support@aarticreations.in\n"
        "🕒 *Working Hours:* 10 AM - 6 PM (Mon - Sat)"
    )

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
    print(f"📤 Sent Contact Info Response: {response.json()}")

def send_welcome_message(to):
    # 1. Send image message first
    image_url = "https://plus.unsplash.com/premium_photo-1679809447923-b3250fb2a0ce?q=80&w=2071&auto=format&fit=crop&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D"  # 👈 Replace with your image URL
    image_payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "image",
        "image": {
            "link": image_url
        }
    }
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    image_response = requests.post(
        f"https://graph.facebook.com/v16.0/{PHONE_NUMBER_ID}/messages",
        headers=headers,
        json=image_payload
    )
    print(f"📤 Sent Image Response: {image_response.json()}")

    # 2. Then send interactive button message
    button_payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {
                "text": "Welcome to our small business! We offer handcrafted goods made with love. How can we assist you?"
            },
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": "menu_button", "title": "📜 View items"}},
                    {"type": "reply", "reply": {"id": "contact_button", "title": "📞 Contact Us"}}
                ]
            }
        }
    }

    button_response = requests.post(
        f"https://graph.facebook.com/v16.0/{PHONE_NUMBER_ID}/messages",
        headers=headers,
        json=button_payload
    )
    print(f"📤 Sent Welcome Message Response: {button_response.json()}")

def send_menu(to):
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

def send_product_cards(to, items):
    """
    Sends product cards with image and 'Add to Cart' buttons on WhatsApp.
    """
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    for item in items:
        try:
            # Step 1: Send Product Image
            image_payload = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "image",
                "image": {"link": item["image"]},
            }

            image_resp = requests.post(
                f"https://graph.facebook.com/v16.0/{PHONE_NUMBER_ID}/messages",
                headers=headers, json=image_payload
            )

            if image_resp.status_code != 200:
                print(f"❌ Failed to send image for {item['title']}: {image_resp.json()}")
            else:
                print(f"🖼️ Image sent for {item['title']}")

            time.sleep(1)  # Avoid API rate limit

            # Step 2: Send Button
            button_payload = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "interactive",
                "interactive": {
                    "type": "button",
                    "body": {
                        "text": f"*{item['title']}*\n{item['description']}"
                    },
                    "action": {
                        "buttons": [
                            {
                                "type": "reply",
                                "reply": {
                                    "id": item["id"],
                                    "title": "➕ Add to Cart"
                                }
                            }
                        ]
                    }
                }
            }

            button_resp = requests.post(
                f"https://graph.facebook.com/v16.0/{PHONE_NUMBER_ID}/messages",
                headers=headers, json=button_payload
            )

            if button_resp.status_code != 200:
                print(f"❌ Failed to send button for {item['title']}: {button_resp.json()}")
            else:
                print(f"✅ Button sent for {item['title']}")

            time.sleep(1)

        except Exception as e:
            print(f"⚠️ Error sending card for {item['title']}: {str(e)}")



def add_to_selection(user_id, item_id):
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
    send_add_more_or_confirm_buttons(user_id)

def send_payment_confirmation(to):
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
            "body": {"text": "✅ Once paid, click below to confirm your payment."},
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {"id": "payment_done", "title": "✅ Payment Done"}
                    }
                ]
            }
        }
    }

    response = requests.post(url, headers=headers, json=payload)
    print(f"📤 Sent Payment Confirmation Button: {response.json()}")

def generate_bill(user_id):
    if user_id not in user_selections or not user_selections[user_id]:
        send_message(user_id, "*Your cart is empty!* Please select items from the menu.")
        return

    items = user_selections[user_id]
    total_cost = sum(item[1] for item in items)

    bill_message = f"*✨ Your Order Summary:*\nOrder ID: 867654\nUserName: Sanket\nAddress: Bhupeshnagar, Nagpur\n"
    for item_name, item_price in items:
        bill_message += f"- {item_name}: ₹{item_price}\n"
    
    bill_message += f"\n*Total: ₹{total_cost}*"
    
    send_message(user_id, bill_message)
    payment_link = "https://razorpay.me/@sanketmarotisuryawanshi"
    send_message(user_id, f"💳 Please make the payment here:\n{payment_link}")
    send_payment_confirmation(user_id)

def send_add_more_or_confirm_buttons(to):
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
            "body": {"text": "Do you want to add more items or confirm your order?"},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": "add_more", "title": "➕ Add More"}},
                    {"type": "reply", "reply": {"id": "confirm_order", "title": "✅ Confirm Order"}}
                ]
            }
        }
    }

    response = requests.post(url, headers=headers, json=payload)
    print(f"📤 Sent Add More or Confirm Buttons: {response.json()}")

def send_message(to, message):
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

def save_bill_to_json(user_id):
    """Store the latest confirmed order in a JSON file and send to seller"""
    bill_data = {
        "user_id": user_id,
        "username": "Sanket",
        "address": "Bhupeshnagar, Nagpur",
        "timestamp": datetime.now().isoformat(),
        "items": [],
        "total": 0
    }

    for item_name, item_price in user_selections.get(user_id, []):
        bill_data["items"].append({"name": item_name, "price": item_price})
        bill_data["total"] += item_price

    if not os.path.exists("bills.json"):
        with open("bills.json", "w") as f:
            json.dump([], f)

    with open("bills.json", "r+") as f:
        data = json.load(f)
        data.append(bill_data)
        f.seek(0)
        json.dump(data, f, indent=2)

    # ✅ Send bill to seller WhatsApp
    send_bill_to_seller(bill_data)


def send_bill_to_seller(bill_data):
    seller_number = "917719436134"  # 👈 Replace this with actual seller number

    message = f"🧾 *New Order Received!*\n"
    message += f"👤 Customer: {bill_data['username']}\n"
    message += f"🏠 Address: {bill_data['address']}\n"
    message += f"🕒 Time: {bill_data['timestamp']}\n\n"
    message += "*🛍️ Items:*\n"
    message +=f"UPI Payment ID - 8374582344"
    for item in bill_data["items"]:
        message += f"- {item['name']}: ₹{item['price']}\n"
    message += f"\n💰 *Total: ₹{bill_data['total']}*"

    url = f"https://graph.facebook.com/v16.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        'Authorization': f'Bearer {WHATSAPP_ACCESS_TOKEN}',
        'Content-Type': 'application/json'
    }

    payload = {
        'messaging_product': 'whatsapp',
        'to': seller_number,
        'text': {'body': message}
    }

    response = requests.post(url, headers=headers, json=payload)
    print(f"📤 Sent Bill to Seller Response: {response.json()}")


@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": True, "message": 'WhatsApp Bot is Running 🚀'})

if __name__ == "__main__":
    app.run(debug=True, port=5000)
