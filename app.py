import streamlit as st
import ezdxf
import pandas as pd
import os

st.set_page_config(page_title="المساح الذكي", layout="wide")
st.title("🏗️ نظام إدارة المساحة والكميات الاحترافي")

def calculate_area(vertices):
    area = 0.0
    for i in range(len(vertices)):
        j = (i + 1) % len(vertices)
        area += vertices[i][0] * vertices[j][1]
        area -= vertices[j][0] * vertices[i][1]
    return abs(area) / 2.0

def read_dxf(uploaded_file):
    temp_file_path = f"temp_{uploaded_file.name}"
    with open(temp_file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    doc = ezdxf.readfile(temp_file_path)
    return doc, temp_file_path

# 1. المترجم الذكي للطبقات
def classify_layer(layer_name):
    layer_name = layer_name.upper()
    if any(x in layer_name for x in ['ZAPATA', 'FOOT', 'قاعدة']): return "قواعد (Footings)"
    if any(x in layer_name for x in ['COLUMN', 'COL', 'عمود']): return "أعمدة (Columns)"
    if any(x in layer_name for x in ['BEAM', 'جسر']): return "جسور (Beams)"
    if any(x in layer_name for x in ['BOUNDARY', 'SITE', 'حد']): return "حدود الأرض (Boundary)"
    return "أخرى (Others)"

st.sidebar.header("⚙️ إعدادات العمل")
device_type = st.sidebar.selectbox("نوع جهازك:", ["Leica (CSV)", "Topcon (TXT)", "Generic (CSV)"])

uploaded_file = st.file_uploader("ارفع مخطط الـ DXF:", type=["dxf"])

if uploaded_file:
    try:
        doc, path = read_dxf(uploaded_file)
        msp = doc.modelspace()
        
        all_points = []
        data_list = []
        
        for entity in msp.query('LWPOLYLINE'):
            layer = entity.dxf.layer
            category = classify_layer(layer)
            vertices = [(v[0], v[1]) for v in entity.get_points()]
            area = calculate_area(vertices)
            
            if area > 0:
                data_list.append({"التصنيف": category, "الطبقة الأصلية": layer, "المساحة": area})
            
            for i, v in enumerate(vertices):
                all_points.append({"ID": f"{layer}_{i}", "Y": v[1], "X": v[0], "Category": category})
        
        # عرض الجدول
        df = pd.DataFrame(data_list)
        st.subheader("📊 جدول الكميات المصنف:")
        st.dataframe(df.groupby("التصنيف").agg({"المساحة": "sum"}))
        
        # الفلترة (اختيار ما تريد تنزيله)
        selected_cat = st.multiselect("اختر العناصر لتنزيل نقاطها:", df["التصنيف"].unique())
        
        if selected_cat:
            filtered_points = pd.DataFrame([p for p in all_points if p['Category'] in selected_cat])
            filtered_points = filtered_points.sort_values(by=["Y", "X"])
            
            sep = ',' if device_type != "Topcon (TXT)" else ' '
            csv_data = filtered_points.to_csv(index=False, sep=sep, header=False)
            st.download_button("📥 تحميل ملف التوقيع المختار", csv_data, "Staking_Points.txt")
        
        os.remove(path)
        st.success("✅ تم تصنيف البيانات وترتيبها بنجاح!")
    except Exception as e:
        st.error(f"خطأ: {e}")
