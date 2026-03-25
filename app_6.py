import streamlit as st
import pandas as pd
import os
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
# 🧪 NUEVO PARSER ANALÍTICA
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

    # FECHA
    fecha_match = re.search(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", texto)
    fecha = fecha_match.group(0) if fecha_match else ""

    cabecera = "- Analítica sanguínea"
    if fecha:
        cabecera += f" ({fecha})"
    cabecera += ":"

    bloques = []

    # HEMOGRAMA
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

    # COAGULACIÓN
    inr = extraer_valor_general(t, ["inr"])
    if inr:
        bloques.append(f"   - Coagulación: INR {inr}")

    # BIOQUÍMICA
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

    # GASOMETRÍA
    ph = extraer_valor_general(t, [r"\bph\b"])
    pco2 = extraer_valor_general(t, ["pco2"])
    po2 = extraer_valor_general(t, ["po2"])
    hco3 = extraer_valor_general(t, ["hco3", "bicarbonato"])
    sbc = extraer_valor_general(t, ["sbc"])
    lact = extraer_valor_general(t, ["lactato"])
    gap = extraer_valor_general(t, ["gap"])

    gaso = []
    if ph:
        gaso.append(f"pH {ph}")
    if pco2:
        gaso.append(f"PCO2 {pco2}")
    if po2:
        gaso.append(f"PO2 {po2}")
    if hco3:
        gaso.append(f"HCO3 {hco3}")
    if sbc:
        gaso.append(f"SBC {sbc}")
    if lact:
        gaso.append(f"lactato {lact}")
    if gap:
        gaso.append(f"GAP {gap}")

    if gaso:
        bloques.append("   - Gasometría venosa: " + ", ".join(gaso))

    if not bloques:
        return ""

    return cabecera + "\n" + "\n".join(bloques)


# ==============================
# 🟢 FRASE INICIAL
# ==============================
def frase_inicial(row):
    partes = []

    posicion = limpio(row.get("Se encuentra"))
    if posicion:
        partes.append(f"se encuentra {posicion}")

    deamb = limpio(row.get("Deambulación"))
    if deamb:
        if "no" in deamb.lower():
            partes.append("no deambula")
        else:
            partes.append("deambula")

    disnea = limpio(row.get("Disnea (mejora/igual/empeora)"))
    if disnea:
        partes.append(f"refiere {disnea} de la disnea")

    ortopnea = limpio(row.get("Ortopnea (Sí/No)"))
    if ortopnea:
        if ortopnea.lower() == "sí":
            partes.append("con ortopnea")
        else:
            partes.append("sin ortopnea")

    texto = "El paciente " + ", ".join(partes) + "."

    extras = []

    if row.get("Dolor torácico (Sí/No)") == "No":
        extras.append("sin dolor torácico")
    if row.get("Palpitaciones (Sí/No)") == "No":
        extras.append("sin palpitaciones")
    if row.get("Mareo (Sí/No)") == "No":
        extras.append("sin mareo")

    if extras:
        texto += " " + ", ".join(extras) + "."

    otros_anamnesis = limpio(row.get("Otros anamnesis"))
    if otros_anamnesis:
        extra = otros_anamnesis.strip().capitalize()
        if not extra.endswith("."):
            extra += "."
        texto += " " + extra

    return texto


# ==============================
# 🟢 EXPLORACIÓN
# ==============================
def exploracion_fisica(row):
    bloques = []

    if limpio(row.get("Constantes")):
        bloques.append(f"- Constantes: {row['Constantes']}")

    if limpio(row.get("General")):
        bloques.append(f"- General: {row['General']}")

    if limpio(row.get("VYI")):
        bloques.append(f"- VYI: {row['VYI']}")

    if limpio(row.get("Exploración cardiaca")):
        bloques.append(f"- Auscultación cardiaca: {row['Exploración cardiaca']}")

    if limpio(row.get("Exploración pulmonar")):
        bloques.append(f"- Auscultación pulmonar: {row['Exploración pulmonar']}")

    if limpio(row.get("Edemas MMII")):
        bloques.append(f"- MMII: {row['Edemas MMII']}")

    if limpio(row.get("Otros")):
        bloques.append(f"- Otros: {row['Otros']}")

    otros_ef = limpio(row.get("Otros EF"))
    if otros_ef:
        bloques.append(f"- Otros EF: {otros_ef.strip()}")

    if not bloques:
        return ""

    return "Exploración física:\n" + "\n".join(bloques)


# ==============================
# 🟢 PPCC
# ==============================
def pruebas_complementarias(row):
    bloques = []

    analitica = parsear_analitica(row.get("AS"))
    if analitica:
        bloques.append(analitica)

    if limpio(row.get("Rx")):
        bloques.append(f"- Rx: {row['Rx']}")

    if limpio(row.get("ECG")):
        bloques.append(f"- ECG: {row['ECG']}")

    if limpio(row.get("Ecocardiograma")):
        bloques.append(f"- Ecocardiograma: {row['Ecocardiograma']}")

    if not bloques:
        return ""

    return "PPCC:\n" + "\n".join(bloques)


# ==============================
# 🟢 PLAN
# ==============================
def plan(row):
    bloques = []

    if limpio(row.get("Furosemida")):
        bloques.append(f"- Furosemida: {row['Furosemida']}")

    if limpio(row.get("Otros tratamientos")):
        bloques.append(f"- Otros: {row['Otros tratamientos']}")

    if not bloques:
        return ""

    return "Plan:\n" + "\n".join(bloques)


# ==============================
# 🟢 GENERADOR
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
# 🟢 IA
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

    df.columns = df.columns.str.strip().str.replace("\n", "")
    df = df.fillna("")

    st.success("Archivo cargado correctamente")

    if st.button("⚙️ Generar evolutivos"):
        resultados = []

        for _, row in df.iterrows():
            texto = generar_evolutivo(row)

            if usar_ia:
                texto = corregir_con_ia(texto, model)

            resultados.append({
                "HCIS": row.get("HCIS", ""),
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
