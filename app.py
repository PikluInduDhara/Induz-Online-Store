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

# ---------------- GOOGLE SHEET DATABASE ----------------
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

# ✅ FIXED (Using Streamlit Secrets instead of file)
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

                products = products_sheet.get_all_records()
                products_sheet.append_row([
                    len(products)+1, name, cost, stock, image.name
                ])
                st.success("Added")

        # PRODUCTS
        st.subheader("Products")
        products = products_sheet.get_all_records()
        for p in products:
            st.write(f"{p['name']} | ₹{p['cost']} | Stock {p['stock']}")

        # STOCK UPDATE
        st.subheader("Update Stock")
        for i, p in enumerate(products, start=2):
            new_stock = st.number_input(f"{p['name']}", 0, key=f"s{i}")
            if st.button(f"Update {i}", key=f"stock_{i}"):
                products_sheet.update_cell(i, 4, new_stock)
                st.rerun()

        # DELIVERY DASHBOARD
        st.subheader("Delivery Dashboard")

        orders = orders_sheet.get_all_records()
        total_sales = 0
        export_data = []

        headers = ["Order ID","Date","Customer","Phone","Address","Product","Qty","Value","Payment","Status","Pay Ref","Delivery Ref"]
        cols = st.columns(len(headers))
        for col, h in zip(cols, headers):
            col.write(f"**{h}**")

        for i, o in enumerate(orders, start=2):
            total_sales += int(o["total"])

            c = st.columns(12)

            c[0].write(o["id"])
            c[1].write(o["order_date"])
            c[2].write(o["customer"])
            c[3].write(o["phone"])
            c[4].write(o["address"])
            c[5].write(o["product"])
            c[6].write(o["quantity"])
            c[7].write(o["total"])

            payment = c[8].selectbox("", ["Yes","No"],
                                    index=0 if o["payment"]=="Yes" else 1,
                                    key=f"pay_{i}")

            status = c[9].selectbox("", ["Pending","Accepted","Cancelled"],
                                   key=f"status_{i}")

            pay_ref = c[10].text_input("", o["payment_ref"], key=f"pref_{i}")
            del_ref = c[11].text_input("", o["delivery_ref"], key=f"dref_{i}")

            if st.button(f"Save {i}", key=f"save_{i}"):

                if status == "Cancelled":
                    for j, p in enumerate(products, start=2):
                        if p["name"] == o["product"]:
                            new_stock = int(p["stock"]) + int(o["quantity"])
                            products_sheet.update_cell(j, 4, new_stock)

                orders_sheet.update_cell(i, 9, payment)
                orders_sheet.update_cell(i, 8, status)
                orders_sheet.update_cell(i, 10, pay_ref)
                orders_sheet.update_cell(i, 11, del_ref)

                st.rerun()

            export_data.append(o)

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
    products = products_sheet.get_all_records()

    if "cart" not in st.session_state:
        st.session_state.cart = []

    for p in products:
        img_path = f"images/{p['image']}"
        if os.path.exists(img_path):
            st.image(img_path, width=200)

        st.write(f"{p['name']} ₹{p['cost']} Stock {p['stock']}")
        qty = st.number_input(f"Qty {p['id']}", 1, int(p['stock']), key=f"q{p['id']}")

        if st.button(f"Add {p['id']}", key=f"add_{p['id']}"):
            st.session_state.cart.append((p, qty))

    st.subheader("Cart")
    total = 0

    for p, q in st.session_state.cart:
        item_total = int(p['cost']) * q
        total += item_total
        st.write(f"{p['name']} x {q} = ₹{item_total}")

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

            orders = orders_sheet.get_all_records()

            for p,q in st.session_state.cart:
                orders_sheet.append_row([
                    len(orders)+1,
                    name, phone, addr,
                    p["name"], q, int(p["cost"])*q,
                    "Pending", "No", "", "", time.strftime("%Y-%m-%d")
                ])

            st.success("Order placed")