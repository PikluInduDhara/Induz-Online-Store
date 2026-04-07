import streamlit as st
import pandas as pd
import sqlite3
import os
import base64
from datetime import datetime

# ---------------- DB ----------------
conn = sqlite3.connect("store.db", check_same_thread=False)
c = conn.cursor()

c.execute('''
CREATE TABLE IF NOT EXISTS orders (
id INTEGER PRIMARY KEY AUTOINCREMENT,
customer TEXT,
phone TEXT,
address TEXT,
product TEXT,
qty INTEGER,
total INTEGER,
date TEXT
)
''')

c.execute('''
CREATE TABLE IF NOT EXISTS products (
id INTEGER PRIMARY KEY AUTOINCREMENT,
name TEXT,
cost INTEGER,
stock INTEGER,
image TEXT
)
''')

conn.commit()

# ---------------- LOAD EXCEL ----------------
def load_products():
    df = pd.read_excel("products.xlsx")
    return df

# ---------------- LOGO BACKGROUND ----------------
def add_bg():
    with open("images/logo.png", "rb") as f:
        data = f.read()
    b64 = base64.b64encode(data).decode()

    st.markdown(f"""
    <style>
    .stApp {{
        background-image: url("data:image/png;base64,{b64}");
        background-size: 300px;
        background-repeat: no-repeat;
        background-position: center;
        background-attachment: fixed;
    }}
    </style>
    """, unsafe_allow_html=True)

add_bg()

# ---------------- TITLE ----------------
st.title("🌸 Sajai Tomay")

# ---------------- LOGIN ----------------
login = st.sidebar.selectbox("Login Type", ["Customer", "Admin"])

# ---------------- CUSTOMER ----------------
if login == "Customer":

    df = load_products()

    st.subheader("🛍️ Our Collection")

    cart = []

    cols = st.columns(3)

    for i, row in df.iterrows():
        with cols[i % 3]:
            st.image(f"images/{row['Image']}", use_column_width=True)
            st.write(f"**{row['ProductName']}**")
            st.write(f"₹{row['CostPrice']}")
            st.write(f"Stock: {row['Stock']}")

            qty = st.number_input(f"Qty {i}", min_value=1, value=1, key=f"qty_{i}")

            if st.button(f"Add {i}"):
                cart.append((row['ProductName'], qty, row['CostPrice']))

    # ---------------- CUSTOMER DETAILS ----------------
    st.subheader("👤 Customer Details")

    name = st.text_input("Name")
    phone = st.text_input("Phone")
    address = st.text_area("Address")

    if st.button("Place Order"):

        total = 0

        for item in cart:
            total += item[1] * item[2]

        for item in cart:
            c.execute(
                "INSERT INTO orders (customer, phone, address, product, qty, total, date) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (name, phone, address, item[0], item[1], item[1]*item[2], str(datetime.now()))
            )

            # STOCK UPDATE
            c.execute(
                "UPDATE products SET stock = stock - ? WHERE name=?",
                (item[1], item[0])
            )

        conn.commit()

        st.success("Order Placed Successfully ✅")

        st.experimental_rerun()

# ---------------- ADMIN ----------------
else:
    password = st.sidebar.text_input("Enter Admin Password", type="password")

    if password == "admin123":

        st.subheader("🛠️ Admin Panel")

        # ---------------- ADD PRODUCT ----------------
        st.subheader("➕ Add Product")

        name = st.text_input("Product Name")
        cost = st.number_input("Cost")
        stock = st.number_input("Stock")

        image = st.file_uploader("Upload Image")

        if st.button("Add Product"):

            if image:
                image_path = f"images/{image.name}"
                with open(image_path, "wb") as f:
                    f.write(image.getbuffer())

                c.execute(
                    "INSERT INTO products (name, cost, stock, image) VALUES (?, ?, ?, ?)",
                    (name, cost, stock, image.name)
                )
                conn.commit()

                st.success("Product Added ✅")

        # ---------------- PRODUCT LIST ----------------
        st.subheader("📋 Product List")

        products = c.execute("SELECT * FROM products").fetchall()

        for p in products:
            col1, col2, col3 = st.columns([3,2,1])

            with col1:
                st.write(f"{p[1]} | ₹{p[2]} | Stock: {p[3]}")

            with col2:
                new_stock = st.number_input(f"Edit Stock {p[0]}", value=p[3], key=f"s{p[0]}")
                if st.button(f"Update {p[0]}"):
                    c.execute("UPDATE products SET stock=? WHERE id=?", (new_stock, p[0]))
                    conn.commit()
                    st.success("Updated ✅")

            with col3:
                if st.button(f"Delete {p[0]}"):
                    c.execute("DELETE FROM products WHERE id=?", (p[0],))
                    conn.commit()
                    st.warning("Deleted ❌")

        # ---------------- ORDERS TABLE ----------------
        st.subheader("📦 Orders")

        orders = c.execute("SELECT * FROM orders").fetchall()

        df_orders = pd.DataFrame(orders, columns=[
            "ID", "Customer", "Phone", "Address", "Product", "Qty", "Total", "Date"
        ])

        st.dataframe(df_orders)

        st.button("🔄 Refresh Orders")

    else:
        st.error("Wrong Password ❌")