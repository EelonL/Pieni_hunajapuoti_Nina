from __future__ import annotations

import re
import smtplib
import time
import uuid
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path

import gspread
import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).parent
PRODUCTS_FILE = BASE_DIR / "products.csv"
IMAGES_DIR = BASE_DIR / "assets" / "images"
SHEET_NAME = "Hunajapuodin tilaukset"

IMAGE_MAP = {
    "Kesähunaja 250 g": IMAGES_DIR / "kesahunaja_250.png",
    "Kesähunaja 500 g": IMAGES_DIR / "kesahunaja_500.png",
    "Metsähunaja 250 g": IMAGES_DIR / "metsahunaja_250.png",
    "Lahjapakkaus": IMAGES_DIR / "lahjapakkaus.png",
}
HERO_IMAGE = IMAGES_DIR / "hero_banner.png"

MIN_SECONDS_BETWEEN_ORDERS = 20

st.set_page_config(page_title="Pieni hunajapuoti Nina", page_icon="🍯", layout="wide")


def inject_styles() -> None:
    st.markdown(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@400;500;600;700&family=Marck+Script&display=swap');
            .stApp { background: linear-gradient(180deg, #fffaf2 0%, #f6efe2 100%); font-family: 'Quicksand', sans-serif; }
            .block-container { padding-top: 1.4rem; padding-bottom: 2rem; }
            html, body, [class*="css"], [data-testid="stAppViewContainer"], [data-testid="stMarkdownContainer"],
            [data-testid="stText"], [data-testid="stMetricLabel"], [data-testid="stMetricValue"],
            .stTextInput label, .stTextArea label, .stSelectbox label { font-family: 'Quicksand', sans-serif; }
            h1, h2, h3 { color: #6f4e18; font-family: 'Quicksand', sans-serif; }
            .shop-title { font-family: 'Marck Script', cursive; font-size: 3.2rem; font-weight: 400; color: #7a5216; margin-bottom: 0.15rem; line-height: 1.1; }
            .shop-subtitle { font-size: 1.1rem; color: #8b6a2b; margin-bottom: 1.4rem; }
            .section-card { background: rgba(255, 248, 235, 0.75); border: 1px solid #e8d7b5; border-radius: 18px; padding: 1rem 1.1rem; margin-bottom: 1rem; box-shadow: 0 4px 14px rgba(111, 78, 24, 0.06); }
            div[data-testid="stMetric"] { background: #fffaf2; border: 1px solid #ecdcb9; padding: 0.55rem 0.8rem; border-radius: 14px; }
            div[data-testid="stMetricLabel"] { color: #8b6a2b; }
            div[data-testid="stMetricValue"] { color: #6f4e18; }
            .stButton > button, .stDownloadButton > button, div[data-testid="stFormSubmitButton"] > button {
                background-color: #c48a1d; color: white; border: none; border-radius: 999px;
                padding: 0.55rem 1.1rem; font-weight: 600; font-family: 'Quicksand', sans-serif;
            }
            .stButton > button:hover, .stDownloadButton > button:hover, div[data-testid="stFormSubmitButton"] > button:hover {
                background-color: #a96f0c; color: white;
            }
            .small-note { color: #8b6a2b; font-size: 0.95rem; }
            .product-description { color: #5f533d; min-height: 3em; }
            .placeholder-box {
                border: 1px dashed #d9c49b; border-radius: 16px; background: rgba(255,248,235,0.65);
                color: #8b6a2b; padding: 2.2rem 1rem; text-align: center; margin-bottom: 0.5rem;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def load_products() -> pd.DataFrame:
    df = pd.read_csv(PRODUCTS_FILE)
    df["price"] = df["price"].astype(float)
    df["stock"] = df["stock"].astype(int)
    df.loc[df["name"] == "Lahjapakkaus", "description"] = "Kaunis hunajalahja kolmella pienellä purkilla."
    return df


def get_product_image(product_name: str) -> Path | None:
    image_path = IMAGE_MAP.get(product_name)
    if image_path and image_path.exists():
        return image_path
    return None


def get_gsheet_worksheet():
    gc = gspread.service_account_from_dict(dict(st.secrets["gcp_service_account"]))
    sh = gc.open(SHEET_NAME)
    return sh.sheet1


def init_state() -> None:
    defaults = {
        "cart": {},
        "last_order": None,
        "last_email_error": None,
        "last_submit_ts": 0.0,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def add_to_cart(product_id: int, quantity: int) -> None:
    current_qty = st.session_state.cart.get(product_id, 0)
    st.session_state.cart[product_id] = current_qty + quantity


def update_cart(product_id: int, quantity: int) -> None:
    if quantity <= 0:
        st.session_state.cart.pop(product_id, None)
    else:
        st.session_state.cart[product_id] = quantity


def clear_cart() -> None:
    st.session_state.cart = {}


def clear_last_order() -> None:
    st.session_state.last_order = None
    st.session_state.last_email_error = None


def cart_dataframe(products: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for product_id, qty in st.session_state.cart.items():
        match = products.loc[products["id"] == product_id]
        if match.empty:
            continue
        product = match.iloc[0]
        rows.append(
            {
                "Tuote": product["name"],
                "Määrä": qty,
                "á-hinta (€)": f"{product['price']:.2f}",
                "Yhteensä (€)": f"{product['price'] * qty:.2f}",
            }
        )
    return pd.DataFrame(rows)


def cart_total(products: pd.DataFrame) -> float:
    total = 0.0
    for product_id, qty in st.session_state.cart.items():
        match = products.loc[products["id"] == product_id]
        if not match.empty:
            total += float(match.iloc[0]["price"]) * qty
    return round(total, 2)


def serialize_items(products: pd.DataFrame) -> str:
    parts = []
    for product_id, qty in st.session_state.cart.items():
        match = products.loc[products["id"] == product_id]
        if not match.empty:
            product = match.iloc[0]
            line_total = float(product["price"]) * int(qty)
            parts.append(f"{product['name']} x {qty} = {line_total:.2f} €")
    return " | ".join(parts)


def order_lines(products: pd.DataFrame) -> list[str]:
    lines = []
    for product_id, qty in st.session_state.cart.items():
        match = products.loc[products["id"] == product_id]
        if not match.empty:
            product = match.iloc[0]
            line_total = float(product["price"]) * int(qty)
            lines.append(f"- {product['name']} x {qty} = {line_total:.2f} €")
    return lines


def ensure_sheet_header() -> None:
    worksheet = get_gsheet_worksheet()
    expected_header = [
        "timestamp", "order_id", "customer_name", "email", "phone",
        "delivery_method", "notes", "items", "total_eur",
    ]
    current_row = worksheet.row_values(1)
    if current_row != expected_header:
        worksheet.update("A1:I1", [expected_header])


def save_order(customer_name: str, email: str, phone: str, delivery_method: str, notes: str, products: pd.DataFrame) -> tuple[str, str, float, str]:
    order_id = str(uuid.uuid4())[:8].upper()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    items = serialize_items(products)
    total = cart_total(products)

    ensure_sheet_header()
    worksheet = get_gsheet_worksheet()
    worksheet.append_row([
        timestamp, order_id, customer_name, email, phone,
        delivery_method, notes, items, f"{total:.2f}",
    ])
    return order_id, timestamp, total, items


def send_email(subject: str, body: str, to_email: str, cc_email: str | None = None) -> None:
    smtp_cfg = st.secrets["smtp"]
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = smtp_cfg["sender_email"]
    msg["To"] = to_email
    if cc_email:
        msg["Cc"] = cc_email
    msg.set_content(body)
    recipients = [to_email] + ([cc_email] if cc_email else [])

    with smtplib.SMTP_SSL(smtp_cfg["host"], int(smtp_cfg["port"])) as server:
        server.login(smtp_cfg["username"], smtp_cfg["password"])
        server.send_message(msg, to_addrs=recipients)


def send_owner_notification(customer_name: str, customer_email: str, phone: str, delivery_method: str, notes: str, order_id: str, timestamp: str, total: float, products: pd.DataFrame) -> None:
    app_cfg = st.secrets["app_config"]
    lines = "\n".join(order_lines(products))
    sheet_url = app_cfg["google_sheet_url"]

    draft_reply = f"""Hei {customer_name},

kiitos tilauksestasi Hunajapuodista.

Olemme vastaanottaneet tilauksesi:
{lines}

Yhteensä: {total:.2f} €

Tilauksesi on käsittelyssä. Vahvistamme vielä erikseen tuotteiden saatavuuden ja lähetämme sinulle tilausvahvistuksen sähköpostitse pian.

Ystävällisin terveisin,
Nina
Hunajapuoti
"""

    owner_subject = f"Uusi tilaus Hunajapuotiin #{order_id}"
    owner_body = f"""Hunajapuotiin saapui uusi tilaus.

Tilausnumero: {order_id}
Aika: {timestamp}

Asiakas: {customer_name}
Sähköposti: {customer_email}
Puhelin: {phone}
Toimitustapa: {delivery_method}
Lisätiedot: {notes or '-'}

Tilauksen sisältö:
{lines}

Yhteensä: {total:.2f} €

Google Sheet:
{sheet_url}

Valmis ehdotus asiakkaalle lähetettäväksi tilausvahvistukseksi:

{draft_reply}
"""

    send_email(owner_subject, owner_body, app_cfg["owner_email"], cc_email=app_cfg.get("cc_email", None))


def build_order_receipt_text(order_data: dict) -> str:
    item_lines = order_data["items"].replace(" | ", "\n")
    return f"""Pieni hunajapuoti Nina

Tilausnumero: {order_data['order_id']}
Aika: {order_data['timestamp']}

Asiakas: {order_data['customer_name']}
Sähköposti: {order_data['email']}
Puhelin: {order_data['phone']}
Toimitustapa: {order_data['delivery_method']}

Tilauksen sisältö:
{item_lines}

Yhteensä: {order_data['total']:.2f} €

Tilauksesi on käsittelyssä ja saat tilausvahvistuksen sähköpostiisi hetken kuluttua.
"""


def show_last_order_box() -> None:
    if not st.session_state.last_order:
        return

    order_data = st.session_state.last_order
    st.success(f"Kiitos! Tilauspyyntösi vastaanotettiin. Tilausnumero: {order_data['order_id']}")
    st.info("Tilauksesi on käsittelyssä ja saat tilausvahvistuksen sähköpostiisi hetken kuluttua.")

    if st.session_state.last_email_error:
        st.warning(
            "Tilaus tallentui onnistuneesti, mutta puodille lähtevän ilmoitusviestin lähetyksessä oli hetkellinen häiriö. "
            "Puoti voi silti tarkistaa tilauksen Google Sheetistä."
        )

    receipt_text = build_order_receipt_text(order_data)
    st.download_button(
        label="Lataa tilausnumero (.txt)",
        data=receipt_text.encode("utf-8"),
        file_name=f"tilaus_{order_data['order_id']}.txt",
        mime="text/plain",
    )


def render_hero() -> None:
    if HERO_IMAGE.exists():
        st.image(str(HERO_IMAGE), use_container_width=True)
    st.markdown('<div class="shop-title">Pieni hunajapuoti Nina</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="shop-subtitle">Paikallista hunajaa suoraan tuottajalta — lämmin, pieni ja luonnonläheinen hunajapuoti.</div>',
        unsafe_allow_html=True,
    )


def render_missing_image_placeholder() -> None:
    st.markdown('<div class="placeholder-box">Tuotekuva tulossa</div>', unsafe_allow_html=True)


def product_card(product: pd.Series) -> None:
    image_path = get_product_image(str(product["name"]))
    with st.container(border=True):
        if image_path:
            st.image(str(image_path), use_container_width=True)
        else:
            render_missing_image_placeholder()

        st.subheader(product["name"])
        st.markdown(f'<div class="product-description">{product["description"]}</div>', unsafe_allow_html=True)
        st.metric("Hinta", f"{product['price']:.2f} €")

        qty = st.number_input(
            f"Määrä tuotteelle {product['id']}",
            min_value=1,
            max_value=max(1, int(product["stock"])),
            value=1,
            key=f"qty_{product['id']}",
        )
        if st.button("Lisää koriin", key=f"add_{product['id']}", use_container_width=True):
            add_to_cart(int(product["id"]), int(qty))
            clear_last_order()
            st.success(f"Lisätty koriin: {product['name']} ({qty} kpl)")


def storefront(products: pd.DataFrame) -> None:
    render_hero()
    st.markdown(
        '<div class="section-card"><h3>Tuotteet</h3><div class="small-note">Pehmeää kesähunajaa, tummempaa metsähunajaa ja lahjapakkaus luonnon ystävälle.</div></div>',
        unsafe_allow_html=True,
    )
    cols = st.columns(2)
    for idx, (_, product) in enumerate(products.iterrows()):
        with cols[idx % 2]:
            product_card(product)


def cart_view(products: pd.DataFrame) -> None:
    st.markdown("### Ostoskori")
    if not st.session_state.cart:
        st.info("Ostoskori on vielä tyhjä. Valitse ensin tuotteita yllä olevasta valikoimasta.")
        return

    cart_df = cart_dataframe(products)
    if cart_df.empty:
        st.info("Korissa ei ole tuotteita.")
        return

    st.dataframe(cart_df, use_container_width=True, hide_index=True)
    st.subheader(f"Yhteensä: {cart_total(products):.2f} €")

    st.markdown("#### Muokkaa ostoskoria")
    for product_id, current_qty in list(st.session_state.cart.items()):
        match = products.loc[products["id"] == product_id]
        if match.empty:
            continue
        product = match.iloc[0]
        new_qty = st.number_input(
            f"{product['name']} (kpl)",
            min_value=0,
            max_value=max(0, int(product["stock"])),
            value=int(current_qty),
            key=f"cart_edit_{product_id}",
        )
        if new_qty != current_qty:
            update_cart(product_id, int(new_qty))
            clear_last_order()
            st.rerun()

    if st.button("Tyhjennä kori"):
        clear_cart()
        clear_last_order()
        st.rerun()


def is_valid_email(email: str) -> bool:
    email = email.strip()
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email))


def is_valid_phone(phone: str) -> bool:
    phone = phone.strip()
    if not phone:
        return True
    digits = re.sub(r"\D", "", phone)
    return len(digits) >= 7


def validate_order_form(customer_name: str, email: str, phone: str, honeypot: str) -> str | None:
    if honeypot.strip():
        return "Lähetystä ei voitu käsitellä. Yritä uudelleen hetken kuluttua."
    if len(customer_name.strip()) < 2:
        return "Kirjoita nimesi hieman tarkemmin."
    if not email.strip():
        return "Täytä sähköpostiosoite."
    if not is_valid_email(email):
        return "Tarkista sähköpostiosoite."
    if not is_valid_phone(phone):
        return "Tarkista puhelinnumero."

    seconds_since_last = time.time() - float(st.session_state.last_submit_ts)
    if seconds_since_last < MIN_SECONDS_BETWEEN_ORDERS:
        remaining = int(MIN_SECONDS_BETWEEN_ORDERS - seconds_since_last) + 1
        return f"Odota vielä hetki ennen uuden tilauksen lähettämistä ({remaining} s)."

    return None


def checkout_form(products: pd.DataFrame) -> None:
    st.markdown("### Lähetä tilauspyyntö")
    show_last_order_box()

    if not st.session_state.cart:
        st.caption("Lisää ensin tuotteita koriin.")
        return

    with st.form("checkout_form"):
        customer_name = st.text_input("Nimi *")
        email = st.text_input("Sähköposti *")
        phone = st.text_input("Puhelin")
        delivery_method = st.selectbox("Toimitustapa", ["Nouto", "Paikallinen toimitus", "Postitus"])
        notes = st.text_area("Lisätiedot")
        honeypot = st.text_input("Jätä tämä kenttä tyhjäksi", value="")
        st.caption("Jos näet tämän kentän, jätä se tyhjäksi.")
        submitted = st.form_submit_button("Lähetä tilaus")

        if submitted:
            validation_error = validate_order_form(customer_name, email, phone, honeypot)
            if validation_error:
                st.error(validation_error)
                return

            try:
                with st.spinner("Tallennetaan tilausta..."):
                    order_id, timestamp, total, items = save_order(
                        customer_name.strip(),
                        email.strip(),
                        phone.strip(),
                        delivery_method,
                        notes.strip(),
                        products,
                    )

                st.session_state.last_submit_ts = time.time()
                st.session_state.last_email_error = None

                try:
                    with st.spinner("Lähetetään ilmoitus puodille..."):
                        send_owner_notification(
                            customer_name=customer_name.strip(),
                            customer_email=email.strip(),
                            phone=phone.strip(),
                            delivery_method=delivery_method,
                            notes=notes.strip(),
                            order_id=order_id,
                            timestamp=timestamp,
                            total=total,
                            products=products,
                        )
                except Exception as e:
                    st.session_state.last_email_error = str(e)

                st.session_state.last_order = {
                    "order_id": order_id,
                    "timestamp": timestamp,
                    "customer_name": customer_name.strip(),
                    "email": email.strip(),
                    "phone": phone.strip(),
                    "delivery_method": delivery_method,
                    "items": items,
                    "total": total,
                }

                clear_cart()
                st.balloons()
                st.rerun()

            except Exception:
                st.error("Tilauksen tallennuksessa tapahtui häiriö. Yritä hetken kuluttua uudelleen.")
                return


def main() -> None:
    init_state()
    inject_styles()
    products = load_products()

    st.sidebar.markdown("### Pieni hunajapuoti Nina")
    st.sidebar.markdown("---")
    st.sidebar.write("Paikallista hunajaa suoraan tuottajalta.")
    st.sidebar.caption("Demo ilman maksamista tai kirjautumista.")
    st.sidebar.caption("Tilaukset tallennetaan turvallisesti puodin omaan taulukkoon.")

    storefront(products)
    st.markdown("---")
    cart_view(products)
    st.markdown("---")
    checkout_form(products)


if __name__ == "__main__":
    main()
