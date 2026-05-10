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

    if password == "Indu@1234#":

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
                    new_sizes,      # ✅ size column
                    new_stock,      # ✅ stock column
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
                products_sheet.update_cell(i, 5, new_stock)
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

        try:
            orders = orders_sheet.get_all_records()
        except:
            st.error("⚠️ Sheet structure broken. Please fix columns in Google Sheet.")
            st.stop()
        total_sales = 0

        headers = ["ID","Date","Customer","Phone","Address","Product","Qty","Value","Payment","Pay Ref","Del Ref","Status"]
        cols = st.columns(len(headers))

        for col, h in zip(cols, headers):
            col.write(f"**{h}**")

        for i, o in enumerate(orders, start=2):

            # ✅ ONLY CHANGE (Sales logic)
            if o["status"] == "Accepted" and o["payment"] == "Yes":
                try:
                    total_sales += int(o["total"])
                except:
                    pass
                
            c = st.columns(len(headers))

            c[0].write(o["id"])
            c[1].write(o["order_date"])
            c[2].write(o["customer"])
            c[3].write(o["phone"])
            c[4].write(o["address"])
            c[5].write(o["product"])
            c[6].write(o["quantity"])
            c[7].write(str(o.get("total", 0)))

            payment = c[8].selectbox("", ["Yes","No"],
                index=0 if o["payment"]=="Yes" else 1, key=f"pay{i}")

            pay_ref = c[9].text_input("", value=o.get("payment_ref",""), key=f"pref{i}")
            del_ref = c[10].text_input("", value=o.get("delivery_ref",""), key=f"dref{i}")

            if o["status"] == "Cancelled":
                status = c[11].selectbox("", ["Cancelled"], key=f"status{i}")
            else:
                status = c[11].selectbox("", ["Pending","Accepted","Cancelled"], key=f"status{i}")

            if st.button(f"Save {i}"):

                # 🔒 HARD LOCK (DO NOT TOUCH CANCELLED)
                if o["status"] == "Cancelled":
                    st.warning("❌ Cancelled orders cannot be modified")
                    st.stop()

                products_latest = products_sheet.get_all_records()

                # ✅ STOCK RETURN ONLY ON FIRST CANCEL
                if status == "Cancelled" and o["status"] != "Cancelled":
                    for j, p in enumerate(products_latest, start=2):
                        if p["name"] == o["product"] and str(p.get("size")) == str(o.get("size")):
                            new_stock = int(p["stock"]) + int(o["quantity"])
                            products_sheet.update_cell(j, 5, new_stock)

                # ✅ UPDATE ORDER (ONLY ONCE)
                orders_sheet.update_cell(i, 10, payment)
                orders_sheet.update_cell(i, 11, pay_ref)
                orders_sheet.update_cell(i, 12, del_ref)
                orders_sheet.update_cell(i, 9, status)

                # 🔄 REFRESH
                st.cache_data.clear()
                st.rerun()
                
        st.write(f"### 💰 Total Sales: ₹{total_sales}")

