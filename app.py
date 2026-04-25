
from __future__ import annotations

import re
import smtplib
import time
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

TRANSLATIONS = {
    "fi": {
        "shop_title": "Pieni hunajapuoti Nina",
        "shop_subtitle": "Paikallista hunajaa suoraan tuottajalta — lämmin, pieni ja luonnonläheinen hunajapuoti.",
        "welcome_title": "Tervetuloa puotiin",
        "welcome_text": "Pieni hunajapuoti Nina tarjoaa paikallista hunajaa suoraan tuottajalta. Jokainen tilaus käsitellään huolella, ja saat tilausvahvistuksen sähköpostiisi pian tilauksen jälkeen. Voit tilata tuotteita helposti tämän sivun kautta, ja noudosta tai toimituksesta sovitaan tilausvahvistuksessa.",
        "steps_title": "Näin tilaus etenee",
        "step_1": "Valitse tuotteet koriin.",
        "step_2": "Tarkista ja muokkaa ostoskoria.",
        "step_3": "Lähetä tilaus.",
        "step_4": "Saat tilausvahvistuksen sähköpostiisi.",
        "products_title": "Tuotteet",
        "products_note": "Pehmeää kesähunajaa, tummempaa metsähunajaa ja lahjapakkaus luonnon ystävälle.",
        "cart_title": "Ostoskori",
        "cart_empty": "Ostoskori on vielä tyhjä. Valitse ensin tuotteita yllä olevasta valikoimasta.",
        "product_col": "Tuote",
        "unit_price": "á-hinta",
        "quantity": "Määrä",
        "total": "Yhteensä",
        "remove": "Poista",
        "add_more": "Lisää vielä tuote ostoskoriin",
        "select_product": "Valitse tuote",
        "add": "Lisää",
        "clear_cart": "Tyhjennä kori",
        "send_order": "Lähetä tilaus",
        "customer_type": "Asiakastyyppi",
        "private_customer": "Yksityishenkilö",
        "business_customer": "Yritys",
        "customer_details": "Tilaajan tiedot",
        "name": "Nimi *",
        "email": "Sähköposti *",
        "phone": "Puhelin",
        "delivery_method": "Toimitustapa",
        "pickup": "Nouto",
        "local_delivery": "Paikallinen toimitus",
        "shipping": "Postitus",
        "payment_method": "Toivottu maksutapa",
        "pay_mobilepay": "MobilePay-linkki",
        "pay_card": "Korttimaksulinkki",
        "pay_bank": "Verkkopankkimaksulinkki",
        "pay_invoice": "Lasku / maksu myöhemmin",
        "pay_cash": "Maksu noudettaessa",
        "business_title": "Yrityksen tiedot",
        "company_name": "Yrityksen nimi *",
        "business_id": "Y-tunnus *",
        "contact_person": "Yhteyshenkilö *",
        "reference_info": "Viitetieto / kustannuspaikka",
        "billing_title": "Laskutusosoite",
        "billing_same_as_delivery": "Laskutusosoite sama kuin toimitusosoite",
        "billing_street_address": "Laskutuskatuosoite",
        "billing_postal_code": "Laskutuksen postinumero",
        "billing_city": "Laskutuksen postitoimipaikka",
        "address_title": "Toimitusosoite",
        "street_address": "Katuosoite",
        "postal_code": "Postinumero",
        "city": "Postitoimipaikka",
        "notes": "Lisätiedot",
        "add_first": "Lisää ensin tuotteita koriin.",
        "save_order": "Tallennetaan tilausta...",
        "notify_shop": "Lähetetään ilmoitus puodille...",
        "success_order": "Kiitos! Tilaus vastaanotettiin. Tilausnumero: {order_id}",
        "processing_info": "Tilauksesi on käsittelyssä ja saat tilausvahvistuksen sähköpostiisi hetken kuluttua.",
        "mail_warn": "Tilaus tallentui onnistuneesti, mutta puodille lähtevän ilmoitusviestin lähetyksessä oli hetkellinen häiriö. Puoti voi silti tarkistaa tilauksen Google Sheetistä.",
        "download_txt": "Lataa tilausnumero (.txt)",
        "image_coming": "Tuotekuva tulossa",
        "name_error": "Kirjoita nimesi hieman tarkemmin.",
        "email_required": "Täytä sähköpostiosoite.",
        "email_error": "Tarkista sähköpostiosoite.",
        "phone_error": "Tarkista puhelinnumero.",
        "company_name_error": "Täytä yrityksen nimi.",
        "business_id_error": "Täytä Y-tunnus.",
        "contact_person_error": "Täytä yhteyshenkilön nimi.",
        "street_error": "Täytä katuosoite.",
        "postal_error": "Täytä postinumero.",
        "city_error": "Täytä postitoimipaikka.",
        "billing_street_error": "Täytä laskutuskatuosoite.",
        "billing_postal_error": "Täytä laskutuksen postinumero.",
        "billing_city_error": "Täytä laskutuksen postitoimipaikka.",
        "honeypot_error": "Lähetystä ei voitu käsitellä. Yritä uudelleen hetken kuluttua.",
        "wait_error": "Odota vielä hetki ennen uuden tilauksen lähettämistä ({remaining} s).",
        "save_error": "Tilauksen tallennuksessa tapahtui häiriö. Yritä hetken kuluttua uudelleen.",
        "receipt_thanks": "Lämmin kiitos tilauksestasi!",
        "receipt_address": "Toimitusosoite",
        "receipt_items": "Tilauksen sisältö",
        "receipt_time": "Aika",
        "receipt_customer": "Asiakas",
        "internal_draft_intro": "Valmis ehdotus asiakkaalle lähetettäväksi tilausvahvistukseksi:",
        "owner_new_order": "Uusi tilaus Hunajapuotiin #{order_id}",
        "owner_order_received": "Hunajapuotiin saapui uusi tilaus.",
        "sheet_link": "Google Sheet",
        "receipt_greeting": "Hei {name},",
        "receipt_email_body": "kiitos tilauksestasi Hunajapuodista.\n\nOlemme vastaanottaneet tilauksesi:\n{lines}\n\nYhteensä: {total}\n\nTilauksesi on käsittelyssä. Vahvistamme vielä erikseen tuotteiden saatavuuden ja lähetämme sinulle tilausvahvistuksen sähköpostitse pian.\n\nYstävällisin terveisin,\nNina\nHunajapuoti",
        "payment_pref_label": "Toivottu maksutapa",
        "payment_link_note": "Lisää tilausvahvistukseen maksulinkki asiakkaan valitseman maksutavan mukaan.",
        "p1_name": "Kesähunaja 250 g",
        "p1_desc": "Pehmeä ja kukkainen kesähunaja pieneen arjen herkutteluun.",
        "p2_name": "Kesähunaja 500 g",
        "p2_desc": "Runsas purkillinen pehmeää kesähunajaa koko perheen käyttöön.",
        "p3_name": "Metsähunaja 250 g",
        "p3_desc": "Tummempi ja täyteläisempi metsähunaja voimakkaamman maun ystävälle.",
        "p4_name": "Lahjapakkaus",
        "p4_desc": "Kaunis hunajalahja kolmella pienellä purkilla.",
    }
}
TRANSLATIONS["sv"] = TRANSLATIONS["fi"] | {
    "shop_title": "Lilla honungsbutiken Nina",
    "shop_subtitle": "Lokal honung direkt från producenten — en varm, liten och naturnära honungsbutik.",
    "welcome_title": "Välkommen till butiken",
    "welcome_text": "Lilla honungsbutiken Nina erbjuder lokal honung direkt från producenten. Varje beställning behandlas omsorgsfullt och du får en orderbekräftelse till din e-post strax efter beställningen. Du kan enkelt beställa produkter via denna sida, och avhämtning eller leverans avtalas i orderbekräftelsen.",
    "steps_title": "Så här går beställningen till",
    "step_1": "Välj produkter till varukorgen.",
    "step_2": "Granska och ändra varukorgen.",
    "step_3": "Skicka beställningen.",
    "step_4": "Du får en orderbekräftelse per e-post.",
    "products_title": "Produkter",
    "products_note": "Mjuk sommarhonung, fylligare skogshonung och en presentförpackning för naturvänner.",
    "cart_title": "Varukorg",
    "cart_empty": "Varukorgen är ännu tom. Välj först produkter från sortimentet ovan.",
    "product_col": "Produkt",
    "unit_price": "à-pris",
    "quantity": "Antal",
    "remove": "Ta bort",
    "add_more": "Lägg till en produkt till i varukorgen",
    "select_product": "Välj produkt",
    "add": "Lägg till",
    "clear_cart": "Töm varukorgen",
    "send_order": "Skicka beställning",
    "customer_type": "Kundtyp",
    "private_customer": "Privatperson",
    "business_customer": "Företag",
    "customer_details": "Kunduppgifter",
    "name": "Namn *",
    "email": "E-post *",
    "phone": "Telefon",
    "delivery_method": "Leveranssätt",
    "pickup": "Avhämtning",
    "local_delivery": "Lokal leverans",
    "shipping": "Postleverans",
    "payment_method": "Önskat betalningssätt",
    "pay_mobilepay": "MobilePay-länk",
    "pay_card": "Kortbetalningslänk",
    "pay_bank": "Nätbanksbetalningslänk",
    "pay_invoice": "Faktura / betala senare",
    "pay_cash": "Betala vid avhämtning",
    "business_title": "Företagsuppgifter",
    "company_name": "Företagsnamn *",
    "business_id": "FO-nummer *",
    "contact_person": "Kontaktperson *",
    "reference_info": "Referens / kostnadsställe",
    "billing_title": "Faktureringsadress",
    "billing_same_as_delivery": "Faktureringsadressen är samma som leveransadressen",
    "billing_street_address": "Faktureringsgata",
    "billing_postal_code": "Fakturans postnummer",
    "billing_city": "Fakturans ort",
    "address_title": "Leveransadress",
    "street_address": "Gatuadress",
    "postal_code": "Postnummer",
    "city": "Ort",
    "notes": "Tilläggsinformation",
    "add_first": "Lägg först produkter i varukorgen.",
    "save_order": "Sparar beställningen...",
    "notify_shop": "Skickar meddelande till butiken...",
    "success_order": "Tack! Beställningen togs emot. Beställningsnummer: {order_id}",
    "processing_info": "Din beställning behandlas och du får en orderbekräftelse till din e-post inom kort.",
    "mail_warn": "Beställningen sparades, men det uppstod ett tillfälligt problem med meddelandet till butiken. Butiken kan ändå kontrollera beställningen i Google Sheet.",
    "download_txt": "Ladda ner beställningsnummer (.txt)",
    "image_coming": "Produktbild kommer snart",
    "name_error": "Skriv ditt namn lite tydligare.",
    "email_required": "Fyll i e-postadress.",
    "email_error": "Kontrollera e-postadressen.",
    "phone_error": "Kontrollera telefonnumret.",
    "company_name_error": "Fyll i företagsnamnet.",
    "business_id_error": "Fyll i FO-numret.",
    "contact_person_error": "Fyll i kontaktpersonens namn.",
    "street_error": "Fyll i gatuadressen.",
    "postal_error": "Fyll i postnumret.",
    "city_error": "Fyll i orten.",
    "billing_street_error": "Fyll i faktureringsgatan.",
    "billing_postal_error": "Fyll i fakturans postnummer.",
    "billing_city_error": "Fyll i fakturans ort.",
    "honeypot_error": "Skickandet kunde inte behandlas. Försök igen om en liten stund.",
    "wait_error": "Vänta ännu en stund innan du skickar en ny beställning ({remaining} s).",
    "save_error": "Det uppstod ett fel när beställningen sparades. Försök igen om en liten stund.",
    "receipt_thanks": "Varmt tack för din beställning!",
    "receipt_address": "Leveransadress",
    "receipt_items": "Beställningens innehåll",
    "receipt_time": "Tid",
    "receipt_customer": "Kund",
    "internal_draft_intro": "Färdigt förslag till orderbekräftelse för kunden:",
    "owner_new_order": "Ny beställning till honungsbutiken #{order_id}",
    "owner_order_received": "En ny beställning har kommit till honungsbutiken.",
    "sheet_link": "Google Sheet",
    "receipt_greeting": "Hej {name},",
    "receipt_email_body": "tack för din beställning från Hunajapuoti.\n\nVi har tagit emot din beställning:\n{lines}\n\nTotalt: {total}\n\nDin beställning behandlas. Vi bekräftar produkternas tillgänglighet separat och skickar en orderbekräftelse per e-post inom kort.\n\nVänliga hälsningar,\nNina\nHunajapuoti",
    "payment_pref_label": "Önskat betalningssätt",
    "payment_link_note": "Lägg till en betalningslänk i orderbekräftelsen enligt kundens valda betalningssätt.",
    "p1_name": "Sommarhonung 250 g",
    "p1_desc": "Mjuk och blommig sommarhonung för små stunder av vardagslyx.",
    "p2_name": "Sommarhonung 500 g",
    "p2_desc": "En generös burk mjuk sommarhonung för hela familjen.",
    "p3_name": "Skogshonung 250 g",
    "p3_desc": "Mörkare och fylligare skogshonung för dig som gillar kraftigare smak.",
    "p4_name": "Presentförpackning",
    "p4_desc": "En vacker honungsgåva med tre små burkar.",
}
TRANSLATIONS["en"] = TRANSLATIONS["fi"] | {
    "shop_title": "Nina's Small Honey Shop",
    "shop_subtitle": "Local honey directly from the producer — a warm, small, nature-inspired honey shop.",
    "welcome_title": "Welcome to the shop",
    "welcome_text": "Nina's Small Honey Shop offers local honey directly from the producer. Every order is handled with care, and you will receive an order confirmation by email soon after placing your order. You can easily order products on this page, and pickup or delivery will be agreed in the confirmation email.",
    "steps_title": "How ordering works",
    "step_1": "Add products to your cart.",
    "step_2": "Review and edit your cart.",
    "step_3": "Send your order.",
    "step_4": "You will receive an order confirmation by email.",
    "products_title": "Products",
    "products_note": "Soft summer honey, fuller forest honey, and a gift set for nature lovers.",
    "cart_title": "Cart",
    "cart_empty": "Your cart is still empty. First choose products from the selection above.",
    "product_col": "Product",
    "unit_price": "Unit price",
    "quantity": "Qty",
    "remove": "Remove",
    "add_more": "Add another product to the cart",
    "select_product": "Select product",
    "add": "Add",
    "clear_cart": "Clear cart",
    "send_order": "Send order",
    "customer_type": "Customer type",
    "private_customer": "Private customer",
    "business_customer": "Business customer",
    "customer_details": "Customer details",
    "name": "Name *",
    "email": "Email *",
    "phone": "Phone",
    "delivery_method": "Delivery method",
    "pickup": "Pickup",
    "local_delivery": "Local delivery",
    "shipping": "Shipping",
    "payment_method": "Preferred payment method",
    "pay_mobilepay": "MobilePay link",
    "pay_card": "Card payment link",
    "pay_bank": "Online bank payment link",
    "pay_invoice": "Invoice / pay later",
    "pay_cash": "Pay on pickup",
    "business_title": "Business details",
    "company_name": "Company name *",
    "business_id": "Business ID *",
    "contact_person": "Contact person *",
    "reference_info": "Reference / cost centre",
    "billing_title": "Billing address",
    "billing_same_as_delivery": "Billing address same as delivery address",
    "billing_street_address": "Billing street address",
    "billing_postal_code": "Billing postal code",
    "billing_city": "Billing city",
    "address_title": "Delivery address",
    "street_address": "Street address",
    "postal_code": "Postal code",
    "city": "City",
    "notes": "Additional information",
    "add_first": "Add products to your cart first.",
    "save_order": "Saving your order...",
    "notify_shop": "Sending notification to the shop...",
    "success_order": "Thank you! Your order was received. Order number: {order_id}",
    "processing_info": "Your order is being processed and you will receive an order confirmation by email shortly.",
    "mail_warn": "The order was saved successfully, but there was a temporary issue sending the notification to the shop. The shop can still check the order in Google Sheet.",
    "download_txt": "Download order number (.txt)",
    "image_coming": "Product image coming soon",
    "name_error": "Please enter your name more clearly.",
    "email_required": "Please enter an email address.",
    "email_error": "Please check the email address.",
    "phone_error": "Please check the phone number.",
    "company_name_error": "Please enter the company name.",
    "business_id_error": "Please enter the business ID.",
    "contact_person_error": "Please enter the contact person.",
    "street_error": "Please enter the street address.",
    "postal_error": "Please enter the postal code.",
    "city_error": "Please enter the city.",
    "billing_street_error": "Please enter the billing street address.",
    "billing_postal_error": "Please enter the billing postal code.",
    "billing_city_error": "Please enter the billing city.",
    "honeypot_error": "The submission could not be processed. Please try again in a moment.",
    "wait_error": "Please wait a moment before sending another order ({remaining} s).",
    "save_error": "There was a problem saving the order. Please try again in a moment.",
    "receipt_thanks": "Warm thanks for your order!",
    "receipt_address": "Delivery address",
    "receipt_items": "Order contents",
    "receipt_time": "Time",
    "receipt_customer": "Customer",
    "internal_draft_intro": "Ready-made suggestion for the customer's order confirmation:",
    "owner_new_order": "New order to the honey shop #{order_id}",
    "owner_order_received": "A new order has arrived at the honey shop.",
    "sheet_link": "Google Sheet",
    "receipt_greeting": "Hello {name},",
    "receipt_email_body": "thank you for your order from Hunajapuoti.\n\nWe have received your order:\n{lines}\n\nTotal: {total}\n\nYour order is being processed. We will separately confirm product availability and send you an order confirmation by email shortly.\n\nBest regards,\nNina\nHunajapuoti",
    "payment_pref_label": "Preferred payment method",
    "payment_link_note": "Add a payment link to the order confirmation according to the customer's selected payment method.",
    "p1_name": "Summer Honey 250 g",
    "p1_desc": "Soft and floral summer honey for small everyday treats.",
    "p2_name": "Summer Honey 500 g",
    "p2_desc": "A generous jar of soft summer honey for the whole family.",
    "p3_name": "Forest Honey 250 g",
    "p3_desc": "Darker and fuller forest honey for those who enjoy a stronger taste.",
    "p4_name": "Gift Set",
    "p4_desc": "A beautiful honey gift with three small jars.",
}

