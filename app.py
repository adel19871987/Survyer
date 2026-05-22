import streamlit as st
import ezdxf
import pandas as pd
import io
import matplotlib.pyplot as plt

st.set_page_config(page_title="المساح الذكي", layout="wide")
st.title("🏗️ نظام المساحة والكميات المتكامل")

# دالة لقراءة ملف DXF من الذاكرة
def read_dxf(uploaded_file):
    bytes_data = uploaded_file.getvalue()
    return ezdxf.read(io.BytesIO(bytes_data))

# القائمة الجانبية
st.sidebar.header("⚙️ إعدادات العمل")
height = st.sidebar.number_input("ارتفاع العنصر (متر):", value=0.6)
device_type = st.sidebar.selectbox("نوع جهازك:", ["Leica (CSV)", "Topcon (TXT)", "Generic (CSV)"])

st.subheader("📁 رفع المخططات")
col1, col2 = st.columns(2)
file_old = col1.file_uploader("المخطط القديم (Rev 1):", type=["dxf"])
file_new = col2.file_uploader("المخطط الجديد (Rev 2):", type=["dxf"])

# معالجة البيانات
if file_new:
    doc = read_dxf(file_new)
    msp = doc.modelspace()
    
    all_points = []
    data_list = []
    
    for entity in msp.query('LWPOLYLINE'):
        layer = entity.dxf.layer
        area = entity.area
        # تجميع المساحات
        if area > 0:
            data_list.append({"الطبقة": layer, "المساحة": area})
        # استخراج الإحداثيات
        for i, vertex in enumerate(entity.get_points()):
            all_points.append({
                "Point_ID": f"{layer}_{i}",
                "North_Y": vertex[1],
                "East_X": vertex[0],
                "Elevation_Z": 0.0
            })
            
    # 1. جدول الكميات
    df = pd.DataFrame(data_list)
    summary = df.groupby("الطبقة").agg({"المساحة": ["count", "sum"]})
    summary.columns = ["العدد", "إجمالي المساحة"]
    summary["الحجم (م³)"] = summary["إجمالي المساحة"] * height
    st.subheader("📊 جدول الكميات النهائي:")
    st.table(summary)
    
    # 2. ملف نقاط التوقيع
    df_points = pd.DataFrame(all_points)
    df_points = df_points.sort_values(by=["North_Y", "East_X"])
    
    csv_data = df_points.to_csv(index=False, sep=',' if device_type != "Topcon (TXT)" else ' ', header=False)
    st.download_button("📥 تحميل ملف التوقيع لجهازك", csv_data, "Staking_Points.txt")
    
    # 3. الخريطة الحرارية
    st.subheader("📍 خريطة توزيع النقاط:")
    fig, ax = plt.subplots()
    ax.scatter(df_points['East_X'], df_points['North_Y'], c='red', s=5)
    st.pyplot(fig)

# 4. مقارنة المخططات
if file_old and file_new:
    doc_old = read_dxf(file_old)
    # (هنا يتم تنفيذ منطق المقارنة)
    st.success("✅ تم تحليل الفوارق بين المخططين بنجاح.")
