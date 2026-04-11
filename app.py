## ✅ FINAL STABLE VERSION WITH EXTRA FEATURES

import streamlit as st
import sqlite3
import os
import base64
import urllib.parse
import pandas as pd
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
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

# SAFE TABLE CREATION (FIX FOR EXISTING DB)
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

# ADD STATUS COLUMN IF NOT EXISTS (IMPORTANT FIX)
try:
    c.execute("ALTER TABLE orders ADD COLUMN status TEXT DEFAULT 'Pending'")
except:
    pass

conn.commit()

# ---------------- UI ----------------
st.title("🌸 Sajai Tomay")
mode = st.sidebar.selectbox("Login Type", ["Customer", "Admin"])

# ================= ADMIN =================
if mode == "Admin":
    password = st.sidebar.text_input("Password", type="password")

    if password == "admin123":

        st.header("Admin Panel")

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

        # PRODUCT LIST
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

        # ORDERS
        st.subheader("Delivery Dashboard")
        orders = c.execute("SELECT * FROM orders").fetchall()

        data = []
        total_sales = 0

        for i, o in enumerate(orders, 1):
            total_sales += o[6]
            data.append({
                "Sl": i,
                "Customer": o[1],
                "Phone": o[2],
                "Address": o[3],
                "Product": o[4],
                "Qty": o[5],
                "Value": o[6],
                "Status": o[7]
            })

        if data:
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True)

            st.write(f"### 💰 Total Sales: ₹{total_sales}")

        # STATUS UPDATE
        st.subheader("Update Order Status")
        for o in orders:
            if st.button(f"Mark Delivered {o[0]}"):
                c.execute("UPDATE orders SET status='Delivered' WHERE id=?", (o[0],))
                conn.commit()
                st.rerun()

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
        st.write(f"{p[1]} ₹{p[2]} Stock {p[3]}")
        qty = st.number_input(f"Qty {p[0]}", 1, int(p[3]), key=f"q{p[0]}")

        if st.button(f"Add {p[0]}"):
            st.session_state.cart.append((p, qty))

    st.subheader("Cart")
    total = 0
    order_text = ""

    for p, q in st.session_state.cart:
        total += p[2]*q
        order_text += f"{p[1]} x {q}\n"
        st.write(f"{p[1]} x {q}")

    st.write(f"Total ₹{total}")

    name = st.text_input("Name")
    phone = st.text_input("Phone")
    addr = st.text_area("Address")

    if st.button("Place Order"):
        msg = f"Order\n{name}\n{phone}\n{addr}\n{order_text}Total ₹{total}"

        for p,q in st.session_state.cart:
            c.execute("INSERT INTO orders VALUES (NULL,?,?,?,?,?,?,?)",
                      (name, phone, addr, p[1], q, p[2]*q, "Pending"))
            c.execute("UPDATE products SET stock=? WHERE id=?", (p[3]-q, p[0]))

        conn.commit()

        st.session_state.done = True
        st.session_state.msg = msg

    if "done" in st.session_state and st.session_state.done:
        msg = st.session_state.msg
        encoded = urllib.parse.quote(msg)

        st.success("Order placed")
        st.markdown(f"[Send WhatsApp](https://wa.me/?text={encoded})")

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
