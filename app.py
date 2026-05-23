import streamlit as st
import ezdxf
import pandas as pd
import os
import math
from fpdf import FPDF

st.set_page_config(page_title="LexiMind Survey Suite", layout="wide")
st.title("🏗️ LexiMind: Ultimate Survey Suite (PDF Edition)")

# ==========================================
# Core Functions
# ==========================================
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
    return "Others"

# ==========================================
# UI & File Handling
# ==========================================
uploaded_dxf = st.file_uploader("Upload DXF:", type=["dxf"])

if uploaded_dxf:
    temp_path = "temp.dxf"
    with open(temp_path, "wb") as f: f.write(uploaded_dxf.getbuffer())
    doc = ezdxf.readfile(temp_path)
    msp = doc.modelspace()
    
    all_points = []
    for entity in msp.query('LWPOLYLINE'):
        category = classify_layer(entity.dxf.layer)
        vertices = [(v[0], v[1]) for v in entity.get_points()]
        if len(vertices) < 3: continue
        
        for i, v in enumerate(vertices):
            all_points.append({"ID": f"{category}_{i+1}", "E": v[0], "N": v[1]})

    df = pd.DataFrame(all_points)
    
    tab1, tab2 = st.tabs(["📊 Data", "📍 PDF Sketch Export"])
    
    with tab1:
        st.dataframe(df)
        
    with tab2:
        st.subheader("📍 Generate PDF Staking Sketch")
        if st.button("Generate & Download PDF"):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(200, 10, txt="Staking Points Sketch", ln=True, align='C')
            pdf.set_font("Arial", size=10)
            
            # كتابة النقاط في الـ PDF
            for _, row in df.iterrows():
                pdf.cell(200, 8, txt=f"{row['ID']} | North: {row['N']:.2f} | East: {row['E']:.2f}", ln=True)
            
            pdf_output = "Staking_Sketch.pdf"
            pdf.output(pdf_output)
            
            with open(pdf_output, "rb") as f:
                st.download_button("📥 Download Staking Sketch (PDF)", f, "Staking_Sketch.pdf", "application/pdf")
            
    os.remove(temp_path)
