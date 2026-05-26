import streamlit as st
from streamlit_image_carousel import image_carousel
import os
import urllib.parse
import pandas as pd
import time
import base64
import requests
import pgeocode
import gspread
st.set_page_config(
    page_title="Sajai Tomay",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<link rel="manifest" href="/.streamlit/manifest.json">
<meta name="theme-color" content="#d63384">
""", unsafe_allow_html=True)

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

# ---------------- GOOGLE SHEET ----------------
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_dict(
    st.secrets["gcp_service_account"], scope
)
client = gspread.authorize(creds)

try:
    sheet = client.open("SajaiTomayDB")
    products_sheet = sheet.worksheet("products")
    orders_sheet = sheet.worksheet("orders")

except Exception as e:
    st.error("⚠️ Google Sheet connection issue. Please refresh.")
    st.stop()

mode = st.sidebar.selectbox("Login Type", ["Customer", "Admin"])

# -------- PREMIUM STICKY NAVBAR --------

if "cart" not in st.session_state:
    st.session_state.cart = []

cart_qty = sum(q for _, q, _ in st.session_state.cart)

st.markdown("""
<style>

/* MAIN CONTENT GAP */
.block-container {
    padding-top: 45px !important;
}

/* FIXED NAVBAR */
.sticky-navbar {
    position: fixed;
    top: 0;
    left: 21rem;
    right: 0;
    height: 65px;
    z-index: 999;
    background: white;
    border-bottom: 2px solid #ffe6ef;
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    padding: 5px 20px;
}

/* MOBILE FIX */
@media (max-width: 768px) {

    .sticky-navbar {
        left: 0 !important;
        height: auto;
        padding: 10px;
    }

    .block-container {
        padding-top: 60px !important;
    }
}
/* BOTTOM MOBILE NAV */

.bottom-nav {
    position: fixed;
    bottom: 0;
    left: 0;
    width: 100%;
    background: white;
    border-top: 1px solid #eee;
    display: flex;
    justify-content: space-around;
    padding: 10px 0;
    z-index: 9999;
    box-shadow: 0 -2px 10px rgba(0,0,0,0.08);
}

.bottom-nav div {
    text-align: center;
    font-size: 14px;
    color: #d63384;
    font-weight: bold;
}

/* EXTRA SPACE FOR MOBILE */
@media (max-width: 768px) {

    .block-container {
        padding-bottom: 90px !important;
    }
}
.product-image img{
    border-radius:18px;
    transition:0.3s;
    cursor:pointer;
}

.product-image img:hover{
    transform:scale(1.04);
    box-shadow:0 8px 20px rgba(0,0,0,0.15);
}
</style>
""", unsafe_allow_html=True)


st.markdown('<div class="sticky-navbar">', unsafe_allow_html=True)

nav1, nav2, nav3, nav4 = st.columns([1,2,5,2])

with nav1:
    st.write("")

with nav2:
    if os.path.exists("images/logo.png"):
        st.image("images/logo.png", width=180)
        
with nav3:
    st.markdown("""
        <h1 style='
            color:#d63384;
            margin-top:20px;
            font-size:48px;
            font-weight:bold;
        '>
        🌸 Sajai Tomay 🌸
        </h1>
    """, unsafe_allow_html=True)

with nav4:

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button(f"🛒 Cart ({cart_qty})", use_container_width=True):

        st.session_state.page = "cart"

        st.rerun()
    if st.button("📦 Track Order", use_container_width=True):

        st.session_state.page = "tracking"

        st.rerun()

st.markdown("</div>", unsafe_allow_html=True)

# ================= ADMIN =================
if mode == "Admin":

    password = st.sidebar.text_input("Password", type="password")

    if password == "Indu@1234#":

        st.header("Admin Panel")
        admin_page = st.sidebar.radio(
            "Admin Menu",
            [
                "📊 Dashboard",
                "📦 Products",
                "🚚 Orders"
            ]
        )
        if admin_page == "📊 Dashboard":

            st.header("📊 Business Dashboard")

            orders = orders_sheet.get_all_records()

            total_orders = len(orders)

            pending_orders = len([
                o for o in orders
                if o["status"] == "Pending"
            ])

            accepted_orders = len([
                o for o in orders
                if o["status"] in [
                    "Accepted",
                    "Packed",
                    "Shipped",
                    "Delivered"
                ]
            ])

            cancelled_orders = len([
                o for o in orders
                if o["status"] == "Cancelled"
            ])

            total_sales = sum(
                int(o.get("total", 0))
                for o in orders
                if o["status"] in [
                    "Accepted",
                    "Packed",
                    "Shipped",
                    "Delivered"
                ]
                and o["payment"] == "Yes"
            )

            c1, c2, c3, c4, c5 = st.columns(5)

            c1.metric("🛒 Orders", total_orders)
            c2.metric("⏳ Pending", pending_orders)
            c3.metric("✅ Accepted", accepted_orders)
            c4.metric("❌ Cancelled", cancelled_orders)
            c5.metric("💰 Sales", f"₹{total_sales}")

            st.markdown("---")

            st.subheader("📦 Category Wise Orders")

            category_summary = {}

            products_data = products_sheet.get_all_records()

            for o in orders:

                product_name = o["product"]

                category = "Others"

                for p in products_data:
                    if p["name"] == product_name:
                        category = p.get("category", "Others")
                        break

                if category not in category_summary:

                    category_summary[category] = {
                        "Total Orders": 0,
                        "Pending": 0,
                        "Accepted": 0,
                        "Cancelled": 0,
                        "Sales": 0
                    }

                # TOTAL ORDERS
                category_summary[category]["Total Orders"] += 1

                # PENDING
                if o["status"] == "Pending":
                    category_summary[category]["Pending"] += 1

                # ACCEPTED
                if o["status"] in [
                    "Accepted",
                    "Packed",
                    "Shipped",
                    "Delivered"
                ]:
                    category_summary[category]["Accepted"] += 1

                # CANCELLED
                if o["status"] == "Cancelled":
                    category_summary[category]["Cancelled"] += 1

                # SALES
                if o["status"] in [
                    "Accepted",
                    "Packed",
                    "Shipped",
                    "Delivered"
                ] and o["payment"] == "Yes":
                    category_summary[category]["Sales"] += int(o.get("total", 0))

            dashboard_df = pd.DataFrame(category_summary).T

            st.dataframe(dashboard_df, use_container_width=True)
            st.bar_chart(dashboard_df["Sales"])
        if admin_page == "📦 Products":
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
        if admin_page == "🚚 Orders":
            # -------- DELIVERY DASHBOARD --------
            st.subheader("Delivery Dashboard")
            st.markdown("""
            <style>

            div[data-testid="stHorizontalBlock"] {
                position: relative;
                z-index: 1;
            }

            .admin-sticky {
                position: sticky;
                top: 75px;
                background: white;
                z-index: 999;
                padding-top: 10px;
                padding-bottom: 10px;
                border-bottom: 2px solid #ffd6e7;
            }

            </style>
            """, unsafe_allow_html=True)
            try:
                orders = orders_sheet.get_all_records()
            except:
                st.error("⚠️ Sheet structure broken. Please fix columns in Google Sheet.")
                st.stop()
            total_sales = 0

            headers = ["ID","Date","Customer","Phone","Address","Product","Qty","Value","Payment","Pay Ref","Del Ref","Status"]

            st.markdown("""
            <style>
            .admin-header{
                position:fixed;
                top:70px;
                left:21rem;
                right:0;
                background:white;
                z-index:9999;
                padding:12px 20px;
                border-bottom:2px solid #ffd6e7;
                box-shadow:0 4px 12px rgba(0,0,0,0.08);
            }
            </style>
            """, unsafe_allow_html=True)

            st.markdown('<div class="admin-sticky">', unsafe_allow_html=True)
            
            cols = st.columns([0.7,1,1.3,1.2,2.2,1.2,0.6,0.8,1,1,1,1.2])

            for col, h in zip(cols, headers):

                col.markdown(f"""
                <div style="
                    font-weight:bold;
                    color:#d63384;
                    text-align:center;
                ">
                {h}
                </div>
                """, unsafe_allow_html=True)

            st.markdown('</div>', unsafe_allow_html=True)
            

            for i, o in enumerate(orders, start=2):

                # ✅ ONLY CHANGE (Sales logic)
                if o["status"] in [
                    "Accepted",
                    "Packed",
                    "Shipped",
                    "Delivered"
                ] and o["payment"] == "Yes":
                    try:
                        total_sales += int(o["total"])
                    except:
                        pass
                    
                c = st.columns([0.7,1,1.3,1.2,2.2,1.2,0.6,0.8,1,1,1,1.2])

                c[0].write(o["id"])
                c[1].write(o["order_date"])
                c[2].write(o["customer"])
                c[3].write(o["phone"])
                c[4].write(
                    f"{o['city']}, {o['state']} - {o['pincode']}\n{o['address']}"
                )
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
                    status = c[11].selectbox(
                        "",
                        [
                            "Pending",
                            "Accepted",
                            "Packed",
                            "Shipped",
                            "Delivered",
                            "Cancelled"
                        ],
                        key=f"status{i}"
                    )

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
                    orders_sheet.update_cell(i, 13, payment)
                    orders_sheet.update_cell(i, 14, pay_ref)
                    orders_sheet.update_cell(i, 15, del_ref)
                    orders_sheet.update_cell(i, 12, status)
                    
                    customer_message = f"""
                    🌸 SAJAI TOMAY UPDATE 🌸

                    🆔 Order ID: {o['id']}

                    📦 Status: {status}

                    🚚 Tracking:
                    {del_ref if del_ref else "Will be updated soon"}

                    ❤️ Thank you for shopping with us
                    """

                    wa_link = (
                        "https://wa.me/91"
                        + str(o["phone"])
                        + "?text="
                        + urllib.parse.quote(customer_message)
                    )

                    st.success("✅ Update Saved")

                    st.markdown(
                        f"[📲 Send WhatsApp Update]({wa_link})"
                    )
                    # 🔄 REFRESH
                    st.cache_data.clear()

                    if st.button("🔄 Refresh Orders"):
                        st.cache_data.clear()
                        st.rerun()                    
            st.write(f"### 💰 Total Sales: ₹{total_sales}")

# ================= CUSTOMER =================
else:

    st.subheader("Products")
    # -------- DYNAMIC HERO SLIDER --------

    banner_sheet = sheet.worksheet("Banners")

    banner_data = banner_sheet.get_all_records()

    banner_urls = [get_image_url(b["Image"]) for b in banner_data]

    slider_html = """
    <style>

    .hero-slider{
        width:100%;
        height:450px;
        overflow:hidden;
        border-radius:25px;
        position:relative;
        margin-bottom:30px;
        box-shadow:0 8px 20px rgba(0,0,0,0.12);
    }

    .hero-slider img{
        width:100%;
        height:450px;
        object-fit:cover;
        position:absolute;
        opacity:0;
        animation:slide """ + str(len(banner_urls)*5) + """s infinite;
    }

    /* MOBILE RESPONSIVE */
    @media (max-width:768px){

        .hero-slider{
            height:220px;
            border-radius:18px;
        }

        .hero-slider img{
            height:220px;
            object-fit:contain;
        }
    }

    """

    for i in range(len(banner_urls)):
        slider_html += f"""
    .hero-slider img:nth-child({i+1}){{
        animation-delay:{i*5}s;
    }}
    """

    slider_html += """

    @keyframes slide{

    0%{opacity:0;}
    10%{opacity:1;}
    30%{opacity:1;}
    40%{opacity:0;}
    100%{opacity:0;}

    }

    </style>

    <div class="hero-slider">
    """

    for url in banner_urls:
        slider_html += f'<img src="{url}">'

    slider_html += "</div>"

    st.markdown(slider_html, unsafe_allow_html=True)

    products = products_sheet.get_all_records()
    products = products_sheet.get_all_records()
    products = pd.DataFrame(products).to_dict("records")
    # 🔥 SEARCH BAR
    search_text = st.text_input("🔍 Search Product")

    # 🔥 CATEGORY BUTTONS (VISIBLE LIKE AMAZON)
    categories = list(set([p.get("category","All") for p in products]))
    # -------- PREMIUM CATEGORY SECTION --------

    st.markdown("""
    <style>

    .category-title{
        font-size:26px;
        font-weight:bold;
        color:#d63384;
        margin-bottom:15px;
    }

    .category-card button{
        width:100%;
        border-radius:20px;
        padding:15px 10px;
        background:white;
        border:1px solid #f3d6e2;
        font-size:16px;
        font-weight:bold;
        transition:0.3s;
        min-height:95px;
        box-shadow:0 2px 8px rgba(0,0,0,0.05);
    }

    .category-card button:hover{
        background:#fff0f5;
        transform:scale(1.05);
        color:#d63384;
        border:1px solid #ff4d94;
    }

    </style>
    """, unsafe_allow_html=True)

    st.markdown(
        '<div class="category-title">🛍️ Shop By Category</div>',
        unsafe_allow_html=True
    )

    # CATEGORY ICONS
    cat_icons = {

        "Saree": "🥻",
        "Dress Men": "👔",
        "Dress WoMen": "👗",
        "Jewellery": "💍",
        "Necklace": "📿",
        "Earrings": "✨",
        "Bangles": "🪬",
        "Kurti": "🌸",
        "Lehenga": "👑",
        "Kids": "🧸",
        "Bags": "👜",
        "Handbag": "👜",
        "Beauty": "💄",
        "Shoes": "👠",
        "Watch": "⌚",
        "Gift": "🎁",
        "Home Decor": "🏠",
        "Toy": "🚗",
        "Car Toy": "🚘",
        "Makeup": "💋",
        "Perfume": "🌺",
        "Festival": "🎉",
        "Wedding": "💒",
        "All": "🛍️"
    }

    all_categories = ["All"] + categories

    # SAVE CATEGORY
    if "selected_category" not in st.session_state:
        st.session_state.selected_category = "All"

    cat_cols = st.columns(4)

    for i, cat in enumerate(all_categories):

        icon = cat_icons.get(cat, "🛒")

        with cat_cols[i % 4]:

            st.markdown('<div class="category-card">', unsafe_allow_html=True)

            if st.button(
                f"{icon}\n{cat}",
                key=f"cat_{cat}"
            ):
                st.session_state.selected_category = cat

            st.markdown('</div>', unsafe_allow_html=True)

    selected_category = st.session_state.selected_category

    if "cart" not in st.session_state:
        st.session_state.cart = []

    if "order_done" not in st.session_state:
        st.session_state.order_done = False
    if "page" not in st.session_state:
        st.session_state.page = "shop"
    if "selected_product" not in st.session_state:
        st.session_state.selected_product = None
    if "track_phone" not in st.session_state:
        st.session_state.track_phone = ""
    cart_qty = sum(q for _, q, _ in st.session_state.cart)

    # -------- GROUP PRODUCTS (FLIPKART STYLE) --------
    grouped = {}

    for p in products:
        key = (p["name"], p["cost"], p.get("image",""), p.get("category",""))

        if key not in grouped:
            grouped[key] = []

        grouped[key].append(p)
    if st.session_state.page == "shop":
        # -------- DISPLAY PRODUCTS --------
        product_list = list(grouped.items())

        for idx in range(0, len(product_list), 2):

            cols = st.columns(2)

            for col_num in range(2):

                if idx + col_num < len(product_list):

                    ((name, cost, image, category), items) = product_list[idx + col_num]

                    with cols[col_num]:

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
                                    background:white;
                                    border-radius:20px;
                                    padding:16px;
                                    margin-bottom:25px;
                                    box-shadow:0 4px 14px rgba(0,0,0,0.08);
                                ">
                                """, unsafe_allow_html=True)

                                # PRODUCT IMAGE
                                if images:

                                    st.image(
                                        get_image_url(images[0]),
                                        use_container_width=True
                                    )

                                # PRODUCT NAME
                                st.markdown(f"""
                                <h3 style="
                                    font-size:22px;
                                    margin-top:10px;
                                    margin-bottom:5px;
                                    color:#222;
                                ">
                                {name}
                                </h3>
                                """, unsafe_allow_html=True)

                                # PRICE
                                st.markdown(f"""
                                <h2 style="
                                    color:#ff3f6c;
                                    font-size:30px;
                                    margin-top:0;
                                ">
                                ₹{cost}
                                </h2>
                                """, unsafe_allow_html=True)

                                # VIEW DETAILS BUTTON
                                if st.button(
                                    "👀 View Details",
                                    key=f"view_{idx}_{col_num}",
                                    use_container_width=True
                                ):

                                    st.session_state.selected_product = {
                                        "name": name,
                                        "cost": cost,
                                        "image": image,
                                        "category": category,
                                        "items": items
                                    }

                                    st.session_state.page = "product"

                                    st.rerun()

                                st.markdown("</div>", unsafe_allow_html=True)

    # -------- PRODUCT DETAILS PAGE --------

    if st.session_state.page == "product":

        p = st.session_state.selected_product

        if p is None:
            st.session_state.page = "shop"
            st.rerun()

        name = p["name"]
        cost = p["cost"]
        image = p["image"]
        items = p["items"]

        images = [img.strip() for img in image.split(",") if img.strip()]

        st.button("⬅ Back", on_click=lambda: st.session_state.update({"page":"shop"}))

        col1, col2 = st.columns([1.2,1])

        # LEFT SIDE IMAGE
        with col1:

            if images:

                image_urls = [
                    get_image_url(img)
                    for img in images
                ]

                image_carousel(
                    image_urls=image_urls,
                    height=500,
                    key="product_page_carousel"
                )

        # RIGHT SIDE DETAILS
        with col2:

            st.markdown(f"""
            <h1 style="
                color:#222;
                font-size:42px;
                font-weight:800;
            ">
            {name}
            </h1>
            """, unsafe_allow_html=True)

            st.markdown(f"""
            <h1 style="
                color:#ff3f6c;
                font-size:48px;
                font-weight:900;
            ">
            ₹{cost}
            </h1>
            """, unsafe_allow_html=True)

            size_list = list(set([
                str(x.get("size","NA"))
                for x in items
            ]))

            selected_size = st.selectbox(
                "Select Size",
                size_list
            )

            selected_product = next(
                x for x in items
                if str(x.get("size")) == str(selected_size)
            )

            stock = int(selected_product["stock"])

            st.success(f"✅ In Stock: {stock}")

            qty = st.number_input(
                "Quantity",
                min_value=1,
                max_value=stock,
                value=1
            )

            if st.button(
                "🛒 ADD TO BAG",
                use_container_width=True
            ):

                found = False

                for i, (cp, cq, cs) in enumerate(st.session_state.cart):

                    if cp["name"] == selected_product["name"] and cs == selected_size:

                        st.session_state.cart[i] = (
                            cp,
                            cq + qty,
                            cs
                        )

                        found = True
                        break

                if not found:

                    st.session_state.cart.append(
                        (selected_product, qty, selected_size)
                    )

                st.toast("✅ Added To Bag")

                time.sleep(0.5)

                st.rerun()
    # -------- ORDER TRACKING PAGE --------

    if st.session_state.page == "tracking":

        st.title("📦 Track Your Order")

        phone_search = st.text_input(
            "Enter Your Phone Number",
            value=st.session_state.track_phone
        )
        order_search = st.text_input(
            "Enter Order ID"
        )

        if st.button("🔍 Track Order"):

            st.session_state.track_phone = phone_search
            
            st.rerun()

        if st.session_state.track_phone:

            orders = orders_sheet.get_all_records()

            customer_orders = [
                o for o in orders
                if str(o["phone"]) == str(st.session_state.track_phone)
                and str(o["id"]) == str(order_search)
            ]

            if customer_orders:

                for o in customer_orders:
                    status_color = "#f39c12"

                    if o["status"] == "Delivered":
                        status_color = "green"

                    elif o["status"] == "Cancelled":
                        status_color = "red"

                    elif o["status"] == "Shipped":
                        status_color = "#3498db"
                    st.markdown(f"""
                    <div style="
                        background:linear-gradient(135deg,#fff,#fff7fb);
                        padding:25px;
                        border-radius:24px;
                        margin-bottom:25px;
                        border:2px solid #ffd6e7;
                        box-shadow:0 8px 24px rgba(0,0,0,0.08);
                    ">

                    <h3 style="color:#d63384;">
                    🆔 Order #{o['id']}
                    </h3>

                    <p><b>🛍️ Product:</b> {o['product']}</p>

                    <p><b>📏 Size:</b> {o['size']}</p>

                    <p><b>🔢 Quantity:</b> {o['quantity']}</p>

                    <p><b>💰 Amount:</b> ₹{o['total']}</p>

                    <p><b>💳 Payment:</b> {o['payment']}</p>
                    
                    <p>
                    <b>📦 Order Status:</b>

                    <span style="
                        color:{status_color};
                        font-weight:bold;
                    ">
                    {o['status']}
                    </span>
                    </p>

                    <p><b>🚚 Courier Tracking:</b> {o.get('delivery_ref','Pending')}</p>

                    </div>
                    """, unsafe_allow_html=True)
                    if o["status"] == "Delivered":

                        st.markdown("### ⭐ Rate This Product")

                        rating = st.slider(
                            "Rate Product",
                            1,
                            5,
                            5,
                            key=f"rate_{o['id']}"
                        )

                        review = st.text_area(
                            "Write Review",
                            key=f"review_{o['id']}"
                        )

                        if st.button(
                            "Submit Review",
                            key=f"submit_review_{o['id']}"
                        ):

                            st.success("❤️ Thank you for your review!")

            else:

                st.warning("No orders found")
            st.stop()
    if st.session_state.page == "cart":
        if not st.session_state.cart and not st.session_state.order_done:

            st.info("🛒 Your cart is empty")

            if st.button("⬅ Go Shopping"):
                st.session_state.page = "shop"
                st.rerun()

            st.stop()
        # -------- CART --------
        st.subheader("Cart")
        if st.button("⬅ Continue Shopping"):
            st.session_state.page = "shop"
            st.rerun()

        total = 0
        order_text = ""

        for idx, (p, q, size) in enumerate(st.session_state.cart):

            col_img, col_info, col_remove = st.columns([1,4,1])

            # -------- PRODUCT IMAGE --------
            images = [img.strip() for img in p.get("image","").split(",") if img.strip()]

            with col_img:
                if images:
                    st.image(get_image_url(images[0]), width=100)

            # -------- PRODUCT INFO --------
            with col_info:

                item_total = int(p['cost']) * q
                total += item_total

                order_text += f"{p['name']} ({size}) x {q} = ₹{item_total}\n"

                st.markdown(f"### {p['name']}")
                st.write(f"Size: {size}")
                st.write(f"Qty: {q}")
                st.write(f"Price: ₹{p['cost']}")
                st.write(f"Total: ₹{item_total}")

            # -------- REMOVE BUTTON --------
            with col_remove:

                # ➕ Increase Quantity
                if st.button("➕", key=f"inc_{idx}"):

                    stock_available = int(p.get("stock", 0))

                    if q < stock_available:

                        st.session_state.cart[idx] = (p, q + 1, size)

                    st.rerun()

                # ➖ Decrease Quantity
                if st.button("➖", key=f"dec_{idx}"):

                    if q > 1:
                        st.session_state.cart[idx] = (p, q - 1, size)
                    else:
                        st.session_state.cart.pop(idx)

                    st.rerun()

            # ❌ Remove Product
            if st.button("❌", key=f"rem{idx}"):

                st.session_state.cart.pop(idx)

                st.session_state.page = "cart"

                st.rerun()

            st.markdown("---")

        st.write(f"Total ₹{total}")
        name = st.text_input("Name")
        phone = st.text_input("Phone")

        pincode = st.text_input("PIN Code")

        state = ""

        district = ""
        state = ""
        city = ""

        if len(pincode) == 6:

            try:
                nomi = pgeocode.Nominatim("in")

                location = nomi.query_postal_code(pincode)

                district = str(location.county_name or "")
                state = str(location.state_name or "")

                if state != "nan":

                    st.success(f"📍 {district}, {state}")

                    city = st.text_input(
                        "City / Area",
                        value=district
                    )

                else:
                    st.error("Invalid PIN Code")

            except:
                st.error("Unable to detect location")

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
                            pincode,
                            state,
                            city,
                            addr,
                            p['name'],
                            size,
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
                    📍 Address: {city}, {state} - {pincode}

                    🏠 {addr}

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
                    st.session_state.customer_city = city
                    st.session_state.customer_pincode = pincode
                    st.session_state.order_total = total

                    # ✅ SAVE CART FOR INVOICE
                    st.session_state.last_order = st.session_state.cart.copy()

                    # THEN CLEAR CART
                    st.session_state.cart = []
                    time.sleep(1)
                    st.rerun()

        if st.session_state.order_done and "last_order" in st.session_state:

            # ✅ ADD THIS LINE HERE
                if "order_id" not in st.session_state:
                    st.stop()
                message = st.session_state.order_message
                url = "https://wa.me/919007893365?text=" + urllib.parse.quote(message)

                st.markdown(f"""
                <div style="
                    background:linear-gradient(135deg,#fff0f6,#ffe6ef);
                    padding:30px;
                    border-radius:25px;
                    border:2px solid #ff4d94;
                    box-shadow:0 8px 24px rgba(0,0,0,0.08);
                    margin-bottom:25px;
                ">

                <h1 style="
                    color:#d63384;
                    text-align:center;
                ">
                ✅ ORDER PLACED SUCCESSFULLY
                </h1>

                <hr>

                <h3>🆔 Order ID: {st.session_state.order_id}</h3>

                <h3>💰 Total Amount: ₹{st.session_state.order_total}</h3>

                <h3>📦 Status: Pending</h3>

                <p style="
                    font-size:18px;
                    color:#555;
                    line-height:1.8;
                ">

                🎉 Thank you for shopping with us.<br><br>

                📲 Please send your order to admin on WhatsApp.<br><br>

                🚚 Our team will contact you soon regarding payment and delivery updates.

                </p>

                </div>
                """, unsafe_allow_html=True)
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
                elements.append(
                    Paragraph(
                        f"<b>Address:</b> "
                        f"{st.session_state.customer_city}, "
                        f"{st.session_state.customer_state} - "
                        f"{st.session_state.customer_pincode}<br/>"
                        f"{st.session_state.customer_address}",
                        styles["Normal"]
                    )
                )
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
                    st.session_state.page = "shop"
                    st.rerun()
