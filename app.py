import streamlit as st
import ezdxf
import pandas as pd
import os
import matplotlib.pyplot as plt

st.set_page_config(page_title="المساح الشامل", layout="wide")
st.title("🏗️ نظام إدارة المساحة والكميات الشامل")

# 1. دوال النظام
def calculate_area(vertices):
    area = 0.0
    for i in range(len(vertices)):
        j = (i + 1) % len(vertices)
        area += vertices[i][0] * vertices[j][1]
        area -= vertices[j][0] * vertices[i][1]
    return abs(area) / 2.0

def classify_layer(layer_name):
    layer_name = layer_name.upper()
    if any(x in layer_name for x in ['ZAPATA', 'FOOT', 'قاعدة']): return "قواعد (Footings)"
    if any(x in layer_name for x in ['COLUMN', 'COL', 'عمود']): return "أعمدة (Columns)"
    if any(x in layer_name for x in ['BEAM', 'جسر']): return "جسور (Beams)"
    if any(x in layer_name for x in ['BOUNDARY', 'SITE', 'حد']): return "حدود (Boundary)"
    return "أخرى (Others)"

# 2. الواجهة والمدخلات
st.sidebar.header("⚙️ خيارات النظام")
device_type = st.sidebar.selectbox("نوع جهاز التوتال ستيشن:", ["Leica (CSV)", "Topcon (TXT)", "Generic (CSV)"])
uploaded_file = st.file_uploader("ارفع ملف المخطط (DXF):", type=["dxf"])

if uploaded_file:
    # حفظ مؤقت وقراءة
    temp_path = f"temp_{uploaded_file.name}"
    with open(temp_path, "wb") as f: f.write(uploaded_file.getbuffer())
    doc = ezdxf.readfile(temp_path)
    msp = doc.modelspace()
    
    all_points, data_list = [], []
    for entity in msp.query('LWPOLYLINE'):
        layer = entity.dxf.layer
        cat = classify_layer(layer)
        vertices = [(v[0], v[1]) for v in entity.get_points()]
        area = calculate_area(vertices)
        if area > 0: data_list.append({"التصنيف": cat, "الطبقة": layer, "المساحة": area})
        for i, v in enumerate(vertices):
            all_points.append({"ID": f"{layer}_{i}", "Y": v[1], "X": v[0], "Category": cat})
    
    # 3. عرض البيانات
    df = pd.DataFrame(data_list)
    st.subheader("📊 جدول الكميات التفصيلي")
    st.table(df.groupby(["التصنيف", "الطبقة"]).agg({"المساحة": "sum"}))
    
    # 4. الفلترة والتنزيل
    selected_cat = st.multiselect("اختر العناصر لتصدير إحداثياتها للجهاز:", df["التصنيف"].unique())
    if selected_cat:
        df_pts = pd.DataFrame([p for p in all_points if p['Category'] in selected_cat]).sort_values(by=["Y", "X"])
        csv_data = df_pts.to_csv(index=False, sep=',' if device_type != "Topcon (TXT)" else ' ', header=False)
        st.download_button("📥 تحميل ملف التوقيع للجهاز", csv_data, "Points.txt")
        
        # خريطة حرارية
        fig, ax = plt.subplots()
        ax.scatter(df_pts['X'], df_pts['Y'], c='red', s=5)
        st.pyplot(fig)
        
    os.remove(temp_path)
    st.success("✅ النظام يعمل بكامل قوته!")
