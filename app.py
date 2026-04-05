import streamlit as st
import pandas as pd
import os
import urllib.parse
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# ---------------- CONFIG ----------------
PACKAGING_COST = 20
PROFIT_MARGIN = 140

STORE_NAME = "🛍️ Induz Online Store"

ADMIN_NUMBER_1 = "917003884969"
ADMIN_NUMBER_2 = "917980238789"

UPI_ID = "yourupi@okbank"   # 🔁 CHANGE

# ---------------- DELIVERY ----------------
def get_delivery_cost(pincode):
    return 70 if str(pincode).startswith("7") else 110

# ---------------- LOAD DATA ----------------
df = pd.read_excel("products.xlsx")

if "cart" not in st.session_state:
    st.session_state.cart = []

# ---------------- UI ----------------
st.set_page_config(page_title="Induz Online Store", layout="wide")

st.markdown(f"# {STORE_NAME}")

# ---------------- PRODUCTS ----------------
st.subheader("🛍️ Products")

cols = st.columns(3)

for i, row in df.iterrows():
    with cols[i % 3]:

        st.markdown("### 🧥 Product")

        image_path = f"images/{row['Image']}"
        if os.path.exists(image_path):
            st.image(image_path)

        st.markdown(f"**{row['ProductName']}**")

        price = row["CostPrice"] + PACKAGING_COST + PROFIT_MARGIN
        st.write(f"💰 ₹{price}")
        st.write(f"📦 Stock: {row['Stock']}")

        qty = st.number_input(f"Qty_{i}", 1, int(row["Stock"]), 1)

        if st.button(f"➕ Add {row['ProductCode']}"):
            st.session_state.cart.append({
                "code": row["ProductCode"],
                "name": row["ProductName"],
                "cost": row["CostPrice"],
                "qty": qty
            })

# ---------------- CART ----------------
st.subheader("🛒 Cart")

total = 0
details = ""

for i, item in enumerate(st.session_state.cart):
    item_total = (item["cost"] + PACKAGING_COST + PROFIT_MARGIN) * item["qty"]
    total += item_total

    details += f"{item['name']} x {item['qty']} = ₹{item_total}\n"

    col1, col2 = st.columns([4,1])

    with col1:
        st.write(f"{item['name']} x {item['qty']}")

    with col2:
        if st.button(f"❌ {i}"):
            st.session_state.cart.pop(i)
            st.rerun()

# ---------------- CUSTOMER ----------------
st.subheader("📦 Customer Details")

name = st.text_input("Name")
phone = st.text_input("Phone")
address = st.text_area("Address")
pincode = st.text_input("Pincode")

# ---------------- ORDER ----------------
if st.button("🚀 Place Order"):

    if not name or not phone or not address or not pincode:
        st.error("Fill all details")

    elif len(st.session_state.cart) == 0:
        st.error("Cart empty")

    else:
        delivery = get_delivery_cost(pincode)
        final_total = total + delivery

        # ---------------- MESSAGE ----------------
        message = f"""
Customer: {name}
Phone: {phone}
Address: {address}

Items:
{details}

Delivery: ₹{delivery}
Total: ₹{final_total}
"""

        encoded = urllib.parse.quote(message)

        customer_number = "91" + phone

        admin1 = f"https://wa.me/{ADMIN_NUMBER_1}?text={encoded}"
        admin2 = f"https://wa.me/{ADMIN_NUMBER_2}?text={encoded}"
        customer = f"https://wa.me/{customer_number}?text={encoded}"

        st.success("Order Ready")

        st.markdown(f"[📲 Admin 1]({admin1})")
        st.markdown(f"[📲 Admin 2]({admin2})")
        st.markdown(f"[📲 Customer Copy]({customer})")

        # ---------------- UPI ----------------
        upi = f"upi://pay?pa={UPI_ID}&pn=Induz&am={final_total}"
        st.markdown(f"[💳 Pay Now]({upi})")

        st.code(message)

        # ---------------- SAVE ORDER ----------------
        order = pd.DataFrame([{
            "Date": datetime.now(),
            "Customer": name,
            "Phone": phone,
            "Address": address,
            "Total": final_total
        }])

        if os.path.exists("orders.xlsx"):
            old = pd.read_excel("orders.xlsx")
            order = pd.concat([old, order])

        order.to_excel("orders.xlsx", index=False)

        # ---------------- PDF ----------------
        doc = SimpleDocTemplate("invoice.pdf")
        styles = getSampleStyleSheet()

        story = []
        story.append(Paragraph("Invoice - Induz Store", styles["Title"]))
        story.append(Spacer(1, 10))
        story.append(Paragraph(message, styles["Normal"]))

        doc.build(story)

        st.success("📄 Invoice Generated")

        st.session_state.cart = []

# ---------------- ORDER HISTORY ----------------
st.subheader("📊 Order History")

if os.path.exists("orders.xlsx"):
    hist = pd.read_excel("orders.xlsx")
    st.dataframe(hist)
else:
    st.info("No orders yet")
