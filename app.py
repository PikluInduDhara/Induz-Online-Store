import streamlit as st
import sqlite3
import os
import urllib.parse
import pandas as pd
import time
import base64
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
for query in [
    "ALTER TABLE orders ADD COLUMN status TEXT DEFAULT 'Pending'",
    "ALTER TABLE orders ADD COLUMN payment TEXT DEFAULT 'No'",
    "ALTER TABLE orders ADD COLUMN tracking TEXT",
    "ALTER TABLE orders ADD COLUMN payment_ref TEXT",
    "ALTER TABLE orders ADD COLUMN delivery_ref TEXT",
    "ALTER TABLE orders ADD COLUMN order_date TEXT"
]:
    try:
        c.execute(query)
    except:
        pass

conn.commit()

# ---------------- HEADER ----------------
col1, col2 = st.columns([2,6])

with col1:
    if os.path.exists("images/logo.png"):
        st.image("images/logo.png", width=120)

with col2:
    st.markdown("""
    <h1 style='color:#d63384; font-size:42px; margin-bottom:0px;'>
        🌸 Sajai Tomay
    </h1>
    <p style='color:gray; font-size:18px; margin-top:0px;'>
        Elegant Collection • Simple Ordering
    </p>
    """, unsafe_allow_html=True)

# ---------------- WATERMARK ----------------
if os.path.exists("images/logo.png"):
    with open("images/logo.png", "rb") as f:
        data = base64.b64encode(f.read()).decode()

    st.markdown(f"""
    <style>
    .stApp {{
        background-image: url("data:image/png;base64,{data}");
        background-repeat: no-repeat;
        background-position: center;
        background-size: 300px;
        opacity: 0.97;
    }}
    </style>
    """, unsafe_allow_html=True)

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
            if st.button(f"Update {p[0]}", key=f"stock_{p[0]}"):
                c.execute("UPDATE products SET stock=? WHERE id=?", (new_stock, p[0]))
                conn.commit()
                st.rerun()

        # DELIVERY DASHBOARD
        st.subheader("Delivery Dashboard")

        orders = c.execute("SELECT * FROM orders").fetchall()
        total_sales = 0
        export_data = []

        headers = ["Order ID","Date","Customer","Phone","Address","Product","Qty","Value","Payment","Status","Pay Ref","Delivery Ref"]
        cols = st.columns(len(headers))
        for col, h in zip(cols, headers):
            col.write(f"**{h}**")

        for o in orders:
            total_sales += o[6]

            c1,c2,c3,c4,c5,c6,c7,c8,c9,c10,c11,c12 = st.columns(12)

            c1.write(o[0])
            c2.write(o[12] if len(o)>12 else "")
            c3.write(o[1])
            c4.write(o[2])
            c5.write(o[3])
            c6.write(o[4])
            c7.write(o[5])
            c8.write(o[6])

            payment = c9.selectbox("", ["Yes","No"],
                                   index=0 if len(o)>8 and o[8]=="Yes" else 1,
                                   key=f"pay_{o[0]}")

            status = c10.selectbox("", ["Pending","Accepted","Cancelled"],
                                   key=f"status_{o[0]}")

            payment_ref = c11.text_input("", value=o[10] if len(o)>10 else "", key=f"ref_{o[0]}")
            delivery_ref = c12.text_input("", value=o[11] if len(o)>11 else "", key=f"dref_{o[0]}")

            if st.button(f"Save {o[0]}", key=f"save_{o[0]}"):

                if status == "Cancelled":
                    c.execute("UPDATE products SET stock = stock + ? WHERE name=?", (o[5], o[4]))

                c.execute("""
                UPDATE orders 
                SET payment=?, status=?, payment_ref=?, delivery_ref=? 
                WHERE id=?
                """, (payment, status, payment_ref, delivery_ref, o[0]))

                conn.commit()
                st.rerun()

            export_data.append({
                "Order ID": o[0],
                "Date": o[12] if len(o)>12 else "",
                "Customer": o[1],
                "Phone": o[2],
                "Address": o[3],
                "Product": o[4],
                "Qty": o[5],
                "Value": o[6],
                "Payment": o[8] if len(o)>8 else "",
                "Status": o[7],
                "Payment Ref": o[10] if len(o)>10 else "",
                "Delivery Ref": o[11] if len(o)>11 else ""
            })

        st.write(f"### 💰 Total Sales: ₹{total_sales}")

        if export_data:
            df = pd.DataFrame(export_data)
            st.download_button("📥 Export to Excel",
                               df.to_csv(index=False).encode("utf-8"),
                               "orders.csv",
                               "text/csv")

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

        if st.button(f"Add {p[0]}", key=f"add_{p[0]}"):
            st.session_state.cart.append((p, qty))

    st.subheader("Cart")
    total = 0
    order_text = ""

    for p, q in st.session_state.cart:
        item_total = p[2] * q
        total += item_total
        order_text += f"{p[1]} x {q} = ₹{item_total}\n"
        st.write(f"{p[1]} x {q} = ₹{item_total}")

    st.write(f"Total ₹{total}")

    name = st.text_input("Name")
    phone = st.text_input("Phone")
    addr = st.text_area("Address")

    if st.button("Place Order"):

        if not name or not phone or not addr:
            st.error("Please fill all details")
        elif len(phone) != 10 or not phone.isdigit():
            st.error("Enter valid 10 digit phone number")
        elif len(addr) < 6:
            st.error("Enter full address with PIN code")
        else:

            order_ids = []

            for p,q in st.session_state.cart:
                c.execute("""
                INSERT INTO orders (customer, phone, address, product, quantity, total, status, order_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (name, phone, addr, p[1], q, p[2]*q, "Pending", time.strftime("%Y-%m-%d")))

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
