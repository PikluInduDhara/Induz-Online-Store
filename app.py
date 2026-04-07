import streamlit as st
from supabase import create_client
import pandas as pd
import urllib.parse
from datetime import datetime

# ---------------- SUPABASE ----------------
SUPABASE_URL = "https://fbwyodmauvexdetkisvl.supabase.co"
SUPABASE_KEY = "sb_publishable_8l4A00wiQdL5oe0zQrxnnQ_dklse2G_"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Sajai Tomay", layout="wide")

st.title("🌸 Sajai Tomay")

login = st.sidebar.selectbox("Login", ["Customer", "Admin"])

# ---------------- CUSTOMER ----------------
if login == "Customer":

    response = supabase.table("products").select("*").execute()
    products = response.data

    st.subheader("🛍️ Collection")

    cart = st.session_state.get("cart", [])

    cols = st.columns(3)

    for i, p in enumerate(products):
        with cols[i % 3]:
            st.image(f"images/{p['image']}")
            st.write(f"**{p['name']}**")
            st.write(f"₹{p['cost']}")
            st.write(f"Stock: {p['stock']}")

            qty = st.number_input(f"Qty {i}", 1, int(p['stock']), key=f"q{i}")

            if st.button(f"Add {i}"):
                cart.append((p, qty))
                st.session_state["cart"] = cart
                st.success("Added ✅")

    # CART VIEW
    st.subheader("🛒 Cart")

    total = 0
    order_text = ""

    for item in cart:
        total += item[0]['cost'] * item[1]
        order_text += f"{item[0]['name']} x {item[1]}\n"
        st.write(f"{item[0]['name']} x {item[1]}")

    st.write(f"### Total: ₹{total}")

    # CUSTOMER DETAILS
    name = st.text_input("Name")
    phone = st.text_input("Phone")
    address = st.text_area("Address")

    if st.button("Place Order"):

        if not cart:
            st.warning("Cart empty ❌")
        else:
            for item in cart:

                supabase.table("orders").insert({
                    "customer": name,
                    "phone": phone,
                    "address": address,
                    "product": item[0]['name'],
                    "qty": item[1],
                    "total": item[0]['cost'] * item[1],
                    "date": str(datetime.now())
                }).execute()

                # UPDATE STOCK
                new_stock = item[0]['stock'] - item[1]

                supabase.table("products").update({
                    "stock": new_stock
                }).eq("id", item[0]['id']).execute()

            # WHATSAPP AUTO
            message = f"""
🌸 Sajai Tomay 🌸

Customer: {name}
Phone: {phone}

Items:
{order_text}

Total: ₹{total}
"""

            msg = urllib.parse.quote(message)

            st.markdown(f"""
            <script>
            window.open("https://wa.me/{phone}?text={msg}", "_blank");
            window.open("https://wa.me/7003884969?text={msg}", "_blank");
            window.open("https://wa.me/7980238789?text={msg}", "_blank");
            </script>
            """, unsafe_allow_html=True)

            st.success("Order Placed ✅")

            st.session_state["cart"] = []
            st.experimental_rerun()

# ---------------- ADMIN ----------------
else:
    password = st.sidebar.text_input("Password", type="password")

    if password == "admin123":

        st.subheader("📊 Dashboard")

        orders = supabase.table("orders").select("*").execute().data
        df = pd.DataFrame(orders)

        st.dataframe(df)

        st.subheader("➕ Add Product")

        name = st.text_input("Product Name")
        cost = st.number_input("Cost")
        stock = st.number_input("Stock")
        image = st.text_input("Image Name (example: J001.jpg)")

        if st.button("Add Product"):

            supabase.table("products").insert({
                "name": name,
                "cost": cost,
                "stock": stock,
                "image": image
            }).execute()

            st.success("Product Added ✅")

    else:
        st.error("Wrong password ❌")