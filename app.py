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
col1, col2 = st.columns([3,5])

with col1:
    if os.path.exists("images/logo.png"):
        st.image("images/logo.png", width=220)

with col2:
    st.markdown(
        "<h1 style='color:#d63384; font-size:42px; margin-top:30px;'>🌸 Sajai Tomay</h1>",
        unsafe_allow_html=True
    )

mode = st.sidebar.selectbox("Login Type", ["Customer", "Admin"])

# ================= ADMIN =================
if mode == "Admin":

    password = st.sidebar.text_input("Password", type="password")

    if password == "admin123":

        st.header("Admin Panel")

        # -------- ADD PRODUCT --------
        st.subheader("➕ Add Product")

        new_name = st.text_input("Product Name")
        new_price = st.text_input("Price")
        new_stock = st.number_input("Stock", 0, 1000)
        new_category = st.text_input("Category (optional)")

        uploaded_file = st.file_uploader("Upload Product Image", type=["png","jpg","jpeg"])

        if st.button("Add Product"):

            if new_name and new_price:

                image_name = ""

                if uploaded_file is not None:
                    image_name = uploaded_file.name
                    os.makedirs("images", exist_ok=True)
                    with open(os.path.join("images", image_name), "wb") as f:
                        f.write(uploaded_file.getbuffer())

                products_sheet.append_row([
                    len(products_sheet.get_all_records())+1,
                    new_name,
                    new_price,
                    new_stock,
                    image_name,
                    new_category
                ])

                st.success("Product Added")
                st.rerun()

        # -------- PRODUCTS --------
        st.subheader("Products")
        products = products_sheet.get_all_records()

        for i, p in enumerate(products, start=2):

            col1, col2, col3, col4 = st.columns([3,2,2,2])

            img_path = f"images/{p.get('image','')}"
            if os.path.exists(img_path):
                col1.image(img_path, width=80)

            col1.write(f"{p['name']} ₹{p['cost']}")

            new_stock = col2.number_input("Stock", value=int(p["stock"]), key=f"s{i}")

            if col3.button("Update", key=f"u{i}"):
                products_sheet.update_cell(i, 4, new_stock)
                st.cache_data.clear()
                st.rerun()

            if col4.button("Delete", key=f"d{i}"):
                products_sheet.delete_rows(i)
                st.cache_data.clear()
                st.rerun()

        if st.button("🔄 Refresh"):
            st.cache_data.clear()
            st.rerun()

        # -------- DELIVERY DASHBOARD --------
        st.subheader("Delivery Dashboard")

        orders = orders_sheet.get_all_records()
        total_sales = 0

        headers = ["ID","Date","Customer","Phone","Address","Product","Qty","Value","Payment","Pay Ref","Del Ref","Status"]
        cols = st.columns(len(headers))

        for col, h in zip(cols, headers):
            col.write(f"**{h}**")

        for i, o in enumerate(orders, start=2):

            # ✅ ONLY CHANGE (Sales logic)
            if o["status"] == "Accepted":
                total_sales += int(o["total"])

            c = st.columns(len(headers))

            c[0].write(o["id"])
            c[1].write(o["order_date"])
            c[2].write(o["customer"])
            c[3].write(o["phone"])
            c[4].write(o["address"])
            c[5].write(o["product"])
            c[6].write(o["quantity"])
            c[7].write(o["total"])

            payment = c[8].selectbox("", ["Yes","No"],
                index=0 if o["payment"]=="Yes" else 1, key=f"pay{i}")

            pay_ref = c[9].text_input("", value=o.get("payment_ref",""), key=f"pref{i}")
            del_ref = c[10].text_input("", value=o.get("delivery_ref",""), key=f"dref{i}")

            if o["status"] == "Cancelled":
                status = c[11].selectbox("", ["Cancelled"], key=f"status{i}")
            else:
                status = c[11].selectbox("", ["Pending","Accepted","Cancelled"], key=f"status{i}")

            if st.button(f"Save {i}"):

                products_latest = products_sheet.get_all_records()

                if status == "Cancelled" and o["status"] != "Cancelled":
                    for j, p in enumerate(products_latest, start=2):
                        if p["name"] == o["product"]:
                            new_stock = int(p["stock"]) + int(o["quantity"])
                            products_sheet.update_cell(j, 4, new_stock)

                orders_sheet.update_cell(i, 9, payment)
                orders_sheet.update_cell(i, 10, pay_ref)
                orders_sheet.update_cell(i, 11, del_ref)
                orders_sheet.update_cell(i, 8, status)

                st.cache_data.clear()
                st.rerun()

        st.write(f"### 💰 Total Sales: ₹{total_sales}")

