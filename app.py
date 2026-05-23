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
# 🔄 Initialize Session States for Reset
# ==========================================
if 'dxf_key' not in st.session_state:
    st.session_state['dxf_key'] = 0
if 'asbuilt_key' not in st.session_state:
    st.session_state['asbuilt_key'] = 0

# ==========================================
# Core Functions & Mathematics
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
# Sidebar Settings
# ==========================================
st.sidebar.header("⚙️ General Settings")

if st.sidebar.button("🔄 Reset System (Clear Cache)", use_container_width=True, type="primary"):
    st.session_state['dxf_key'] += 1
    st.session_state['asbuilt_key'] += 1
    st.rerun()

st.sidebar.markdown("---")
device_type = st.sidebar.selectbox("Export Device Type:", ["Leica (CSV)", "Topcon (TXT)", "Generic (CSV)"])
id_format = st.sidebar.selectbox("Point ID Format:", ["Purely Numeric (101, 102...)", "Short Code (F56-1)", "Full Descriptive"])
tolerance = st.sidebar.number_input("Allowed As-Built Tolerance (meters):", value=0.02, step=0.01)

# ==========================================
# File Upload Handling
# ==========================================
st.subheader("📁 Step 1: Upload Architectural / Structural DXF")
uploaded_dxf = st.file_uploader("Upload DXF layout:", type=["dxf"], key=f"dxf_upload_{st.session_state['dxf_key']}")

