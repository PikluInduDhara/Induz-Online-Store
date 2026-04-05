import streamlit as st
import pandas as pd
import os
import urllib.parse

PACKAGING_COST = 20
PROFIT_MARGIN = 140

STORE_NAME = "🛍️ Induz Online Store"

def get_delivery_cost(pincode):
    return 70 if str(pincode).startswith("7") else 110

st.set_page_config(page_title="Induz Online Store", layout="wide")

st.title(STORE_NAME)

# Load products
df = pd.read_excel("products.xlsx")

if "cart" not in st.session_state:
    st.session_state.cart = []

# 🛍️ Product Display
cols = st.columns(3)

for i, row in df.iterrows():
    with cols[i % 3]:
        image_path = f"images/{row['Image']}"
        
        if os.path.exists(image_path):
            st.image(image_path, use_container_width=True)

        st.subheader(row["ProductName"])
        price = row["CostPrice"] + PACKAGING_COST + PROFIT_MARGIN
        st.write(f"Price: ₹{price}")
        st.write(f"Stock: {row['Stock']}")

        # 🚫 Prevent selecting more than stock
        qty = st.number_input(
            f"Qty_{i}", 
            min_value=1, 
            max_value=int(row["Stock"]), 
            step=1
        )

        if st.button(f"Add {row['ProductCode']}"):
            if qty > row["Stock"]:
                st.error("Not enough stock!")
            else:
                st.session_state.cart.append({
                    "code": row["ProductCode"],
                    "name": row["ProductName"],
                    "cost": row["CostPrice"],
                    "qty": qty
                })

# 🛒 Cart
st.subheader("🛒 Your Cart")

total = 0
details = ""

for item in st.session_state.cart:
    item_total = (item["cost"] + PACKAGING_COST + PROFIT_MARGIN) * item["qty"]
    total += item_total
    details += f"{item['name']} x {item['qty']} = ₹{item_total}\n"
    st.write(f"{item['name']} x {item['qty']}")

# 📦 Customer Details
st.subheader("📦 Delivery Details")

pincode = st.text_input("Pincode")
name = st.text_input("Customer Name")

if st.button("Place Order"):

    # 🔥 Reduce stock
    for item in st.session_state.cart:
        df.loc[df["ProductCode"] == item["code"], "Stock"] -= item["qty"]

    # Save updated stock
    df.to_excel("products.xlsx", index=False)

    delivery = get_delivery_cost(pincode)
    final_total = total + delivery

    st.success("Order Placed!")

    message = f"""
Hello {name} 😊

Welcome to Induz Online Store

Items:
{details}

Delivery: ₹{delivery}
Total Amount: ₹{final_total}
"""

    st.subheader("📱 WhatsApp Order")

    encoded_msg = urllib.parse.quote(message)

    whatsapp_url = f"https://wa.me/YOUR_NUMBER?text={encoded_msg}"

    st.markdown(f"[👉 Click to Order on WhatsApp]({whatsapp_url})")

    # 💳 UPI Payment
    st.subheader("💳 Pay via UPI")

    upi_link = f"upi://pay?pa=yourupi@okbank&pn=InduzStore&am={final_total}"

    st.markdown(f"[👉 Pay Now]({upi_link})")

    st.code(message)

    # Clear cart
    st.session_state.cart = []