# ================= CUSTOMER =================
else:

    st.subheader("Products")
    # -------- PREMIUM OFFER BANNER --------
    st.markdown("""
    <div style="
        background:#ffe6ef;
        padding:25px;
        border-radius:18px;
        border:2px solid #ff4d94;
        margin-bottom:25px;
        text-align:center;
    ">

    <h1 style='color:#d63384; font-size:38px; margin-bottom:10px;'>
    🎉 GRAND OPENING OFFER 🎉
    </h1>

    <div style="
        background:white;
        padding:18px;
        border-radius:12px;
        margin-top:15px;
    ">

    <p style='font-size:20px; color:#444; line-height:1.8;'>

    🚚 <b>FREE SHIPPING</b><br>
    06 Jun 2026 → 05 Jul 2026<br><br>

    🎁 Free Gifts on orders above <b>₹2000</b><br><br>

    ✨ HAPPY SHOPPING ✨<br>

    ❤️ <b>SAJAI TOMAY</b> ❤️

    </p>

    </div>
    </div>
    """, unsafe_allow_html=True)
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

    # -------- GROUP PRODUCTS (FLIPKART STYLE) --------
    grouped = {}

    for p in products:
        key = (p["name"], p["cost"], p.get("image",""), p.get("category",""))

        if key not in grouped:
            grouped[key] = []

        grouped[key].append(p)

    # -------- DISPLAY PRODUCTS --------
    for (name, cost, image, category), items in grouped.items():

        # 🔥 FILTER (KEEP YOUR EXISTING FILTER LOGIC)
        if selected_category != "All" and category != selected_category:
            continue

        if search_text and search_text.lower() not in name.lower():
            continue

        images = [img.strip() for img in image.split(",") if img.strip()]

        card = st.container()

        with card:
            st.markdown("""
                <div style="
                    border:1px solid #eee;
                    border-radius:10px;
                    padding:15px;
                    margin-bottom:15px;
                    box-shadow:0 2px 6px rgba(0,0,0,0.05);
                ">
            """, unsafe_allow_html=True)

            col_img, col_info = st.columns([1,2])
            # -------- IMAGE --------
            with col_img:
                if images:
                    cols = st.columns(3)
                    for i, img in enumerate(images[:3]):
                        cols[i].image(get_image_url(img), width=120)

            # -------- INFO --------
            with col_info:
                st.markdown(f"### {name}")
                st.write(f"₹{cost}")

                size_list = list(set([str(x.get("size", "NA")) for x in items]))

                selected_size = st.selectbox(
                    "Select Size",
                    size_list,
                    key=f"size_{name}_{cost}"
                )

                selected_product = next(x for x in items if str(x.get("size")) == str(selected_size))

                stock = int(selected_product["stock"])

                st.write(f"Stock: {stock}")

            # -------- QTY + ADD --------
            if stock > 0:
                col1, col2, col3 = st.columns([1,2,1])

                if col1.button("-", key=f"minus_{name}_{cost}"):
                    st.session_state[f"q_{name}_{cost}"] = max(
                        1,
                        st.session_state.get(f"q_{name}_{cost}", 1) - 1
                    )

                qty = col2.number_input(
                    "",
                    min_value=1,
                    max_value=stock,
                    value=st.session_state.get(f"q_{name}_{cost}", 1),
                    key=f"q_{name}_{cost}"
                )

                if col3.button("+", key=f"plus_{name}_{cost}"):
                    st.session_state[f"q_{name}_{cost}"] = min(
                        stock,
                        st.session_state.get(f"q_{name}_{cost}", 1) + 1
                    )

                if st.button(f"Add {name}", key=f"add_{name}_{cost}"):

                    found = False

                    for i, (cp, cq, cs) in enumerate(st.session_state.cart):
                        if cp["name"] == selected_product["name"] and cs == selected_size:
                            st.session_state.cart[i] = (cp, cq + qty, cs)
                            found = True
                            break

                    if not found:
                        st.session_state.cart.append((selected_product, qty, selected_size))

            else:
                st.write("❌ Out of Stock")

            st.markdown("</div>", unsafe_allow_html=True)

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

            try:
                orders = orders_sheet.get_all_records()
            except:
                st.error("⚠️ Sheet structure broken. Please fix columns in Google Sheet.")
                st.stop()
            order_id = len(orders) + 1

            for p, q, size in st.session_state.cart:

                item_total = int(p["cost"]) * q

                orders_sheet.append_row([
                    order_id,
                    name,
                    phone,
                    f"{state}, {addr}",
                    p['name'],        # ✅ clean product name
                    size,             # ✅ NEW SIZE COLUMN
                    q,
                    item_total,
                    "Pending",
                    "No",
                    "",
                    "",
                    time.strftime("%Y-%m-%d")
                ])

                products_latest = products_sheet.get_all_records()

                for k, prod in enumerate(products_latest, start=2):
                    if prod["name"] == p["name"] and str(prod.get("size")) == str(size):
                        new_stock = max(0, int(prod["stock"]) - q)
                        products_sheet.update_cell(k, 5, new_stock)

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
            ✨ WELCOME TO “SAJAI TOMAY” ❤️
            This page will serve you your dream jewellery and stylish dresses.. at its best quality and best price with love 💖
            Our team will contact you for further delivery related updates once you make the payment as per WhatsApp confirmation

            ▪️ ⏳ Expect reply from us within 2–3 business days after dropping the message.

            ▪️ 📞 If no reply within 2–3 days, call: 9007893365
            (After placing the order if you don’t get any reply or confirmation from us within 2–3 business days)

            ◾ 💖 ALL OF US FROM “SAJAI TOMAY” ARE WORKING HARD EVERYDAY TO PROVIDE YOU THE BEST PRODUCT OR SERVICE .

            ◾ RULES & REGULATIONS :–
            ▪️ This is a complete online boutique.
            ▪️ We don’t have any shop or outlet.
            ▪️ ❌ No COD available.
            ▪️ 💳 Payments only via Google Pay, PhonePe, Paytm & Bank Transfer.
            ▪️ 🚫 If the payment not made within 2 days order will be cancelled automatically
            ▪️ 🎥 After receiving parcel, Opening Video is MUST.
            ❌ Without opening video, no complaints will be accepted.
            👉 Issue must be clearly visible in the video.

            ▪️ 🌍 We ship worldwide.

            ▪️ 🚚 Shipping charge all over India: ₹60/-
            Except Tripura & Assam.

            ▪️ 🚚 For Tripura & Assam: ₹80/-

            ▪️ 👗 Shipping charge may change for Kurti or Dresses.
            🌍 International shipping charges vary by location.

            🎁 Purchase above ₹2000/- & get free gifts from us.

            ▪️ ❌ No refund facility available.
            ✅ Replacement / Repolish only if product is broken or discolored.

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
        url = "https://wa.me/919007893365?text=" + urllib.parse.quote(message)

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
            """
            <b>👉 ✨ WELCOME TO “SAJAI TOMAY” ❤️<br/><br/>

            This page will serve you your dream jewellery and stylish dresses at best quality and best price with love 💖<br/><br/>

            Our team will contact you for further delivery related updates once you make the payment as per WhatsApp confirmation.<br/><br/>

            ▪️ ⏳ Expect reply within 2–3 business days after dropping the message.<br/><br/>

            ▪️ 📞 If no reply within 2–3 days, call: 9007893365<br/>
            (After placing the order if you don’t get any reply or confirmation within 2–3 business days)<br/><br/>

            ◾ 💖 ALL OF US FROM “SAJAI TOMAY” ARE WORKING HARD EVERYDAY TO PROVIDE YOU THE BEST PRODUCT OR SERVICE.<br/><br/>

            ◾ RULES & REGULATIONS:<br/>
            ▪️ This is a complete online boutique.<br/>
            ▪️ We don’t have any shop or outlet.<br/>
            ▪️ ❌ No COD available.<br/>
            ▪️ 💳 Payments only via Google Pay, PhonePe, Paytm & Bank Transfer.<br/>
            ▪️ 🚫 If payment is not made within 2 days, order will be cancelled automatically.<br/>
            ▪️ 🎥 After receiving parcel, Opening Video is MUST.<br/>
            ❌ Without opening video, no complaints will be accepted.<br/>
            👉 Issue must be clearly visible in the video.<br/><br/>

            ▪️ 🌍 We ship worldwide.<br/><br/>

            ▪️ 🚚 Shipping charge all over India: ₹60/- (Except Tripura & Assam)<br/>
            ▪️ 🚚 Tripura & Assam: ₹80/-<br/>
            ▪️ 👗 Shipping may change for Kurti/Dresses.<br/>
            🌍 International shipping varies by location.<br/><br/>

            🎁 Purchase above ₹2000/- & get free gifts from us.<br/><br/>

            ▪️ ❌ No refund facility available.<br/>
            ✅ Replacement / Repolish only if product is broken or discolored.
            </b>
            """,
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