def t(key: str, **kwargs) -> str:
    lang = st.session_state.get("lang", "fi")
    text = TRANSLATIONS[lang].get(key, key)
    return text.format(**kwargs) if kwargs else text

def inject_styles() -> None:
    css = """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@400;500;600;700&family=Marck+Script&display=swap');
        .stApp { background: linear-gradient(180deg, #fffaf2 0%, #f6efe2 100%); font-family: 'Quicksand', sans-serif; }
        .block-container { padding-top: 3.8rem; padding-bottom: 2.2rem; max-width: 1180px; }
        section[data-testid="stSidebar"], button[kind="header"], [data-testid="collapsedControl"] { display: none !important; }
        html, body, [class*="css"], [data-testid="stAppViewContainer"], [data-testid="stMarkdownContainer"], [data-testid="stText"], [data-testid="stMetricLabel"], [data-testid="stMetricValue"], .stTextInput label, .stTextArea label, .stSelectbox label { font-family: 'Quicksand', sans-serif; }
        h1, h2, h3 { color: #6f4e18; font-family: 'Quicksand', sans-serif; }
        .shop-title { font-family: 'Marck Script', cursive; font-size: 3.1rem; font-weight: 400; color: #7a5216; margin-bottom: 0.2rem; line-height: 1.1; }
        .shop-subtitle { font-size: 1.1rem; color: #8b6a2b; margin-bottom: 1.2rem; }
        .section-card, .intro-card, .steps-card { background: rgba(255, 248, 235, 0.82); border: 1px solid #e8d7b5; border-radius: 18px; padding: 1rem 1.2rem; margin-bottom: 1rem; box-shadow: 0 4px 14px rgba(111, 78, 24, 0.06); }
        .intro-title, .steps-title { color: #7a5216; font-size: 1.15rem; font-weight: 700; margin-bottom: 0.35rem; }
        .intro-text, .steps-list { color: #5f533d; line-height: 1.65; }
        .steps-list { margin: 0; padding-left: 1.15rem; }
        div[data-testid="stMetric"] { background: #fffaf2; border: 1px solid #ecdcb9; padding: 0.55rem 0.8rem; border-radius: 14px; }
        .stButton > button, .stDownloadButton > button, div[data-testid="stFormSubmitButton"] > button { background-color: #c48a1d; color: white; border: none; border-radius: 999px; padding: 0.55rem 1.1rem; font-weight: 600; }
        .stButton > button:hover, .stDownloadButton > button:hover, div[data-testid="stFormSubmitButton"] > button:hover { background-color: #a96f0c; color: white; }
        .small-note, .product-description { color: #5f533d; }
        .product-description { min-height: 3em; }
        .placeholder-box { border: 1px dashed #d9c49b; border-radius: 16px; background: rgba(255,248,235,0.65); color: #8b6a2b; padding: 2.2rem 1rem; text-align: center; margin-bottom: 0.5rem; }
        .cart-header, .cart-row { background: rgba(255, 248, 235, 0.82); border: 1px solid #e8d7b5; border-radius: 14px; padding: 0.65rem 0.9rem; margin-bottom: 0.55rem; }
        .cart-header { font-weight: 700; color: #7a5216; }
        .cart-product { color: #6f4e18; font-weight: 700; line-height: 1.3; }
        .cart-price, .cart-sum { color: #8b6a2b; font-size: 0.97rem; padding-top: 0.15rem; }
        .lang-switcher-wrap { margin-top: 0.2rem; margin-bottom: 0.85rem; }
        div[data-testid="stTextInput"]:has(input[aria-label="Website"]) { display: none; }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

def euro_fi(value: float) -> str:
    return f"{value:.2f}".replace(".", ",") + " €"

def render_language_switcher() -> None:
    lang = st.session_state.get("lang", "fi")
    st.markdown('<div class="lang-switcher-wrap"></div>', unsafe_allow_html=True)
    cols = st.columns([8, 0.8, 0.8, 0.8])
    with cols[1]:
        if st.button("FI", use_container_width=True, type="primary" if lang == "fi" else "secondary"):
            st.session_state.lang = "fi"; st.rerun()
    with cols[2]:
        if st.button("SV", use_container_width=True, type="primary" if lang == "sv" else "secondary"):
            st.session_state.lang = "sv"; st.rerun()
    with cols[3]:
        if st.button("EN", use_container_width=True, type="primary" if lang == "en" else "secondary"):
            st.session_state.lang = "en"; st.rerun()

def translated_name_map() -> dict:
    return {"Kesähunaja 250 g": t("p1_name"), "Kesähunaja 500 g": t("p2_name"), "Metsähunaja 250 g": t("p3_name"), "Lahjapakkaus": t("p4_name")}

def translated_desc_map() -> dict:
    return {"Kesähunaja 250 g": t("p1_desc"), "Kesähunaja 500 g": t("p2_desc"), "Metsähunaja 250 g": t("p3_desc"), "Lahjapakkaus": t("p4_desc")}

def payment_options() -> list[str]:
    return [t("pay_mobilepay"), t("pay_card"), t("pay_bank"), t("pay_invoice"), t("pay_cash")]

def load_products() -> pd.DataFrame:
    df = pd.read_csv(PRODUCTS_FILE)
    df["price"] = df["price"].astype(float)
    df["stock"] = df["stock"].astype(int)
    df["display_name"] = df["name"].map(translated_name_map())
    df["description"] = df["name"].map(translated_desc_map())
    return df

def get_product_image(product_name: str) -> Path | None:
    image_path = IMAGE_MAP.get(product_name)
    return image_path if image_path and image_path.exists() else None

def get_gsheet_worksheet():
    gc = gspread.service_account_from_dict(dict(st.secrets["gcp_service_account"]))
    return gc.open(SHEET_NAME).sheet1

def init_state() -> None:
    for key, value in {"cart": {}, "last_order": None, "last_email_error": None, "last_submit_ts": 0.0, "lang": "fi"}.items():
        if key not in st.session_state:
            st.session_state[key] = value

def add_to_cart(product_id: int, quantity: int) -> None:
    st.session_state.cart[product_id] = st.session_state.cart.get(product_id, 0) + quantity

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
            parts.append(f"{product['display_name']} x {qty} = {euro_fi(float(product['price']) * int(qty))}")
    return " | ".join(parts)

def order_lines(products: pd.DataFrame) -> list[str]:
    lines = []
    for product_id, qty in st.session_state.cart.items():
        match = products.loc[products["id"] == product_id]
        if not match.empty:
            product = match.iloc[0]
            lines.append(f"- {product['display_name']} x {qty} = {euro_fi(float(product['price']) * int(qty))}")
    return lines

def next_order_id(worksheet) -> str:
    today = datetime.now().strftime("%Y%m%d")
    prefix = f"HN-{today}-"
    try:
        order_ids = worksheet.col_values(2)[1:]
    except Exception:
        order_ids = []
    max_seq = 0
    for oid in order_ids:
        if oid.startswith(prefix):
            try:
                max_seq = max(max_seq, int(oid.split("-")[-1]))
            except Exception:
                pass
    return f"{prefix}{max_seq + 1:03d}"

def ensure_sheet_header() -> None:
    worksheet = get_gsheet_worksheet()
    expected = [
        "timestamp", "order_id", "customer_type", "company_name", "business_id", "contact_person",
        "reference_info", "customer_name", "email", "phone", "delivery_method", "payment_method",
        "street_address", "postal_code", "city", "billing_same_as_delivery", "billing_street_address",
        "billing_postal_code", "billing_city", "notes", "items", "total_eur", "language"
    ]
    if worksheet.row_values(1) != expected:
        worksheet.update("A1:W1", [expected])

def save_order(customer_type: str, company_name: str, business_id: str, contact_person: str, reference_info: str,
               customer_name: str, email: str, phone: str, delivery_method: str, payment_method: str,
               street_address: str, postal_code: str, city: str, billing_same_as_delivery: str,
               billing_street_address: str, billing_postal_code: str, billing_city: str, notes: str,
               products: pd.DataFrame) -> tuple[str, str, float, str]:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    items = serialize_items(products)
    total = cart_total(products)
    ensure_sheet_header()
    worksheet = get_gsheet_worksheet()
    order_id = next_order_id(worksheet)
    worksheet.append_row([
        timestamp, order_id, customer_type, company_name, business_id, contact_person, reference_info,
        customer_name, email, phone, delivery_method, payment_method, street_address, postal_code, city,
        billing_same_as_delivery, billing_street_address, billing_postal_code, billing_city, notes, items, total,
        st.session_state.lang
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

def send_owner_notification(customer_type: str, company_name: str, business_id: str, contact_person: str, reference_info: str,
                            customer_name: str, customer_email: str, phone: str, delivery_method: str, payment_method: str,
                            street_address: str, postal_code: str, city: str, billing_same_as_delivery: str,
                            billing_street_address: str, billing_postal_code: str, billing_city: str, notes: str,
                            order_id: str, timestamp: str, total: float, products: pd.DataFrame) -> None:
    app_cfg = st.secrets["app_config"]
    lines = "\n".join(order_lines(products))
    address_block = "-" if delivery_method == t("pickup") else f"{street_address}, {postal_code} {city}"
    if billing_same_as_delivery == "yes":
        billing_block = address_block
    else:
        billing_block = f"{billing_street_address}, {billing_postal_code} {billing_city}"
    draft_reply = f"{t('receipt_greeting', name=customer_name)}\n\n{t('receipt_email_body', lines=lines, total=euro_fi(total))}\n"
    owner_body = f"""{t('owner_order_received')}