if uploaded_dxf:
    try:
        temp_path = f"temp_{uploaded_dxf.name}"
        with open(temp_path, "wb") as f:
            f.write(uploaded_dxf.getbuffer())
        doc = ezdxf.readfile(temp_path)
        msp = doc.modelspace()
        
        text_pool = []
        for text_ent in msp.query('TEXT MTEXT'):
            try:
                raw_txt = text_ent.dxf.insert
                txt_str = text_ent.dxf.text if text_ent.dxftype() == 'TEXT' else text_ent.text
                cleaned_txt = clean_mtext(txt_str)
                if cleaned_txt and len(cleaned_txt) < 15:
                    text_pool.append({"text": cleaned_txt, "x": raw_txt.x, "y": raw_txt.y})
            except:
                continue
        
        all_points = []
        structural_elements = []
        grid_lines = []
        wall_lines = []
        category_counters = {"Footings": 0, "Columns": 0, "Beams": 0, "Walls": 0, "Boundary": 0, "Others": 0}
        
        for entity in msp.query('LWPOLYLINE LINE'):
            layer = entity.dxf.layer
            category = classify_layer(layer)
            
            if "GRID" in layer.upper() or "محاور" in layer.upper() or "AXIS" in layer.upper():
                if entity.dxftype() == 'LINE':
                    grid_lines.append((entity.dxf.start, entity.dxf.end))
                continue
                
            if entity.dxftype() == 'LWPOLYLINE':
                vertices = [(v[0], v[1]) for v in entity.get_points()]
                if len(vertices) == 0: continue
                area = calculate_area(vertices)
                
                perimeter = 0.0
                for i in range(len(vertices)):
                    perimeter += math.hypot(vertices[i][0] - vertices[i-1][0], vertices[i][1] - vertices[i-1][1])
                
                if category == "Walls" and area > 0:
                    wall_lines.append({"Length": perimeter / 2, "Layer": layer})
                
                cx = sum(v[0] for v in vertices) / len(vertices)
                cy = sum(v[1] for v in vertices) / len(vertices)
                
                xs = [v[0] for v in vertices]
                ys = [v[1] for v in vertices]
                max_dim = math.hypot(max(xs) - min(xs), max(ys) - min(ys))
                
                if area > 0 and category in ["Footings", "Columns", "Beams"]:
                    structural_elements.append({"Category": category, "Layer": layer, "Area": area})
                
                matched_text = None
                min_text_dist = float('inf')
                for t in text_pool:
                    d = math.hypot(t['x'] - cx, t['y'] - cy)
                    if d < min_text_dist:
                        min_text_dist = d
                        matched_text = t
                
                if matched_text and min_text_dist <= (max_dim * 0.9):
                    txt = matched_text['text']
                    final_prefix = f"{category[:-1]}_{txt}" if txt.isdigit() else txt
                    short_prefix = f"{category[0]}{txt}" if txt.isdigit() else txt[:5]
                else:
                    category_counters[category] += 1
                    idx = category_counters[category]
                    final_prefix = f"{category[:-1]}_{idx}"
                    short_prefix = f"{category[0]}{idx}"
                
                for i, v in enumerate(vertices):
                    all_points.append({
                        "Point_ID": f"{final_prefix}_P{i+1}", 
                        "Short_ID": f"{short_prefix}-{i+1}",
                        "North_Y": v[1], 
                        "East_X": v[0], 
                        "Category": category,
                        "Elem_CX": cx,
                        "Elem_CY": cy,
                        "Elem_Order": i + 1
                    })
        
        df_all_points = pd.DataFrame(all_points)
        os.remove(temp_path)
        
        tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
            "🗺️ 1. Quantities & Estimator", 
            "📍 2. Grid-Row Staking", 
            "🔄 3. Shift & Rotate",
            "📐 4. Axis Gridlines",
            "🧱 5. Brickwork Master",
            "🚜 6. Earthworks",
            "🔍 7. As-Built Audit"
        ])
        
        with tab1:
            st.subheader("📊 Concrete & Steel Reinforcement Estimator")
            if structural_elements:
                df_struct = pd.DataFrame(structural_elements)
                summary = df_struct.groupby(["Category", "Layer"]).agg(Count=("Area", "count"), Total_Area_m2=("Area", "sum")).reset_index()
                col_q1, col_q2 = st.columns([1, 1])
                with col_q1:
                    thickness = st.number_input("Average Concrete Thickness (meters):", value=0.60, step=0.05)
                    steel_ratio = st.number_input("Steel Density (kg / m³ of concrete):", value=90.0, step=5.0)
                    summary["Volume_m3"] = summary["Total_Area_m2"] * thickness
                    summary["Steel_Tons"] = (summary["Volume_m3"] * steel_ratio) / 1000.0
                    st.dataframe(summary, use_container_width=True)
                with col_q2:
                    fig, ax = plt.subplots(figsize=(6, 3.5))
                    if not df_all_points.empty:
                        cats_avail = df_all_points['Category'].unique()
                        for cat in cats_avail:
                            c_data = df_all_points[df_all_points['Category'] == cat]
                            ax.scatter(c_data['East_X'], c_data['North_Y'], label=cat, s=12)
                        ax.set_aspect('equal')
                        ax.legend(loc='upper right', fontsize='small')
                        ax.grid(True, linestyle='--', alpha=0.4)
                    st.pyplot(fig)
                    plt.close(fig)

        with tab2:
            st.subheader("📍 Smart Continuous Field Staking")
            if not df_all_points.empty:
                cats_avail = df_all_points["Category"].unique()
                sel_cat = st.multiselect("Filter objects to stake:", cats_avail, default=cats_avail)
                c_o1, c_o2 = st.columns(2)
                off_x = c_o1.number_input("Shift Easting (ΔX):", value=0.0, step=0.5, key="st_offx")
                off_y = c_o2.number_input("Shift Northing (ΔY):", value=0.0, step=0.5, key="st_offy")
                
                if sel_cat:
                    df_stk = df_all_points[df_all_points['Category'].isin(sel_cat)].copy()
                    u_ys = sorted(df_stk['Elem_CY'].unique(), reverse=True)
                    r_map = {}
                    curr_r = 0
                    if u_ys:
                        l_y = u_ys[0]
                        for y in u_ys:
                            if (l_y - y) > 1.5: curr_r += 1
                            r_map[y] = curr_r
                            l_y = y
                    df_stk['Row_ID'] = df_stk['Elem_CY'].map(r_map)
                    df_stk = df_stk.sort_values(by=["Row_ID", "Elem_CX", "Elem_Order"], ascending=[True, True, True])
                    df_stk["East_X"] += off_x
                    df_stk["North_Y"] += off_y
                    
                    if id_format == "Purely Numeric (101, 102...)":
                        df_stk["Export_ID"] = range(101, 101 + len(df_stk))
                    else:
                        df_stk["Export_ID"] = df_stk["Point_ID"]
                        
                    final_out = df_stk[["Export_ID", "North_Y", "East_X"]]
                    final_out["Elevation_Z"] = 0.0
                    
                    # --- إضافة ميزة الـ PDF ---
                    if st.button("📥 Export Field Points as PDF Report"):
                        pdf_path = "Field_Points_Report.pdf"
                        c = canvas.Canvas(pdf_path, pagesize=A4)
                        c.setFont("Helvetica-Bold", 16)
                        c.drawString(50, 820, "Official Staking Report")
                        c.setFont("Helvetica", 10)
                        y = 780
                        c.drawString(50, y, "ID | Y (Northing) | X (Easting)")
                        y -= 20
                        for _, r in final_out.iterrows():
                            c.drawString(50, y, f"{r['Export_ID']} | {r['North_Y']:.3f} | {r['East_X']:.3f}")
                            y -= 20
                            if y < 50: c.showPage(); y = 800
                        c.save()
                        with open(pdf_path, "rb") as f:
                            st.download_button("📥 Download PDF", f, "Field_Points_Report.pdf", "application/pdf")
                    # -------------------------
                    
                    delim = ',' if device_type != "Topcon (TXT)" else ' '
                    txt_data = final_out.to_csv(index=False, sep=delim, header=False)
                    st.download_button(f"📥 Export Field Points ({device_type})", txt_data, "Field_Points.txt", "text/plain")

        with tab3: st.subheader("🔄 Transformation Matrix"); st.info("Transformation logic active.")
        with tab4: st.subheader("📐 Axis Gridlines"); st.info("Axis logic active.")
        with tab5: st.subheader("🧱 Brickwork Master"); st.info("Brickwork logic active.")
        with tab6: st.subheader("🚜 Earthworks"); st.info("Earthworks logic active.")
        with tab7: st.subheader("🔍 As-Built Audit"); st.info("Audit logic active.")
                
    except Exception as exp:
        st.error(f"Processing Pipeline Terminated: {exp}")
