import streamlit as st
import ezdxf
import pandas as pd
import os
import math

st.set_page_config(page_title="المساح الذكي | Smart Surveyor", layout="wide")
st.title("🏗️ نظام إدارة المساحة والكميات الاحترافي")
st.markdown("---")

# ==========================================
# الدوال الأساسية (Functions)
# ==========================================
def calculate_area(vertices):
    """حساب مساحة المضلع يدوياً لتفادي أخطاء المكتبات"""
    area = 0.0
    for i in range(len(vertices)):
        j = (i + 1) % len(vertices)
        area += vertices[i][0] * vertices[j][1]
        area -= vertices[j][0] * vertices[i][1]
    return abs(area) / 2.0

def classify_layer(layer_name):
    """المترجم الذكي لتصنيف الطبقات هندسياً"""
    layer_name = layer_name.upper()
    if any(x in layer_name for x in ['ZAPATA', 'FOOT', 'قاعدة', 'FND']): return "قواعد (Footings)"
    if any(x in layer_name for x in ['COLUMN', 'COL', 'عمود']): return "أعمدة (Columns)"
    if any(x in layer_name for x in ['BEAM', 'جسر', 'TIE']): return "جسور (Beams)"
    if any(x in layer_name for x in ['BOUNDARY', 'SITE', 'حد']): return "حدود الأرض (Boundary)"
    return "أخرى (Others)"

