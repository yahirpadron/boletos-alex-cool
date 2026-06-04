import streamlit as st
import sqlite3
import qrcode
from io import BytesIO
from PIL import Image, ImageDraw

# ---------------------------------------------------------
# 1. CONFIGURACIÓN DE LA PÁGINA (Estilo Móvil)
# ---------------------------------------------------------
st.set_page_config(page_title="Alex Cool - Ticket POS", page_icon="🎟️", layout="centered")

st.markdown("""
    <style>
    .main { background-color: #121212; color: #FFFFFF; }
    div.stButton > button:first-child {
        background-color: #27AE60; color: white; font-weight: bold;
        font-size: 18px; border-radius: 10px; border: none;
        height: 50px; width: 100%; display: block; margin: auto;
    }
    div.stButton > button:first-child:hover { background-color: #218C53; }
    h1, h2, h3 { color: #2ECC71 !important; text-align: center; }
    .stSelectbox, .stTextInput, .stNumberInput { background-color: #1E1E1E !important; }
    .card { background-color: #1E1E1E; padding: 20px; border-radius: 10px; border: 1px solid #333; margin-bottom: 15px; }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. BASE DE DATOS LOCAL
# ---------------------------------------------------------
def conectar_db():
    conn = sqlite3.connect("boletos_data.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reservaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            clave TEXT UNIQUE,
            evento TEXT,
            cliente TEXT,
            total_personas INTEGER,
            entrados INTEGER DEFAULT 0,
            pago REAL,
            mesa TEXT,
            estatus TEXT DEFAULT 'Sin Usar'
        )
    """)
    conn.commit()
    return conn, cursor

# ---------------------------------------------------------
# 3. GENERADOR DE IMAGEN DEL BOLETO CON LOGO JPEG
# ---------------------------------------------------------
def generar_imagen_boleto(clave, evento, cliente, personas, mesa):
    # 1. Crear el QR
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(clave)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="#141414", back_color="white").convert("RGB")
    qr_img = qr_img.resize((230, 230))

    # 2. Crear lienzo del boleto (Ancho: 420px, Alto: 680px)
    imagen = Image.new("RGB", (420, 680), "#141414")
    lienzo = ImageDraw.Draw(imagen)

    # Bordes del boleto
    lienzo.rectangle([12, 12, 408, 668], outline="#2ECC71", width=3)
    
    # 3. LEER EL LOGO JPEG DIRECTO DESDE TU ESCRITORIO
    pos_y_actual = 30
    try:
        # Apuntamos exactamente a tu archivo .jpeg
        logo = Image.open("logo_papa.jpeg").convert("RGB")
        # Cambiar el tamaño para que quepa perfecto de forma proporcional (Max 120px de alto)
        logo.thumbnail((220, 120), Image.Resampling.LANCZOS)
        
        # Calcular el centro horizontal
        ancho_logo, alto_logo = logo.size
        centro_x = (420 - ancho_logo) // 2
        
        # Pegar el logo en el lienzo
        imagen.paste(logo, (centro_x, pos_y_actual))
        pos_y_actual += alto_logo + 15
    except FileNotFoundError:
        # Respaldo por si se mueve el archivo
        lienzo.text((210, pos_y_actual + 20), "★ EVENTOS ALEX COOL ★", fill="#2ECC71", anchor="mm")
        pos_y_actual += 50

    # Línea divisoria debajo del logo
    lienzo.line([(40, pos_y_actual), (380, pos_y_actual)], fill="#27AE60", width=2)
    pos_y_actual += 20

    # 4. TEXTOS DEL BOLETO
    lienzo.text((210, pos_y_actual), "PASE DE ACCESO DIGITAL", fill="#888888", anchor="mm")
    pos_y_actual += 35
    
    lienzo.text((40, pos_y_actual), "EVENTO:", fill="#2ECC71")
    lienzo.text((40, pos_y_actual + 22), f"{evento.upper()}", fill="#F1C40F")
    pos_y_actual += 60

    lienzo.text((40, pos_y_actual), f"CLIENTE:  {cliente}", fill="white")
    pos_y_actual += 30
    lienzo.text((40, pos_y_actual), f"ACCESOS:  {personas} PERSONAS", fill="white")
    pos_y_actual += 30
    lienzo.text((40, pos_y_actual), f"MESA RESERVADA:  {mesa}", fill="white")
    pos_y_actual += 35

    # Línea divisoria antes del QR
    lienzo.line([(40, pos_y_actual), (380, pos_y_actual)], fill="#333333", width=1)
    pos_y_actual += 20

    # 5. PEGAR EL CÓDIGO QR
    centro_qr_x = (420 - 230) // 2
    imagen.paste(qr_img, (centro_qr_x, pos_y_actual))
    pos_y_actual += 245

    # Folio al fondo
    lienzo.text((210, pos_y_actual), f"FOLIO: {clave}", fill="#2ECC71", anchor="mm")

    buf = BytesIO()
    imagen.save(buf, format="PNG")
    return buf.getvalue()

# ---------------------------------------------------------
# 4. MENÚ DE NAVEGACIÓN PRINCIPAL
# ---------------------------------------------------------
pestana_papa, pestana_puerta = st.tabs(["📱 Papá: Generar Boletos", "🛡️ Tú: Control de Puerta"])

