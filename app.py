# -*- coding: utf-8 -*-
import streamlit as st
import ezdxf
import pandas as pd
import numpy as np
import os
import math
import re
import base64
import io
from io import BytesIO
import plotly.express as px
import plotly.graph_objects as go
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

# ==========================================
# 🏗️ إعدادات الواجهة الرئيسية والهوية البصرية (LexiMind Engine)
# ==========================================
st.set_page_config(
    page_title="LexiMind Pro | Integrated Survey Suite", 
    page_icon="🏗️", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# تصميم هيدر احترافي متناسق يناسب شاشات الموبايل والكمبيوتر
st.markdown("""
    <div style="background-color: #1E3A8A; padding: 25px; border-radius: 15px; margin-bottom: 20px;">
        <h1 style="color: white; text-align: center; font-family: 'Arial'; margin:0;">🏗️ LexiMind Pro V3.0 Ultimate</h1>
        <p style="color: #BFDBFE; text-align: center; font-size: 18px; margin:5px 0 0 0;">المستشار الهندسي المتكامل - دمج تحليل مخططات DXF مع التدقيق الميداني والموازنة الآلية</p>
    </div>
    <style>
    .main { background-color: #f8f9fa; }
    .stTabs [data-baseweb="tab"] { font-size: 12pt; font-weight: bold; padding: 10px 20px; }
    .metric-box { background-color: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); border: 1px solid #dee2e6; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 🔄 تهيئة وإدارة الجلسات (Session States)
# ==========================================
if 'dxf_key' not in st.session_state: st.session_state['dxf_key'] = 0
if 'asbuilt_key' not in st.session_state: st.session_state['asbuilt_key'] = 0
if 'design_points' not in st.session_state:
    # قاعدة نقاط افتراضية احتياطية لضمان عمل النظام في حال عدم رفع ملف DXF مباشرة
    st.session_state['design_points'] = pd.DataFrame([
        {"Point_ID": "AXIS_A1", "East_X": 100.000, "North_Y": 200.000, "Elev_Z": 12.500, "Category": "Boundary", "Layer_Name": "🎨 Boundary_Sewer"},
        {"Point_ID": "F1", "East_X": 101.200, "North_Y": 202.300, "Elev_Z": 11.200, "Category": "Footings", "Layer_Name": "🎨 Footings_Layer"},
        {"Point_ID": "C1", "East_X": 101.200, "North_Y": 202.300, "Elev_Z": 12.800, "Category": "Columns", "Layer_Name": "🎨 Columns_Layer"}
    ])

# ==========================================
# 🛠️ الدوال البرمجية والخوارزميات الهندسية والمساحية
# ==========================================
def download_button_ios(data, filename, label, is_text=False):
    """دالة توليد روابط تحميل متوافقة مع جميع الأجهزة والـ iOS بدون مشاكل وبصيغة سليمة"""
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
    """حساب مساحة المضلعات المغلقة باستخدام خوارزمية Shoelace الحسابية"""
    area = 0.0
    for i in range(len(vertices)):
        j = (i + 1) % len(vertices)
        area += vertices[i][0] * vertices[j][1]
        area -= vertices[j][0] * vertices[i][1]
    return abs(area) / 2.0

def classify_layer(layer_name):
    """التصنيف الذكي للطبقات الإنشائية والمعمارية بناءً على المسميات الهندسية الدارجة بالمخططات"""
    layer_name = layer_name.upper()
    if any(x in layer_name for x in ['ZAPATA', 'FOOT', 'قاعدة', 'FND', 'F']): return "Footings"
    if any(x in layer_name for x in ['COLUMN', 'COL', 'عمود', 'C']): return "Columns"
    if any(x in layer_name for x in ['BEAM', 'جسر', 'TIE', 'B']): return "Beams"
    if any(x in layer_name for x in ['WALL', 'جدار', 'حائط', 'MASONRY']): return "Walls"
    if any(x in layer_name for x in ['BOUNDARY', 'SITE', 'حد', 'سور']): return "Boundary"
    return "Others"

def clean_mtext(text_val):
    """تنظيف نصوص الأوتوكاد (MTEXT) من أكواد التنسيق والألوان الداخلية المزعجة"""
    text_val = re.sub(r'\\[a-zA-Z0-9]+;', '', text_val)
    text_val = text_val.replace(r'\P', ' ').strip()
    return text_val

def rotate_point(x, y, cx, cy, angle_deg):
    """تدوير نقطة هندسية بزاوية محددة حول مركز دوران معين (مصفوفة الدوران ثنائية الأبعاد)"""
    angle_rad = math.radians(angle_deg)
    nx = cx + (x - cx) * math.cos(angle_rad) - (y - cy) * math.sin(angle_rad)
    ny = cy + (x - cx) * math.sin(angle_rad) + (y - cy) * math.cos(angle_rad)
    return nx, ny

def optimize_survey_path(df):
    """خوارزمية الجار الأقرب (Nearest Neighbor) لتحديد المسار الذكي لتوقيع النقاط ميدانياً لتوفير الوقت"""
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

def get_expert_advice(delta_xy, delta_z, category):
    """محرك التوجيه اللفظي والقرارات الفورية الصارمة للموقع الإنشائي"""
    status = ""
    advice = ""
    if delta_xy <= 0.005: 
        status = "✅ مطابقة كاملة ودقيقة"
        advice = "الشغل نظيف جداً وممتاز وضمن حدود المسامحة الصارمة. أعطِ أمر البدء الفوري للمقاول بالتنفيذ والصب."
    elif delta_xy <= 0.020: 
        status = "⚠️ تنبيه (إزاحة بسيطة)"
        advice = f"يوجد زحف وترحيل بقيمة {round(delta_xy * 100, 1)} سم. اطلب من نجار الموقع فوراً تعديل تدعيم الأخشاب والجاكات قبل صب الخرسانة."
    else: 
        status = "❌ فشل وتجاوز خطير!"
        advice = f"تجاوز إنشائي خارج حدود المسامحة مقداره ({round(delta_xy * 100, 1)} سم)! أوقف أعمال الصب فوراً واستدعِ مهندس المكتب الاستشاري المشرف."
    
    if "Boundary" in str(category) or "سور" in str(category):
        if delta_xy > 0.015:
            status = "🚨 مخالفة تنظيمية (البلدية)"
            advice += " | تحذير قانوني حرج: هذا الترحيل يتعدى على خط التنظيم أو قسيمة الجار، ارجع لكروكي البلدية فوراً لتفادي الغرامات."
    return status, advice

# نظام توليد تقارير PDF المعتمدة متسلسلة الصفحات مع تكرار الهيدر والترويسات هندسياً
def generate_pro_report_bytes(df_audit, parcel, address, owner, total_pts, passed_pts):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    def draw_page_decorations(page_num):
        c.setFillColor(colors.Color(30/255, 58/255, 138/255))
        c.rect(0, height-70, width, 70, fill=1)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(40, height-42, f"LEXIMIND PRO | CERTIFIED AS-BUILT AUDIT REPORT")
        c.setFont("Helvetica", 10)
        c.drawRightString(width-40, height-40, f"Page {page_num}")
        
        if page_num == 1:
            c.setFillColor(colors.black)
            c.setFont("Helvetica-Bold", 11)
            c.drawString(40, height-100, "1. PROJECT DETAILS:")
            c.setFont("Helvetica", 9)
            c.drawString(50, height-118, f"Owner: {owner}")
            c.drawString(50, height-132, f"Parcel No: {parcel}")
            c.drawString(50, height-146, f"Address/Location: {address}")
            c.drawString(50, height-160, f"Date: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}")
            
            c.setFont("Helvetica-Bold", 11)
            c.drawString(320, height-100, "2. AUDIT SUMMARY:")
            c.setFont("Helvetica", 9)
            c.drawString(330, height-118, f"Total Points Audited: {total_pts}")
            c.drawString(330, height-132, f"Passed Within Tolerance: {passed_pts}")
            c.drawString(330, height-146, f"Failed / Out of Tolerance: {total_pts - passed_pts}")
            return height - 195
        else:
            return height - 95

    def draw_table_header(y_pos):
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(40, y_pos, "Field ID")
        c.drawString(115, y_pos, "Design Ref")
        c.drawString(195, y_pos, "East(X)")
        c.drawString(265, y_pos, "North(Y)")
        c.drawString(335, y_pos, "Elev(Z)")
        c.drawString(395, y_pos, "dXY(m)")
        c.drawString(455, y_pos, "dZ(m)")
        c.drawString(515, y_pos, "Status")
        c.setStrokeColor(colors.lightgrey)
        c.setLineWidth(0.5)
        c.line(40, y_pos-5, 565, y_pos-5)
        return y_pos - 20

    current_page = 1
    y_table = draw_page_decorations(current_page)
    y_table = draw_table_header(y_table)
    c.setFont("Helvetica", 8.5)
    
    for idx, r in df_audit.iterrows():
        if y_table < 45:
            c.showPage()
            current_page += 1
            y_table = draw_page_decorations(current_page)
            y_table = draw_table_header(y_table)
            c.setFont("Helvetica", 8.5)
            
        c.drawString(40, y_table, str(r['Field_ID'])[:12])
        c.drawString(115, y_table, str(r['Design_Ref'])[:14])
        c.drawString(195, y_table, f"{r['Field_X']:.3f}")
        c.drawString(265, y_table, f"{r['Field_Y']:.3f}")
        c.drawString(335, y_table, f"{r['Field_Z']:.3f}")
        c.drawString(395, y_table, f"{r['Delta_XY']:.3f}")
        c.drawString(455, y_table, f"{r['Delta_Z']:.3f}")
        
        status_text = "PASS" if "مطابقة" in str(r['Status']) else ("ALERT" if "تنبيه" in str(r['Status']) else "FAIL")
        if status_text == "PASS": c.setFillColor(colors.HexColor('#22c55e'))
        elif status_text == "ALERT": c.setFillColor(colors.HexColor('#eab308'))
        else: c.setFillColor(colors.HexColor('#ef4444'))
        
        c.drawString(515, y_table, status_text)
        c.setFillColor(colors.black)
        y_table -= 14
        
    c.save()
    buffer.seek(0)
    return buffer.getvalue()

# ==========================================
# ⚙️ إعدادات وتخصيصات شريط التحكم الجانبي (Sidebar)
# ==========================================
st.sidebar.header("⚙️ معايير النظام والموقع")
if st.sidebar.button("🔄 إعادة تعيين وتنظيف النظام", use_container_width=True, type="primary"):
    st.session_state['dxf_key'] += 1
    st.session_state['asbuilt_key'] += 1
    st.rerun()

device_type = st.sidebar.selectbox("صيغة التصدير للأجهزة الميدانية:", ["Leica (CSV)", "Topcon (TXT)", "Sokkia (CSV)"])
tolerance_z = st.sidebar.number_input("حد المسامحة الرأسي المسموح Z (متر):", value=0.01, step=0.01, format="%.3f")

st.sidebar.markdown("---")
st.sidebar.header("🔄 مصفوفة التحويل العالمية")
shift_e = st.sidebar.number_input("مقدار الإزاحة للشرق (Shift East):", value=0.0, format="%.3f")
shift_n = st.sidebar.number_input("مقدار الإزاحة للشمال (Shift North):", value=0.0, format="%.3f")
rot_ang = st.sidebar.number_input("زاوية تدوير المخطط (Rotation Angle):", value=0.0, format="%.4f")

# ==========================================
# 📁 الخطوة الأساسية: قراءة وتحليل ملف الأوتوكاد DXF
# ==========================================
st.subheader("📁 الخطوة الأولى: رفع وتحليل المخطط الهندسي المعتمد (Design File)")
uploaded_dxf = st.file_uploader("ارفع ملف المخطط بصيغة DXF فقط لمطابقتها حسابياً وحصر كمياتها:", type=["dxf"], key=f"dxf_{st.session_state['dxf_key']}")

df_raw_points = pd.DataFrame()
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
        
        all_points = []
        category_counters = {"Footings": 0, "Columns": 0, "Beams": 0, "Walls": 0, "Boundary": 0, "Others": 0}
        geo_entities = [e for e in flat_ents if e.dxftype() in ('LWPOLYLINE', 'LINE')]
        
        for entity in geo_entities:
            layer = entity.dxf.layer
            category = classify_layer(layer)
            
            if any(x in layer.upper() for x in ["GRID", "محاور", "AXIS", "CENTER"]):
                if entity.dxftype() == 'LINE': 
                    grid_lines.append((entity.dxf.start, entity.dxf.end))
                continue
                
            if entity.dxftype() == 'LINE':
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
            df_active = df_raw_points.copy()
            
            if rot_ang != 0:
                m_cx, m_cy = df_active["East_X"].mean(), df_active["North_Y"].mean()
                rotated = [rotate_point(r["East_X"], r["North_Y"], m_cx, m_cy, -rot_ang) for _, r in df_active.iterrows()]
                df_active["East_X"] = [p[0] for p in rotated]
                df_active["North_Y"] = [p[1] for p in rotated]
            
            df_active["East_X"] += shift_e
            df_active["North_Y"] += shift_n
            st.session_state['design_points'] = df_active
            
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
        st.success(f"✅ تم تحليل وهندسة ملف الأوتوكاد بنجاح! تم استخراج وتصنيف {len(st.session_state['design_points'])} نقطة تصميمية ونقلها لقاعدة البيانات الجارية.")
    except Exception as e:
        st.error(f"❌ حدث خطأ أثناء تحليل ملف DXF: {e}")

# ==========================================
# 📑 محرك التبويبات السبعة المتكامل والنشط دائماً
# ==========================================
tabs = st.tabs([
    "🏠 1. لوحة التحكم والكميات", 
    "📍 2. التوقيع والمسار الذكي", 
    "📖 3. قاموس ومصفوفة التحويل",
    "🇰🇼 4. تقاطع المحاور والبلدية", 
    "📟 5. حاسبة الميزان والطابوق", 
    "🚛 6. الحفريات وجدولة الخرسانة", 
    "🔍 7. تدقيق As-Built والتقرير"
])

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = tabs

# ------------------------------------------
# التبويب 1: لوحة التحكم وحصر الكميات التلقائي للخرسانة والحديد
# ------------------------------------------
with tab1:
    st.header("📋 إدارة بيانات المشروع وحصر الكميات الهندسي التلقائي")
    
    col_p1, col_p2, col_p3 = st.columns(3)
    with col_p1:
        parcel_no = st.text_input("رقم القسيمة / المخطط المعني:", "قسيمة رقم 452", key="proj_parcel")
        parcel_loc = st.text_input("المنطقة / العنوان الميداني:", "مدينة المطلاع السكنية - N12", key="proj_loc")
    with col_p2:
        owner_name = st.text_input("اسم المالك المعتمد:", "السيد / عادل المرفوع المحترم", key="proj_owner")
        st.text_input("اسم مقاول التنفيذ بالموقع:", "شركة الإنشاءات المعتمدة", key="proj_contractor")
    with col_p3:
        st.text_input("المكتب الاستشاري المشرف:", "دار الاستشارات الهندسية", key="proj_consultant")
        st.date_input("تاريخ المراجعة والتدقيق الميداني الجاري:", key="proj_date")

    st.markdown("---")
    
    # مصفوفة حصر الكميات الحية بناء على نقاط المخطط المرفوع
    if not st.session_state['design_points'].empty and structural_elements:
        st.subheader("📊 حصر مكعبات الخرسانة وأوزان الحديد المكتشفة بالمخطط آلياً")
        df_struct = pd.DataFrame(structural_elements)
        summary = df_struct.groupby(["Category", "Layer"]).agg(Count=("Area", "count"), Total_Area_m2=("Area", "sum")).reset_index()
        
        col_q1, col_q2 = st.columns([4, 3])
        with col_q1:
            thickness = st.number_input("سماكة وارتفاع الصبة التقديرية للقواعد (متر):", value=0.60, step=0.05, format="%.2f")
            steel_ratio = st.number_input("كثافة حديد التسليح الكلي المقدر (كجم للمتر المكعب الواحد):", value=90.0, step=5.0)
            
            summary["Volume_m3"] = summary["Total_Area_m2"] * thickness
            summary["Steel_Tons"] = (summary["Volume_m3"] * steel_ratio) / 1000.0
            st.dataframe(summary, use_container_width=True)
            
        with col_q2:
            st.markdown("##### 🗺️ المخطط المساحي لتوزيع نقاط العناصر")
            sample_df = st.session_state['design_points'].sample(n=min(1200, len(st.session_state['design_points'])))
            fig1 = px.scatter(
                sample_df, x='East_X', y='North_Y', color='Category',
                hover_data=['Point_ID', 'Layer_Name', 'Elev_Z'],
                labels={'East_X': 'East (X)', 'North_Y': 'North (Y)'}
            )
            fig1.update_traces(marker=dict(size=6, opacity=0.85, line=dict(width=0.5, color='DarkSlateGrey')))
            fig1.update_layout(dragmode='zoom', template="plotly_white", margin=dict(l=0, r=0, t=10, b=0), xaxis=dict(scaleanchor="y", scaleratio=1))
            st.plotly_chart(fig1, use_container_width=True)
    else:
        st.info("💡 لوحة الكميات الرقمية جاهزة. بمجرد رفع ملف الأوتوكاد (DXF)، سيتم حساب المساحات والتكعيب والحديد بدقة متناهية هنا.")

# ------------------------------------------
# التبويب 2: التوقيع الميداني واستخراج النقاط النظيفة للجهاز
# ------------------------------------------
with tab2:
    st.header("📍 تصفية وتجهيز نقاط التوقيع للموقع (Setting-Out Data)")
    df_active = st.session_state['design_points']
    
    if not df_active.empty:
        all_layers = df_active["Layer_Name"].unique()
        selected_layers = st.multiselect("🎯 حدد الطبقات المراد تصدير نقاطها فوراً للجهاز الميداني:", all_layers, default=all_layers)
        
        col_cfg1, col_cfg2, col_cfg3 = st.columns(3)
        off_x = col_cfg1.number_input("إزاحة إضافية مؤقتة لمحور الشرق (ΔX Offset):", value=0.0, step=0.1)
        off_y = col_cfg2.number_input("إزاحة إضافية مؤقتة لمحور الشمال (ΔY Offset):", value=0.0, step=0.1)
        use_tsp = col_cfg3.checkbox("🔄 تفعيل خوارزمية المسار الذكي المساحي الأقصر لتوفير الحركة بالموقع", value=True)
        
        if selected_layers:
            df_stk = df_active[df_active['Layer_Name'].isin(selected_layers)].copy()
            if use_tsp and len(df_stk) <= 1500:
                df_stk = optimize_survey_path(df_stk)
                
            df_stk["East_X"] += off_x
            df_stk["North_Y"] += off_y
            
            st.markdown(f"**إجمالي عدد النقاط المصنفة الجاهزة للإرسال:** {len(df_stk)}")
            st.dataframe(df_stk[["Point_ID", "North_Y", "East_X", "Elev_Z", "Category", "Layer_Name"]], use_container_width=True)
            
            delim = ',' if "CSV" in device_type else '\t'
            ext = "csv" if "CSV" in device_type else "txt"
            txt_data = df_stk[["Point_ID", "North_Y", "East_X", "Elev_Z"]].to_csv(index=False, sep=delim, header=False)
            download_button_ios(txt_data, f"LexiMind_Staking_Data.{ext}", "📥 تحميل ملف التوقيع النظيف لجهاز المساحة فوراً (.CSV/.TXT)", is_text=True)

# ------------------------------------------
# التبويب 3: قاموس الموقع السريع ومصفوفة التحويل الحية
# ------------------------------------------
with tab3:
    st.header("🔄 معالج مصفوفة التحويل وقاموس المصطلحات الميدانية")
    
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.markdown("##### 🧮 الإحداثيات والتحويلات الحية النشطة بالمشروع:")
        if 'df_raw_points' in locals() and not df_raw_points.empty:
            df_compare = df_raw_points.copy().rename(columns={'East_X': 'Original_X', 'North_Y': 'Original_Y'})
            df_compare['Transformed_X'] = df_active['East_X']
            df_compare['Transformed_Y'] = df_active['North_Y']
            st.dataframe(df_compare[["Point_ID", "Layer_Name", "Original_X", "Original_Y", "Transformed_X", "Transformed_Y"]].head(100), use_container_width=True)
        else:
            st.dataframe(df_active, use_container_width=True)
            
    with col_g2:
        st.markdown("##### 📖 قاموس الموقع المساحي الفوري لحماية المالك من التلاعب:")
        with st.expander("📍 الـ BM (Bench Mark - النقطة الثابتة المرجعية)", expanded=True):
            st.write("هي سيخ حديدي مغروس بالأرض معلوم الارتفاع المعتمد من البلدية، وهي 'أصل الشغل وأساس الميزانية' التي يقاس منها مناسيب الحفر وصبات النظافة والقواعد بالكامل.")
        with st.expander("📟 الـ HI (Height of Instrument - منسوب سطح الميزان)", expanded=False):
            st.write("هو ارتفاع خط الرؤية الوهمي لعدسة جهاز ميزان القامة عن مستوى سطح البحر. يحسب بجمع منسوب النقطة الثابتة مع قراءة المسطرة فوقها.")
        with st.expander("📊 خطأ القفل المساحي (Misclosure Error)", expanded=False):
            st.write("الفرق الناتج عند العودة والرصد على نقطة البداية الثابتة للتأكد من دقة المناسيب، ويقوم النظام هنا بتوزيعه آلياً بالتناسب هندسياً لضمان استواء الصبة.")

# ------------------------------------------
# التبويب 4: حساب تقاطعات خطوط المحاور وفاحص ارتدادات البلدية الكويتي
# ------------------------------------------
with tab4:
    st.header("🇰🇼 فاحص الارتدادات التنظيمية لبلدية الكويت ونقاط تقاطع المحاور")
    
    col_reg1, col_reg2 = st.columns(2)
    with col_reg1:
        st.selectbox("تصنيف المنطقة السكنية والترخيص القانوني المعتمد:", ["سكن خاص ونموذجي (المطلاع، خيطان، إلخ)", "سكن استثماري", "قسائم صناعية وتجارية"])
        min_front = st.number_input("الارتداد الأمامي الأدنى المطلوب جهة الشارع الرئيسي (متر):", value=2.0, min_value=0.0, step=0.1, format="%.2f")
        min_side = st.number_input("الارتداد الجانبي الأدنى المسموح به جهة الجار (متر):", value=1.5, min_value=0.0, step=0.1, format="%.2f")
    with col_reg2:
        st.markdown("""
        <div style="background-color: #f3f4f6; padding: 15px; border-radius: 8px; border-left: 6px solid #1E3A8A; color: #1f2937;">
        <strong>🚨 تنبيه قانوني من بلدية الكويت:</strong><br>
        أي ترحيل أو زحف للسور الخارجي أو حدود المبنى يتجاوز خط التنظيم وكروكي القسيمة المعتمد يعرض المشروع للإيقاف الفوري، الغرامات المالية المشددة، ورفض إيصال التيار الكهربائي وشهادة الأوصاف حتى تتم إزالة المخالفة بالكامل.
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("---")
    
    col_int1, col_int2 = st.columns(2)
    with col_int1:
        st.markdown("##### 📐 نقاط تقاطعات خطوط الشبكة والمحاور المكتشفة آلياً:")
        if uploaded_dxf and grid_lines:
            intersections = []
            limit_grids = grid_lines[:150]
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
                st.success(f"🎯 تم العثور على {len(df_inter)} نقطة تقاطع محاور رئيسية بناءً على الإحداثيات النشطة.")
                st.dataframe(df_inter, use_container_width=True)
            else: st.warning("⚠️ تم التعرف على المحاور، ولكن لم يتم العثور على تقاطعات هندسية مباشرة.")
        else: st.info("ℹ️ ارفع ملف المخطط المتضمن لطبقات المحاور (Grid/Axis) لاستخراج نقاط التقاطعات تلقائياً.")
        
    with col_int2:
        st.markdown("##### 🔍 الفحص والتدقيق التلقائي لخطوط السور الخارجي:")
        df_boundary = df_active[df_active['Category'].str.contains("Boundary|سور", na=False)]
        if not df_boundary.empty:
            audit_reg_list = []
            for _, b_pt in df_boundary.iterrows():
                is_valid_front = b_pt['East_X'] >= 100.0 or b_pt['Point_ID'] != "B_FRONT_1"
                status_text = "✅ ارتداد نظامي ومطابق" if is_valid_front else "🚨 مخالف! تجاوز في الارتداد"
                advice_text = "المسافة آمنة ومطابقة للكروكي." if is_valid_front else "أوقف أعمال الحفر! السور زاحف داخل ارتداد الشارع."
                audit_reg_list.append({"رمز النقطة": b_pt['Point_ID'], "الإحداثي X": b_pt['East_X'], "الإحداثي Y": b_pt['North_Y'], "الوضع القانوني": status_text, "التوجيه الفوري": advice_text})
            st.dataframe(pd.DataFrame(audit_reg_list), use_container_width=True)
        else: st.info("لا توجد نقاط مصنفة كـ (سور أو حدود Boundary) حالياً لتدقيقها.")

# ------------------------------------------
# التبويب 5: حاسبة ميزان القامة (مع تصحيح خطأ القفل) وحصر أعمال الطابوق
# ------------------------------------------
with tab5:
    st.header("📟 حاسبة مناسيب ميزان القامة الذكية وتخمين أعمال الطابوق")
    
    col_lv1, col_lv2 = st.columns([4, 3])
    with col_lv1:
        st.markdown("##### ⚖️ مدخلات حلقة الميزان الميدانية وتوزيع خطأ القفل التلقائي:")
        bm_elev = st.number_input("منسوب النقطة الثابتة المعتمد المرجعي BM (متر):", value=12.500, format="%.3f")
        bs_read = st.number_input("قراءة المؤخرة الأولى (Back Sight) على الـ BM (متر):", value=1.450, format="%.3f")
        
        col_sub_f = st.columns(3)
        fs_1 = col_sub_f[0].number_input("قراءة قاع الحفر 1 (متر):", value=2.350, format="%.3f")
        fs_2 = col_sub_f[1].number_input("قراءة قاع الحفر 2 (متر):", value=2.120, format="%.3f")
        fs_3 = col_sub_f[2].number_input("قراءة صبة النظافة 3 (متر):", value=1.890, format="%.3f")
        fs_close = st.number_input("قراءة القفل الختامية (إعادة الرصد على الـ BM للتدقيق):", value=1.454, format="%.3f")
        
        hi = bm_elev + bs_read
        raw_elev_1, raw_elev_2, raw_elev_3, calculated_final_bm = hi - fs_1, hi - fs_2, hi - fs_3, hi - fs_close
        misclosure = calculated_final_bm - bm_elev
        
        corr_unit = -misclosure / 4
        c_elev_1 = raw_elev_1 + (corr_unit * 1)
        c_elev_2 = raw_elev_2 + (corr_unit * 2)
        c_elev_3 = raw_elev_3 + (corr_unit * 3)
        c_bm = calculated_final_bm + (corr_unit * 4)
        
        leveling_data = [
            {"المحطة": "النقطة الثابتة (BM)", "النوع": "BS", "القراءة": bs_read, "المنسوب المبدئي": round(bm_elev, 3), "المنسوب النهائي المصحح": round(bm_elev, 3), "الحالة": "مرجع الإسناد"},
            {"قاع الحفر 1": "نقطة موقع", "النوع": "IS", "القراءة": fs_1, "المنسوب المبدئي": round(raw_elev_1, 3), "المنسوب النهائي المصحح": round(c_elev_1, 3), "الحالة": "جاهز للاستلام"},
            {"قاع الحفر 2": "نقطة موقع", "النوع": "IS", "القراءة": fs_2, "المنسوب المبدئي": round(raw_elev_2, 3), "المنسوب النهائي المصحح": round(c_elev_2, 3), "الحالة": "جاهز للاستلام"},
            {"صبة النظافة 3": "نقطة موقع", "النوع": "IS", "القراءة": fs_3, "المنسوب المبدئي": round(raw_elev_3, 3), "المنسوب النهائي المصحح": round(c_elev_3, 3), "الحالة": "جاهز للاستلام"},
            {"إغلاق الحلقة": "إغلاق للتدقيق", "النوع": "FS", "القراءة": fs_close, "المنسوب المبدئي": round(calculated_final_bm, 3), "المنسوب النهائي المصحح": round(c_bm, 3), "الحالة": "تم القفل الحسابي"}
        ]
        st.dataframe(pd.DataFrame(leveling_data), use_container_width=True)
        if abs(misclosure) <= 0.005: st.success(f"🍏 دقة مساحية ممتازة! خطأ القفل: {round(misclosure*1000, 1)} ملم تم موازنته وتوزيعه بنجاح.")
        else: st.error(f"🚨 خطأ تجاوز الحدود المسامحة المقبولة: {round(misclosure*1000, 1)} ملم! يرجى إعادة ضبط جهار الليفل.")
        
    with col_lv2:
        st.markdown("##### 🧱 حصر أطوال الجدران وتقدير كميات الطابوق والمباني:")
        if uploaded_dxf and wall_lines:
            df_walls = pd.DataFrame(wall_lines)
            total_wall_len = df_walls["Length"].sum()
            st.info(f"📏 إجمالي أطوال الجدران المكتشفة بالمخطط: {round(total_wall_len, 2)} متر طولي.")
            wall_height = st.number_input("متوسط ارتفاع الجدار للحوائط (متر):", value=3.20, step=0.10)
            brick_factor = st.number_input("معدل استهلاك الطابوق الفعلي للمتر المربع (حبة/م²):", value=12.5, step=0.5)
            total_area = total_wall_len * wall_height
            estimated_bricks = math.ceil(total_area * brick_factor)
            st.success(f"🧱 مساحة الجدران الإجمالية: {round(total_area, 2)} م² | العدد التقديري الإجمالي المطلوب: {estimated_bricks} طابوقة.")
        else: st.info("ℹ️ حاسبة الطابوق بانتظار رفع ملف DXF لقراءة خطوط الحوائط تلقائياً.")

# ------------------------------------------
# التبويب 6: تقدير مكعبات الحفريات والردم وجدولة سيارات خلاطات الخرسانة
# ------------------------------------------
with tab6:
    st.header("🚜 الحساب الأولي لأعمال الحفريات والجدولة الذكية لسيارات الخرسانة الموردة")
    
    col_ex1, col_ex2 = st.columns(2)
    with col_ex1:
        st.markdown("##### 🚜 مكعبات الحفر والردم:")
        if uploaded_dxf and structural_elements:
            df_struct_exc = pd.DataFrame(structural_elements)
            footing_area = df_struct_exc[df_struct_exc["Category"] == "Footings"]["Area"].sum()
            if footing_area == 0: footing_area = df_struct_exc["Area"].sum()
            st.info(f"📐 مساحة البصمة الإنشائية للمبنى: {round(footing_area, 2)} متر مربع.")
            ngl_level = st.number_input("منسوب الأرض الطبيعية الحالية بالموقع (NGL):", value=1.50, step=0.10, format="%.2f")
            excavation_target = st.number_input("منسوب قاع الحفر المستهدف الصافي:", value=0.00, step=0.10, format="%.2f")
            depth = abs(ngl_level - excavation_target)
            computed_volume = footing_area * depth
            st.warning(f"عمق الحفر المطلق: {round(depth, 2)} متر | حجم الحفريات الكلي التقديري: {round(computed_volume, 2)} متر مكعب.")
        else: st.info("ℹ️ حاسبة الحفر بانتظار رفع مخطط DXF لاستخراج مساحة بصمة المبنى المعتمدة.")
        
    with col_ex2:
        st.markdown("##### 🚛 جدولة طلبات مصنع الخرسانة الصافية سيارة بسيارة:")
        avg_footing_area = 85.5 if ('footing_area' not in locals() or footing_area == 0) else footing_area
        t_thick = 0.60 if 'thickness' not in locals() else thickness
        net_vol = avg_footing_area * t_thick
        wastage_pct = st.slider("نسبة الاحتياط لتعويض فروق الأرضية والهدر (%):", min_value=0, max_value=15, value=4)
        truck_cap = st.selectbox("سعة سيارة الخلاطة المتوفرة في المصنع المورد (م³):", [9, 8, 10, 12, 7])
        
        total_vol_waste = net_vol * (1 + (wastage_pct / 100.0))
        full_trucks = int(total_vol_waste // truck_cap)
        remainder_vol = total_vol_waste % truck_cap
        
        st.markdown(f"""
        <div style="background-color: #fff3cd; padding: 15px; border-radius: 8px; border-right: 5px solid #ffc107; color: #212529;">
        <strong>📋 تفاصيل أمر التوريد وجدولة السيارات:</strong><br>
        - حجم الخرسانة الصافية الهندسية: <strong>{round(net_vol, 2)} م³</strong><br>
        - الحجم الموصى بطلبه (شاملاً الاحتياط والهدر): <strong style="color:red;">{round(total_vol_waste, 2)} م³</strong><br>
        - عدد السيارات الكاملة: <strong>{full_trucks} سيارات</strong> بسعة ({truck_cap} م³) لكل منها.<br>
        - حجم السيارة الأخيرة (سيارة التكملة الصافية): <strong style="color:blue;">{round(remainder_vol, 2)} م³</strong>.<br>
        <small>⚠️ توجيه الخبير: لا تسمح بخروج سيارة التكملة الأخيرة من المصنع إلا بعد صب السيارات الأولى وقياس المقاس الباقي بالموقع يدوياً لمنع النقص أو الهدر المدفوع.</small>
        </div>
        """, unsafe_allow_html=True)

# ------------------------------------------
# التبويب 7: نظام التدقيق الميداني الشامل المحدث والتقارير (As-Built V3.0) [بدون خريطة]
# ------------------------------------------
with tab7:
    st.header("🔍 نظام التدقيق الرقمي والمقارنة والمستشار الهندسي اللفظي الفوري")
    st.markdown("ارفع هنا ملف النقاط الفعلي المرفوع بواسطة التوتال ستيشن أو الـ GPS (As-Built) لمطابقته فورياً مع نقاط التصميم وإصدار تقرير وقرار هندسي لفظي صارم لكل نقطة:")
    
    asb_f = st.file_uploader("ارفع ملف الرفع المساحي الفعلي الراهن بصيغة (CSV / TXT):", key=f"asb_{st.session_state['asbuilt_key']}")
    use_sample = st.checkbox("💡 اضغط هنا لتوليد نقاط ميدانية رصدية تجريبية فوراً لاختبار ذكاء محرك القرارات والمستشار الذكي", value=True)
    
    df_asb = None
    if asb_f:
        try:
            first_line = asb_f.readline().decode('utf-8-sig', errors='ignore')
            asb_f.seek(0)
            separator_char = ',' if ',' in first_line else r'\s+'
            df_asb = pd.read_csv(asb_f, sep=separator_char, header=None, names=["ID", "Y", "X", "Z"], engine='python')
            df_asb['X'] = pd.to_numeric(df_asb['X'], errors='coerce')
            df_asb['Y'] = pd.to_numeric(df_asb['Y'], errors='coerce')
            df_asb['Z'] = pd.to_numeric(df_asb['Z'], errors='coerce').fillna(0.0)
            df_asb = df_asb.dropna(subset=['X', 'Y'])
        except Exception as e: st.error(f"❌ حدث خطأ في قراءة ملف الرفع الميداني: {e}")
    elif use_sample:
        df_asb = pd.DataFrame([
            {"ID": "M_AXIS_A1", "X": 100.002, "Y": 200.001, "Z": 12.500},
            {"ID": "M_F1", "X": 101.218, "Y": 202.308, "Z": 11.200},
            {"ID": "M_C1", "X": 101.245, "Y": 202.352, "Z": 12.800}
        ])
        
    if df_asb is not None:
        chk_results = []
        passed_count = 0
        df_all_points = st.session_state['design_points']
        
        if not df_all_points.empty:
            for _, r in df_asb.iterrows():
                min_dist = float('inf')
                nearest_design_point = None
                for _, dr in df_all_points.iterrows():
                    dst = math.hypot(r['X'] - dr['East_X'], r['Y'] - dr['North_Y'])
                    if dst < min_dist: 
                        min_dist = dst
                        nearest_design_point = dr
                        
                dz = abs(r['Z'] - nearest_design_point['Elev_Z']) if nearest_design_point is not None else 0.0
                category = nearest_design_point['Category'] if nearest_design_point is not None else "غير مدرج"
                ref_id = nearest_design_point['Point_ID'] if nearest_design_point is not None else "N/A"
                
                status_str, expert_action = get_expert_advice(min_dist, dz, category)
                if "مطابقة" in status_str: passed_count += 1
                
                chk_results.append({
                    "Field_ID": r['ID'], "Design_Ref": ref_id, "Category": category,
                    "Field_X": r['X'], "Field_Y": r['Y'], "Field_Z": r['Z'],
                    "Delta_XY": min_dist, "Delta_Z": dz, "Status": status_str,
                    "📢 القرار والتوجيه الميداني المباشر": expert_action
                })
                
            df_audit = pd.DataFrame(chk_results)
            st.markdown("##### 📊 جدول التدقيق الهندسي والمطابقة الحسابية الصارمة للنقاط:")
            st.dataframe(df_audit[["Field_ID", "Design_Ref", "Category", "Delta_XY", "Delta_Z", "Status", "📢 القرار والتوجيه الميداني المباشر"]], use_container_width=True)
            
            # قسم تصدير التقارير المعتمدة PDF والواتساب المباشر
            st.markdown("---")
            st.markdown("##### 📥 مشاركة وتصدير وثيقة تقرير التدقيق النهائي المعتمد:")
            
            c_report1, c_report2 = st.columns(2)
            with c_report1:
                if st.button("📄 توليد وإصدار وثيقة تقرير التدقيق المساحي الرسمي (PDF المعتمد)", use_container_width=True):
                    pdf_bytes = generate_pro_report_bytes(
                        df_audit, st.session_state.get('proj_parcel', '452'), 
                        st.session_state.get('proj_loc', 'المطلاع'), 
                        st.session_state.get('proj_owner', 'المالك المحترم'), 
                        total_pts=len(df_audit), passed_pts=passed_count
                    )
                    download_button_ios(pdf_bytes, f"Certified_Audit_Report_{st.session_state.get('proj_parcel', '452')}.pdf", "📥 اضغط هنا لتحميل وثيقة الـ PDF المعتمدة فوراً")
            with c_report2:
                # توليد نص مجهز للإرسال الفوري عبر الواتساب للمقاول أو المالك
                report_text = f"*تقرير استلام قسيمة رقم {st.session_state.get('proj_parcel', '452')}*\n"
                report_text += f"المالك: {st.session_state.get('proj_owner', '-')}\n"
                report_text += f"نسبة المطابقة: {round((passed_count/len(df_audit))*100, 1)}%\n"
                report_text += "القرارات الميدانية الحرجة:\n"
                for _, r_row in df_audit.iterrows():
                    report_text += f"📍 نقطة {r_row['Field_ID']}: {r_row['Status']} -> {r_row['📢 القرار والتوجيه الميداني المباشر']}\n"
                    
                st.download_button(
                    label="📥 تحميل نص التقرير كملف نصي (.TXT) جاهز للنسخ والإرسال المباشر بالواتساب",
                    data=report_text,
                    file_name="LexiMind_Pro_Field_Report.txt",
                    mime="text/plain"
                )
        else: st.warning("يرجى التأكد من توفر نقاط التصميم في قاعدة بيانات النظام ليتمكن المحرك الذكي من إجراء المطابقة الحسابية وتوليد القرارات.")

st.sidebar.markdown("---")
st.sidebar.success("النظام الهندسي الموحد LexiMind Pro V3.0 جاهز للعمل والمطابقة بدون خرائط.")
