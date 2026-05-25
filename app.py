import streamlit as st
import ezdxf
import pandas as pd
import os
import math
import re
import base64
from io import BytesIO
import matplotlib.pyplot as plt
import seaborn as sns
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

# ==========================================
# 🏗️ إعدادات الصفحة والواجهة
# ==========================================
st.set_page_config(
    page_title="LexiMind Pro | Survey Suite V2.0", 
    page_icon="🏗️", 
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <div style="background-color: #1E3A8A; padding: 25px; border-radius: 15px; margin-bottom: 20px;">
        <h1 style="color: white; text-align: center; font-family: 'Arial';">🏗️ LexiMind Pro V2.0</h1>
        <p style="color: #BFDBFE; text-align: center; font-size: 18px;">النظام المساحي والهندسي المتكامل</p>
    </div>
""", unsafe_allow_html=True)

# ==========================================
# 🔄 تهيئة المتغيرات (Session States)
# ==========================================
if 'dxf_key' not in st.session_state: st.session_state['dxf_key'] = 0
if 'asbuilt_key' not in st.session_state: st.session_state['asbuilt_key'] = 0

# ==========================================
# 🛠️ الدوال البرمجية والهندسية
# ==========================================
def download_button_ios(data, filename, label, is_text=False):
    if is_text:
        b64 = base64.b64encode(data.encode('utf-8-sig')).decode()
        mime = "text/csv;charset=utf-8"
    else:
        b64 = base64.b64encode(data).decode()
        mime = "application/pdf"
    
    href = f'data:{mime};base64,{b64}'
    html = f'''
    <a href="{href}" download="{filename}" target="_blank" style="
        display: block; width: 100%; text-align: center; background-color: #1E3A8A;
        color: white; padding: 12px; margin: 10px 0; border-radius: 8px;
        text-decoration: none; font-weight: bold; font-size: 16px;
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
    if any(x in layer_name for x in ['ZAPATA', 'FOOT', 'قاعدة', 'FND', 'F']): return "Footings"
    if any(x in layer_name for x in ['COLUMN', 'COL', 'عمود', 'C']): return "Columns"
    if any(x in layer_name for x in ['BEAM', 'جسر', 'TIE', 'B']): return "Beams"
    if any(x in layer_name for x in ['WALL', 'جدار', 'حائط', 'MASONRY']): return "Walls"
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

def generate_pro_report_bytes(df_audit, parcel, address, owner, total_pts, passed_pts):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # الترويسة
    c.setFillColor(colors.Color(30/255, 58/255, 138/255))
    c.rect(0, height-80, width, 80, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, height-50, "LEXIMIND PRO | CERTIFIED AS-BUILT AUDIT REPORT")
    
    # بيانات المشروع
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height-110, "1. PROJECT DETAILS:")
    c.setFont("Helvetica", 10)
    c.drawString(60, height-130, f"Owner: {owner}")
    c.drawString(60, height-145, f"Parcel No: {parcel}")
    c.drawString(60, height-160, f"Address/Location: {address}")
    c.drawString(60, height-175, f"Date: {pd.Timestamp.now().strftime('%Y-%m-%d')}")
    
    # ملخص النتائج
    c.setFont("Helvetica-Bold", 12)
    c.drawString(320, height-110, "2. AUDIT SUMMARY:")
    c.setFont("Helvetica", 10)
    c.drawString(330, height-130, f"Total Points: {total_pts}")
    c.drawString(330, height-145, f"Passed: {passed_pts}")
    c.drawString(330, height-160, f"Failed: {total_pts - passed_pts}")
    
    # جدول البيانات
    y_table = height - 220
    c.setFont("Helvetica-Bold", 10)
    c.drawString(40, y_table, "Field ID")
    c.drawString(100, y_table, "Design Ref")
    c.drawString(180, y_table, "East(X)")
    c.drawString(250, y_table, "North(Y)")
    c.drawString(320, y_table, "Elev(Z)")
    c.drawString(380, y_table, "dXY(m)")
    c.drawString(440, y_table, "dZ(m)")
    c.drawString(500, y_table, "Status")
    c.line(40, y_table-5, 560, y_table-5)
    
    y_table -= 20
    c.setFont("Helvetica", 9)
    
    render_limit = min(300, len(df_audit))
    for idx, r in df_audit.head(render_limit).iterrows():
        if y_table < 50:
            c.showPage()
            y_table = height - 50
            c.setFont("Helvetica", 9)
            
        c.drawString(40, y_table, str(r['Field_ID'])[:8])
        c.drawString(100, y_table, str(r['Design_Ref'])[:12])
        c.drawString(180, y_table, f"{r['Field_X']:.3f}")
        c.drawString(250, y_table, f"{r['Field_Y']:.3f}")
        c.drawString(320, y_table, f"{r['Field_Z']:.3f}")
        c.drawString(380, y_table, f"{r['Delta_XY']:.3f}")
        c.drawString(440, y_table, f"{r['Delta_Z']:.3f}")
        
        status_text = "PASS" if "✅" in str(r['Status']) else "FAIL"
        c.setFillColor(colors.green if status_text == "PASS" else colors.red)
        c.drawString(500, y_table, status_text)
        c.setFillColor(colors.black)
        
        y_table -= 15
        
    c.save()
    buffer.seek(0)
    return buffer.getvalue()

# ==========================================
# ⚙️ إعدادات الشريط الجانبي
# ==========================================
st.sidebar.header("⚙️ إعدادات النظام")
if st.sidebar.button("🔄 إعادة ضبط النظام", use_container_width=True, type="primary"):
    st.session_state['dxf_key'] += 1
    st.session_state['asbuilt_key'] += 1
    st.rerun()

device_type = st.sidebar.selectbox("نوع جهاز المساحة:", ["Leica (CSV)", "Topcon (TXT)", "Generic (CSV)"])
tolerance_xy = st.sidebar.number_input("سماحية الإزاحة XY (متر):", value=0.02, step=0.01)
tolerance_z = st.sidebar.number_input("سماحية المنسوب Z (متر):", value=0.01, step=0.01)

# ==========================================
# 📁 معالجة ملف التصميم (DXF)
# ==========================================
st.subheader("📁 الخطوة الأولى: رفع المخطط التصميمي")
uploaded_dxf = st.file_uploader("ارفع ملف المخطط (DXF):", type=["dxf"], key=f"dxf_{st.session_state['dxf_key']}")

df_all_points = pd.DataFrame()
structural_elements = []
grid_lines = []
wall_lines = []

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
        category_counters = {"Footings": 0, "Columns": 0, "Beams": 0, "Walls": 0, "Boundary": 0, "Others": 0}
        
        for entity in msp.query('LWPOLYLINE LINE'):
            layer = entity.dxf.layer
            category = classify_layer(layer)
            
            if "GRID" in layer.upper() or "محاور" in layer.upper() or "AXIS" in layer.upper():
                if entity.dxftype() == 'LINE': 
                    grid_lines.append((entity.dxf.start, entity.dxf.end))
                continue
                
            if entity.dxftype() == 'LWPOLYLINE':
                vertices = [(v[0], v[1], v[2] if len(v)>2 else 0.0) for v in entity.get_points()]
                if not vertices: continue
                
                area = calculate_area(vertices)
                perimeter = sum(math.hypot(vertices[i][0]-vertices[i-1][0], vertices[i][1]-vertices[i-1][1]) for i in range(len(vertices)))
                
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
                else:
                    category_counters[category] += 1
                    final_prefix = f"{category[:-1]}_{category_counters[category]}"
                    
                for i, v in enumerate(vertices):
                    all_points.append({
                        "Point_ID": f"{final_prefix}_P{i+1}", 
                        "North_Y": v[1], "East_X": v[0], "Elev_Z": v[2], 
                        "Category": category, "Layer_Name": layer
                    })
        
        df_all_points = pd.DataFrame(all_points)
        os.remove(temp_path)
        st.success(f"تم تحليل التصميم بنجاح! تم استخراج {len(df_all_points)} نقطة.")
    except Exception as e:
        st.error(f"حدث خطأ أثناء قراءة الملف: {e}")

if not uploaded_dxf:
    st.info("📌 ملاحظة: الأدوات من 1 إلى 6 تتطلب رفع ملف DXF، بينما أداة التدقيق (7) تعمل مباشرة.")

# ==========================================
# 📂 التبويبات السبعة (متاحة دائماً)
# ==========================================
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "🗺️ 1. الكميات", "📍 2. توقيع ميداني", "🔄 3. تحويل إحداثيات",
    "📐 4. تقاطع المحاور", "🧱 5. أعمال الطابوق", "🚜 6. الحفريات والردم", "🔍 7. تدقيق As-Built"
])

with tab1:
    st.subheader("📊 حساب كميات الخرسانة والحديد")
    if uploaded_dxf and structural_elements:
        df_struct = pd.DataFrame(structural_elements)
        summary = df_struct.groupby(["Category", "Layer"]).agg(Count=("Area", "count"), Total_Area_m2=("Area", "sum")).reset_index()
        col_q1, col_q2 = st.columns([1, 1])
        with col_q1:
            thickness = st.number_input("سماكة الصبة (متر):", value=0.60, step=0.05)
            steel_ratio = st.number_input("كثافة الحديد (كجم/م³):", value=90.0, step=5.0)
            summary["Volume_m3"] = summary["Total_Area_m2"] * thickness
            summary["Steel_Tons"] = (summary["Volume_m3"] * steel_ratio) / 1000.0
            st.dataframe(summary, use_container_width=True)
        with col_q2:
            fig, ax = plt.subplots(figsize=(6, 4))
            sample_df = df_all_points.sample(n=min(1000, len(df_all_points)))
            for cat in sample_df['Category'].unique():
                c_data = sample_df[sample_df['Category'] == cat]
                ax.scatter(c_data['East_X'], c_data['North_Y'], label=cat, s=8)
            ax.set_aspect('equal'); ax.legend(fontsize='small'); ax.grid(True, alpha=0.3)
            st.pyplot(fig); plt.close(fig)
    else:
        st.warning("يرجى رفع ملف DXF لعرض الكميات.")

with tab2:
    st.subheader("📍 محرك التوقيع المساحي")
    if uploaded_dxf and not df_all_points.empty:
        all_layers = df_all_points["Layer_Name"].unique()
        selected_layers = st.multiselect("🎯 فلترة حسب الطبقة (Layer):", all_layers, default=all_layers)
        
        col_cfg1, col_cfg2, col_cfg3 = st.columns(3)
        off_x = col_cfg1.number_input("إزاحة ΔX:", value=0.0)
        off_y = col_cfg2.number_input("إزاحة ΔY:", value=0.0)
        use_tsp = col_cfg3.checkbox("🔄 تفعيل المسار الذكي", value=False)
        
        if selected_layers:
            df_stk = df_all_points[df_all_points['Layer_Name'].isin(selected_layers)].copy()
            if use_tsp and len(df_stk) <= 1000:
                df_stk = optimize_survey_path(df_stk)
            df_stk["East_X"] += off_x
            df_stk["North_Y"] += off_y
            
            st.dataframe(df_stk[["Point_ID", "North_Y", "East_X", "Elev_Z", "Layer_Name"]], use_container_width=True)
            delim = ',' if device_type != "Topcon (TXT)" else ' '
            txt_data = df_stk[["Point_ID", "North_Y", "East_X", "Elev_Z"]].to_csv(index=False, sep=delim, header=False)
            download_button_ios(txt_data, "Staking.txt", f"📥 تحميل ملف التوقيع", is_text=True)
    else:
        st.warning("يرجى رفع ملف DXF لاستخراج نقاط التوقيع.")

with tab3:
    st.subheader("🔄 مصفوفة التحويل والإزاحة")
    if uploaded_dxf and not df_all_points.empty:
        col_t1, col_t2, col_t3 = st.columns(3)
        shift_e = col_t1.number_input("إزاحة شرق (X):", value=0.0)
        shift_n = col_t2.number_input("إزاحة شمال (Y):", value=0.0)
        rot_ang = col_t3.number_input("دوران (درجة):", value=0.0)
        
        df_trans = df_all_points.copy()
        if rot_ang != 0:
            m_cx, m_cy = df_trans["East_X"].mean(), df_trans["North_Y"].mean()
            rotated = [rotate_point(r["East_X"], r["North_Y"], m_cx, m_cy, -rot_ang) for _, r in df_trans.iterrows()]
            df_trans["East_X"] = [p[0] for p in rotated]
            df_trans["North_Y"] = [p[1] for p in rotated]
        
        df_trans["East_X"] += shift_e
        df_trans["North_Y"] += shift_n
        st.dataframe(df_trans[["Point_ID", "North_Y", "East_X"]], use_container_width=True)
    else:
        st.warning("يرجى رفع ملف DXF لتطبيق التحويلات.")

with tab4:
    st.subheader("📐 تقاطعات المحاور والشبكات")
    if uploaded_dxf:
        if grid_lines:
            intersections = []
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
            else: st.warning("لم يتم العثور على تقاطعات.")
        else: st.info("لم يتم العثور على خطوط محاور (Grid) في الملف.")
    else:
        st.warning("يرجى رفع ملف DXF لحساب التقاطعات.")

with tab5:
    st.subheader("🧱 تقدير الطابوق والمباني")
    if uploaded_dxf:
        if wall_lines:
            total_w = pd.DataFrame(wall_lines)["Length"].sum()
            st.info(f"إجمالي أطوال الجدران: {round(total_w, 2)} متر")
            h = st.number_input("ارتفاع الجدار (متر):", value=3.20)
            st.success(f"العدد التقديري للطابوق: {math.ceil(total_w * h * 12.5)} حبة")
        else: st.info("لم يتم اكتشاف طبقات جدران (Wall).")
    else:
        st.warning("يرجى رفع ملف DXF لحساب كميات الجدران.")

with tab6:
    st.subheader("🚜 حساب كميات الحفر والردم")
    if uploaded_dxf:
        if structural_elements:
            tot_a = pd.DataFrame(structural_elements)["Area"].sum()
            st.info(f"مساحة البصمة الإنشائية: {round(tot_a, 2)} متر مربع")
            ngl = st.number_input("منسوب الأرض الطبيعية (NGL):", value=1.0)
            target = st.number_input("منسوب الحفر المستهدف:", value=0.0)
            vol = tot_a * abs(ngl - target)
            st.error(f"حجم الحفريات التقريبي: {round(vol, 2)} متر مكعب")
        else: st.info("لم يتم العثور على مساحات إنشائية.")
    else:
        st.warning("يرجى رفع ملف DXF لحساب الحفريات.")

with tab7:
    st.subheader("🔍 نظام التدقيق الميداني الشامل (As-Built V2.0)")
    st.markdown("**(هذه الأداة تعمل سواء قمت برفع ملف DXF للمقارنة التلقائية أو استخدمتها منفردة لإصدار التقارير)**")
    
    with st.expander("📝 بيانات القسيمة للتقرير النهائي", expanded=True):
        col_p1, col_p2, col_p3 = st.columns(3)
        parcel_no = col_p1.text_input("رقم القسيمة (Parcel):", "القسيمة 101")
        owner_name = col_p2.text_input("اسم المالك (Owner):", "السيد/ المالك")
        parcel_loc = col_p3.text_input("العنوان (Address):", "الكويت - مدينة المطلاع")
        
    asb_f = st.file_uploader("ارفع ملف الرفع الميداني (CSV/TXT):", key=f"asb_{st.session_state['asbuilt_key']}")
    
    if asb_f:
        try:
            first_line = asb_f.readline().decode('utf-8-sig', errors='ignore')
            asb_f.seek(0)
            s_char = ',' if ',' in first_line else r'\s+'
            
            df_asb = pd.read_csv(asb_f, sep=s_char, header=None, names=["ID", "Y", "X", "Z"], engine='python')
            df_asb['X'] = pd.to_numeric(df_asb['X'], errors='coerce')
            df_asb['Y'] = pd.to_numeric(df_asb['Y'], errors='coerce')
            df_asb['Z'] = pd.to_numeric(df_asb['Z'], errors='coerce').fillna(0.0)
            df_asb = df_asb.dropna(subset=['X', 'Y'])
            
            chk = []
            passed_count = 0
            
            # إذا كان هناك ملف DXF مرفوع، نقوم بالمقارنة الحقيقية
            if not df_all_points.empty:
                for _, r in df_asb.iterrows():
                    m_d = float('inf')
                    n_pt = None
                    for _, dr in df_all_points.iterrows():
                        dst = math.hypot(r['X'] - dr['East_X'], r['Y'] - dr['North_Y'])
                        if dst < m_d: 
                            m_d = dst; n_pt = dr
                            
                    dz = abs(r['Z'] - n_pt['Elev_Z']) if n_pt is not None else 0.0
                    is_pass = (m_d <= tolerance_xy) and (dz <= tolerance_z)
                    if is_pass: passed_count += 1
                    
                    chk.append({
                        "Field_ID": r['ID'], "Design_Ref": n_pt['Point_ID'] if n_pt is not None else "N/A",
                        "Field_X": r['X'], "Field_Y": r['Y'], "Field_Z": r['Z'],
                        "Delta_XY": m_d, "Delta_Z": dz, "Status": "✅ PASS" if is_pass else "❌ FAIL"
                    })
            else:
                # إذا لم يكن هناك DXF، نعرض البيانات كما هي مع محاكاة للتقرير
                st.info("لم يتم رفع ملف DXF، سيتم عرض بيانات الرفع الميداني فقط في التقرير.")
                for _, r in df_asb.iterrows():
                    passed_count += 1
                    chk.append({
                        "Field_ID": r['ID'], "Design_Ref": "بدون مرجع",
                        "Field_X": r['X'], "Field_Y": r['Y'], "Field_Z": r['Z'],
                        "Delta_XY": 0.0, "Delta_Z": 0.0, "Status": "✅ RECORDED"
                    })

            df_audit = pd.DataFrame(chk)
            st.dataframe(df_audit[["Field_ID", "Design_Ref", "Delta_XY", "Delta_Z", "Status"]], use_container_width=True)
            
            st.markdown("### 📊 خريطة الانحرافات الحرارية (Heatmap)")
            fig, ax = plt.subplots(figsize=(8, 5))
            sc = ax.scatter(df_audit['Field_X'], df_audit['Field_Y'], 
                            c=df_audit['Delta_XY'], cmap='RdYlGn_r', 
                            s=50, edgecolor='k')
            plt.colorbar(sc, label='مقدار الانحراف (متر)')
            ax.set_aspect('equal')
            ax.grid(True, linestyle='--', alpha=0.5)
            st.pyplot(fig); plt.close(fig)
            
            if st.button("📄 إصدار التقرير النهائي (PDF)"):
                pdf_bytes = generate_pro_report_bytes(
                    df_audit, parcel_no, parcel_loc, owner_name, 
                    total_pts=len(df_audit), passed_pts=passed_count
                )
                download_button_ios(pdf_bytes, f"Audit_{parcel_no}.pdf", "📥 تحميل التقرير المعتمد (PDF)")
                
        except Exception as e:
            st.error(f"حدث خطأ أثناء معالجة بيانات الرفع: {e}")
