import streamlit as st
import sqlite3
import os
from PIL import Image
import base64

# ------------------ CONFIG ------------------
st.set_page_config(page_title="Sajai Tomay", layout="wide")

# ------------------ DATABASE ------------------
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
    product TEXT,
    quantity INTEGER,
    total INTEGER
)
""")

conn.commit()

# ------------------ BACKGROUND LOGO ------------------
def set_bg():
    if os.path.exists("images/logo.png"):
        with open("images/logo.png", "rb") as f:
            data = base64.b64encode(f.read()).decode()

        st.markdown(f"""
        <style>
        .stApp {{
            background-image: url("data:image/png;base64,{data}");
            background-size: 300px;
            background-repeat: no-repeat;
            background-position: center;
        }}
        </style>
        """, unsafe_allow_html=True)

set_bg()

# ------------------ TITLE ------------------
st.markdown("<h1 style='text-align:center;'>🌸 Sajai Tomay</h1>", unsafe_allow_html=True)

# ------------------ LOGIN ------------------
mode = st.sidebar.selectbox("Login Type", ["Customer", "Admin"])

# =========================================================
# ===================== ADMIN PANEL =======================
# =========================================================

if mode == "Admin":
    password = st.sidebar.text_input("Enter Admin Password", type="password")

    if password == "admin123":

        st.header("🛠 Admin Panel")

        # -------- ADD PRODUCT --------
        st.subheader("➕ Add Product")

        name = st.text_input("Product Name")
        cost = st.number_input("Cost", 0)
        stock = st.number_input("Stock", 0)
        image_file = st.file_uploader("Upload Image")

        if st.button("Add Product"):
            if image_file is not None:

                os.makedirs("images", exist_ok=True)

                image_path = f"images/{image_file.name}"
                with open(image_path, "wb") as f:
                    f.write(image_file.getbuffer())

                c.execute("INSERT INTO products (name, cost, stock, image) VALUES (?, ?, ?, ?)",
                          (name, cost, stock, image_file.name))
                conn.commit()

                st.success("Product Added ✅")

        # -------- DELETE PRODUCT --------
        st.subheader("🗑 Delete Product")

        products = c.execute("SELECT id, name FROM products").fetchall()
        product_dict = {p[1]: p[0] for p in products}

        selected = st.selectbox("Select Product", list(product_dict.keys()))

        if st.button("Delete"):
            c.execute("DELETE FROM products WHERE id=?", (product_dict[selected],))
            conn.commit()
            st.warning("Deleted ❌")

        # -------- VIEW ORDERS --------
        st.subheader("📦 All Orders")
        orders = c.execute("SELECT * FROM orders").fetchall()

        for o in orders:
            st.write(f"Customer: {o[1]} | Product: {o[2]} | Qty: {o[3]} | ₹{o[4]}")

    else:
        st.warning("Enter correct password")

# =========================================================
# ===================== CUSTOMER VIEW =====================
# =========================================================

else:

    st.subheader("🛍 Our Collection")

    products = c.execute("SELECT * FROM products").fetchall()

    cols = st.columns(3)

    cart = []

    for i, p in enumerate(products):
        with cols[i % 3]:
            image_path = f"images/{p[4]}"

            if os.path.exists(image_path):
                st.image(image_path)

            st.write(f"**{p[1]}**")
            st.write(f"₹{p[2]}")
            st.write(f"Stock: {p[3]}")

            qty = st.number_input(f"Qty {p[0]}", 1, int(p[3]), key=p[0])

            if st.button(f"Add {p[0]}"):
                cart.append((p, qty))

    # -------- ORDER --------
    st.subheader("🧾 Place Order")

    customer = st.text_input("Customer Name")

    if st.button("Place Order"):
        total = 0

        for p, qty in cart:
            total += p[2] * qty

            # STOCK UPDATE
            new_stock = p[3] - qty
            c.execute("UPDATE products SET stock=? WHERE id=?", (new_stock, p[0]))

            # SAVE ORDER
            c.execute("INSERT INTO orders (customer, product, quantity, total) VALUES (?, ?, ?, ?)",
                      (customer, p[1], qty, p[2]*qty))

        conn.commit()

        st.success("Order Placed ✅")

        st.markdown(f"""
        Hello {customer} 😊  
        Thank you for shopping with **Sajai Tomay** 🌸  
        Your order has been confirmed!
        """)
