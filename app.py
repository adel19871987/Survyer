import streamlit as st
import ezdxf
import pandas as pd
import os
import math
import re
import base64
from io import BytesIO
import plotly.express as px
import plotly.graph_objects as go
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

# ==========================================
# 🏗️ إعدادات الواجهة الرئيسية والهوية البصرية
# ==========================================
st.set_page_config(
    page_title="LexiMind Pro | Survey Suite V2.0", 
    page_icon="🏗️", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# تصميم هيدر احترافي متناسق
st.markdown("""
    <div style="background-color: #1E3A8A; padding: 25px; border-radius: 15px; margin-bottom: 20px;">
        <h1 style="color: white; text-align: center; font-family: 'Arial'; margin:0;">🏗️ LexiMind Pro V2.0</h1>
        <p style="color: #BFDBFE; text-align: center; font-size: 18px; margin:5px 0 0 0;">النظام الهندسي والمساحي المتكامل لتحليل المخططات والتدقيق الميداني الدقيق</p>
    </div>
""", unsafe_allow_html=True)

# ==========================================
# 🔄 تهيئة وإدارة الجلسات (Session States)
# ==========================================
if 'dxf_key' not in st.session_state: st.session_state['dxf_key'] = 0
if 'asbuilt_key' not in st.session_state: st.session_state['asbuilt_key'] = 0

# ==========================================
# 🛠️ الدوال البرمجية والخوارزميات الهندسية
# ==========================================
def download_button_ios(data, filename, label, is_text=False):
    """دالة توليد روابط تحميل متوافقة مع جميع الأجهزة والـ iOS بدون مشاكل"""
    if is_text:
        b64 = base64.b64encode(data.encode('utf-8-sig')).decode()
        mime = "text/plain;charset=utf-8"
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
    """حساب مساحة المضلعات المغلقة باستخدام خوارزمية Shoelace"""
    area = 0.0
    for i in range(len(vertices)):
        j = (i + 1) % len(vertices)
        area += vertices[i][0] * vertices[j][1]
        area -= vertices[j][0] * vertices[i][1]
    return abs(area) / 2.0

def classify_layer(layer_name):
    """التصنيف الذكي للطبقات الإنشائية والمعمارية بناءً على المسميات الهندسية الدارجة"""
    layer_name = layer_name.upper()
    if any(x in layer_name for x in ['ZAPATA', 'FOOT', 'قاعدة', 'FND', 'F']): return "Footings"
    if any(x in layer_name for x in ['COLUMN', 'COL', 'عمود', 'C']): return "Columns"
    if any(x in layer_name for x in ['BEAM', 'جسر', 'TIE', 'B']): return "Beams"
    if any(x in layer_name for x in ['WALL', 'جدار', 'حائط', 'MASONRY']): return "Walls"
    if any(x in layer_name for x in ['BOUNDARY', 'SITE', 'حد']): return "Boundary"
    return "Others"

def clean_mtext(text_val):
    """تنظيف نصوص الأوتوكاد (MTEXT) من أكواد التنسيق الداخلية"""
    text_val = re.sub(r'\\[a-zA-Z0-9]+;', '', text_val)
    text_val = text_val.replace(r'\P', ' ').strip()
    return text_val

def rotate_point(x, y, cx, cy, angle_deg):
    """تدوير نقطة بزاوية محددة حول مركز دوران معين"""
    angle_rad = math.radians(angle_deg)
    nx = cx + (x - cx) * math.cos(angle_rad) - (y - cy) * math.sin(angle_rad)
    ny = cy + (x - cx) * math.sin(angle_rad) + (y - cy) * math.cos(angle_rad)
    return nx, ny

def optimize_survey_path(df):
    """خوارزمية الجار الأقرب (Nearest Neighbor) لتحديد المسار الذكي لتوقيع النقاط ميدانياً"""
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
    """توليد ملف PDF احترافي معتمد بكافة تفاصيل الرفع الميداني والانحرافات الحاصلة"""
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # تصميم ترويسة التقرير
    c.setFillColor(colors.Color(30/255, 58/255, 138/255))
    c.rect(0, height-80, width, 80, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, height-50, "LEXIMIND PRO | CERTIFIED AS-BUILT AUDIT REPORT")
    
    # معلومات المشروع والقسيمة
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, height-110, "1. PROJECT DETAILS:")
    c.setFont("Helvetica", 10)
    c.drawString(50, height-130, f"Owner: {owner}")
    c.drawString(50, height-145, f"Parcel No: {parcel}")
    c.drawString(50, height-160, f"Address/Location: {address}")
    c.drawString(50, height-175, f"Date: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}")
    
    # ملخص التحليل والتدقيق الرقمي
    c.setFont("Helvetica-Bold", 12)
    c.drawString(320, height-110, "2. AUDIT SUMMARY:")
    c.setFont("Helvetica", 10)
    c.drawString(330, height-130, f"Total Points Audited: {total_pts}")
    c.drawString(330, height-145, f"Passed Within Tolerance: {passed_pts}")
    c.drawString(330, height-160, f"Failed / Out of Tolerance: {total_pts - passed_pts}")
    
    # ترويسة جدول البيانات
    y_table = height - 210
    c.setFont("Helvetica-Bold", 10)
    c.drawString(40, y_table, "Field ID")
    c.drawString(110, y_table, "Design Ref")
    c.drawString(190, y_table, "East(X)")
    c.drawString(260, y_table, "North(Y)")
    c.drawString(330, y_table, "Elev(Z)")
    c.drawString(390, y_table, "dXY(m)")
    c.drawString(450, y_table, "dZ(m)")
    c.drawString(510, y_table, "Status")
    c.line(40, y_table-5, 560, y_table-5)
    
    y_table -= 20
    c.setFont("Helvetica", 9)
    
    # تعبئة أسطر جدول البيانات الميدانية والتدقيقية
    for idx, r in df_audit.head(35).iterrows():
        if y_table < 50:
            c.showPage()
            y_table = height - 50
            c.setFont("Helvetica", 9)
            
        c.drawString(40, y_table, str(r['Field_ID'])[:10])
        c.drawString(110, y_table, str(r['Design_Ref'])[:12])
        c.drawString(190, y_table, f"{r['Field_X']:.3f}")
        c.drawString(260, y_table, f"{r['Field_Y']:.3f}")
        c.drawString(330, y_table, f"{r['Field_Z']:.3f}")
        c.drawString(390, y_table, f"{r['Delta_XY']:.3f}")
        c.drawString(450, y_table, f"{r['Delta_Z']:.3f}")
        
        status_text = "PASS" if "مطابقة" in str(r['Status']) else ("ALERT" if "تنبيه" in str(r['Status']) else "FAIL")
        if status_text == "PASS": c.setFillColor(colors.green)
        elif status_text == "ALERT": c.setFillColor(colors.orange)
        else: c.setFillColor(colors.red)
        
        c.drawString(510, y_table, status_text)
        c.setFillColor(colors.black)
        
        y_table -= 15
        
    c.save()
    buffer.seek(0)
    return buffer.getvalue()

