import streamlit as st
import os
import urllib.parse
import pandas as pd
import time
import base64
import gspread
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib import colors
from oauth2client.service_account import ServiceAccountCredentials
from reportlab.lib.styles import getSampleStyleSheet
def get_image_url(img):
    if "drive.google.com" in img:
        try:
            file_id = img.split("/d/")[1].split("/")[0]
            return f"https://lh3.googleusercontent.com/d/{file_id}"
        except:
            return img
    return f"images/{img}"

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
        new_sizes = st.text_input("Sizes (comma separated: S,M,L,XL)")

        uploaded_files = st.file_uploader(
            "Upload Product Images",
            type=["png","jpg","jpeg"],
            accept_multiple_files=True
        )

        if st.button("Add Product"):

            if new_name and new_price:

                image_names = []

                if uploaded_files:
                    os.makedirs("images", exist_ok=True)

                    for file in uploaded_files:
                        filename = file.name
                        image_names.append(filename)

                        with open(os.path.join("images", filename), "wb") as f:
                            f.write(file.getbuffer())

                image_name = ",".join(image_names)
                products_sheet.append_row([
                    len(products_sheet.get_all_records())+1,
                    new_name,
                    new_price,
                    new_stock,
                    image_name,
                    new_category,
                    new_sizes
                ])

                st.success("Product Added")
                st.rerun()

        # -------- PRODUCTS --------
        st.subheader("Products")
        products = products_sheet.get_all_records()

        for i, p in enumerate(products, start=2):

            col1, col2, col3, col4 = st.columns([3,2,2,2])

            images = [img.strip() for img in p.get("image","").split(",") if img.strip()]

            if images:
                cols = st.columns(3)   # fixed 3 per row (clean look)

                for j, img in enumerate(images):
                    cols[j % 3].image(get_image_url(img), width=120)
            col1.write(f"{p['name']} ₹{p['cost']}")
            col1.write(f"Sizes: {p.get('size','')}")

            stock_value = int(p.get("stock", 0) or 0)

            new_stock = col2.number_input(
                "Stock",
                min_value=0,
                value=stock_value,
                key=f"s_{i}"
            )

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
    selected_category = st.radio("Category", ["All"] + categories, horizontal=True)

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

        images = [img.strip() for img in p.get("image","").split(",") if img.strip()]

        col_img, col_info = st.columns([1,2])

        with col_img:
            if images:
                cols = st.columns(min(len(images), 3))
                for i, img in enumerate(images[:3]):
                    cols[i].image(get_image_url(img), width=120)

        with col_info:
            st.markdown(f"### {p['name']}")
            st.write(f"₹{p['cost']}")

            sizes = p.get("size", "")
            
            if sizes:
                size_list = [s.strip() for s in sizes.split(",")]

                selected_size = st.selectbox(
                    f"Select Size {p['id']}",
                    size_list,
                    key=f"size_{p['id']}_{p['name']}"
                )
            else:
                selected_size = "Default"

        st.write(f"Stock: {p['stock']}")

        stock = int(p.get('stock', 0) or 0)

        if stock <= 0:
            st.write("❌ Out of Stock")
            continue

        col1, col2, col3 = st.columns([1,2,1])

        if col1.button("-", key=f"minus_{p['id']}"):
            st.session_state[f"q_{p['id']}"] = max(1, st.session_state.get(f"q_{p['id']}", 1) - 1)

        qty = col2.number_input(
            "",
            min_value=1,
            max_value=stock,
            value=st.session_state.get(f"q_{p['id']}", 1),
            key=f"q_{p['id']}"
        )

        if col3.button("+", key=f"plus_{p['id']}"):
            st.session_state[f"q_{p['id']}"] = min(
                stock,
                st.session_state.get(f"q_{p['id']}", 1) + 1
            )

        if st.button(f"Add {p['id']}", key=f"add_{p['id']}"):

            found = False

            for i, (cp, cq, cs) in enumerate(st.session_state.cart):
                if cp["id"] == p["id"] and cs == selected_size:
                    st.session_state.cart[i] = (cp, cq + qty, cs)
                    found = True
                    break

            if not found:
                st.session_state.cart.append((p, qty, selected_size))

    # -------- CART --------
    st.subheader("Cart")

    total = 0
    order_text = ""

    for idx, (p, q, size) in enumerate(st.session_state.cart):

        col1, col2 = st.columns([4,1])

        item_total = int(p['cost']) * q
        total += item_total
        order_text += f"{p['name']} ({size}) x {q} = ₹{item_total}\n"

        col1.write(f"{p['name']} ({size}) x {q} = ₹{item_total}")

        if col2.button("❌", key=f"rem{idx}"):
            st.session_state.cart.pop(idx)
            st.rerun()

    st.write(f"Total ₹{total}")
    name = st.text_input("Name")
    phone = st.text_input("Phone")

    state = st.selectbox(
        "State",
        ["West Bengal","Bihar","Jharkhand","Odisha","Assam","UP","Delhi","Other"]
    )

    addr = st.text_area("Address")

    if st.button("Place Order"):

        if not st.session_state.cart:
            st.error("⚠️ Please add at least 1 product before placing order")
            st.stop()

        if not name or not phone or not addr:
            st.error("Fill all details")

        elif len(phone) != 10:
            st.error("Invalid phone")

        else:

            orders = orders_sheet.get_all_records()
            order_id = len(orders) + 1

            for p, q, size in st.session_state.cart:

                item_total = int(p["cost"]) * q

                orders_sheet.append_row([
                    order_id,
                    name, phone, f"{state}, {addr}",
                    f"{p['name']} ({size})", q, item_total,
                    "Pending", "No", "", "", time.strftime("%Y-%m-%d")
                ])

                products_latest = products_sheet.get_all_records()

                for k, prod in enumerate(products_latest, start=2):
                    if prod["name"] == p["name"]:
                        new_stock = max(0, int(prod["stock"]) - q)
                        products_sheet.update_cell(k, 4, new_stock)

            st.cache_data.clear()

            message = f"""
            🌸 Sajai Tomay Order 🌸

            🆔 Order ID: {order_id}

            👤 Name: {name}
            📞 Phone: {phone}
            📍 Address: {state}, {addr}

            🛒 Items:
            {order_text}

            💰 Total: ₹{total}

            -------------------------------------
            Our team will contact you for further delivery related updates once you make the payment as per WhatsApp confirmation.
            
            Return or refund is only applicable if you receive any broken or discolored product

            DISPATCH TIME 5-7 DAYS

            PLEASE EXPECT DELIVERY WITHIN 10-12 WORKING DAYS🙏♥️
            HAPPY SHOPPING 
            ✨SAJAI TOMAY❤️

            -------------------------------------

            SAJAI TOMAY 🌻Everyone will be replied to as soon as possible🙏👇
            ALL OVER 🇮🇳INDIA🇮🇳 DELIVERY AVAILABLE

            My Address:
            Howrah Kona, Tentultala 711114
            (near sagor Toto garage before piyara bagan)

            📞 calling no. +91 9007893365 (call time 3pm to 9pm)

            🚚 Shipping:
            West Bengal → 50 (prepaid)
            Outside WB → 80 (prepaid)

            🚫 COD not available

            📌 For booking:
            Please take a screenshot and send your full address

            🌻 Shipping charges may change for Kurti/Dresses
            """
            st.session_state.order_done = True
            st.session_state.order_message = message

            # ✅ SAVE ORDER DATA FOR INVOICE
            st.session_state.order_id = order_id
            st.session_state.customer_name = name
            st.session_state.customer_phone = phone
            st.session_state.customer_address = addr
            st.session_state.customer_state = state
            st.session_state.order_total = total

            # ✅ SAVE CART FOR INVOICE
            st.session_state.last_order = st.session_state.cart.copy()

            # THEN CLEAR CART
            st.session_state.cart = []

            st.rerun()

    if st.session_state.order_done and "last_order" in st.session_state:

    # ✅ ADD THIS LINE HERE
        if "order_id" not in st.session_state:
            st.stop()
        message = st.session_state.order_message
        url = "https://wa.me/917003884969?text=" + urllib.parse.quote(message)

        st.success("Order placed successfully!")
        st.markdown(f"[📲 Send Order to Admin]({url})")

        doc = SimpleDocTemplate("invoice.pdf")
        styles = getSampleStyleSheet()

        extra_text = """
        <br/><br/>-------------------------------------<br/><br/>

        Return or refund is only applicable if you receive any broken or discolored product<br/><br/>

        DISPATCH TIME 5-7 DAYS<br/><br/>

        PLEASE EXPECT DELIVERY WITHIN 10-12 WORKING DAYS🙏♥️<br/>
        HAPPY SHOPPING<br/>
        ✨SAJAI TOMAY❤️<br/><br/>

        -------------------------------------<br/><br/>

        SAJAI TOMAY 🌻Everyone will be replied to as soon as possible🙏👇<br/><br/>

        ALL OVER 🇮🇳INDIA🇮🇳 DELIVERY AVAILABLE<br/><br/>

        My Address:<br/>
        Howrah Kona, Tentultala 711114<br/>
        (near sagor Toto garage before piyara bagan)<br/><br/>

        📞 calling no. +91 9007893365 (call time 3pm to 9pm)<br/><br/>

        🚚 Shipping:<br/>
        West Bengal → 50 (prepaid)<br/>
        Outside WB → 80 (prepaid)<br/><br/>

        🚫 COD not available<br/><br/>

        📌 For booking:<br/>
        Please take a screenshot and send your full address<br/><br/>

        🌻 Shipping charges may change for Kurti/Dresses
                """
        elements = []

        # -------- LOGO --------
        if os.path.exists("images/logo.png"):
            elements.append(Image("images/logo.png", width=120, height=120))

        elements.append(Spacer(1, 10))

        # -------- TITLE --------
        elements.append(Paragraph("<b>SAJAI TOMAY INVOICE</b>", styles["Title"]))
        elements.append(Spacer(1, 15))

        # -------- CUSTOMER DETAILS --------
        elements.append(Paragraph(f"<b>Order ID:</b> {st.session_state.order_id}", styles["Normal"]))
        elements.append(Paragraph(f"<b>Name:</b> {st.session_state.customer_name}", styles["Normal"]))
        elements.append(Paragraph(f"<b>Phone:</b> {st.session_state.customer_phone}", styles["Normal"]))
        elements.append(Paragraph(f"<b>Address:</b> {st.session_state.customer_state}, {st.session_state.customer_address}", styles["Normal"]))
        elements.append(Spacer(1, 15))

        # -------- TABLE (FLIPKART STYLE) --------
        table_data = [["Product", "Qty", "Price", "Total"]]

        for p, q, size in st.session_state.last_order:
            price = int(p["cost"])
            total_item = price * q
            table_data.append([f"{p['name']} ({size})", q, f"₹{price}", f"₹{total_item}"])      

        table = Table(table_data)

        table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.pink),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("GRID", (0,0), (-1,-1), 1, colors.black),
            ("ALIGN", (1,1), (-1,-1), "CENTER"),
        ]))

        elements.append(table)
        elements.append(Spacer(1, 15))

        # -------- TOTAL --------
        elements.append(Paragraph(f"<b>Total Amount: ₹{st.session_state.order_total}</b>", styles["Normal"]))
        elements.append(Spacer(1, 20))

        # -------- PAYMENT MESSAGE --------
        elements.append(Paragraph(
            "<b>👉 Our team will contact you further delivery related update once you make the payment as per WhatsApp confirmation.</b>",
            styles["Normal"]
        ))
        elements.append(Spacer(1, 20))

        # -------- POLICY --------
        elements.append(Paragraph("<b>Return & Delivery Policy</b>", styles["Heading2"]))
        elements.append(Spacer(1, 10))

        elements.append(Paragraph(
            "Return only for damaged/discolored items.<br/>"
            "Dispatch: 5-7 days<br/>"
            "Delivery: 10-12 working days<br/><br/>"
            "🙏 Happy Shopping<br/>✨ SAJAI TOMAY ❤️",
            styles["Normal"]
        ))
        elements.append(Spacer(1, 20))

        # -------- CONTACT --------
        elements.append(Paragraph("<b>Contact & Shipping</b>", styles["Heading2"]))
        elements.append(Spacer(1, 10))

        elements.append(Paragraph(
            "📍 Howrah Kona, Tentultala<br/>"
            "📞 +91 9007893365 (3pm–9pm)<br/><br/>"
            "🚚 WB: ₹50 | Outside: ₹80<br/>"
            "🚫 COD Not Available",
            styles["Normal"]
        ))

        # -------- BUILD --------
        doc.build(elements)

        with open("invoice.pdf", "rb") as f:
            st.download_button("📄 Download Invoice", f, "invoice.pdf")

        if st.button("🛒 Next Order"):
            st.session_state.order_done = False
            st.rerun()