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
reference_map = {}
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


import os
import razorpay
import uuid

# Fetch from environment
RAZORPAY_KEY_ID = os.getenv("key_id")
RAZORPAY_SECRET = os.getenv("key_secret")

# ✅ Correct usage (pass variables, not strings)
razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_SECRET))


# In-memory reference map (user_id <-> reference_id)
reference_map = {}

def generate_bill(user_id):
    if user_id not in user_selections or not user_selections[user_id]:
        send_message(user_id, "*🛒 Your cart is empty!* Please select items from the menu.")
        return

    items = user_selections[user_id]
    total_cost = sum(item[1] for item in items)
    amount_in_paise = total_cost * 100

    order_id = str(uuid.uuid4())[:8]  # short reference id
    reference_map[order_id] = user_id  # Save mapping for webhook

    # Build bill message
    bill_message = f"*✨ Your Order Summary:*\nOrder ID: {order_id}\nUserName: Sanket\nAddress: Bhupeshnagar, Nagpur\n"
    for item_name, item_price in items:
        bill_message += f"- {item_name}: ₹{item_price}\n"
    bill_message += f"\n*Total: ₹{total_cost}*"

    send_message(user_id, bill_message)

    # Razorpay payment link creation
    try:
        payment_link_data = {
            "amount": amount_in_paise,
            "currency": "INR",
            "accept_partial": False,
            "reference_id": order_id,
            "description": "Mahila Udyam Order Payment",
            "customer": {
                "name": "Sanket",
                "contact": user_id,  # Assuming user_id is phone
                "email": "demo@example.com"
            },
            "notify": {
                "sms": False,
                "email": False
            },
            "callback_url": "https://4b10-14-139-61-211.ngrok-free.app/payment/webhook"
            
        }

        response = razorpay_client.payment_link.create(payment_link_data)
        payment_link = response['short_url']

        send_message(user_id, f"💳 Please make the payment here:\n{payment_link}")
        send_message(user_id, "📌 Once payment is complete, you’ll get a confirmation automatically.")

    except Exception as e:
        print("❌ Razorpay error:", e)
        send_message(user_id, "⚠️ Failed to generate payment link. Please try again later.")


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
    message += f"🧾 UPI Payment ID: {bill_data.get('payment_id', 'N/A')}\n\n"
    message +="Order to be prepared in 5 days"
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

@app.route('/payment/webhook', methods=['POST'])
def payment_webhook():
    data = request.json
    print("📩 Incoming Webhook Data:", data)

    event = data.get('event')
    payload = data.get('payload', {})
    
    if event == "payment_link.paid":
        payment_info = payload.get("payment_link", {}).get("entity", {})
        reference_id = payment_info.get("reference_id")
        payment_id = payment_info.get("id")
        amount = int(payment_info.get("amount", 0)) // 100

        user_id = reference_map.get(reference_id)
        if not user_id:
            print("⚠️ No matching user found for reference_id:", reference_id)
            return '', 200

        items = user_selections.get(user_id, [])
        if not items:
            send_message(user_id, "⚠️ Your order could not be found after payment.")
            return '', 200

        now = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        username = "Sanket"
        address = "Bhupeshnagar, Nagpur"

        # Format items into dict list for seller function
        formatted_items = [{"name": name, "price": price} for name, price in items]

        # Build `bill_data` dict
        bill_data = {
            "username": username,
            "address": address,
            "timestamp": now,
            "items": formatted_items,
            "total": amount,
            "payment_id": payment_id
        }

        # Save to file
        with open("orders.json", "a") as f:
            f.write(json.dumps(bill_data) + "\n")

        # Clear cart
        user_selections[user_id] = []

        # Final message to user
        receipt = f"""🧾 *Mahila Udyam - Order Receipt*\n
Order ID: {reference_id}
Payment ID: {payment_id}
Date: {now}

Items:\n""" + "\n".join([f"- {i['name']}: ₹{i['price']}" for i in formatted_items]) + f"\n\n*Total Paid: ₹{amount}*\n✅ Payment Successful."

        send_message(user_id, receipt)
        save_bill_to_json(user_id)
        

        # ✅ CALL YOUR FUNCTION TO NOTIFY SELLER
        send_bill_to_seller(bill_data)


    return '', 200




if __name__ == "__main__":
    app.run(debug=True, port=5000)
