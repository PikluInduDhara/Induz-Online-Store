import streamlit as st
import sqlite3
import os
import base64
import urllib.parse
import pandas as pd
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet


# ---------------- CONFIG ----------------
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

conn.commit()

# ---------------- BACKGROUND LOGO ----------------
def set_bg():
    if os.path.exists("images/logo.png"):
        with open("images/logo.png", "rb") as f:
            data = base64.b64encode(f.read()).decode()

        st.markdown(f"""
        <style>
        .stApp {{
            background-image: url("data:image/png;base64,{data}");
            background-size: 280px;
            background-repeat: no-repeat;
            background-position: center;
            opacity: 0.97;
        }}
        </style>
        """, unsafe_allow_html=True)

set_bg()

# ---------------- TITLE ----------------
st.markdown("<h1 style='text-align:center;'>🌸 Sajai Tomay</h1>", unsafe_allow_html=True)

# ---------------- LOGIN ----------------
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
            if image_file:
                os.makedirs("images", exist_ok=True)

                path = f"images/{image_file.name}"
                with open(path, "wb") as f:
                    f.write(image_file.getbuffer())

                c.execute("INSERT INTO products (name, cost, stock, image) VALUES (?, ?, ?, ?)",
                          (name, cost, stock, image_file.name))
                conn.commit()

                st.success("Product Added ✅")

        # -------- PRODUCT LIST --------
        st.subheader("📋 Product List")

        products = c.execute("SELECT * FROM products").fetchall()

        for p in products:
            col1, col2 = st.columns([4,1])

            with col1:
                st.write(f"{p[1]} | ₹{p[2]} | Stock: {p[3]}")

            with col2:
                if st.button(f"Delete {p[0]}"):
                    c.execute("DELETE FROM products WHERE id=?", (p[0],))
                    conn.commit()
                    st.success("Deleted")
                    st.rerun()

        # -------- STOCK UPDATE --------
        st.subheader("📦 Update Stock")

        for p in products:
            col1, col2, col3 = st.columns([3,2,1])

            with col1:
                st.write(p[1])

            with col2:
                new_stock = st.number_input(f"New Stock for {p[1]}", 0, key=f"stock_{p[0]}")

            with col3:
                if st.button(f"Update {p[0]}"):
                    c.execute("UPDATE products SET stock=? WHERE id=?", (new_stock, p[0]))
                    conn.commit()
                    st.success(f"{p[1]} stock updated ✅")
                    st.rerun()

        # -------- DELIVERY DASHBOARD --------
        st.subheader("📦 Delivery Dashboard")

        orders = c.execute("SELECT * FROM orders").fetchall()

        if orders:
            data = []
            for i, o in enumerate(orders, start=1):
                data.append({
                    "Sl No": i,
                    "Customer Name": o[1],
                    "Phone": o[2],
                    "Address": o[3],
                    "Product": o[4],
                    "Qty": o[5],
                    "Invoice Value (₹)": o[6]
                })

            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True)

        # 🔥 AUTO REFRESH ADMIN (IMPORTANT FIX)
        st.rerun()

    else:
        st.warning("Enter correct password")

# =========================================================
# ===================== CUSTOMER VIEW =====================
# =========================================================
else:

    st.subheader("🛍 Our Collection")

    products = c.execute("SELECT * FROM products").fetchall()

    if "cart" not in st.session_state:
        st.session_state.cart = []

    cols = st.columns(3)

    for i, p in enumerate(products):
        with cols[i % 3]:

            img_path = f"images/{p[4]}"
            if os.path.exists(img_path):
                st.image(img_path)

            st.write(f"**{p[1]}**")
            st.write(f"₹{p[2]}")
            st.write(f"Stock: {p[3]}")

            qty = st.number_input(f"Qty {p[0]}", 1, int(p[3]), key=f"qty_{p[0]}")

            if st.button(f"Add {p[0]}"):
                st.session_state.cart.append((p, qty))
                st.success("Added to cart")

    # ---------------- CART ----------------
    st.subheader("🛒 Cart")

    total = 0
    order_text = ""

    for p, qty in st.session_state.cart:
        st.write(f"{p[1]} x {qty} = ₹{p[2]*qty}")
        total += p[2] * qty
        order_text += f"{p[1]} x {qty} = ₹{p[2]*qty}\n"

    st.write(f"### Total: ₹{total}")

    # ---------------- CHECKOUT ----------------
    st.subheader("🧾 Checkout")

    customer = st.text_input("Customer Name")
    phone = st.text_input("Phone Number")
    address = st.text_area("Delivery Address")

    if st.button("Place Order"):

        message = f"""
🌸 Sajai Tomay Order 🌸

👤 Name: {customer}
📞 Phone: {phone}
📍 Address: {address}

🛍 Items:
{order_text}

💰 Total: ₹{total}

Thank you for shopping with us ❤️
"""

        for p, qty in st.session_state.cart:
            new_stock = p[3] - qty
            c.execute("UPDATE products SET stock=? WHERE id=?", (new_stock, p[0]))

            c.execute("INSERT INTO orders (customer, phone, address, product, quantity, total) VALUES (?, ?, ?, ?, ?, ?)",
                      (customer, phone, address, p[1], qty, p[2]*qty))

        conn.commit()

        # 🔥 IMPORTANT FIX: DO NOT RERUN HERE
        st.session_state.order_done = True
        st.session_state.last_message = message

    # ✅ SHOW AFTER ORDER (PERSIST FIX)
    if "order_done" in st.session_state and st.session_state.order_done:

        message = st.session_state.last_message
        encoded = urllib.parse.quote(message)

        st.success("Order Placed ✅")

        st.markdown("### 📲 Send Order to WhatsApp")
        st.markdown(f"[👉 Send to 7003884969](https://wa.me/917003884969?text={encoded})")
        st.markdown(f"[👉 Send to 7980238789](https://wa.me/917980238789?text={encoded})")

        pdf_file = "invoice.pdf"
        doc = SimpleDocTemplate(pdf_file)
        styles = getSampleStyleSheet()

        elements = []
        elements.append(Paragraph("Sajai Tomay Invoice", styles["Title"]))
        elements.append(Spacer(1, 10))
        elements.append(Paragraph(message, styles["Normal"]))

        doc.build(elements)

        with open(pdf_file, "rb") as f:
            st.download_button("📄 Download Invoice", f, file_name="invoice.pdf")

        st.markdown(f"""
        ### 🎉 Order Confirmed!

        Hello 😊  
        Your order has been placed successfully.

        🚚 Delivery coming soon  
        💖 Thank you for choosing Sajai Tomay!
        """)

        if st.button("Clear Order"):
            st.session_state.cart = []
            st.session_state.order_done = False
            st.rerun()