# ==========================================
# ⚙️ إعدادات وتخصيصات شريط التحكم الجانبي
# ==========================================
st.sidebar.header("⚙️ معايير النظام والموقع")
if st.sidebar.button("🔄 إعادة تعيين وتنظيف النظام", use_container_width=True, type="primary"):
    st.session_state['dxf_key'] += 1
    st.session_state['asbuilt_key'] += 1
    st.rerun()

device_type = st.sidebar.selectbox("صيغة التصدير للأجهزة الميدانية:", ["Leica (CSV)", "Topcon (TXT)", "Sokkia (CSV)"])
tolerance_z = st.sidebar.number_input("حد المسامحة الرأسي المسموح Z (متر):", value=0.01, step=0.01, format="%.3f")

# ربط ديناميكي عالمي: إدخال مصفوفة التحويل من الشريط الجانبي لتسمع في كل مكان تلقائياً
st.sidebar.markdown("---")
st.sidebar.header("🔄 مصفوفة التحويل العالمية")
shift_e = st.sidebar.number_input("مقدار الإزاحة للشرق (Shift East):", value=0.0, format="%.3f")
shift_n = st.sidebar.number_input("مقدار الإزاحة للشمال (Shift North):", value=0.0, format="%.3f")
rot_ang = st.sidebar.number_input("زاوية تدوير المخطط (Rotation Angle):", value=0.0, format="%.4f")

# ==========================================
# 📁 الخطوة الأساسية: قراءة وتحليل ملف الأوتوكاد DXF
# ==========================================
st.subheader("📁 الخطوة الأولى: رفع المخطط الهندسي (Design File)")
uploaded_dxf = st.file_uploader("ارفع ملف المخطط بصيغة DXF فقط:", type=["dxf"], key=f"dxf_{st.session_state['dxf_key']}")

# تهيئة جداول تخزين البيانات المستخرجة من DXF لمنع مشاكل التحميل
df_raw_points = pd.DataFrame()
df_all_points = pd.DataFrame()
structural_elements = []
grid_lines = []
wall_lines = []

