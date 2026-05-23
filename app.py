import streamlit as st
import ezdxf
import pandas as pd
import os
import math
import re
import matplotlib.pyplot as plt
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

st.set_page_config(page_title="LexiMind Survey Suite", layout="wide")
st.title("🏗️ LexiMind: Ultimate Survey & Quantity Takeoff Suite")
st.markdown("---")

# ==========================================
# 🔄 Initialize Session States
# ==========================================
if 'dxf_key' not in st.session_state: st.session_state['dxf_key'] = 0
if 'asbuilt_key' not in st.session_state: st.session_state['asbuilt_key'] = 0

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
    if any(x in layer_name for x in ['ZAPATA', 'FOOT', 'قاعدة', 'FND', 'F1', 'F2', 'F3', 'F4', 'F5']): return "Footings"
    if any(x in layer_name for x in ['COLUMN', 'COL', 'عمود', 'C1', 'C2', 'C3']): return "Columns"
    if any(x in layer_name for x in ['BEAM', 'جسر', 'TIE', 'B1', 'B2']): return "Beams"
    if any(x in layer_name for x in ['WALL', 'جدار', 'حائط', 'MASONRY', 'BLOCK']): return "Walls"
    if any(x in layer_name for x in ['BOUNDARY', 'SITE', 'حد']): return "Boundary"
    return "Others"

def clean_mtext(text_val):
    text_val = re.sub(r'\\[a-zA-Z0-9]+;', '', text_val)
    text_val = text_val.replace(r'\P', ' ').strip()
    return text_val

def rotate_point(x, y, cx, cy, angle_deg):
    angle_rad = math.radians(angle_deg)
    nx = cx + (x - cx) * math.cos(angle_rad) - (y - cy) * math.sin(angle_rad)
    ny = cy + (x - cx) * math.sin(angle_rad) + (y - cy) * math.cos(angle_rad)
    return nx, ny

# ==========================================
# UI & Main Process
# ==========================================
st.sidebar.header("⚙️ General Settings")
if st.sidebar.button("🔄 Reset System", use_container_width=True, type="primary"):
    st.session_state['dxf_key'] += 1
    st.rerun()

uploaded_dxf = st.file_uploader("Upload DXF layout:", type=["dxf"], key=f"dxf_upload_{st.session_state['dxf_key']}")

if uploaded_dxf:
    temp_path = f"temp_{uploaded_dxf.name}"
    with open(temp_path, "wb") as f: f.write(uploaded_dxf.getbuffer())
    doc = ezdxf.readfile(temp_path)
    msp = doc.modelspace()
    
    # [هنا تضع منطق استخراج النقاط والبيانات كما في كودك الطويل]
    # (نظراً لطول الكود، تأكد من وجود كود استخراج الـ all_points و structural_elements هنا)
    
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "🗺️ 1. Quantities", "📍 2. Grid-Row Staking", "🔄 3. Shift & Rotate",
        "📐 4. Axis Gridlines", "🧱 5. Brickwork", "🚜 6. Earthworks", "🔍 7. As-Built"
    ])
    
    with tab2:
        st.subheader("📍 Smart Continuous Field Staking")
        # [منطق الـ Staking الخاص بك]
        
        # إضافة ميزة تصدير PDF الاحترافي هنا:
        if st.button("📥 Export Field Points as PDF Report"):
            pdf_path = "Field_Points_Report.pdf"
            c = canvas.Canvas(pdf_path, pagesize=A4)
            c.setFont("Helvetica-Bold", 16)
            c.drawString(50, 820, "Official Staking Points Report")
            c.setFont("Helvetica", 10)
            y = 780
            c.drawString(50, y, "Point ID | Northing (Y) | Easting (X)")
            y -= 20
            # نستخدم df_stk الذي هو نتاج عملك السابق
            for _, r in df_stk.iterrows():
                line = f"{r['Export_ID']} | {r['North_Y']:.3f} | {r['East_X']:.3f}"
                c.drawString(50, y, line)
                y -= 20
                if y < 50: c.showPage(); y = 800
            c.save()
            with open(pdf_path, "rb") as f:
                st.download_button("📥 Download PDF Report", f, "Field_Points_Report.pdf", "application/pdf")
    
    # [بقية التبويبات 1، 3، 4، 5، 6، 7 كما هي في كودك الأصلي]
    
    os.remove(temp_path)
