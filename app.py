import streamlit as st
import sqlite3
import os
import base64
import urllib.parse
import pandas as pd
import time
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

st.set_page_config(page_title="Sajai Tomay", layout="wide")

# ---------------- DATABASE ----------------
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
    customer TEXT,
    phone TEXT,
    address TEXT,
    product TEXT,
    quantity INTEGER,
    total INTEGER
)
""")

# SAFE COLUMN ADDITIONS
try:
    c.execute("ALTER TABLE orders ADD COLUMN status TEXT DEFAULT 'Pending'")
except:
    pass

try:
    c.execute("ALTER TABLE orders ADD COLUMN payment TEXT DEFAULT 'No'")
except:
    pass

try:
    c.execute("ALTER TABLE orders ADD COLUMN tracking TEXT")
except:
    pass

conn.commit()

# ---------------- BACKGROUND ----------------
def set_bg():
    if os.path.exists("images/logo.png"):
        with open("images/logo.png", "rb") as f:
            data = base64.b64encode(f.read()).decode()

        st.markdown(f"""
        <style>
        .stApp {{
            background-image: url("data:image/png;base64,{data}");
            background-size: 250px;
            background-repeat: no-repeat;
            background-position: center;
        }}
        </style>
        """, unsafe_allow_html=True)

set_bg()

# ---------------- UI ----------------
st.title("🌸 Sajai Tomay")
mode = st.sidebar.selectbox("Login Type", ["Customer", "Admin"])

# ================= ADMIN =================
if mode == "Admin":

    password = st.sidebar.text_input("Password", type="password")

    if password == "admin123":

        st.header("Admin Panel")

        # AUTO REFRESH
        if "last_refresh" not in st.session_state:
            st.session_state.last_refresh = time.time()

        if time.time() - st.session_state.last_refresh > 5:
            st.session_state.last_refresh = time.time()
            st.rerun()

        # ADD PRODUCT
        st.subheader("Add Product")
        name = st.text_input("Name")
        cost = st.number_input("Cost", 0)
        stock = st.number_input("Stock", 0)
        image = st.file_uploader("Image")

        if st.button("Add"):
            if image:
                os.makedirs("images", exist_ok=True)
                path = f"images/{image.name}"
                with open(path, "wb") as f:
                    f.write(image.getbuffer())

                c.execute("INSERT INTO products VALUES (NULL,?,?,?,?)",
                          (name, cost, stock, image.name))
                conn.commit()
                st.success("Added")

        # PRODUCTS
        st.subheader("Products")
        products = c.execute("SELECT * FROM products").fetchall()

        for p in products:
            st.write(f"{p[1]} | ₹{p[2]} | Stock {p[3]}")

        # STOCK UPDATE
        st.subheader("Update Stock")
        for p in products:
            new_stock = st.number_input(f"{p[1]}", 0, key=f"s{p[0]}")
            if st.button(f"Update {p[0]}"):
                c.execute("UPDATE products SET stock=? WHERE id=?", (new_stock, p[0]))
                conn.commit()
                st.rerun()

        # DELIVERY DASHBOARD
        st.subheader("Delivery Dashboard")

        orders = c.execute("SELECT * FROM orders").fetchall()
        total_sales = 0

        for o in orders:
            total_sales += o[6]

            col1, col2, col3, col4 = st.columns([2,3,3,2])

            with col1:
                payment = st.selectbox(
                    f"Payment {o[0]}",
                    ["Yes", "No"],
                    index=0 if o[8] == "Yes" else 1,
                    key=f"pay_{o[0]}"
                )

            with col2:
                tracking = st.text_input(
                    f"Tracking {o[0]}",
                    value=o[9] if o[9] else "",
                    key=f"track_{o[0]}"
                )

            with col3:
                st.write(f"""
                👤 {o[1]}  
                📞 {o[2]}  
                📍 {o[3]}  
                🛍 {o[4]} x{o[5]} = ₹{o[6]}
                """)

            with col4:
                if st.button(f"Update {o[0]}"):
                    c.execute(
                        "UPDATE orders SET payment=?, tracking=? WHERE id=?",
                        (payment, tracking, o[0])
                    )
                    conn.commit()
                    st.success("Updated ✅")
                    st.rerun()

        st.write(f"### 💰 Total Sales: ₹{total_sales}")

        # STATUS UPDATE
        st.subheader("Update Order Status")
        for o in orders:
            if st.button(f"Mark Delivered {o[0]}"):
                c.execute("UPDATE orders SET status='Delivered' WHERE id=?", (o[0],))
                conn.commit()
                st.rerun()

    else:
        st.warning("Wrong password")

# ================= CUSTOMER =================
else:

    st.subheader("Products")
    products = c.execute("SELECT * FROM products").fetchall()

    if "cart" not in st.session_state:
        st.session_state.cart = []

    for p in products:
        img_path = f"images/{p[4]}"
        if os.path.exists(img_path):
            st.image(img_path, width=200)

        st.write(f"{p[1]} ₹{p[2]} Stock {p[3]}")
        qty = st.number_input(f"Qty {p[0]}", 1, int(p[3]), key=f"q{p[0]}")

        if st.button(f"Add {p[0]}"):
            st.session_state.cart.append((p, qty))

    # CART
    st.subheader("Cart")
    total = 0
    order_text = ""

    for p, q in st.session_state.cart:
        item_total = p[2] * q
        total += item_total
        order_text += f"{p[1]} x {q} = ₹{item_total}\n"
        st.write(f"{p[1]} x {q} = ₹{item_total}")

    st.write(f"Total ₹{total}")

    # CUSTOMER DETAILS
    name = st.text_input("Name")
    phone = st.text_input("Phone")
    addr = st.text_area("Address")

    # PLACE ORDER
    if st.button("Place Order"):

        order_ids = []

        for p,q in st.session_state.cart:
            c.execute("INSERT INTO orders VALUES (NULL,?,?,?,?,?,?,?)",
                      (name, phone, addr, p[1], q, p[2]*q, "Pending"))
            order_ids.append(c.lastrowid)

            c.execute("UPDATE products SET stock=? WHERE id=?", (p[3]-q, p[0]))

        conn.commit()

        order_id = order_ids[-1] if order_ids else "N/A"

        msg = f"""
🌸 Sajai Tomay Order 🌸

🆔 Order ID: {order_id}

👤 Name: {name}
📞 Phone: {phone}
📍 Address: {addr}

🛍 Items:
{order_text}

💰 Total: ₹{total}

Thank you for shopping with us ❤️
"""

        st.session_state.done = True
        st.session_state.msg = msg

    # AFTER ORDER
    if "done" in st.session_state and st.session_state.done:

        msg = st.session_state.msg
        encoded = urllib.parse.quote(msg)

        st.success("Order placed")
        st.toast("🆕 New Order Ready to Send!", icon="🔔")

        st.markdown(f"[📩 Send Order](https://wa.me/917003884969?text={encoded})")

        pdf = "invoice.pdf"
        doc = SimpleDocTemplate(pdf)
        styles = getSampleStyleSheet()
        doc.build([Paragraph(msg, styles["Normal"])])

        with open(pdf, "rb") as f:
            st.download_button("Download Invoice", f)

        if st.button("Next Order"):
            st.session_state.cart = []
            st.session_state.done = False
            st.rerun()