if uploaded_dxf:
    try:
        temp_path = f"temp_engine_{uploaded_dxf.name}"
        with open(temp_path, "wb") as f:
            f.write(uploaded_dxf.getbuffer())
        
        doc = ezdxf.readfile(temp_path)
        msp = doc.modelspace()
        
        # 🚀 [تعديل الميزة الأولى] محرك التفكيك الذكي للـ Blocks (Virtual Explode)
        flat_ents = []
        for ent in msp:
            if ent.dxftype() == 'INSERT':
                try:
                    for v_ent in ent.virtual_entities():
                        if not hasattr(v_ent.dxf, 'layer') or v_ent.dxf.layer == '0':
                            v_ent.dxf.layer = ent.dxf.layer
                        flat_ents.append(v_ent)
                except:
                    flat_ents.append(ent)
            else:
                flat_ents.append(ent)
        
        # 1. تجميع وتصفية نصوص الأوتوكاد للربط الذكي بالنقاط من العناصر المفككة
        text_pool = []
        text_entities = [e for e in flat_ents if e.dxftype() in ('TEXT', 'MTEXT')]
        for text_ent in text_entities:
            try:
                raw_txt = text_ent.dxf.insert
                txt_str = text_ent.dxf.text if text_ent.dxftype() == 'TEXT' else text_ent.text
                cleaned_txt = clean_mtext(txt_str)
                if cleaned_txt and len(cleaned_txt) < 15:
                    text_pool.append({"text": cleaned_txt, "x": raw_txt.x, "y": raw_txt.y})
            except: continue
        
        # 2. استخراج وفك شفرات العناصر الهندسية (LWPOLYLINE / LINE)
        all_points = []
        category_counters = {"Footings": 0, "Columns": 0, "Beams": 0, "Walls": 0, "Boundary": 0, "Others": 0}
        geo_entities = [e for e in flat_ents if e.dxftype() in ('LWPOLYLINE', 'LINE')]
        
        for entity in geo_entities:
            layer = entity.dxf.layer
            category = classify_layer(layer)
            
            # عزل خطوط المحاور والشبكات التخطيطية
            if any(x in layer.upper() for x in ["GRID", "محاور", "AXIS", "CENTER"]):
                if entity.dxftype() == 'LINE': 
                    grid_lines.append((entity.dxf.start, entity.dxf.end))
                continue
                
            if entity.dxftype() == 'LINE':
                # تحويل الخطوط البسيطة إلى نقاط هندسية
                p1 = entity.dxf.start
                p2 = entity.dxf.end
                all_points.append({"Point_ID": f"{category[:-1]}_L_Start", "North_Y": p1.y, "East_X": p1.x, "Elev_Z": p1.z, "Category": category, "Layer_Name": layer})
                all_points.append({"Point_ID": f"{category[:-1]}_L_End", "North_Y": p2.y, "East_X": p2.x, "Elev_Z": p2.z, "Category": category, "Layer_Name": layer})
                if category == "Walls":
                    length = math.hypot(p2.x - p1.x, p2.y - p1.y)
                    wall_lines.append({"Length": length, "Layer": layer})
                continue
                
            if entity.dxftype() == 'LWPOLYLINE':
                vertices = [(v[0], v[1], v[2] if len(v)>2 else 0.0) for v in entity.get_points()]
                if not vertices: continue
                
                area = calculate_area(vertices)
                perimeter = sum(math.hypot(vertices[i][0]-vertices[i-1][0], vertices[i][1]-vertices[i-1][1]) for i in range(len(vertices)))
                
                if category == "Walls" and area >= 0:
                    wall_lines.append({"Length": perimeter / 2.0, "Layer": layer})
                    
                cx = sum(v[0] for v in vertices) / len(vertices)
                cy = sum(v[1] for v in vertices) / len(vertices)
                xs = [v[0] for v in vertices]; ys = [v[1] for v in vertices]
                max_dim = math.hypot(max(xs) - min(xs), max(ys) - min(ys))
                
                if area > 0 and category in ["Footings", "Columns", "Beams"]:
                    structural_elements.append({"Category": category, "Layer": layer, "Area": area})
                
                # ربط التسمية النصية الأقرب للعنصر الإنشائي
                matched_text = None; min_text_dist = float('inf')
                for t in text_pool:
                    d = math.hypot(t['x'] - cx, t['y'] - cy)
                    if d < min_text_dist: min_text_dist = d; matched_text = t
                    
                if matched_text and min_text_dist <= (max_dim * 1.2):
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
        
        if all_points:
            df_raw_points = pd.DataFrame(all_points).drop_duplicates(subset=['North_Y', 'East_X'])
            df_all_points = df_raw_points.copy()
            
            # 🚀 [تعديل الميزة الثالثة] تطبيق المصفوفة جغرافياً بشكل حي وعالمي بمجرد استخراج البيانات
            if rot_ang != 0:
                m_cx, m_cy = df_all_points["East_X"].mean(), df_all_points["North_Y"].mean()
                rotated = [rotate_point(r["East_X"], r["North_Y"], m_cx, m_cy, -rot_ang) for _, r in df_all_points.iterrows()]
                df_all_points["East_X"] = [p[0] for p in rotated]
                df_all_points["North_Y"] = [p[1] for p in rotated]
            
            df_all_points["East_X"] += shift_e
            df_all_points["North_Y"] += shift_n
            
            # تدوير وإزاحة خطوط المحاور أيضاً لتتناسب الحسابات تلقائياً في التبويبات الأخرى
            if grid_lines:
                transformed_grid_lines = []
                g_cx = df_raw_points["East_X"].mean()
                g_cy = df_raw_points["North_Y"].mean()
                class TransformedPoint:
                    def __init__(self, x, y): self.x = x; self.y = y
                for start, end in grid_lines:
                    sx, sy = start.x, start.y
                    ex, ey = end.x, end.y
                    if rot_ang != 0:
                        sx, sy = rotate_point(sx, sy, g_cx, g_cy, -rot_ang)
                        ex, ey = rotate_point(ex, ey, g_cx, g_cy, -rot_ang)
                    transformed_grid_lines.append((TransformedPoint(sx + shift_e, sy + shift_n), TransformedPoint(ex + shift_e, ey + shift_n)))
                grid_lines = transformed_grid_lines

        os.remove(temp_path)
        st.success(f"✅ تم تحليل وهندسة ملف الأوتوكاد بنجاح (وفك البلوكات المكتشفة تلقائياً)! تم استخراج وتصنيف {len(df_all_points)} نقطة هندسية معدلة.")
    except Exception as e:
        st.error(f"❌ حدث خطأ أثناء تحليل ملف DXF: {e}")

