import streamlit as st
import ezdxf
import pandas as pd
import os
import math
import re
import matplotlib.pyplot as plt

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
# Core Core Functions & Mathematics
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
        
        # Extract Texts for Smart Naming
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
        
        # Process Polylines & Lines
        for entity in msp.query('LWPOLYLINE LINE'):
            layer = entity.dxf.layer
            category = classify_layer(layer)
            
            # Handle Axis Lines (Grids)
            if "GRID" in layer.upper() or "محاور" in layer.upper() or "AXIS" in layer.upper():
                if entity.dxftype() == 'LINE':
                    grid_lines.append((entity.dxf.start, entity.dxf.end))
                continue
                
            if entity.dxftype() == 'LWPOLYLINE':
                vertices = [(v[0], v[1]) for v in entity.get_points()]
                if len(vertices) == 0: continue
                area = calculate_area(vertices)
                
                # Extract Perimeter for Walls/Quantities
                perimeter = 0.0
                for i in range(len(vertices)):
                    perimeter += math.hypot(vertices[i][0] - vertices[i-1][0], vertices[i][1] - vertices[i-1][1])
                
                if category == "Walls" and area > 0:
                    wall_lines.append({"Length": perimeter / 2, "Layer": layer}) # Approximate centerline
                
                cx = sum(v[0] for v in vertices) / len(vertices)
                cy = sum(v[1] for v in vertices) / len(vertices)
                
                xs = [v[0] for v in vertices]
                ys = [v[1] for v in vertices]
                max_dim = math.hypot(max(xs) - min(xs), max(ys) - min(ys))
                
                if area > 0 and category in ["Footings", "Columns", "Beams"]:
                    structural_elements.append({"Category": category, "Layer": layer, "Area": area})
                
                # Matching smart texts
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
        
        # ==========================================
        # Multi-Tool Tabs System
        # ==========================================
        tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
            "🗺️ 1. Quantities & Estimator", 
            "📍 2. Grid-Row Staking", 
            "🔄 3. Shift & Rotate",
            "📐 4. Axis Gridlines",
            "🧱 5. Brickwork Master",
            "🚜 6. Earthworks",
            "🔍 7. As-Built Audit"
        ])
        
        # ------------------------------------------
        # Tab 1: Structural Quantities
        # ------------------------------------------
        with tab1:
            st.subheader("📊 Concrete & Steel Reinforcement Estimator")
            if structural_elements:
                df_struct = pd.DataFrame(structural_elements)
                summary = df_struct.groupby(["Category", "Layer"]).agg(Count=("Area", "count"), Total_Area_m2=("Area", "sum")).reset_index()
                
                col_q1, col_q2 = st.columns([1, 1])
                with col_q1:
                    st.markdown("**Parameters Input:**")
                    thickness = st.number_input("Average Concrete Thickness (meters):", value=0.60, step=0.05)
                    steel_ratio = st.number_input("Steel Density (kg / m³ of concrete):", value=90.0, step=5.0)
                    
                    summary["Volume_m3"] = summary["Total_Area_m2"] * thickness
                    summary["Steel_Tons"] = (summary["Volume_m3"] * steel_ratio) / 1000.0
                    st.dataframe(summary, use_container_width=True)
                
                with col_q2:
                    st.markdown("**🎨 Visual Spatial Layout Map:**")
                    fig, ax = plt.subplots(figsize=(6, 3.5))
                    cats = df_all_points['Category'].unique()
                    for i, cat in enumerate(cats):
                        c_data = df_all_points[df_all_points['Category'] == cat]
                        ax.scatter(c_data['East_X'], c_data['North_Y'], label=cat, s=12)
                    ax.set_aspect('equal')
                    ax.legend(loc='upper right', fontsize='xs')
                    ax.grid(True, linestyle='--', alpha=0.4)
                    st.pyplot(fig)
            else:
                st.info("No closed geometric elements found to extract areas.")

        # ------------------------------------------
        # Tab 2: Grid-Row Staking Export
        # ------------------------------------------
        with tab2:
            st.subheader("📍 Smart Continuous Field Staking")
            if not df_all_points.empty:
                cats_avail = df_all_points["Category"].unique()
                sel_cat = st.multiselect("Filter objects to stake:", cats_avail, default=cats_avail)
                
                st.markdown("**Local Safe Offset Values (Midan Obstacles Override):**")
                c_o1, c_o2 = st.columns(2)
                off_x = c_o1.number_input("Shift Easting (ΔX):", value=0.0, step=0.5, key="st_offx")
                off_y = c_o2.number_input("Shift Northing (ΔY):", value=0.0, step=0.5, key="st_offy")
                
                if sel_cat:
                    df_stk = df_all_points[df_all_points['Category'].isin(sel_cat)].copy()
                    
                    # Row Clustering Logic to avoid jumps
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
                    elif id_format == "Short Code (F56-1)":
                        df_stk["Export_ID"] = df_stk["Short_ID"]
                    else:
                        df_stk["Export_ID"] = df_stk["Point_ID"]
                        
                    final_out = df_stk[["Export_ID", "North_Y", "East_X"]]
                    final_out["Elevation_Z"] = 0.0
                    
                    delim = ',' if device_type != "Topcon (TXT)" else ' '
                    txt_data = final_out.to_csv(index=False, sep=delim, header=False)
                    
                    st.success(f"Successfully sequenced {len(final_out)} points.")
                    st.download_button(f"📥 Export Field Points ({device_type})", txt_data, "Field_Points.txt", "text/plain")
                    
                    # 🌟 BONUS: CAD Sketch Generation
                    try:
                        out_dxf = ezdxf.new('R2010')
                        out_msp = out_dxf.modelspace()
                        for _, r in df_stk.iterrows():
                            out_msp.add_text(str(r['Export_ID']), dxfattribs={'insert': (r['East_X'], r['North_Y']), 'height': 0.25})
                        out_dxf.saveas("Staking_Sketch.dxf")
                        with open("Staking_Sketch.dxf", "rb") as f_dxf:
                            st.download_button("📥 Download CAD Staking Sketch (.DXF kroke)", f_dxf.read(), "Staking_Sketch.dxf", "application/dxf")
                        os.remove("Staking_Sketch.dxf")
                    except Exception as e: pass

        # ------------------------------------------
        # Tab 3: Coordinate Shift & Rotate
        # ------------------------------------------
        with tab3:
            st.subheader("🔄 Transformation Matrix (Local to Real-World Geo)")
            col_t1, col_t2, col_t3 = st.columns(3)
            shift_e = col_t1.number_input("Constant ΔEast (X Shift):", value=0.0)
            shift_n = col_t2.number_input("Constant ΔNorth (Y Shift):", value=0.0)
            rot_ang = col_t3.number_input("Rotation Angle (Degrees clockwise):", value=0.0)
            
            if not df_all_points.empty:
                df_trans = df_all_points.copy()
                # Find bounding center for rotation anchor
                m_cx = df_trans["East_X"].mean()
                m_cy = df_trans["North_Y"].mean()
                
                # Apply Rotation then Shift
                if rot_ang != 0:
                    rotated = [rotate_point(r["East_X"], r["North_Y"], m_cx, m_cy, -rot_ang) for _, r in df_trans.iterrows()]
                    df_trans["East_X"] = [p[0] for p in rotated]
                    df_trans["North_Y"] = [p[1] for p in rotated]
                
                df_trans["East_X"] += shift_e
                df_trans["North_Y"] += shift_n
                
                st.dataframe(df_trans[["Point_ID", "North_Y", "East_X", "Category"]], use_container_width=True)
                delim_t = ',' if device_type != "Topcon (TXT)" else ' '
                trans_txt = df_trans[["Point_ID", "North_Y", "East_X"]].to_csv(index=False, sep=delim_t, header=False)
                st.download_button("📥 Download Transformed Coordinates", trans_txt, "Transformed_Points.txt", "text/plain")

        # ------------------------------------------
        # Tab 4: Axis Gridlines Stakeout
        # ------------------------------------------
        with tab4:
            st.subheader("📐 Automatic Structural Axis Intersection Extractor")
            if grid_lines:
                st.info(f"Detected {len(grid_lines)} primary geometric grid segments inside CAD file.")
                intersections = []
                # Simple mathematical line intersection check
                for i in range(len(grid_lines)):
                    for j in range(i + 1, len(grid_lines)):
                        p1, p2 = grid_lines[i][0], grid_lines[i][1]
                        p3, p4 = grid_lines[j][0], grid_lines[j][1]
                        
                        den = (p4.x - p3.x) * (p2.y - p1.y) - (p4.y - p3.y) * (p2.x - p1.x)
                        if abs(den) < 1e-5: continue # Parallel
                        
                        ua = ((p4.x - p3.x) * (p1.y - p3.y) - (p4.y - p3.y) * (p1.x - p3.x)) / den
                        ub = ((p2.x - p1.x) * (p1.y - p3.y) - (p2.y - p1.y) * (p1.x - p3.x)) / den
                        
                        if 0 <= ua <= 1 and 0 <= ub <= 1:
                            ix = p1.x + ua * (p2.x - p1.x)
                            iy = p1.y + ua * (p2.y - p1.y)
                            intersections.append((ix, iy))
                
                if intersections:
                    df_inter = pd.DataFrame(intersections, columns=["X", "Y"]).drop_duplicates()
                    df_inter.insert(0, "Axis_ID", [f"Grid_Intersection_{k+1}" for k in range(len(df_inter))])
                    st.dataframe(df_inter, use_container_width=True)
                    delim_g = ',' if device_type != "Topcon (TXT)" else ' '
                    grid_txt = df_inter.to_csv(index=False, sep=delim_g, header=False)
                    st.download_button("📥 Download Axis Points File", grid_txt, "Axis_Grid_Points.txt", "text/plain")
                else:
                    st.warning("No intersection intersections matching exact segments found.")
            else:
                st.info("To use this tool, make sure your DXF has a separate layer named (Grid, Axis, or محاور).")

        # ------------------------------------------
        # Tab 5: Brickwork Master
        # ------------------------------------------
        with tab5:
            st.subheader("🧱 Advanced Architectural Brickwork & Mortar Estimator")
            if wall_lines:
                df_w = pd.DataFrame(wall_lines)
                total_w_len = df_w["Length"].sum()
                st.info(f"Total Structural Linear Wall Length Extracted: **{round(total_w_len, 2)}** meters.")
                
                col_b1, col_b2, col_b3 = st.columns(3)
                w_height = col_b1.number_input("Wall Clear Height (meters):", value=3.20, step=0.1)
                b_thickness = col_b2.selectbox("Block Thickness Type:", [0.20, 0.15, 0.10])
                wastage = col_b3.number_input("Material Breakage Wastage Allowance (%):", value=5.0, step=1.0)
                
                # Standard calculations based on 40x20x20 cm blocks
                wall_area = total_w_len * w_height
                blocks_per_m2 = 12.5 # standard factor
                total_blocks = wall_area * blocks_per_m2 * (1 + wastage/100)
                
                # Mortar consumption
                cement_bags = wall_area * 0.25 # approx. bags per m2
                sand_m3 = wall_area * 0.03
                
                st.markdown("---")
                st.markdown("### 📋 Bill of Quantities (BOQ) Summary for Masonry Work:")
                st.success(f"🧱 Estimated Required Blocks: **{math.ceil(total_blocks)}** pieces.")
                st.success(f"🧪 Estimated Cement Required: **{math.ceil(cement_bags)}** Ordinary Portland Bags (50kg).")
                st.success(f"⏳ Estimated Sand Required: **{round(sand_m3, 2)}** Cubic Meters (m³).")
            else:
                st.info("No architectural elements found matching layer criteria 'Walls' or 'جدار'.")

        # ------------------------------------------
        # Tab 6: Earthworks Volumetrics
        # ------------------------------------------
        with tab6:
            st.subheader("🚜 Topographical Volumetric Calculation (Cut / Fill)")
            if structural_elements:
                tot_a = pd.DataFrame(structural_elements)["Area"].sum()
                st.info(f"Total Combined Dig/Footprint Boundary Area: **{round(tot_a, 2)}** m²")
                col_e1, col_e2 = st.columns(2)
                ngl = col_e1.number_input("Natural Ground Level (NGL Bench Z):", value=1.0, step=0.1)
                target_z = col_e2.number_input("Target Subgrade Bottom Excavation Level:", value=0.0, step=0.1)
                
                h_diff = ngl - target_z
                vol = tot_a * h_diff
                st.markdown("---")
                if h_diff > 0:
                    st.error(f"⚠️ Site Status: EXCAVATION (CUT) required. Depth: {round(h_diff,2)} m.")
                    st.error(f"📉 Estimated Volume to Shift Out: **{round(vol, 2)}** Bulk Cubic Meters.")
                elif h_diff < 0:
                    st.success(f"⚠️ Site Status: EMBANKMENT (FILL) required. Height: {round(abs(h_diff),2)} m.")
                    st.success(f"📈 Estimated Volume to Backfill: **{round(abs(vol), 2)}** Compacted Cubic Meters.")
                else:
                    st.info("Match. Natural Ground matches target level exactly.")

        # ------------------------------------------
        # Tab 7: As-Built Audit Reports
        # ------------------------------------------
        with tab7:
            st.subheader("🔍 Field Deviation Verification Engine")
            asb_f = st.file_uploader("Upload surveyed As-Built point data file (CSV/TXT):", type=["csv", "txt"], key=f"as_built_{st.session_state['asbuilt_key']}")
            if asb_f:
                s_char = ',' if asb_f.name.endswith('.csv') else ' '
                df_asb = pd.read_csv(asb_f, sep=s_char, header=None, names=["ID", "Y", "X", "Z"])
                chk_res = []
                for _, r in df_asb.iterrows():
                    ay, ax = r['Y'], r['X']
                    m_d = float('inf')
                    n_pt = None
                    for _, d_r in df_all_points.iterrows():
                        dst = math.hypot(ax - d_r['East_X'], ay - d_r['North_Y'])
                        if dst < m_d:
                            m_d = dst
                            n_pt = d_r
                    stat = "✅ Match" if m_d <= tolerance else "❌ Deviation"
                    chk_res.append({
                        "Field Point": r['ID'],
                        "Design Match Ref": n_pt['Point_ID'] if n_pt is not None else "N/A",
                        "Delta Discrepancy (m)": round(m_d, 3),
                        "Inspection Status": stat
                    })
                df_res_f = pd.DataFrame(chk_res)
                st.dataframe(df_res_f.style.map(lambda v: 'background-color: #ffcccc' if 'Deviation' in str(v) else 'background-color: #ccffcc', subset=['Inspection Status']), use_container_width=True)
                
                # HTML Engineering Export Report
                h_table = df_res_f.to_html(index=False)
                html_out = f"<html><body style='font-family:sans-serif; padding:20px;'><h2 style='color:#1E3A8A;'>As-Built Survey Verification Matrix</h2><p>Tolerance Used: {tolerance}m</p>{h_table}</body></html>"
                st.download_button("📥 Save Official PDF/HTML Inspection Report", html_out, "AsBuilt_Verification.html", "text/html", use_container_width=True)
                
    except Exception as exp:
        st.error(f"Processing Pipeline Terminated: {exp}")
