import streamlit as st
import pandas as pd
import re
from openai import OpenAI

# ==============================
# IA SETUP
# ==============================
client = None

# ==============================
# CONFIG
# ==============================
st.set_page_config(page_title="Generador Evolutivos Clínicos", layout="wide")
st.title("🩺 Generador de evolutivos clínicos")

with st.expander("🔐 Configuración IA (opcional)"):
    api_key = st.text_input("API Key", type="password")
    model = st.selectbox("Modelo", ["gpt-4.1-mini", "gpt-4.1", "gpt-5-mini"])
    usar_ia = st.checkbox("Usar IA como corrector de estilo", value=False)

    if api_key:
        client = OpenAI(api_key=api_key)

# ==============================
# FUNCIONES
# ==============================

def limpio(v):
    v = str(v).strip()
    return v if v != "" else None


# ==============================
# 🧪 PARSER ANALÍTICA
# ==============================

def extraer_valor_general(texto, claves):
    for clave in claves:
        patron = rf"{clave}[^0-9\-]*([\d.,]+)"
        m = re.search(patron, texto, re.IGNORECASE)
        if m:
            return m.group(1).replace(",", ".")
    return None


def parsear_analitica(texto):
    if not texto or texto.strip() == "":
        return ""

    t = texto.lower()

    fecha_match = re.search(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", texto)
    fecha = fecha_match.group(0) if fecha_match else ""

    cabecera = "- Analítica sanguínea"
    if fecha:
        cabecera += f" ({fecha})"
    cabecera += ":"

    bloques = []

    # Hemograma
    hb = extraer_valor_general(t, ["hemoglobina", "hb"])
    leu = extraer_valor_general(t, ["leucocitos"])
    plt = extraer_valor_general(t, ["plaquetas"])

    hemograma = []
    if hb:
        hemograma.append(f"Hb {hb}")
    if leu:
        hemograma.append(f"leucocitos {leu}")
    if plt:
        hemograma.append(f"plaquetas {plt}")

    if hemograma:
        bloques.append("   - Hemograma: " + ", ".join(hemograma))

    # Coagulación
    inr = extraer_valor_general(t, ["inr"])
    if inr:
        bloques.append(f"   - Coagulación: INR {inr}")

    # Bioquímica
    glc = extraer_valor_general(t, ["glucosa"])
    urea = extraer_valor_general(t, ["urea"])
    crea = extraer_valor_general(t, ["creatinina"])
    fg = extraer_valor_general(t, ["filtrado", "ckd-epi"])
    na = extraer_valor_general(t, ["sodio", r"\bna\b"])
    k = extraer_valor_general(t, [r"\bk\b", "potasio"])
    cl = extraer_valor_general(t, ["cloro", r"\bcl\b"])
    mg = extraer_valor_general(t, ["magnesio"])
    pcr = extraer_valor_general(t, ["proteina c reactiva", "pcr"])
    pct = extraer_valor_general(t, ["procalcitonina", "pct"])

    bio = []
    if glc:
        bio.append(f"glc {glc}")
    if urea:
        bio.append(f"urea {urea}")
    if crea:
        bio.append(f"creatinina {crea}")
    if fg:
        bio.append(f"filtrado glomerular {fg}")
    if na:
        bio.append(f"Na {na}")
    if k:
        bio.append(f"K {k}")
    if cl:
        bio.append(f"Cl {cl}")
    if mg:
        bio.append(f"magnesio {mg}")
    if pcr:
        bio.append(f"PCR {pcr}")
    if pct:
        bio.append(f"PCT {pct}")

    if bio:
        bloques.append("   - Bioquímica: " + ", ".join(bio))

    if not bloques:
        return ""

    return cabecera + "\n" + "\n".join(bloques)


# ==============================
# FRASE INICIAL
# ==============================
def frase_inicial(row):
    partes = []

    posicion = limpio(row.get("se encuentra"))
    if posicion:
        partes.append(f"se encuentra {posicion}")

    deamb = limpio(row.get("deambulación"))
    if deamb:
        partes.append("no deambula" if "no" in deamb.lower() else "deambula")

    disnea = limpio(row.get("disnea (mejora/igual/empeora)"))
    if disnea:
        partes.append(f"refiere {disnea} de la disnea")

    ortopnea = limpio(row.get("ortopnea (sí/no)"))
    if ortopnea:
        partes.append("con ortopnea" if ortopnea.lower() in ["sí", "si"] else "sin ortopnea")

    texto = "El paciente " + ", ".join(partes) + "."

    extras = []
    if row.get("dolor torácico (sí/no)") == "No":
        extras.append("sin dolor torácico")
    if row.get("palpitaciones (sí/no)") == "No":
        extras.append("sin palpitaciones")
    if row.get("mareo (sí/no)") == "No":
        extras.append("sin mareo")

    if extras:
        texto += " " + ", ".join(extras) + "."

    otros = limpio(row.get("otros anamnesis"))
    if otros:
        extra = otros.strip().capitalize()
        if not extra.endswith("."):
            extra += "."
        texto += " " + extra

    return texto


# ==============================
# EXPLORACIÓN
# ==============================
def exploracion_fisica(row):
    bloques = []

    for campo, etiqueta in [
        ("constantes", "Constantes"),
        ("general", "General"),
        ("vyi", "VYI"),
        ("exploración cardiaca", "Auscultación cardiaca"),
        ("exploración pulmonar", "Auscultación pulmonar"),
        ("edemas mmii", "MMII"),
        ("otros ef", "Otros EF"),
    ]:
        valor = limpio(row.get(campo))
        if valor:
            bloques.append(f"- {etiqueta}: {valor}")

    if not bloques:
        return ""

    return "Exploración física:\n" + "\n".join(bloques)


# ==============================
# PPCC
# ==============================
def pruebas_complementarias(row):
    bloques = []

    analitica = parsear_analitica(row.get("as"))
    if analitica:
        bloques.append(analitica)

    for campo in ["rx", "ecg", "ecocardiograma"]:
        valor = limpio(row.get(campo))
        if valor:
            bloques.append(f"- {campo.upper()}: {valor}")

    if not bloques:
        return ""

    return "PPCC:\n" + "\n".join(bloques)


# ==============================
# PLAN
# ==============================
def plan(row):
    bloques = []

    for campo, etiqueta in [
        ("furosemida", "Furosemida"),
        ("otros tratamientos", "Otros"),
        ("plan", "Plan previo"),
    ]:
        valor = limpio(row.get(campo))
        if valor:
            bloques.append(f"- {etiqueta}: {valor}")

    if not bloques:
        return ""

    return "Plan:\n" + "\n".join(bloques)


# ==============================
# GENERADOR
# ==============================
def generar_evolutivo(row):
    partes = []

    partes.append(frase_inicial(row))

    ef = exploracion_fisica(row)
    if ef:
        partes.append("\n" + ef)

    ppcc = pruebas_complementarias(row)
    if ppcc:
        partes.append("\n" + ppcc)

    pl = plan(row)
    if pl:
        partes.append("\n" + pl)

    return "\n".join(partes)


# ==============================
# IA
# ==============================
def corregir_con_ia(texto, model):
    if client is None:
        return texto

    try:
        resp = client.responses.create(
            model=model,
            input=(
                "Corrige el estilo del siguiente evolutivo clínico en español. "
                "NO añadas información. NO inventes datos. "
                "Mantén exactamente el contenido:\n\n" + texto
            ),
            temperature=0
        )
        return resp.output_text.strip()
    except Exception:
        return texto


# ==============================
# APP
# ==============================
archivo = st.file_uploader("Sube tu Excel", type=["xlsx"])

if archivo:
    df = pd.read_excel(archivo)

    # NORMALIZACIÓN CLAVE
    df.columns = (
        df.columns
        .str.strip()
        .str.replace("\n", "")
        .str.lower()
    )

    # ELIMINAR DUPLICADAS
    df = df.loc[:, ~df.columns.duplicated()]

    df = df.fillna("")

    st.success("Archivo cargado correctamente")
    st.write("Columnas detectadas:", df.columns.tolist())

    if st.button("⚙️ Generar evolutivos"):
        resultados = []

        for _, row in df.iterrows():
            texto = generar_evolutivo(row)

            if usar_ia:
                texto = corregir_con_ia(texto, model)

            resultados.append({
                "HCIS": limpio(row.get("hcis")) or "",
                "Evolutivo": texto
            })

        df_resultado = pd.DataFrame(resultados)

        st.dataframe(df_resultado, use_container_width=True)

        csv = df_resultado.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Descargar CSV", csv, "evolutivos.csv", "text/csv")

        st.subheader("📋 Copiar rápido")
        for _, r in df_resultado.iterrows():
            st.text_area(f"HCIS {r['HCIS']}", r["Evolutivo"], height=200)

else:
    st.info("Sube el Excel para empezar")