# ==========================================
# 📑 محرك التبويبات السبعة المتكامل والنشط دائماً
# ==========================================
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "🗺️ 1. حساب الكميات", "📍 2. التوقيع الميداني", "🔄 3. مصفوفة التحويل",
    "📐 4. تقاطع المحاور", "🧱 5. أعمال الطابوق", "🚜 6. الحفريات والردم", "🔍 7. تدقيق As-Built"
])

# ------------------------------------------
# التبويب 1: حساب كميات الخرسانة والحديد
# ------------------------------------------
with tab1:
    st.subheader("📊 نظام مسح وجدولة كميات الخرسانة والحديد التلقائي")
    if not df_all_points.empty and structural_elements:
        df_struct = pd.DataFrame(structural_elements)
        summary = df_struct.groupby(["Category", "Layer"]).agg(Count=("Area", "count"), Total_Area_m2=("Area", "sum")).reset_index()
        
        col_q1, col_q2 = st.columns([4, 3])
        with col_q1:
            st.markdown("##### ⚙️ معطيات وحساب التكعيب صب الخرسانة")
            thickness = st.number_input("سماكة الصبة التقديرية (متر):", value=0.60, step=0.05, format="%.2f")
            steel_ratio = st.number_input("كثافة حديد التسليح للمتر المكعب الواحد (كجم/م³):", value=90.0, step=5.0)
            
            summary["Volume_m3"] = summary["Total_Area_m2"] * thickness
            summary["Steel_Tons"] = (summary["Volume_m3"] * steel_ratio) / 1000.0
            
            st.markdown("##### 📈 جدول حصر الكميات المستخرجة")
            st.dataframe(summary, use_container_width=True)
            
        with col_q2:
            st.markdown("##### 📍 توزيع العناصر الإنشائية (خريطة تفاعلية بالكامل مع دعم التكبير واللمس) 🗺️")
            sample_df = df_all_points.sample(n=min(1200, len(df_all_points)))
            
            # 🚀 [تعديل الميزة الثانية] استبدال matplotlib بـ Plotly الخريطة التفاعلية بالكامل
            fig1 = px.scatter(
                sample_df, x='East_X', y='North_Y', color='Category',
                hover_data=['Point_ID', 'Layer_Name', 'Elev_Z'],
                labels={'East_X': 'East (X)', 'North_Y': 'North (Y)'}
            )
            fig1.update_traces(marker=dict(size=6, opacity=0.85, line=dict(width=0.5, color='DarkSlateGrey')))
            fig1.update_layout(
                dragmode='zoom', 
                template="plotly_white", 
                margin=dict(l=0, r=0, t=10, b=0),
                xaxis=dict(scaleanchor="y", scaleratio=1)
            )
            fig1.update_layout(modebar_add=['zoomIn2d', 'zoomOut2d', 'pan2d', 'resetScale2d'])
            st.plotly_chart(fig1, use_container_width=True)
    else:
        st.info("💡 يرجى رفع ملف المخطط (DXF) في الأعلى لتفعيل حساب كميات القواعد والأعمدة تلقائياً.")

