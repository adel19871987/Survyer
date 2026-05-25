import streamlit as st
import ezdxf
import pandas as pd
import os
import math
import re
import base64
import matplotlib.pyplot as plt
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

# ==========================================
# 🏗️ LexiMind Pro: Branding & UI Styling
# ==========================================
st.set_page_config(
    page_title="LexiMind Pro | Survey Suite", 
    page_icon="🏗️", 
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <div style="background-color: #1E3A8A; padding: 25px; border-radius: 15px; margin-bottom: 20px;">
        <h1 style="color: white; text-align: center; font-family: 'Arial';">🏗️ LexiMind Pro</h1>
        <p style="color: #BFDBFE; text-align: center; font-size: 18px;">High-Performance Survey & Quantity Engineering Suite</p>
    </div>
""", unsafe_allow_html=True)

# ==========================================
# 🔄 Initialize Session States
# ==========================================
if 'dxf_key' not in st.session_state:
    st.session_state['dxf_key'] = 0
if 'asbuilt_key' not in st.session_state:
    st.session_state['asbuilt_key'] = 0

# ==========================================
# 🛠️ Core & iOS Safe Download Functions
# ==========================================
def download_button_ios(data, filename, label, is_text=False):
    """دالة مشفرة لفتح روابط التحميل في نافذة خارجية مستقلة لحماية المتصفح من الانهيار"""
    if is_text:
        b64 = base64.b64encode(data.encode('utf-8-sig')).decode()
        mime = "text/csv;charset=utf-8"
    else:
        b64 = base64.b64encode(data).decode()
        mime = "application/pdf"
    
    href = f'data:{mime};base64,{b64}'
    html = f'''
    <a href="{href}" download="{filename}" target="_blank" style="
        display: block;
        width: 100%;
        text-align: center;
        background-color: #1E3A8A;
        color: white;
        padding: 12px;
        margin: 10px 0;
        border-radius: 8px;
        text-decoration: none;
        font-weight: bold;
        font-size: 16px;
        box-shadow: 0px 4px 6px rgba(0,0,0,0.1);
    ">{label}</a>
    '''
    st.markdown(html, unsafe_allow_html=True)

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

def optimize_survey_path(df):
    if len(df) < 2: return df
    unvisited = df.to_dict('records')
    optimized_path = []
    current_pt = unvisited.pop(0)
    optimized_path.append(current_pt)
    
    while unvisited:
        next_pt = min(unvisited, key=lambda p: math.hypot(p['East_X'] - current_pt['East_X'], p['North_Y'] - current_pt['North_Y']))
        unvisited.remove(next_pt)
        optimized_path.append(next_pt)
        current_pt = next_pt
    return pd.DataFrame(optimized_path)

# ==========================================
# ⚙️ Sidebar Settings
# ==========================================
st.sidebar.header("⚙️ System Settings")
if st.sidebar.button("🔄 Reset Suite", use_container_width=True, type="primary"):
    st.session_state['dxf_key'] += 1
    st.session_state['asbuilt_key'] += 1
    st.rerun()

st.sidebar.markdown("---")
device_type = st.sidebar.selectbox("Device Format:", ["Leica (CSV)", "Topcon (TXT)", "Generic (CSV)"])
id_format = st.sidebar.selectbox("Point ID Type:", ["Purely Numeric (101, 102...)", "Short Code (F56-1)", "Full Descriptive"])
tolerance = st.sidebar.number_input("Tolerance (m):", value=0.02, step=0.01)

# ==========================================
# 📁 DXF Processing (Step 1)
# ==========================================
st.subheader("📁 Step 1: Design Input (DXF)")
uploaded_dxf = st.file_uploader("Upload Structural/Architectural DXF:", type=["dxf"], key=f"dxf_upload_{st.session_state['dxf_key']}")

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
            except: continue
        
        all_points = []
        structural_elements = []
        grid_lines = []
        wall_lines = []
        category_counters = {"Footings": 0, "Columns": 0, "Beams": 0, "Walls": 0, "Boundary": 0, "Others": 0}
        
        for entity in msp.query('LWPOLYLINE LINE'):
            layer = entity.dxf.layer
            category = classify_layer(layer)
            if "GRID" in layer.upper() or "محاور" in layer.upper() or "AXIS" in layer.upper():
                if entity.dxftype() == 'LINE': grid_lines.append((entity.dxf.start, entity.dxf.end))
                continue
            if entity.dxftype() == 'LWPOLYLINE':
                vertices = [(v[0], v[1]) for v in entity.get_points()]
                if not vertices: continue
                area = calculate_area(vertices)
                perimeter = 0.0
                for i in range(len(vertices)):
                    perimeter += math.hypot(vertices[i][0] - vertices[i-1][0], vertices[i][1] - vertices[i-1][1])
                if category == "Walls" and area > 0:
                    wall_lines.append({"Length": perimeter / 2, "Layer": layer})
                cx = sum(v[0] for v in vertices) / len(vertices)
                cy = sum(v[1] for v in vertices) / len(vertices)
                xs = [v[0] for v in vertices]; ys = [v[1] for v in vertices]
                max_dim = math.hypot(max(xs) - min(xs), max(ys) - min(ys))
                if area > 0 and category in ["Footings", "Columns", "Beams"]:
                    structural_elements.append({"Category": category, "Layer": layer, "Area": area})
                matched_text = None; min_text_dist = float('inf')
                for t in text_pool:
                    d = math.hypot(t['x'] - cx, t['y'] - cy)
                    if d < min_text_dist: min_text_dist = d; matched_text = t
                if matched_text and min_text_dist <= (max_dim * 0.9):
                    txt = matched_text['text']
                    final_prefix = f"{category[:-1]}_{txt}" if txt.isdigit() else txt
                    short_prefix = f"{category[0]}{txt}" if txt.isdigit() else txt[:5]
                else:
                    category_counters[category] += 1; idx = category_counters[category]
                    final_prefix = f"{category[:-1]}_{idx}"; short_prefix = f"{category[0]}{idx}"
                for i, v in enumerate(vertices):
                    all_points.append({
                        "Point_ID": f"{final_prefix}_P{i+1}", "Short_ID": f"{short_prefix}-{i+1}",
                        "North_Y": v[1], "East_X": v[0], "Category": category,
                        "Elem_CX": cx, "Elem_CY": cy, "Elem_Order": i + 1, "Layer_Name": layer
                    })
        
        df_all_points = pd.DataFrame(all_points)
        os.remove(temp_path)
        
        # ==========================================
        # 📂 Suite Tabs (7 Complete Tools)
        # ==========================================
        tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
            "🗺️ 1. Quantities", "📍 2. Field Staking", "🔄 3. Shift & Rotate",
            "📐 4. Axis Gridlines", "🧱 5. Brickwork Master", "🚜 6. Earthworks", "🔍 7. As-Built Audit"
        ])
        
        with tab1:
            st.subheader("📊 Concrete & Steel Reinforcement Estimator")
            if structural_elements:
                df_struct = pd.DataFrame(structural_elements)
                summary = df_struct.groupby(["Category", "Layer"]).agg(Count=("Area", "count"), Total_Area_m2=("Area", "sum")).reset_index()
                col_q1, col_q2 = st.columns([1, 1])
                with col_q1:
                    thickness = st.number_input("Concrete Thickness (m):", value=0.60, step=0.05)
                    steel_ratio = st.number_input("Steel Density (kg/m³):", value=90.0, step=5.0)
                    summary["Volume_m3"] = summary["Total_Area_m2"] * thickness
                    summary["Steel_Tons"] = (summary["Volume_m3"] * steel_ratio) / 1000.0
                    st.dataframe(summary, use_container_width=True)
                with col_q2:
                    fig, ax = plt.subplots(figsize=(6, 3.5))
                    if not df_all_points.empty:
                        # رسم عينة خفيفة للسرعة إذا كانت النقاط ضخمة
                        sample_df = df_all_points.sample(n=min(1000, len(df_all_points)))
                        for cat in sample_df['Category'].unique():
                            c_data = sample_df[sample_df['Category'] == cat]
                            ax.scatter(c_data['East_X'], c_data['North_Y'], label=cat, s=8)
                        ax.set_aspect('equal'); ax.legend(fontsize='small'); ax.grid(True, alpha=0.3)
                    st.pyplot(fig); plt.close(fig)

        with tab2:
            st.subheader("📍 Smart Field Stakeout Engine")
            if not df_all_points.empty:
                # فلترة ذكية حسب الطبقة لتقليل الـ 4000 نقطة عند الحاجة
                all_layers = df_all_points["Layer_Name"].unique()
                selected_layers = st.multiselect("🎯 Filter by AutoCAD Layer (Recommended for large files):", all_layers, default=all_layers)
                
                col_cfg1, col_cfg2, col_cfg3 = st.columns([1, 1, 1])
                off_x = col_cfg1.number_input("Shift ΔX (East):", value=0.0, step=0.1)
                off_y = col_cfg2.number_input("Shift ΔY (North):", value=0.0, step=0.1)
                use_tsp = col_cfg3.checkbox("🔄 Enable Smart Path Optimization", value=False)
                
                if selected_layers:
                    df_stk = df_all_points[df_all_points['Layer_Name'].isin(selected_layers)].copy()
                    st.info(f"📊 Selected Points: {len(df_stk)} rows out of {len(df_all_points)}")
                    
                    # حماية الجوال من التعليق عند معالجة الملفات المليونية
                    if use_tsp and len(df_stk) > 1000:
                        st.warning("⚠️ High Point Count: Path optimization disabled automatically to prevent crashing your mobile browser.")
                        use_tsp = False
                    
                    if use_tsp and len(df_stk) <= 1000:
                        df_stk = optimize_survey_path(df_stk)
                        st.success("✅ Path Optimized successfully.")

                    df_stk["East_X"] += off_x
                    df_stk["North_Y"] += off_y
                    
                    if id_format == "Purely Numeric (101, 102...)":
                        df_stk["Export_ID"] = range(101, 101 + len(df_stk))
                    else:
                        df_stk["Export_ID"] = df_stk["Point_ID"]
                        
                    st.dataframe(df_stk[["Export_ID", "North_Y", "East_X", "Category", "Layer_Name"]], use_container_width=True)

                    # توليد تقرير PDF فوري وخفيف
                    pdf_path = "Survey_Stakeout_Report.pdf"
                    c = canvas.Canvas(pdf_path, pagesize=A4)
                    width, height = A4
                    
                    c.setFillColor(colors.Color(30/255, 58/255, 138/255))
                    c.rect(0, height-80, width, 80, fill=1)
                    c.setFillColor(colors.white)
                    c.setFont("Helvetica-Bold", 20)
                    c.drawString(50, height-50, "LEXIMIND PRO | HIGH-VOLUME REPORT")
                    
                    c.setFillColor(colors.black)
                    c.setFont("Helvetica-Bold", 12)
                    c.drawString(50, height-110, "1. PROJECT SUMMARY")
                    c.setFont("Helvetica", 10)
                    c.drawString(60, height-130, f"Date: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}")
                    c.drawString(60, height-145, f"Total Rendered Points: {len(df_stk)}")
                    
                    y_table = height - 190
                    c.setFont("Helvetica-Bold", 11)
                    c.drawString(50, y_table, "Point ID | Easting (X) | Northing (Y) | Layer")
                    c.line(50, y_table-5, 550, y_table-5)
                    
                    y_table -= 20
                    c.setFont("Helvetica", 9)
                    
                    # نكتفي بكتابة أول 500 نقطة في ملف الـ PDF المطبوع لحماية الذاكرة من الانهيار إذا كان الملف ضخماً
                    render_limit = min(500, len(df_stk))
                    for idx, r in df_stk.head(render_limit).iterrows():
                        if y_table < 50:
                            c.showPage()
                            y_table = height - 50
                            c.setFont("Helvetica", 9)
                        c.drawString(60, y_table, str(r['Export_ID']))
                        c.drawString(180, y_table, f"{r['East_X']:.3f}")
                        c.drawString(300, y_table, f"{r['North_Y']:.3f}")
                        c.drawString(420, y_table, str(r['Layer_Name'])[:15])
                        y_table -= 15
                    
                    if len(df_stk) > 500:
                        c.setFont("Helvetica-Bold", 10)
                        c.setFillColor(colors.red)
                        c.drawString(50, y_table, f"... Note: PDF preview limited to first 500 points. Total file contains {len(df_stk)} points.")
                    
                    c.save()
                    
                    with open(pdf_path, "rb") as f:
                        pdf_bytes = f.read()
                    download_button_ios(pdf_bytes, pdf_path, "📥 Download Official PDF Report (iOS Safe)")
                    
                    delim = ',' if device_type != "Topcon (TXT)" else ' '
                    txt_data = df_stk[["Export_ID", "North_Y", "East_X"]].to_csv(index=False, sep=delim, header=False)
                    download_button_ios(txt_data, "Staking_Data.txt", f"📥 Download FULL Field File ({device_type})", is_text=True)

        with tab3:
            st.subheader("🔄 Transformation Matrix")
            col_t1, col_t2, col_t3 = st.columns(3)
            shift_e = col_t1.number_input("ΔEast (X):", value=0.0, key="trans_x")
            shift_n = col_t2.number_input("ΔNorth (Y):", value=0.0, key="trans_y")
            rot_ang = col_t3.number_input("Rotation (° CW):", value=0.0, key="trans_rot")
            if not df_all_points.empty:
                df_trans = df_all_points.copy()
                if rot_ang != 0:
                    m_cx, m_cy = df_trans["East_X"].mean(), df_trans["North_Y"].mean()
                    rotated = [rotate_point(r["East_X"], r["North_Y"], m_cx, m_cy, -rot_ang) for _, r in df_trans.iterrows()]
                    df_trans["East_X"] = [p[0] for p in rotated]
                    df_trans["North_Y"] = [p[1] for p in rotated]
                df_trans["East_X"] += shift_e
                df_trans["North_Y"] += shift_n
                st.dataframe(df_trans[["Point_ID", "North_Y", "East_X", "Category", "Layer_Name"]], use_container_width=True)

        with tab4:
            st.subheader("📐 Axis Gridline Intersections")
            if grid_lines:
                intersections = []
                # تفادي التكرار اللانهائي في الخطوط الضخمة للحفاظ على السرعة
                limit_grids = grid_lines[:100] 
                for i in range(len(limit_grids)):
                    for j in range(i + 1, len(limit_grids)):
                        p1, p2 = limit_grids[i][0], limit_grids[i][1]
                        p3, p4 = limit_grids[j][0], limit_grids[j][1]
                        den = (p4.x - p3.x) * (p2.y - p1.y) - (p4.y - p3.y) * (p2.x - p1.x)
                        if abs(den) < 1e-5: continue
                        ua = ((p4.x - p3.x) * (p1.y - p3.y) - (p4.y - p3.y) * (p1.x - p3.x)) / den
                        ub = ((p2.x - p1.x) * (p1.y - p3.y) - (p2.y - p1.y) * (p1.x - p3.x)) / den
                        if 0 <= ua <= 1 and 0 <= ub <= 1: intersections.append((p1.x + ua * (p2.x - p1.x), p1.y + ua * (p2.y - p1.y)))
                if intersections:
                    df_inter = pd.DataFrame(intersections, columns=["X", "Y"]).drop_duplicates()
                    st.dataframe(df_inter, use_container_width=True)
                else: st.warning("No grid intersections found in the selected sample.")
            else: st.info("No grid lines detected in DXF.")

        with tab5:
            st.subheader("🧱 Brickwork & Masonry Estimator")
            if wall_lines:
                total_w = pd.DataFrame(wall_lines)["Length"].sum()
                st.info(f"Total Wall Length: {round(total_w, 2)}m")
                h = st.number_input("Wall Height (m):", value=3.20, key="wall_h")
                st.success(f"Estimated Blocks: {math.ceil(total_w * h * 12.5)} pcs")
            else: st.info("No walls detected in DXF.")

        with tab6:
            st.subheader("🚜 Earthworks Volumetrics")
            if structural_elements:
                tot_a = pd.DataFrame(structural_elements)["Area"].sum()
                st.info(f"Footprint Area: {round(tot_a, 2)} m²")
                ngl = st.number_input("NGL Level:", value=1.0, key="ngl_v")
                target = st.number_input("Target Level:", value=0.0, key="tgt_v")
                vol = tot_a * abs(ngl - target)
                st.error(f"Volume: {round(vol, 2)} m³")
            else: st.info("No structural elements found to calculate footprint area.")

        with tab7:
            st.subheader("🔍 As-Built Audit Engine")
            asb_f = st.file_uploader("Upload Field Survey (CSV/TXT):", type=["csv", "txt"], key=f"as_built_{st.session_state['asbuilt_key']}")
            if asb_f:
                s_char = ',' if asb_f.name.endswith('.csv') else ' '
                df_asb = pd.read_csv(asb_f, sep=s_char, header=None, names=["ID", "Y", "X", "Z"])
                chk = []
                # تحسين الأداء لملفات المراجعة الكبيرة عبر أخذ عينة للمقارنة السريعة
                for _, r in df_asb.head(500).iterrows():
                    m_d = float('inf')
                    n_pt = None
                    for _, dr in df_all_points.iterrows():
                        dst = math.hypot(r['X'] - dr['East_X'], r['Y'] - dr['North_Y'])
                        if dst < m_d: m_d = dst; n_pt = dr
                    chk.append({"ID": r['ID'], "Ref": n_pt['Point_ID'] if n_pt is not None else "N/A", "Delta": round(m_d, 3), "Status": "✅" if m_d <= tolerance else "❌"})
                st.dataframe(pd.DataFrame(chk), use_container_width=True)

    except Exception as exp:
        st.error(f"Pipeline Error: {exp}")