{t('receipt_time')}: {timestamp}
{t('customer_type')}: {customer_type}
{t('receipt_customer')}: {customer_name}
{t('email').replace(' *','')}: {customer_email}
{t('phone')}: {phone}
{t('delivery_method')}: {delivery_method}
{t('payment_pref_label')}: {payment_method}
{t('receipt_address')}: {address_block}
{t('billing_title')}: {billing_block}
{t('notes')}: {notes or '-'}

"""
    if customer_type == t("business_customer"):
        owner_body += f"""{t('company_name').replace(' *','')}: {company_name}
{t('business_id').replace(' *','')}: {business_id}
{t('contact_person').replace(' *','')}: {contact_person}
{t('reference_info')}: {reference_info or '-'}
"""
    owner_body += f"""
{t('receipt_items')}:
{lines}

{t('total')}: {euro_fi(total)}

{t('payment_link_note')}

{t('sheet_link')}:
{app_cfg["google_sheet_url"]}

{t('internal_draft_intro')}

{draft_reply}
"""
    send_email(t('owner_new_order', order_id=order_id), owner_body, app_cfg["owner_email"], cc_email=app_cfg.get("cc_email"))

def build_order_receipt_text(order_data: dict) -> str:
    item_lines = order_data["items"].replace(" | ", "\n")
    address_block = "-" if order_data["delivery_method"] == t("pickup") else f"{order_data['street_address']}, {order_data['postal_code']} {order_data['city']}"
    lines = [
        t('shop_title'),
        "",
        f"{t('receipt_time')}: {order_data['timestamp']}",
        f"{t('customer_type')}: {order_data['customer_type']}",
        f"{t('receipt_customer')}: {order_data['customer_name']}",
        f"{t('email').replace(' *','')}: {order_data['email']}",
        f"{t('phone')}: {order_data['phone']}",
        f"{t('delivery_method')}: {order_data['delivery_method']}",
        f"{t('payment_pref_label')}: {order_data['payment_method']}",
        f"{t('receipt_address')}: {address_block}",
    ]
    if order_data['customer_type'] == t('business_customer'):
        lines.extend([
            f"{t('company_name').replace(' *','')}: {order_data['company_name']}",
            f"{t('business_id').replace(' *','')}: {order_data['business_id']}",
            f"{t('contact_person').replace(' *','')}: {order_data['contact_person']}",
            f"{t('reference_info')}: {order_data['reference_info'] or '-'}",
        ])
    lines.extend([
        "",
        f"{t('receipt_items')}:",
        item_lines,
        "",
        f"{t('total')}: {euro_fi(order_data['total'])}",
        "",
        t('processing_info'),
        "",
        t('receipt_thanks'),
    ])
    return "\n".join(lines)

def show_last_order_box() -> None:
    if not st.session_state.last_order:
        return
    od = st.session_state.last_order
    st.success(t("success_order", order_id=od["order_id"]))
    st.info(t("processing_info"))
    if st.session_state.last_email_error:
        st.warning(t("mail_warn"))
    st.download_button(t("download_txt"), build_order_receipt_text(od).encode("utf-8"), file_name=f"tilaus_{od['order_id']}.txt", mime="text/plain")

def render_hero() -> None:
    render_language_switcher()
    if HERO_IMAGE.exists():
        st.image(str(HERO_IMAGE), use_container_width=True)
    st.markdown(f"<div class='shop-title'>{t('shop_title')}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='shop-subtitle'>{t('shop_subtitle')}</div>", unsafe_allow_html=True)

def render_intro() -> None:
    st.markdown(f"<div class='intro-card'><div class='intro-title'>{t('welcome_title')}</div><div class='intro-text'>{t('welcome_text')}</div></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='steps-card'><div class='steps-title'>{t('steps_title')}</div><ol class='steps-list'><li>{t('step_1')}</li><li>{t('step_2')}</li><li>{t('step_3')}</li><li>{t('step_4')}</li></ol></div>", unsafe_allow_html=True)

def render_missing_image_placeholder() -> None:
    st.markdown(f"<div class='placeholder-box'>{t('image_coming')}</div>", unsafe_allow_html=True)

def product_card(product: pd.Series) -> None:
    image_path = get_product_image(str(product["name"]))
    with st.container(border=True):
        if image_path:
            st.image(str(image_path), use_container_width=True)
        else:
            render_missing_image_placeholder()
        st.subheader(product["display_name"])
        st.markdown(f"<div class='product-description'>{product['description']}</div>", unsafe_allow_html=True)
        st.metric(t("unit_price"), euro_fi(float(product["price"])))
        qty = st.number_input(f"{product['display_name']} {t('quantity')}", min_value=1, max_value=max(1, int(product["stock"])), value=1, key=f"qty_{product['id']}")
        if st.button(t("add"), key=f"add_{product['id']}", use_container_width=True):
            add_to_cart(int(product["id"]), int(qty))
            clear_last_order()
            st.success(f"{t('add')}: {product['display_name']} ({qty})")

def storefront(products: pd.DataFrame) -> None:
    render_hero()
    render_intro()
    st.markdown(f"<div class='section-card'><h3>{t('products_title')}</h3><div class='small-note'>{t('products_note')}</div></div>", unsafe_allow_html=True)
    cols = st.columns(2)
    for idx, (_, product) in enumerate(products.iterrows()):
        with cols[idx % 2]:
            product_card(product)

def cart_view(products: pd.DataFrame) -> None:
    st.markdown(f"### {t('cart_title')}")
    if not st.session_state.cart:
        st.info(t("cart_empty"))
        return
    header_cols = st.columns([3.8, 1.3, 1.3, 1.3, 1.3])
    for col, title in zip(header_cols, [t("product_col"), t("unit_price"), t("quantity"), t("total"), ""]):
        with col:
            st.markdown(f"<div class='cart-header'>{title}</div>", unsafe_allow_html=True)
    for product_id, current_qty in list(st.session_state.cart.items()):
        match = products.loc[products["id"] == product_id]
        if match.empty:
            continue
        product = match.iloc[0]
        line_total = float(product["price"]) * int(current_qty)
        cols = st.columns([3.8, 1.3, 1.3, 1.3, 1.3])
        with cols[0]:
            st.markdown(f"<div class='cart-row'><div class='cart-product'>{product['display_name']}</div></div>", unsafe_allow_html=True)
        with cols[1]:
            st.markdown(f"<div class='cart-row'><div class='cart-price'>{euro_fi(float(product['price']))}</div></div>", unsafe_allow_html=True)
        with cols[2]:
            new_qty = st.number_input(f"{product['display_name']} {t('quantity')}", min_value=0, max_value=max(0, int(product['stock'])), value=int(current_qty), key=f"cart_edit_{product_id}", label_visibility="collapsed")
        with cols[3]:
            st.markdown(f"<div class='cart-row'><div class='cart-sum'>{euro_fi(line_total)}</div></div>", unsafe_allow_html=True)
        with cols[4]:
            if st.button(t("remove"), key=f"remove_{product_id}", use_container_width=True):
                update_cart(product_id, 0)
                clear_last_order()
                st.rerun()
        if new_qty != current_qty:
            update_cart(product_id, int(new_qty))
            clear_last_order()
            st.rerun()
    st.markdown(f"#### {t('add_more')}")
    add_cols = st.columns([3.2, 1.2, 1.2])
    with add_cols[0]:
        options = [("", "")] + [(name, display) for name, display in zip(products["name"], products["display_name"])]
        display_options = [d for _, d in options]
        selected_display = st.selectbox(t("select_product"), display_options, key="cart_add_product")
        selected_name = next((internal for internal, display in options if display == selected_display), "")
    with add_cols[1]:
        add_qty = st.number_input(t("quantity"), min_value=1, value=1, key="cart_add_qty")
    with add_cols[2]:
        st.write(""); st.write("")
        if st.button(t("add"), key="cart_add_button", use_container_width=True) and selected_name:
            match = products.loc[products["name"] == selected_name]
            if not match.empty:
                add_to_cart(int(match.iloc[0]["id"]), int(add_qty))
                clear_last_order()
                st.rerun()
    st.subheader(f"{t('total')}: {euro_fi(cart_total(products))}")
    if st.button(t("clear_cart")):
        clear_cart()
        clear_last_order()
        st.rerun()

def is_valid_email(email: str) -> bool:
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email.strip()))

def is_valid_phone(phone: str) -> bool:
    if not phone.strip():
        return True
    return len(re.sub(r"\D", "", phone.strip())) >= 7

def validate_order_form(customer_type: str, company_name: str, business_id: str, contact_person: str,
                        email: str, phone: str, delivery_method: str, street_address: str,
                        postal_code: str, city: str, billing_same_as_delivery: bool,
                        billing_street_address: str, billing_postal_code: str, billing_city: str,
                        honeypot: str) -> str | None:
    if honeypot.strip():
        return t("honeypot_error")
    if customer_type == t("business_customer"):
        if not company_name.strip():
            return t("company_name_error")
        if not business_id.strip():
            return t("business_id_error")
        if not contact_person.strip():
            return t("contact_person_error")
    else:
        if len(contact_person.strip()) < 2:
            return t("name_error")
    if not email.strip():
        return t("email_required")
    if not is_valid_email(email):
        return t("email_error")
    if not is_valid_phone(phone):
        return t("phone_error")
    if delivery_method != t("pickup"):
        if not street_address.strip():
            return t("street_error")
        if not postal_code.strip():
            return t("postal_error")
        if not city.strip():
            return t("city_error")
    if customer_type == t("business_customer") and not billing_same_as_delivery:
        if not billing_street_address.strip():
            return t("billing_street_error")
        if not billing_postal_code.strip():
            return t("billing_postal_error")
        if not billing_city.strip():
            return t("billing_city_error")
    seconds_since_last = time.time() - float(st.session_state.last_submit_ts)
    if seconds_since_last < MIN_SECONDS_BETWEEN_ORDERS:
        return t("wait_error", remaining=int(MIN_SECONDS_BETWEEN_ORDERS - seconds_since_last) + 1)
    return None

def checkout_form(products: pd.DataFrame) -> None:
    st.markdown(f"### {t('send_order')}")
    show_last_order_box()
    if not st.session_state.cart:
        st.caption(t("add_first"))
        return
    delivery_options = [t("pickup"), t("local_delivery"), t("shipping")]
    payment_choices = payment_options()
    customer_type_options = [t("private_customer"), t("business_customer")]
    with st.form("checkout_form"):
        customer_type = st.selectbox(t("customer_type"), customer_type_options)

        company_name = business_id = reference_info = ""
        billing_same_as_delivery = True
        billing_street_address = billing_postal_code = billing_city = ""

        if customer_type == t("business_customer"):
            st.markdown(f"#### {t('business_title')}")
            company_name = st.text_input(t("company_name"))
            business_id = st.text_input(t("business_id"))
            contact_person = st.text_input(t("contact_person"))
            reference_info = st.text_input(t("reference_info"))
        else:
            st.markdown(f"#### {t('customer_details')}")
            contact_person = st.text_input(t("name"))

        email = st.text_input(t("email"))
        phone = st.text_input(t("phone"))
        delivery_method = st.selectbox(t("delivery_method"), delivery_options)
        payment_method = st.selectbox(t("payment_method"), payment_choices)

        st.markdown(f"#### {t('address_title')}")
        street_address = st.text_input(t("street_address"))
        col1, col2 = st.columns(2)
        with col1:
            postal_code = st.text_input(t("postal_code"))
        with col2:
            city = st.text_input(t("city"))

        if customer_type == t("business_customer"):
            st.markdown(f"#### {t('billing_title')}")
            billing_same_as_delivery = st.checkbox(t("billing_same_as_delivery"), value=True)
            if not billing_same_as_delivery:
                billing_street_address = st.text_input(t("billing_street_address"))
                b1, b2 = st.columns(2)
                with b1:
                    billing_postal_code = st.text_input(t("billing_postal_code"))
                with b2:
                    billing_city = st.text_input(t("billing_city"))
            else:
                billing_street_address = street_address
                billing_postal_code = postal_code
                billing_city = city

        notes = st.text_area(t("notes"))
        honeypot = st.text_input("Website", value="")
        submitted = st.form_submit_button(t("send_order"))

        if submitted:
            validation_error = validate_order_form(
                customer_type, company_name, business_id, contact_person, email, phone,
                delivery_method, street_address, postal_code, city, billing_same_as_delivery,
                billing_street_address, billing_postal_code, billing_city, honeypot
            )
            if validation_error:
                st.error(validation_error)
                return
            try:
                with st.spinner("Tallennetaan tilausta..."):
                    order_id, timestamp, total, items = save_order(
                        customer_type, company_name.strip(), business_id.strip(), contact_person.strip(), reference_info.strip(),
                        contact_person.strip(), email.strip(), phone.strip(), delivery_method, payment_method,
                        street_address.strip(), postal_code.strip(), city.strip(),
                        "yes" if billing_same_as_delivery else "no",
                        billing_street_address.strip(), billing_postal_code.strip(), billing_city.strip(),
                        notes.strip(), products
                    )
                st.session_state.last_submit_ts = time.time()
                st.session_state.last_email_error = None
                try:
                    with st.spinner("Lähetetään ilmoitus puodille..."):
                        send_owner_notification(
                            customer_type, company_name.strip(), business_id.strip(), contact_person.strip(), reference_info.strip(),
                            contact_person.strip(), email.strip(), phone.strip(), delivery_method, payment_method,
                            street_address.strip(), postal_code.strip(), city.strip(),
                            "yes" if billing_same_as_delivery else "no",
                            billing_street_address.strip(), billing_postal_code.strip(), billing_city.strip(),
                            notes.strip(), order_id, timestamp, total, products
                        )
                except Exception as e:
                    st.session_state.last_email_error = str(e)
                st.session_state.last_order = {
                    "order_id": order_id, "timestamp": timestamp, "customer_type": customer_type,
                    "company_name": company_name.strip(), "business_id": business_id.strip(), "contact_person": contact_person.strip(),
                    "reference_info": reference_info.strip(), "customer_name": contact_person.strip(), "email": email.strip(),
                    "phone": phone.strip(), "delivery_method": delivery_method, "payment_method": payment_method,
                    "street_address": street_address.strip(), "postal_code": postal_code.strip(), "city": city.strip(),
                    "items": items, "total": total,
                }
                clear_cart()
                st.balloons()
                st.rerun()
            except Exception:
                st.error(t("save_error"))

def main() -> None:
    if "lang" not in st.session_state:
        st.session_state.lang = "fi"
    init_state()
    inject_styles()
    products = load_products()
    storefront(products)
    st.markdown("---")
    cart_view(products)
    st.markdown("---")
    checkout_form(products)

if __name__ == "__main__":
    main()