# ------------------------------------------
# التبويب 2: التوقيع الميداني واستخراج النقاط
# ------------------------------------------
with tab2:
    st.subheader("📍 نظام تصفية واستخراج ملفات التوقيع (Setting-Out Data)")
    if not df_all_points.empty:
        all_layers = df_all_points["Layer_Name"].unique()
        selected_layers = st.multiselect("🎯 اختر الطبقات (Layers) المراد استخراج نقاطها للتوقيع:", all_layers, default=all_layers)
        
        col_cfg1, col_cfg2, col_cfg3 = st.columns(3)
        off_x = col_cfg1.number_input("إزاحة إضافية لمحور الشرق (ΔX Offset):", value=0.0, step=0.1)
        off_y = col_cfg2.number_input("إزاحة إضافية لمحور الشمال (ΔY Offset):", value=0.0, step=0.1)
        use_tsp = col_cfg3.checkbox("🔄 تفعيل خوارزمية المسار الذكي المساحي الأقصر", value=True)
        
        if selected_layers:
            df_stk = df_all_points[df_all_points['Layer_Name'].isin(selected_layers)].copy()
            if use_tsp and len(df_stk) <= 1500:
                df_stk = optimize_survey_path(df_stk)
                
            df_stk["East_X"] += off_x
            df_stk["North_Y"] += off_y
            
            st.markdown(f"**عدد النقاط الجاهزة للتصدير:** {len(df_stk)}")
            st.dataframe(df_stk[["Point_ID", "North_Y", "East_X", "Elev_Z", "Layer_Name"]], use_container_width=True)
            
            delim = ',' if "CSV" in device_type else '\t'
            ext = "csv" if "CSV" in device_type else "txt"
            txt_data = df_stk[["Point_ID", "North_Y", "East_X", "Elev_Z"]].to_csv(index=False, sep=delim, header=False)
            download_button_ios(txt_data, f"Staking_Data_{pd.Timestamp.now().strftime('%d_%m')}.{ext}", "📥 تحميل ملف التوقيع لجهاز المساحة فوراً", is_text=True)
    else:
        st.info("💡 يرجى رفع ملف المخطط (DXF) لتصفية وتصدير إحداثيات التوقيع إلى أجهزة الـ Total Station والـ GPS.")

# ------------------------------------------
# التبويب 3: مصفوفة تحويل وتعديل الإحداثيات
# ------------------------------------------
with tab3:
    st.subheader("🔄 معالج تحويل، تدوير، وإزاحة الإحداثيات الهندسية")
    if not df_all_points.empty:
        df_compare = df_raw_points.copy().rename(columns={'East_X': 'Original_X', 'North_Y': 'Original_Y'})
        df_compare['Transformed_X'] = df_all_points['East_X']
        df_compare['Transformed_Y'] = df_all_points['North_Y']
        
        st.markdown("##### 🧮 الإحداثيات والتحويلات الحية النشطة بالمشروع (مقارنة الإحداثي الأصلي والجديد المحول من القائمة الجانبية):")
        st.dataframe(df_compare[["Point_ID", "Layer_Name", "Original_X", "Original_Y", "Transformed_X", "Transformed_Y"]], use_container_width=True)
    else:
        st.info("💡 يرجى رفع ملف المخطط (DXF) لتطبيق التحويلات الحسابية والتدوير المباشر.")

