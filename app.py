import streamlit as st
import ezdxf
import pandas as pd
import os
import math
import re
import matplotlib.pyplot as plt

st.set_page_config(page_title="Smart Surveyor Pro", layout="wide")
st.title("🏗️ Professional Survey & Quantity Management System")
st.markdown("---")

# ==========================================
# 🔄 Initialize Session States for Reset (Go Back)
# ==========================================
if 'dxf_key' not in st.session_state:
    st.session_state['dxf_key'] = 0
if 'asbuilt_key' not in st.session_state:
    st.session_state['asbuilt_key'] = 0

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
    if any(x in layer_name for x in ['BOUNDARY', 'SITE', 'حد']): return "Boundary"
    return "Others"

def clean_mtext(text_val):
    text_val = re.sub(r'\\[a-zA-Z0-9]+;', '', text_val)
    text_val = text_val.replace(r'\P', ' ').strip()
    return text_val

def read_dxf(uploaded_file):
    temp_file_path = f"temp_{uploaded_file.name}"
    with open(temp_file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    doc = ezdxf.readfile(temp_file_path)
    return doc, temp_file_path

def calc_distance(x1, y1, x2, y2):
    return math.hypot(x2 - x1, y2 - y1)

# ==========================================
# Sidebar Settings & Reset Button
# ==========================================
st.sidebar.header("⚙️ System Settings")

# 🌟 زر العودة إلى الوراء وإعادة تعيين النظام 🌟
if st.sidebar.button("🔄 Reset System (Go Back)", use_container_width=True, type="primary"):
    st.session_state['dxf_key'] += 1
    st.session_state['asbuilt_key'] += 1
    st.rerun()

st.sidebar.markdown("---")
device_type = st.sidebar.selectbox("Export Device Type:", ["Leica (CSV)", "Topcon (TXT)", "Generic (CSV)"])
tolerance = st.sidebar.number_input("Allowed Tolerance (meters):", value=0.02, step=0.01)

# ==========================================
# Main DXF Processing
# ==========================================
st.subheader("📁 Upload Base Layout (DXF)")
uploaded_dxf = st.file_uploader("Upload approved DXF layout here:", type=["dxf"], key=f"dxf_upload_{st.session_state['dxf_key']}")

if uploaded_dxf:
    try:
        doc, path = read_dxf(uploaded_dxf)
        msp = doc.modelspace()
        
        text_pool = []
        for text_ent in msp.query('TEXT MTEXT'):
            try:
                if text_ent.dxftype() == 'TEXT':
                    raw_txt = text_ent.dxf.insert
                    txt_str = text_ent.dxf.text
                else:
                    raw_txt = text_ent.dxf.insert
                    txt_str = text_ent.text
                
                cleaned_txt = clean_mtext(txt_str)
                if cleaned_txt and len(cleaned_txt) < 15:
                    text_pool.append({"text": cleaned_txt, "x": raw_txt.x, "y": raw_txt.y})
            except:
                continue
        
        all_points = []
        data_list = []
        category_counters = {"Footings": 0, "Columns": 0, "Beams": 0, "Boundary": 0, "Others": 0}
        
        for entity in msp.query('LWPOLYLINE'):
            layer = entity.dxf.layer
            category = classify_layer(layer)
            vertices = [(v[0], v[1]) for v in entity.get_points()]
            area = calculate_area(vertices)
            
            if len(vertices) == 0:
                continue
                
            if area > 0:
                data_list.append({"Category": category, "Layer Name": layer, "Area (m2)": area})
            
            category_counters[category] += 1
            item_num = category_counters[category]
            
            cx = sum(v[0] for v in vertices) / len(vertices)
            cy = sum(v[1] for v in vertices) / len(vertices)
            
            xs = [v[0] for v in vertices]
            ys = [v[1] for v in vertices]
            max_dim = math.hypot(max(xs) - min(xs), max(ys) - min(ys))
            
            matched_text = None
            min_text_dist = float('inf')
            for t in text_pool:
                d = math.hypot(t['x'] - cx, t['y'] - cy)
                if d < min_text_dist:
                    min_text_dist = d
                    matched_text = t
            
            generic_layers = ['0', 'DEFPOINTS', 'ZAPATA', 'ZAPATAS', 'FOOTING', 'FOOTINGS', 'COLUMN', 'COLUMNS', 'BEAM', 'BEAMS', 'CONCRETE']
            layer_upper = layer.upper().strip()
            
            if matched_text and min_text_dist <= (max_dim * 0.9):
                final_prefix = matched_text['text']
            elif layer_upper not in generic_layers and len(layer_upper) <= 10:
                final_prefix = layer
            else:
                if category == "Footings": final_prefix = f"Footing_{item_num}"
                elif category == "Columns": final_prefix = f"Column_{item_num}"
                elif category == "Beams": final_prefix = f"Beam_{item_num}"
                else: final_prefix = f"Object_{item_num}"
            
            for i, v in enumerate(vertices):
                all_points.append({
                    "Point_ID": f"{final_prefix}_P{i+1}", 
                    "North_Y": v[1], 
                    "East_X": v[0], 
                    "Category": category
                })
                
        df_all_points = pd.DataFrame(all_points)
        os.remove(path)
        
        # ---------------------------------------------------------
        # Unified Tab System
        # ---------------------------------------------------------
        tab1, tab2, tab3, tab4 = st.tabs([
            "🗺️ 1. Map & Quantities", 
            "📍 2. Staking & Offset", 
            "🚜 3. Earthworks (Cut/Fill)",
            "✅ 4. As-Built Verification"
        ])
        
        # --- Tab 1: Map & Quantities ---
        with tab1:
            col1, col2 = st.columns([1, 1])
            with col1:
                st.subheader("📊 Quantity Takeoff Summary")
                if data_list:
                    df_quantities = pd.DataFrame(data_list)
                    summary = df_quantities.groupby(["Category", "Layer Name"]).agg(
                        Count=("Area (m2)", "count"),
                        Total_Area_m2=("Area (m2)", "sum")
                    ).reset_index()
                    st.dataframe(summary, use_container_width=True)
            
            with col2:
                st.subheader("🗺️ Visual Layout Preview")
                if not df_all_points.empty:
                    fig, ax = plt.subplots(figsize=(6, 4))
                    categories = df_all_points['Category'].unique()
                    colors = plt.cm.get_cmap('tab10', len(categories))
                    
                    for i, cat in enumerate(categories):
                        cat_data = df_all_points[df_all_points['Category'] == cat]
                        ax.scatter(cat_data['East_X'], cat_data['North_Y'], label=cat, color=colors(i), s=10)
                    
                    ax.set_aspect('equal')
                    ax.set_xlabel('East (X)')
                    ax.set_ylabel('North (Y)')
                    ax.legend(loc='upper right', fontsize='small')
                    ax.grid(True, linestyle='--', alpha=0.5)
                    st.pyplot(fig)

        # --- Tab 2: Staking & Offsets ---
        with tab2:
            st.subheader("📍 Prepare Staking Points & Offsets")
            categories_available = df_all_points["Category"].unique()
            selected_cat = st.multiselect("Select elements for staking:", categories_available, default=categories_available)
            
            st.markdown("**Create Offset Points (To bypass obstacles):**")
            col_off1, col_off2 = st.columns(2)
            offset_x = col_off1.number_input("East Offset (X) in meters:", value=0.0, step=0.5)
            offset_y = col_off2.number_input("North Offset (Y) in meters:", value=0.0, step=0.5)
            
            if selected_cat:
                filtered_points = df_all_points[df_all_points['Category'].isin(selected_cat)].copy()
                filtered_points = filtered_points.sort_values(by=["North_Y", "East_X"])
                
                filtered_points["East_X"] = filtered_points["East_X"] + offset_x
                filtered_points["North_Y"] = filtered_points["North_Y"] + offset_y
                
                export_points = filtered_points[["Point_ID", "North_Y", "East_X"]]
                export_points["Elevation_Z"] = 0.0
                
                sep = ',' if device_type != "Topcon (TXT)" else ' '
                csv_data = export_points.to_csv(index=False, sep=sep, header=False)
                
                st.success(f"Successfully prepared {len(export_points)} points.")
                st.download_button(f"📥 Download {device_type.split()[0]} File", csv_data, "Staking_Points.txt", "text/plain")

        # --- Tab 3: Earthworks ---
        with tab3:
            st.subheader("🚜 Estimated Earthworks Volumetric Calculation")
            if data_list:
                total_area = summary['Total_Area_m2'].sum()
                st.info(f"Total Structural Footprint Area: **{round(total_area, 2)}** m²")
                
                col_z1, col_z2 = st.columns(2)
                current_level = col_z1.number_input("Natural Ground Level (NGL):", value=1.0, step=0.1)
                target_level = col_z2.number_input("Target Design Level (Excavation):", value=0.0, step=0.1)
                
                depth = current_level - target_level
                volume = total_area * depth
                
                st.markdown("---")
                if depth > 0:
                    st.error(f"⚠️ Site requires EXCAVATION (CUT) depth: {round(depth, 2)} meters.")
                    st.error(f"📉 Total Estimated CUT Volume: **{round(volume, 2)}** m³.")
                elif depth < 0:
                    st.success(f"⚠️ Site requires EMBANKMENT (FILL) height: {round(abs(depth), 2)} meters.")
                    st.success(f"📈 Total Estimated FILL Volume: **{round(abs(volume), 2)}** m³.")
                else:
                    st.info("Ground is exactly at the target design level.")

        # --- Tab 4: As-Built Verification ---
        with tab4:
            st.subheader("🔍 Site Inspection & As-Built Verification Report")
            asbuilt_file = st.file_uploader("Upload field survey file (CSV/TXT):", type=["csv", "txt"], key=f"asbuilt_upload_{st.session_state['asbuilt_key']}")
            
            if asbuilt_file:
                sep_asb = ',' if asbuilt_file.name.endswith('.csv') else ' '
                df_asb = pd.read_csv(asbuilt_file, sep=sep_asb, header=None, names=["ID", "Y", "X", "Z"])
                
                results = []
                for index, row in df_asb.iterrows():
                    asb_y, asb_x = row['Y'], row['X']
                    min_dist = float('inf')
                    nearest_point = None
                    
                    for _, design_row in df_all_points.iterrows():
                        dist = calc_distance(asb_x, asb_y, design_row['East_X'], design_row['North_Y'])
                        if dist < min_dist:
                            min_dist = dist
                            nearest_point = design_row
                            
                    status = "✅ Match" if min_dist <= tolerance else "❌ Deviation"
                    results.append({
                        "Surveyed Point ID": row['ID'],
                        "Design Reference ID": nearest_point['Point_ID'],
                        "Deviation (m)": round(min_dist, 3),
                        "Status": status
                    })
                
                df_results = pd.DataFrame(results)
                df_results.insert(0, 'No.', range(1, 1 + len(df_results)))
                
                def highlight_errors(val):
                    color = '#ffcccc' if val == '❌ Deviation' else '#ccffcc'
                    return f'background-color: {color}'
                
                st.dataframe(df_results.style.map(highlight_errors, subset=['Status']), use_container_width=True)
                
                # HTML Report Generator
                st.markdown("---")
                html_table = df_results.to_html(index=False, classes='report-table')
                html_report = f"""
                <html>
                <head>
                    <meta charset="utf-8">
                    <style>
                        body {{ font-family: 'Arial', sans-serif; direction: ltr; text-align: left; padding: 30px; }}
                        .header-title {{ color: #1E3A8A; text-align: center; border-bottom: 3px solid #1E3A8A; padding-bottom: 15px; margin-bottom: 20px; }}
                        .info-section {{ background-color: #f8fafc; padding: 15px; border-radius: 8px; border: 1px solid #e2e8f0; margin-bottom: 20px; }}
                        .report-table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
                        .report-table th, .report-table td {{ border: 1px solid #cbd5e1; padding: 12px; text-align: center; font-size: 14px; }}
                        .report-table th {{ background-color: #f1f5f9; color: #1e293b; font-weight: bold; }}
                        .match {{ background-color: #dcfce7; color: #15803d; font-weight: bold; }}
                        .deviation {{ background-color: #fee2e2; color: #b91c1c; font-weight: bold; }}
                        .footer {{ margin-top: 40px; text-align: center; font-size: 12px; color: #64748b; border-top: 1px solid #e2e8f0; padding-top: 10px; }}
                    </style>
                </head>
                <body>
                    <div class="header-title">
                        <h2>📊 As-Built Survey Verification Report</h2>
                    </div>
                    <div class="info-section">
                        <p><strong>📂 Survey File Name:</strong> {asbuilt_file.name}</p>
                        <p><strong>⏱️ Report Date/Time:</strong> {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}</p>
                        <p><strong>🎯 Approved Tolerance Limit:</strong> {tolerance} m ({int(tolerance*1000)} mm)</p>
                    </div>
                    {html_table.replace('<td>✅ Match</td>', '<td class="match">✅ Match</td>').replace('<td>❌ Deviation</td>', '<td class="deviation">❌ Deviation</td>')}
                    <div class="footer">
                        <p>Generated automatically by Smart Surveyor Pro System</p>
                    </div>
                </body>
                </html>
                """
                
                st.download_button(
                    label="📥 Download Official Report for PDF Printing",
                    data=html_report,
                    file_name=f"AsBuilt_Report_{asbuilt_file.name.split('.')[0]}.html",
                    mime="text/html",
                    use_container_width=True
                )
                
    except Exception as e:
        st.error(f"An error occurred while processing files: {e}")