# --- PESTAÑA 1: EL LADO DE TU PAPÁ ---
with pestana_papa:
    st.title("🎟️ PANEL DE BOLETAJE")
    
    EVENTOS_DISPONIBLES = {
        "Gran Baile de Rock Urbano": "RUR",
        "Festival de Cerveza y Rock": "FCR",
        "Concierto Especial Alex Cool": "EAC"
    }

    evento_sel = st.selectbox("1. Selecciona el Evento:", list(EVENTOS_DISPONIBLES.keys()))
    nombre_cliente = st.text_input("2. Nombre completo del Cliente:").upper()
    cantidad_personas = st.number_input("3. Cantidad de Personas (Boletos):", min_value=1, max_value=100, value=1, step=1)
    opcion_mesa = st.radio("4. ¿Tiene Mesa Reservada?", ["NO", "SÍ"], horizontal=True)
    monto_pagado = st.number_input("5. Total Dinero Recibido ($):", min_value=0.0, value=0.0, step=50.0)
    str_personas = f"{cantidad_personas:02d}"

    st.markdown("---")

    if st.button("✨ GENERAR BOLETO PRO Y GUARDAR"):
        if not nombre_cliente.strip():
            st.error("❌ Por favor, escribe el nombre del cliente.")
        else:
            conn, cursor = conectar_db()
            prefijo = EVENTOS_DISPONIBLES[evento_sel]
            cursor.execute("SELECT COUNT(*) FROM reservaciones WHERE evento = ?", (evento_sel,))
            consecutivo = cursor.fetchone()[0] + 1
            clave_ticket = f"{prefijo}-{consecutivo}-{str_personas}"
            
            try:
                cursor.execute("""
                    INSERT INTO reservaciones (clave, evento, cliente, total_personas, pago, mesa)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (clave_ticket, evento_sel, nombre_cliente, cantidad_personas, monto_pagado, opcion_mesa))
                conn.commit()
                conn.close()

                st.success(f"✅ ¡Boleto guardado! Clave: {clave_ticket}")
                img_boleto = generar_imagen_boleto(clave_ticket, evento_sel, nombre_cliente, str_personas, opcion_mesa)
                st.image(img_boleto, caption="Vista Previa de Boleto Premium")
                st.download_button(label="📥 GUARDAR IMAGEN", data=img_boleto, file_name=f"boleto_{clave_ticket}.png", mime="image/png")
            except sqlite3.IntegrityError:
                st.error("Error de duplicación. Intenta de nuevo.")
                conn.close()

# --- PESTAÑA 2: EL LADO TUYO EN LA PUERTA ---
with pestana_puerta:
    st.title("🛡️ CONTROL DE ACCESO")
    st.markdown("### Buscador de Claves / Check-In")

    buscar_ticket = st.text_input("🔍 Ingresa la Clave del QR o Nombre del Cliente:").upper().strip()

    if buscar_ticket:
        conn, cursor = conectar_db()
        cursor.execute("""
            SELECT clave, cliente, total_personas, entrados, mesa, pago, estatus 
            FROM reservaciones 
            WHERE clave = ? OR cliente LIKE ?
        """, (buscar_ticket, f"%{buscar_ticket}%"))
        
        resultado = cursor.fetchone()
        
        if resultado:
            clave, cliente, total, entrados, mesa, pago, estatus = resultado
            disponibles = total - entrados

            if entrados == 0:
                color_alerta = "🟢 SIN USAR (Nadie ha entrado)"
            elif entrados < total:
                color_alerta = f"🟡 PARCIAL ({entrados} adentro, quedan {disponibles} por entrar)"
            else:
                color_alerta = "🔴 COMPLETADO (Todos los accesos usados)"

            st.markdown(f"""
                <div class="card">
                    <h3 style='color:#F1C40F !important; text-align:left;'>🎫 Ticket: {clave}</h3>
                    <b>👤 Cliente:</b> {cliente}<br>
                    <b>🛋️ ¿Tiene Mesa?:</b> {mesa}<br>
                    <b>💰 Pago Registrado:</b> ${pago:,.2f} MXN<br>
                    <hr style='border-color:#444;'>
                    <h3>Estatus: {color_alerta}</h3>
                    <p style='font-size:18px;'><b>Personas dentro:</b> {entrados} / {total}</p>
                </div>
            """, unsafe_allow_html=True)

            if disponibles > 0:
                st.markdown("### 📥 Registrar entrada parcial o total:")
                personas_a_ingresar = st.number_input(
                    f"¿Cuántas personas ingresan ahorita? (Máximo {disponibles}):", 
                    min_value=1, 
                    max_value=disponibles, 
                    value=min(1, disponibles),
                    step=1
                )
                
                if st.button("🚀 CONFIRMAR INGRESO"):
                    nuevos_entrados = entrados + personas_a_ingresar
                    nuevo_estatus = "Completado" if nuevos_entrados == total else "Parcial"
                    
                    cursor.execute("""
                        UPDATE reservaciones 
                        SET entrados = ?, estatus = ? 
                        WHERE clave = ?
                    """, (nuevos_entrados, nuevo_estatus, clave))
                    conn.commit()
                    st.success(f"⚡ ¡Acceso Registrado! Entraron {personas_a_ingresar} personas.")
                    st.rerun()
            else:
                st.error("❌ ALERTA: Este boleto ya agotó todos sus accesos.")
        else:
            st.error("❌ BOLETO NO ENCONTRADO.")
        
        conn.close()