# ================= CUSTOMER =================
else:

    st.subheader("Products")

    products = products_sheet.get_all_records()
    products = pd.DataFrame(products).to_dict("records")
    # 🔥 SEARCH BAR
    search_text = st.text_input("🔍 Search Product")

    # 🔥 CATEGORY BUTTONS (VISIBLE LIKE AMAZON)
    categories = list(set([p.get("category","All") for p in products]))
    selected_category = st.selectbox("Category", ["All"] + categories, horizontal=True)
    categories = list(set([p.get("category","All") for p in products]))
    selected_category = st.selectbox("Category", ["All"] + categories)

    if "cart" not in st.session_state:
        st.session_state.cart = []

    if "order_done" not in st.session_state:
        st.session_state.order_done = False

    for p in products:

          # 🔥 CATEGORY FILTER
        if selected_category != "All" and p.get("category") != selected_category:
         continue

        # 🔥 SEARCH FILTER
        if search_text and search_text.lower() not in p["name"].lower():
            continue
        img_path = f"images/{p.get('image','')}"
        if os.path.exists(img_path):
            st.image(img_path, width=200)

        st.write(f"{p['name']} ₹{p['cost']} Stock {p['stock']}")

        qty = st.number_input(f"Qty {p['id']}", 1, int(p['stock']), key=f"q{p['id']}")

        if st.button(f"Add {p['id']}"):
            st.session_state.cart.append((p, qty))

    # -------- CART --------
    st.subheader("Cart")

    total = 0
    order_text = ""

    for idx, (p, q) in enumerate(st.session_state.cart):

        col1, col2 = st.columns([4,1])

        item_total = int(p['cost']) * q
        total += item_total
        order_text += f"{p['name']} x {q} = ₹{item_total}\n"

        col1.write(f"{p['name']} x {q} = ₹{item_total}")

        if col2.button("❌", key=f"rem{idx}"):
            st.session_state.cart.pop(idx)
            st.rerun()

    st.write(f"Total ₹{total}")

    name = st.text_input("Name")
    phone = st.text_input("Phone")
    addr = st.text_area("Address")

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

                products_latest = products_sheet.get_all_records()

                for i, prod in enumerate(products_latest, start=2):
                    if prod["name"] == p["name"]:
                        new_stock = max(0, int(prod["stock"]) - q)
                        products_sheet.update_cell(i, 4, new_stock)

            st.cache_data.clear()

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

            st.session_state.order_done = True
            st.session_state.order_message = message
            st.session_state.cart = []

            st.rerun()

    if st.session_state.order_done:

        message = st.session_state.order_message
        url = "https://wa.me/917003884969?text=" + urllib.parse.quote(message)

        st.success("Order placed successfully!")
        st.markdown(f"[📲 Send Order to Admin]({url})")

        doc = SimpleDocTemplate("invoice.pdf")
        styles = getSampleStyleSheet()

        doc.build([
            Paragraph("Invoice", styles["Title"]),
            Paragraph(message, styles["Normal"])
        ])

        with open("invoice.pdf", "rb") as f:
            st.download_button("📄 Download Invoice", f, "invoice.pdf")

        if st.button("🛒 Next Order"):
            st.session_state.order_done = False
            st.rerun()