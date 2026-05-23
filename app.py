import streamlit as st
import ezdxf
import pandas as pd
import os
import math
import matplotlib.pyplot as plt

st.set_page_config(page_title="المساح الذكي | Smart Surveyor", layout="wide")
st.title("🏗️ نظام إدارة المساحة والكميات الاحترافي - النسخة الشاملة")
st.markdown("---")

# ==========================================
# الدوال الأساسية (Functions)
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
    if any(x in layer_name for x in ['ZAPATA', 'FOOT', 'قاعدة', 'FND']): return "قواعد (Footings)"
    if any(x in layer_name for x in ['COLUMN', 'COL', 'عمود']): return "أعمدة (Columns)"
    if any(x in layer_name for x in ['BEAM', 'جسر', 'TIE']): return "جسور (Beams)"
    if any(x in layer_name for x in ['BOUNDARY', 'SITE', 'حد']): return "حدود الأرض (Boundary)"
    return "أخرى (Others)"

def read_dxf(uploaded_file):
    temp_file_path = f"temp_{uploaded_file.name}"
    with open(temp_file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    doc = ezdxf.readfile(temp_file_path)
    return doc, temp_file_path

def calc_distance(x1, y1, x2, y2):
    return math.hypot(x2 - x1, y2 - y1)

# ==========================================
# الإعدادات الجانبية
# ==========================================
st.sidebar.header("⚙️ إعدادات النظام")
device_type = st.sidebar.selectbox("نوع الجهاز للتصدير:", ["Leica (CSV)", "Topcon (TXT)", "Generic (CSV)"])
tolerance = st.sidebar.number_input("السماحية المقبولة للتنفيذ (بالمتر):", value=0.02, step=0.01)

# ==========================================
# معالجة المخطط الأساسي
# ==========================================
st.subheader("📁 رفع المخطط الأساسي (DXF)")
uploaded_dxf = st.file_uploader("ارفع المخطط المعتمد هنا:", type=["dxf"])

if uploaded_dxf:
    try:
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
        os.remove(path)
        
        # ---------------------------------------------------------
        # نظام التبويبات الشامل
        # ---------------------------------------------------------
        tab1, tab2, tab3, tab4 = st.tabs([
            "🗺️ 1. الخريطة والكميات", 
            "📍 2. التوقيع والأوفسيت", 
            "🚜 3. حساب الحفر والردم",
            "✅ 4. المطابقة والتقارير (As-Built)"
        ])
        
        # --- التبويب الأول: الخريطة التفاعلية والكميات ---
        with tab1:
            col1, col2 = st.columns([1, 1])
            with col1:
                st.subheader("📊 جدول الكميات")
                if data_list:
                    df_quantities = pd.DataFrame(data_list)
                    summary = df_quantities.groupby(["التصنيف", "اسم الطبقة"]).agg(
                        العدد=("المساحة (م٢)", "count"),
                        إجمالي_المساحة=("المساحة (م٢)", "sum")
                    ).reset_index()
                    st.dataframe(summary, use_container_width=True)
            
            with col2:
                st.subheader("🗺️ المعاينة البصرية للمخطط")
                if not df_all_points.empty:
                    fig, ax = plt.subplots(figsize=(6, 4))
                    categories = df_all_points['Category'].unique()
                    colors = plt.cm.get_cmap('tab10', len(categories))
                    
                    for i, cat in enumerate(categories):
                        cat_data = df_all_points[df_all_points['Category'] == cat]
                        # استخراج المسمى الإنجليزي لتفادي مشكلة الخط العربي المقلوب بالسحابة
                        eng_label = cat.split('(')[-1].replace(')', '') if '(' in cat else cat
                        ax.scatter(cat_data['East_X'], cat_data['North_Y'], label=eng_label, color=colors(i), s=10)
                    
                    ax.set_aspect('equal')
                    ax.set_xlabel('East (X)')
                    ax.set_ylabel('North (Y)')
                    ax.legend(loc='upper right', fontsize='small')
                    ax.grid(True, linestyle='--', alpha=0.5)
                    st.pyplot(fig)

        # --- التبويب الثاني: التوقيع ونقاط الأوفسيت ---
        with tab2:
            st.subheader("📍 تجهيز نقاط التوقيع وإنشاء الأوفسيت")
            categories_available = df_all_points["Category"].unique()
            selected_cat = st.multiselect("اختر العناصر للتوقيع:", categories_available, default=categories_available)
            
            st.markdown("**إنشاء نقاط مساعدة (Offset) لتجاوز العوائق:**")
            col_off1, col_off2 = st.columns(2)
            offset_x = col_off1.number_input("إزاحة باتجاه الشرق (X) بالمتر:", value=0.0, step=0.5)
            offset_y = col_off2.number_input("إزاحة باتجاه الشمال (Y) بالمتر:", value=0.0, step=0.5)
            
            if selected_cat:
                filtered_points = df_all_points[df_all_points['Category'].isin(selected_cat)].copy()
                filtered_points = filtered_points.sort_values(by=["North_Y", "East_X"])
                
                # تطبيق الأوفسيت
                filtered_points["East_X"] = filtered_points["East_X"] + offset_x
                filtered_points["North_Y"] = filtered_points["North_Y"] + offset_y
                
                export_points = filtered_points[["Point_ID", "North_Y", "East_X"]]
                export_points["Elevation_Z"] = 0.0
                
                sep = ',' if device_type != "Topcon (TXT)" else ' '
                csv_data = export_points.to_csv(index=False, sep=sep, header=False)
                
                st.success(f"تم تجهيز {len(export_points)} نقطة (مع الإزاحة إذا تم إدخالها).")
                st.download_button(f"📥 تحميل ملف {device_type.split()[0]}", csv_data, "Staking_Points.txt", "text/plain")

        # --- التبويب الثالث: حساب الحفر والردم ---
        with tab3:
            st.subheader("🚜 حساب كميات الحفر والردم التقديرية")
            if data_list:
                total_area = summary['إجمالي_المساحة'].sum()
                st.info(f"إجمالي المساحات المغلقة في المخطط: **{round(total_area, 2)}** متر مربع")
                
                col_z1, col_z2 = st.columns(2)
                current_level = col_z1.number_input("منسوب الأرض الطبيعية الحالي (NGS):", value=1.0, step=0.1)
                target_level = col_z2.number_input("المنسوب التصميمي المطلوب (الحفرية):", value=0.0, step=0.1)
                
                depth = current_level - target_level
                volume = total_area * depth
                
                st.markdown("---")
                if depth > 0:
                    st.error(f"⚠️ الموقع يحتاج إلى **حفر** بعمق: {round(depth, 2)} متر.")
                    st.error(f"📉 إجمالي كمية الحفر التقديرية: **{round(volume, 2)}** متر مكعب.")
                elif depth < 0:
                    st.success(f"⚠️ الموقع يحتاج إلى **ردم** بارتفاع: {round(abs(depth), 2)} متر.")
                    st.success(f"📈 إجمالي كمية الردم التقديرية: **{round(abs(volume), 2)}** متر مكعب.")
                else:
                    st.info("الأرض على المنسوب المطلوب تماماً (0 مكعبات).")

        # --- التبويب الرابع: المطابقة والتقارير ---
        with tab4:
            st.subheader("🔍 استلام الموقع وإصدار التقرير")
            asbuilt_file = st.file_uploader("ارفع ملف الرصد الميداني (CSV/TXT):", type=["csv", "txt"])
            
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
                            
                    status = "✅ مطابق" if min_dist <= tolerance else "❌ يوجد انحراف"
                    results.append({
                        "النقطة": row['ID'],
                        "المرجع": nearest_point['Point_ID'],
                        "الخطأ (متر)": round(min_dist, 3),
                        "الحالة": status
                    })
                
                df_results = pd.DataFrame(results)
                
                def highlight_errors(val):
                    color = '#ffcccc' if val == '❌ يوجد انحراف' else '#ccffcc'
                    return f'background-color: {color}'
                
                st.dataframe(df_results.style.map(highlight_errors, subset=['الحالة']), use_container_width=True)
                
                st.markdown("---")
                st.info("💡 لطباعة هذا التقرير وإرساله للاستشاري كـ PDF: اضغط على `Ctrl + P` في لوحة المفاتيح (أو Print من المتصفح) واختر 'Save as PDF'.")
                
    except Exception as e:
        st.error(f"حدث خطأ أثناء معالجة الملفات: {e}")