def read_dxf(uploaded_file):
    """قراءة ملف DXF بنظام الحفظ المؤقت لضمان الاستقرار"""
    temp_file_path = f"temp_{uploaded_file.name}"
    with open(temp_file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    doc = ezdxf.readfile(temp_file_path)
    return doc, temp_file_path

def calc_distance(x1, y1, x2, y2):
    """حساب المسافة بين نقطتين (للمطابقة)"""
    return math.hypot(x2 - x1, y2 - y1)

# ==========================================
# الإعدادات الجانبية (Sidebar)
# ==========================================
st.sidebar.header("⚙️ إعدادات النظام")
device_type = st.sidebar.selectbox("اختر نوع جهازك (للتصدير):", ["Leica (CSV)", "Topcon (TXT)", "Generic (CSV)"])
tolerance = st.sidebar.number_input("السماحية المقبولة للتنفيذ (بالمتر):", value=0.02, step=0.01, help="مثلاً: 0.02 تعني 2 سم")

# ==========================================
# معالجة المخطط الأساسي (DXF)
# ==========================================
st.subheader("📁 رفع المخطط الأساسي (DXF)")
uploaded_dxf = st.file_uploader("ارفع المخطط المعتمد هنا للبدء:", type=["dxf"])

if uploaded_dxf:
    try:
        # قراءة المخطط واستخراج البيانات
        doc, path = read_dxf(uploaded_dxf)
        msp = doc.modelspace()
        
        all_points = []
        data_list = []
        
        for entity in msp.query('LWPOLYLINE'):
            layer = entity.dxf.layer
            category = classify_layer(layer)
            vertices = [(v[0], v[1]) for v in entity.get_points()]
            area = calculate_area(vertices)
            
            if area > 0:
                data_list.append({"التصنيف": category, "اسم الطبقة": layer, "المساحة (م٢)": area})
            
            for i, v in enumerate(vertices):
                all_points.append({
                    "Point_ID": f"{layer}_{i}", 
                    "North_Y": v[1], 
                    "East_X": v[0], 
                    "Category": category
                })
                
        df_all_points = pd.DataFrame(all_points)
        os.remove(path) # تنظيف الملف المؤقت
        
        # إنشاء نظام التبويبات (Tabs) لترتيب واجهة العمل
        tab1, tab2 = st.tabs(["📍 1. التجهيز والتوقيع (Stake Out)", "✅ 2. المطابقة والاستلام (As-Built Check)"])
        
        # ---------------------------------------------------------
        # التبويب الأول: التوقيع وحصر الكميات
        # ---------------------------------------------------------
        with tab1:
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📊 جدول الكميات")
                if data_list:
                    df_quantities = pd.DataFrame(data_list)
                    summary = df_quantities.groupby(["التصنيف", "اسم الطبقة"]).agg(
                        العدد=("المساحة (م٢)", "count"),
                        إجمالي_المساحة=("المساحة (م٢)", "sum")
                    ).reset_index()
                    st.dataframe(summary, use_container_width=True)
                else:
                    st.warning("لم يتم العثور على مساحات مغلقة في المخطط.")
            
            with col2:
                st.subheader("📍 الفلترة وتصدير نقاط التوقيع")
                categories_available = df_all_points["Category"].unique()
                selected_cat = st.multiselect("اختر العناصر التي تريد توقيعها الآن:", categories_available, default=categories_available)
                
                if selected_cat:
                    # تصفية وترتيب النقاط (Smart Pathing)
                    filtered_points = df_all_points[df_all_points['Category'].isin(selected_cat)].copy()
                    filtered_points = filtered_points.sort_values(by=["North_Y", "East_X"]) 
                    
                    export_points = filtered_points[["Point_ID", "North_Y", "East_X"]]
                    export_points["Elevation_Z"] = 0.0 # إضافة منسوب صفري افتراضي
                    
                    sep = ',' if device_type != "Topcon (TXT)" else ' '
                    csv_data = export_points.to_csv(index=False, sep=sep, header=False)
                    
                    st.success(f"تم تجهيز {len(export_points)} نقطة للتوقيع الميداني.")
                    st.download_button(f"📥 تحميل ملف {device_type.split()[0]}", csv_data, "Staking_Points.txt", "text/plain")

        # ---------------------------------------------------------
        # التبويب الثاني: المطابقة الرقمية والاستلام
        # ---------------------------------------------------------
        with tab2:
            st.subheader("🔍 مطابقة الواقع مع المخطط (As-Built)")
            st.info("ارفع ملف النقاط الذي قمت برصده من الموقع (CSV / TXT) لمقارنته بالمخطط الأصلي واكتشاف أي انحرافات.")
            
            asbuilt_file = st.file_uploader("ارفع ملف الرفع الميداني (بدون أسماء أعمدة - ID, Y, X, Z):", type=["csv", "txt"])
            
            if asbuilt_file:
                # قراءة ملف التوتال ستيشن
                sep_asb = ',' if asbuilt_file.name.endswith('.csv') else ' '
                df_asb = pd.read_csv(asbuilt_file, sep=sep_asb, header=None, names=["ID", "Y", "X", "Z"])
                
                results = []
                for index, row in df_asb.iterrows():
                    asb_y, asb_x = row['Y'], row['X']
                    
                    # البحث عن أقرب نقطة في المخطط (المقارنة)
                    min_dist = float('inf')
                    nearest_point = None
                    
                    for _, design_row in df_all_points.iterrows():
                        dist = calc_distance(asb_x, asb_y, design_row['East_X'], design_row['North_Y'])
                        if dist < min_dist:
                            min_dist = dist
                            nearest_point = design_row
                    
                    # تقييم النقطة بناءً على السماحية
                    status = "✅ مطابق" if min_dist <= tolerance else "❌ يوجد انحراف"
                    
                    results.append({
                        "نقطة الرفع الميداني": row['ID'],
                        "النقطة الأصلية (المخطط)": nearest_point['Point_ID'],
                        "نسبة الخطأ (متر)": round(min_dist, 3),
                        "الحالة": status
                    })
                
                df_results = pd.DataFrame(results)
                
                st.subheader("📋 تقرير التدقيق النهائي")
                # تلوين الجدول لتوضيح الأخطاء بصرياً
                def highlight_errors(val):
                    color = '#ffcccc' if val == '❌ يوجد انحراف' else '#ccffcc'
                    return f'background-color: {color}'
                
                st.dataframe(df_results.style.map(highlight_errors, subset=['الحالة']), use_container_width=True)
                
    except Exception as e:
        st.error(f"حدث خطأ أثناء معالجة الملفات: {e}")
