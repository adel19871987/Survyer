import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
from shapely.geometry import Polygon
from fpdf import FPDF
import tempfile
import os
import ezdxf

st.set_page_config(page_title="مساحي مصغر", layout="wide", page_icon="📐")
st.title("📐 مساحي مصغر - أدواتك بالموقع")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["رفع النقاط", "الحسابات", "BM & الرفع", "التصدير", "التقرير PDF"])

if 'df' not in st.session_state:
    st.session_state.df = None
if 'bm_points' not in st.session_state:
    st.session_state.bm_points = None

def parse_dxf(uploaded_file):
    """يقرأ النقاط من ملف DXF بدون الحاجة لمسار ملف"""
    content = uploaded_file.read()
    doc = ezdxf.read(content)
    msp = doc.modelspace()
    points = []

    for entity in msp:
        if entity.dxftype() == 'POINT':
            points.append({
               
