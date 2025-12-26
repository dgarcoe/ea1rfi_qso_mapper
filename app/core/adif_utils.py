import streamlit as st
import adif_io
import pandas as pd
import re

def clean_adif_header(adif_str: str) -> str:
    """
    Eliminates the header
    """
    match = re.search(r"<EOH\s*>", adif_str, flags=re.IGNORECASE)
    if not match:
        # si no hay <EOH>, devuelve el contenido tal cual
        return adif_str
    # Devuelve el contenido a partir del primer carácter después de <EOH>
    return adif_str[match.end():].lstrip()

@st.cache_data(show_spinner="Parsing ADIF…")
def load_adif(file_bytes):

    adif_content = file_bytes.decode(encoding="ISO-8859-15", errors="ignore")
    adif_content_clean = clean_adif_header(adif_content)
    adif_data, _ = adif_io.read_from_string(adif_content_clean)

    return pd.DataFrame(adif_data)