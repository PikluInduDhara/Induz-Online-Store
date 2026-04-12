import streamlit as st
import os
import urllib.parse
import pandas as pd
import time
import base64
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

st.set_page_config(page_title="Sajai Tomay", layout="wide")

# ---------------- GOOGLE SHEET ----------------
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_dict(
    st.secrets["gcp_service_account"], scope
)
client = gspread.authorize(creds)

sheet = client.open("SajaiTomayDB")
products_sheet = sheet.worksheet("products")
orders_sheet = sheet.worksheet("orders")

# ---------------- HEADER ----------------
col1, col2 = st.columns([2,6])

with col1:
    if os.path.exists("images/logo.png"):
        st.image("images/logo.png", width=120)

with col2:
    st.markdown("""
    <h1 style='color:#d63384;'>🌸 Sajai Tomay</h1>
    """, unsafe_allow_html=True)

mode = st.sidebar.selectbox("Login Type", ["Customer", "Admin"])

# ================= ADMIN =================
if mode == "Admin":

    password = st.sidebar.text_input("Password", type="password")

    if password == "admin123":

        st.header("Admin Panel")

        # -------- ADD PRODUCT --------
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

                products = products_sheet.get_all_records()
                products_sheet.append_row([
                    len(products)+1, name, cost, stock, image.name
                ])
                st.success("Added")

        # -------- PRODUCTS (INLINE CONTROL) --------
        st.subheader("Products")

        products = products_sheet.get_all_records()

        for i, p in enumerate(products, start=2):

            col1, col2, col3, col4 = st.columns([3,2,2,2])

            col1.write(f"{p['name']} ₹{p['cost']}")

            new_stock = col2.number_input(
                "Stock", value=int(p["stock"]), key=f"s{i}"
            )

            if col3.button("Update", key=f"u{i}"):
                products_sheet.update_cell(i, 4, new_stock)
                st.rerun()

            if col4.button("Delete", key=f"d{i}"):
                products_sheet.delete_rows(i)
                st.rerun()

        # -------- REFRESH --------
        if st.button("🔄 Refresh"):
            st.rerun()

        # -------- DELIVERY DASHBOARD --------
        st.subheader("Delivery Dashboard")

        orders = orders_sheet.get_all_records()
        total_sales = 0

        headers = ["ID","Date","Customer","Phone","Product","Qty","Value","Payment","Status"]
        cols = st.columns(len(headers))

        for col, h in zip(cols, headers):
            col.write(f"**{h}**")

        for i, o in enumerate(orders, start=2):

            total_sales += int(o["total"])

            c = st.columns(len(headers))

            c[0].write(o["id"])
            c[1].write(o["order_date"])
            c[2].write(o["customer"])
            c[3].write(o["phone"])
            c[4].write(o["product"])
            c[5].write(o["quantity"])
            c[6].write(o["total"])

            payment = c[7].selectbox(
                "", ["Yes","No"],
                index=0 if o["payment"]=="Yes" else 1,
                key=f"pay{i}"
            )

            status = c[8].selectbox(
                "", ["Pending","Accepted","Cancelled"],
                key=f"status{i}"
            )

            if st.button(f"Save {i}"):

                # STOCK RETURN IF CANCELLED
                if status == "Cancelled":
                    for j, p in enumerate(products, start=2):
                        if p["name"] == o["product"]:
                            new_stock = int(p["stock"]) + int(o["quantity"])
                            products_sheet.update_cell(j, 4, new_stock)

                orders_sheet.update_cell(i, 9, payment)
                orders_sheet.update_cell(i, 8, status)

                st.rerun()

        st.write(f"### 💰 Total Sales: ₹{total_sales}")

# ================= CUSTOMER =================
else:

    st.subheader("Products")

    products = products_sheet.get_all_records()

    if "cart" not in st.session_state:
        st.session_state.cart = []

    for p in products:

        img_path = f"images/{p['image']}"
        if os.path.exists(img_path):
            st.image(img_path, width=200)

        st.write(f"{p['name']} ₹{p['cost']} Stock {p['stock']}")

        qty = st.number_input(
            f"Qty {p['id']}", 1, int(p['stock']), key=f"q{p['id']}"
        )

        if st.button(f"Add {p['id']}"):
            st.session_state.cart.append((p, qty))

    # -------- CART --------
    st.subheader("Cart")

    total = 0
    order_text = ""

    for p, q in st.session_state.cart:
        item_total = int(p['cost']) * q
        total += item_total
        order_text += f"{p['name']} x {q} = ₹{item_total}\n"
        st.write(f"{p['name']} x {q} = ₹{item_total}")

    st.write(f"Total ₹{total}")

    name = st.text_input("Name")
    phone = st.text_input("Phone")
    addr = st.text_area("Address")

    # -------- PLACE ORDER --------
    if st.button("Place Order"):

        if not name or not phone or not addr:
            st.error("Fill all details")

        elif len(phone) != 10:
            st.error("Invalid phone")

        else:

            orders = orders_sheet.get_all_records()
            order_id = len(orders) + 1

            for p, q in st.session_state.cart:

                item_total = int(p["cost"]) * q

                orders_sheet.append_row([
                    order_id,
                    name, phone, addr,
                    p["name"], q, item_total,
                    "Pending", "No", "", "", time.strftime("%Y-%m-%d")
                ])

                # STOCK REDUCE
                for i, prod in enumerate(products, start=2):
                    if prod["name"] == p["name"]:
                        new_stock = int(prod["stock"]) - q
                        products_sheet.update_cell(i, 4, new_stock)

            # -------- WHATSAPP --------
            message = f"""
🌸 Sajai Tomay Order 🌸

🆔 Order ID: {order_id}

👤 Name: {name}
📞 Phone: {phone}
📍 Address: {addr}

🛒 Items:
{order_text}

💰 Total: ₹{total}
"""

            url = "https://wa.me/917003884969?text=" + urllib.parse.quote(message)

            st.success("Order placed")
            st.markdown(f"[📲 Send to Admin]({url})")

            # -------- INVOICE --------
            doc = SimpleDocTemplate("invoice.pdf")
            styles = getSampleStyleSheet()

            doc.build([
                Paragraph("Invoice", styles["Title"]),
                Paragraph(message, styles["Normal"])
            ])

            with open("invoice.pdf", "rb") as f:
                st.download_button("📄 Download Invoice", f, "invoice.pdf")

            st.session_state.cart = []