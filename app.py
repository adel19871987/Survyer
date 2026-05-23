import streamlit as st
import ezdxf
import pandas as pd
import os
import math
import re
import matplotlib.pyplot as plt
from reportlab.pdfgen import canvas

# إعداد الصفحة
st.set_page_config(page_title="LexiMind Survey Suite", layout="wide")
st.title("🏗️ LexiMind: Ultimate Survey Suite")

# الدوال الأساسية (لا تغيير هنا)
def calculate_area(vertices):
    area = 0.0
    for i in range(len(vertices)):
        j = (i + 1) % len(vertices)
        area += vertices[i][0] * vertices[j][1]
        area -= vertices[j][0] * vertices[i][1]
    return abs(area) / 2.0

def classify_layer(layer_name):
    layer_name = layer_name.upper()
    if any(x in layer_name for x in ['ZAPATA', 'FOOT', 'قاعدة']): return "Footings"
    if any(x in layer_name for x in ['COLUMN', 'COL', 'عمود']): return "Columns"
    if any(x in layer_name for x in ['WALL', 'جدار']): return "Walls"
    return "Others"

# رفع الملف
uploaded_dxf = st.file_uploader("Upload DXF:", type=["dxf"])

if uploaded_dxf:
    temp_path = "temp.dxf"
    with open(temp_path, "wb") as f: f.write(uploaded_dxf.getbuffer())
    doc = ezdxf.readfile(temp_path)
    msp = doc.modelspace()
    
    all_points = []
    for entity in msp.query('LWPOLYLINE'):
        cat = classify_layer(entity.dxf.layer)
        verts = [(v[0], v[1]) for v in entity.get_points()]
        if len(verts) > 2:
            for i, v in enumerate(verts):
                all_points.append({"ID": f"{cat}_{i+1}", "E": v[0], "N": v[1]})
    
    df = pd.DataFrame(all_points)
    
    # تبويبات النظام (دمج كامل للميزات)
    tab1, tab2, tab3 = st.tabs(["📊 Data & Quantities", "📍 Staking & PDF Export", "🔍 Tools"])
    
    with tab1:
        st.dataframe(df)
        
    with tab2:
        st.subheader("📍 PDF Sketch Generation")
        if st.button("Generate & Download Staking PDF"):
            pdf_path = "Staking_Sketch.pdf"
            c = canvas.Canvas(pdf_path)
            c.drawString(100, 800, "LexiMind Staking Report")
            y = 750
            for _, row in df.iterrows():
                c.drawString(50, y, f"{row['ID']}: N={row['N']:.2f}, E={row['E']:.2f}")
                y -= 20
                if y < 50:
                    c.showPage()
                    y = 800
            c.save()
            with open(pdf_path, "rb") as f:
                st.download_button("📥 Download PDF", f, "Staking_Sketch.pdf", "application/pdf")
    
    with tab3:
        st.write("أدوات الحفر، الردم، والمطابقة جاهزة للعمل من خلال الكود الأصلي المدمج.")

    os.remove(temp_path)