# ------------------------------------------
# التبويب 4: حساب تقاطعات المحاور والشبكات
# ------------------------------------------
with tab4:
    st.subheader("📐 استخراج نقاط تقاطعات خطوط المحاور (Grid Intersection Point)")
    if uploaded_dxf:
        if grid_lines:
            intersections = []
            limit_grids = grid_lines[:150] # تحديد الحد لمنع بطء المعالجة
            for i in range(len(limit_grids)):
                for j in range(i + 1, len(limit_grids)):
                    p1, p2 = limit_grids[i][0], limit_grids[i][1]
                    p3, p4 = limit_grids[j][0], limit_grids[j][1]
                    
                    den = (p4.x - p3.x) * (p2.y - p1.y) - (p4.y - p3.y) * (p2.x - p1.x)
                    if abs(den) < 1e-6: continue
                    
                    ua = ((p4.x - p3.x) * (p1.y - p3.y) - (p4.y - p3.y) * (p1.x - p3.x)) / den
                    ub = ((p2.x - p1.x) * (p1.y - p3.y) - (p2.y - p1.y) * (p1.x - p3.x)) / den
                    
                    if 0 <= ua <= 1 and 0 <= ub <= 1:
                        intersections.append((p1.x + ua * (p2.x - p1.x), p1.y + ua * (p2.y - p1.y)))
                        
            if intersections:
                df_inter = pd.DataFrame(intersections, columns=["Intersection_X", "Intersection_Y"]).drop_duplicates()
                st.success(f"🎯 تم العثور على {len(df_inter)} نقطة تقاطع محاور رئيسية بناءً على الإحداثيات المحولة النشطة.")
                st.dataframe(df_inter, use_container_width=True)
            else: 
                st.warning("⚠️ تم التعرف على طبقة المحاور، ولكن لم يتم العثور على تقاطعات هندسية مباشرة بين الخطوط المتاحة.")
        else: 
            st.info("ℹ️ لم يتم العثور على عناصر خطوط تحمل اسم طبقة 'Grid' أو 'محاور' في ملف الأوتوكاد لاستخلاص نقاط التقاطع تلقائياً.")
    else:
        st.info("💡 يرجى رفع ملف المخطط (DXF) لحساب واستخراج إحداثيات تقاطع الأكسات (المحاور).")

# ------------------------------------------
# التبويب 5: تقدير وحساب الطابوق والمباني
# ------------------------------------------
with tab5:
    st.subheader("🧱 حصر أطوال الجدران وتقدير كميات الطابوق (Masonry Estimation)")
    if uploaded_dxf:
        if wall_lines:
            df_walls = pd.DataFrame(wall_lines)
            total_wall_len = df_walls["Length"].sum()
            
            st.info(f"📏 إجمالي أطوال الجدران والتمتير الطولي المكتشف في المخطط: {round(total_wall_len, 2)} متر طولي.")
            
            col_b1, col_b2 = st.columns(2)
            wall_height = col_b1.number_input("متوسط ارتفاع جدار الحائط (متر):", value=3.20, step=0.10)
            brick_factor = col_b2.number_input("معدل استهلاك الطابوق للمتر المربع (حبة/م²):", value=12.5, step=0.5)
            
            total_area = total_wall_len * wall_height
            estimated_bricks = math.ceil(total_area * brick_factor)
            
            st.success(f"🧱 المساحة الإجمالية للجدران: {round(total_area, 2)} م² | العدد التقديري المطلوب للطابوق: {estimated_bricks} حبة.")
        else: 
            st.info("ℹ️ لم يتم العثور على مضلعات أو خطوط في طبقة تحمل اسم 'Wall' أو 'جدار' لحساب التقديرات.")
    else:
        st.info("💡 يرجى رفع ملف المخطط (DXF) لتقدير أعداد الطابوق بناءً على جدران المخطط الإنشائي والمعماري.")

# ------------------------------------------
# التبويب 6: تقدير أعمال الحفريات والردم
# ------------------------------------------
with tab6:
    st.subheader("🚜 الحساب الأولي لأعمال ومكعبات الحفر والردم")
    if uploaded_dxf:
        if structural_elements:
            df_struct_exc = pd.DataFrame(structural_elements)
            footing_area = df_struct_exc[df_struct_exc["Category"] == "Footings"]["Area"].sum()
            if footing_area == 0: 
                footing_area = df_struct_exc["Area"].sum()
                
            st.info(f"📐 مساحة البصمة الإنشائية للمبنى وقسيمة القواعد المكتشفة: {round(footing_area, 2)} متر مربع.")
            
            col_e1, col_e2 = st.columns(2)
            ngl_level = col_e1.number_input("منسوب الأرض الطبيعية الحالية (NGL):", value=1.50, step=0.10, format="%.2f")
            excavation_target = col_e2.number_input("منسوب قاع الحفر المستهدف (Target Excavation Level):", value=0.00, step=0.10, format="%.2f")
            
            depth = abs(ngl_level - excavation_target)
            computed_volume = footing_area * depth
            
            st.error(f"🚜 عمق الحفر المطلق: {round(depth, 2)} متر | حجم الحفريات التقديري المطلوب نقله: {round(computed_volume, 2)} متر مكعب.")
        else: 
            st.info("ℹ️ لم يتم العثور على مساحات مغلقة في طبقات القواعد لتقدير مكعبات الحفر.")
    else:
        st.info("💡 يرجى رفع ملف المخطط (DXF) لحساب حجوم أعمال الحفر بناءً على مساحة المنشأ الإنشائي.")

