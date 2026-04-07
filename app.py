import streamlit as st
import sqlite3
import os
import urllib.parse
from datetime import datetime

# ---------------- CONFIG ----------------
PACKAGING_COST = 20
PROFIT_MARGIN = 140

ADMIN_NUMBER = "917003884969"  # MAIN NUMBER (use WhatsApp group for both)
UPI_ID = "yourupi@okbank"

# ---------------- DB SETUP ----------------
conn = sqlite3.connect("store.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    cost INTEGER,
    stock INTEGER,
    image TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    customer TEXT,
    phone TEXT,
    address TEXT,
    total INTEGER
)
""")

conn.commit()

# ---------------- LOAD PRODUCTS ----------------
products = c.execute("SELECT * FROM products").fetchall()

# ---------------- UI ----------------
st.set_page_config(page_title="Sajai Tomay", layout="wide")

st.markdown("<h1 style='text-align:center;'>🌸 Sajai Tomay</h1>", unsafe_allow_html=True)

# ---------------- CART ----------------
if "cart" not in st.session_state:
    st.session_state.cart = []

# ---------------- PRODUCTS UI ----------------
st.markdown("## 🛍️ Our Collection")

cols = st.columns(3)

for i, p in enumerate(products):
    with cols[i % 3]:
        st.markdown("----")

        if os.path.exists(f"images/{p[4]}"):
            st.image(f"images/{p[4]}", use_container_width=True)

        price = p[2] + PACKAGING_COST + PROFIT_MARGIN

        st.markdown(f"### {p[1]}")
        st.markdown(f"💰 ₹{price}")
        st.markdown(f"📦 Stock: {p[3]}")

        qty = st.number_input(f"qty_{p[0]}", 1, int(p[3]), 1)

        if st.button(f"Add {p[0]}"):
            st.session_state.cart.append({
                "id": p[0],
                "name": p[1],
                "qty": qty,
                "price": price
            })

# ---------------- CART ----------------
st.markdown("## 🛒 Your Cart")

total = 0
details = ""

for i, item in enumerate(st.session_state.cart):
    item_total = item["price"] * item["qty"]
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
st.markdown("## 📦 Delivery Details")

name = st.text_input("Name")
phone = st.text_input("Phone")
address = st.text_area("Address")
pincode = st.text_input("Pincode")

def delivery_cost(pin):
    return 70 if str(pin).startswith("7") else 110

# ---------------- ORDER ----------------
if st.button("🚀 Place Order"):

    if not name or not phone or not address:
        st.error("Fill all details")

    elif len(st.session_state.cart) == 0:
        st.error("Cart empty")

    else:
        delivery = delivery_cost(pincode)
        final = total + delivery

        # 🔥 PROFESSIONAL MESSAGE
        message = f"""
🌸 Sajai Tomay 🌸

Thank you for your order ❤️

Customer: {name}
Phone: {phone}
Address: {address}

Items:
{details}

Delivery: ₹{delivery}
Total Amount: ₹{final}

✨ We will contact you shortly for confirmation.
Thank you for shopping with us!
"""

        encoded = urllib.parse.quote(message)

        whatsapp_link = f"https://wa.me/{ADMIN_NUMBER}?text={encoded}"
        customer_link = f"https://wa.me/91{phone}?text={encoded}"

        st.success("✅ Order Ready")

        st.markdown(f"👉 [📲 Send Order (Admin)]({whatsapp_link})")
        st.markdown(f"👉 [📲 Get Copy (Customer)]({customer_link})")

        # ---------------- SAVE ORDER ----------------
        c.execute("""
        INSERT INTO orders (date, customer, phone, address, total)
        VALUES (?, ?, ?, ?, ?)
        """, (str(datetime.now()), name, phone, address, final))

        # ---------------- UPDATE STOCK ----------------
        for item in st.session_state.cart:
            c.execute("UPDATE products SET stock = stock - ? WHERE id = ?",
                      (item["qty"], item["id"]))

        conn.commit()

        # ---------------- PAYMENT ----------------
        upi = f"upi://pay?pa={UPI_ID}&pn=SajaiTomay&am={final}"
        st.markdown(f"👉 [💳 Pay Now]({upi})")

        st.session_state.cart = []

# ---------------- ADMIN PANEL ----------------
st.sidebar.title("🔐 Admin Login")

user = st.sidebar.text_input("User")
pwd = st.sidebar.text_input("Pass", type="password")

if user == "admin" and pwd == "1234":
    st.sidebar.success("Logged in")

    st.markdown("## 📊 Order History")

    data = c.execute("SELECT * FROM orders").fetchall()
    st.dataframe(data)
    
import sqlite3
conn = sqlite3.connect("store.db")
c = conn.cursor()

c.execute("INSERT INTO products (name, cost, stock, image) VALUES ('Earrings', 80, 20, 'J001.jpg')")
conn.commit()