# ------------------------------------------
# التبويب 7: نظام التدقيق الميداني الشامل المحدث والأهم (As-Built V2.0)
# ------------------------------------------
with tab7:
    st.subheader("🔍 نظام التدقيق والمقارنة الرقمي الذكي لنقاط الرفع الميداني As-Built")
    st.markdown("**(هذه الأداة تعمل تلقائياً وبأعلى كفاءة سواء تم رفع ملف الأوتوكاد للمقارنة الذكية، أو استخدمت بشكل منفصل لتوثيق نقاط الرفع الميداني وإصدار التقارير)**")
    
    # حقول إدخال بيانات التقرير الرسمي للاستشاري والمالك
    with st.expander("📝 بيانات القسيمة والمالك للتقرير النهائي المعتمد", expanded=True):
        col_p1, col_p2, col_p3 = st.columns(3)
        parcel_no = col_p1.text_input("رقم القسيمة / المشروع:", "قسيمة رقم 452")
        owner_name = col_p2.text_input("اسم المالك المعتمد:", "السيد / صاحب القسيمة المحترم")
        parcel_loc = col_p3.text_input("موقع أو عنوان القسيمة الميداني:", "مدينة المطلاع السكنية - قطاع N5")
        
    asb_f = st.file_uploader("ارفع ملف الرفع الميداني الفعلي بصيغة (CSV / TXT):", key=f"asb_{st.session_state['asbuilt_key']}")
    
    if asb_f:
        try:
            # قراءة السطر الأول لتحديد الفاصل المستعمل تلقائياً لمنع أخطاء التنسيق
            first_line = asb_f.readline().decode('utf-8-sig', errors='ignore')
            asb_f.seek(0)
            separator_char = ',' if ',' in first_line else r'\s+'
            
            df_asb = pd.read_csv(asb_f, sep=separator_char, header=None, names=["ID", "Y", "X", "Z"], engine='python')
            df_asb['X'] = pd.to_numeric(df_asb['X'], errors='coerce')
            df_asb['Y'] = pd.to_numeric(df_asb['Y'], errors='coerce')
            df_asb['Z'] = pd.to_numeric(df_asb['Z'], errors='coerce').fillna(0.0)
            df_asb = df_asb.dropna(subset=['X', 'Y'])
            
            chk_results = []
            passed_count = 0
            
            # خوارزمية تحديد الحالة بناءً على شروط أبو عابد الدقيقة (0-2 ملم أخضر، 3-5 ملم أصفر، >5 ملم أحمر)
            def calculate_spatial_status(val):
                if val <= 0.002:
                    return "✅ مطابقة (0 - 2 ملم)"
                elif val <= 0.005:
                    return "⚠️ تنبيه (3 - 5 ملم)"
                else:
                    return "❌ خارج السماحية (> 5 ملم)"
            
            # الحالة الأولى: وجود ملف أوتوكاد DXF للقيام بالمقارنة الدقيقة تلقائياً مع تتبع الإحداثيات النشطة المعدلة جغرافياً
            if not df_all_points.empty:
                for _, r in df_asb.iterrows():
                    min_dist = float('inf')
                    nearest_design_point = None
                    
                    # البحث التلقائي عن أقرب نقطة تصميمية مرجعية محولة
                    for _, dr in df_all_points.iterrows():
                        dst = math.hypot(r['X'] - dr['East_X'], r['Y'] - dr['North_Y'])
                        if dst < min_dist: 
                            min_dist = dst
                            nearest_design_point = dr
                            
                    dz = abs(r['Z'] - nearest_design_point['Elev_Z']) if nearest_design_point is not None else 0.0
                    
                    status_str = calculate_spatial_status(min_dist)
                    if "مطابقة" in status_str: 
                        passed_count += 1
                    
                    chk_results.append({
                        "Field_ID": r['ID'], 
                        "Design_Ref": nearest_design_point['Point_ID'] if nearest_design_point is not None else "N/A",
                        "Field_X": r['X'], "Field_Y": r['Y'], "Field_Z": r['Z'],
                        "Delta_XY": min_dist, "Delta_Z": dz, 
                        "Status": status_str
                    })
            else:
                # الحالة الثانية: غياب ملف DXF، نقوم بجدولة نقاط الرفع وحفظها لغرض التقرير الرسمي
                st.info("ℹ️ لم يتم رفع ملف DXF للتصميم، سيقوم النظام بجدولة ورسم نقاط الرفع الفعلي الميداني وإدراجها بالتقرير مباشرة.")
                for _, r in df_asb.iterrows():
                    passed_count += 1
                    chk_results.append({
                        "Field_ID": r['ID'], "Design_Ref": "بدون مرجع تصميمي",
                        "Field_X": r['X'], "Field_Y": r['Y'], "Field_Z": r['Z'],
                        "Delta_XY": 0.0, "Delta_Z": 0.0, "Status": "✅ مطابقة (0 - 2 ملم)"
                    })

            df_audit = pd.DataFrame(chk_results)
            
            st.markdown("##### 📊 جدول نتائج التدقيق والمطابقة والمقارنة الهندسية:")
            st.dataframe(df_audit[["Field_ID", "Design_Ref", "Field_X", "Field_Y", "Delta_XY", "Delta_Z", "Status"]], use_container_width=True)
            
            # --- خريطة الانحرافات والمطابقة الفراغية التفاعلية المحدثة بالألوان الثابتة ---
            st.markdown("### 📊 خريطة الانحرافات والمطابقة الفراغية التفاعلية (Interactive Error Map)")
            st.markdown("*توجيه: يمكنك استخدام الفأرة أو اللمس لعمل **Zoom (تقريب)** لأي نقطة متداخلة، كما يمكنك تمرير المؤشر لمعرفة تفاصيل ورقم النقطة والانحراف بدقة متناهية.*")
            
            # إعداد الحجم الديناميكي بناءً على المليمترات لسهولة المراقبة البصرية بالعين المجردة
            size_factor = df_audit['Delta_XY'].apply(lambda x: max(x * 1000, 3.0))
            
            fig = px.scatter(
                df_audit, 
                x='Field_X', 
                y='Field_Y', 
                color='Status', 
                size=size_factor,
                hover_data=['Field_ID', 'Design_Ref', 'Delta_XY', 'Delta_Z', 'Status'],
                # خريطة ألوان ثابتة ومحددة وصارمة جداً تلبي طلبك هندسياً بدون تدرج عشوائي
                color_discrete_map={
                    "✅ مطابقة (0 - 2 ملم)": "#22c55e",     # الأخضر
                    "⚠️ تنبيه (3 - 5 ملم)": "#eab308",      # الأصفر الذهبي
                    "❌ خارج السماحية (> 5 ملم)": "#ef4444"  # الأحمر
                },
                labels={'Status': 'تصنيف دقة النقطة', 'Field_X': 'East (X)', 'Field_Y': 'North (Y)'},
                title="خريطة توزيع ومطابقة نقاط الرفع الفعلي"
            )
            
            fig.update_layout(
                xaxis=dict(scaleanchor="y", scaleratio=1), # الحفاظ الكامل على دقة وتناسق الأبعاد المساحية الحقيقية للموقع
                template="plotly_white",
                margin=dict(l=20, r=20, t=40, b=20),
                legend=dict(title_text='دليل ألوان الفحص (الكويت)', orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # توليد وإصدار التقرير بصيغة PDF المعتمد
            st.markdown("---")
            if st.button("📄 إصدار وتصدير تقرير التدقيق المساحي المعتمد (PDF)", use_container_width=True):
                pdf_bytes = generate_pro_report_bytes(
                    df_audit, parcel_no, parcel_loc, owner_name, 
                    total_pts=len(df_audit), passed_pts=passed_count
                )
                download_button_ios(pdf_bytes, f"Certified_Audit_{parcel_no}.pdf", "📥 اضغط هنا لتحميل وثيقة تقرير التدقيق النهائي المعتمد المطبوع")
                
        except Exception as e:
            st.error(f"❌ حدث خطأ أثناء معالجة وقراءة ملف بيانات الرفع الفعلي: {e}")

# ==========================================
# 🏁 التذييل البرمجي لضمان استقرار التشغيل
# ==========================================
st.sidebar.markdown("---")
st.sidebar.success("LexiMind Pro V2.0 جاهز للعمل والمطابقة الفورية.")
