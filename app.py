import streamlit as st
import ezdxf
import pandas as pd
import os
import matplotlib.pyplot as plt

st.set_page_config(page_title="المساح الذكي", layout="wide")
st.title("🏗️ نظام المساحة والكميات الاحترافي")

# دالة لحساب المساحة يدوياً (لحل مشكلة attribute 'area')
def calculate_area(points):
    # معادلة shoelace لحساب مساحة المضلع
    area = 0
    n = len(points)
    for i in range(n):
        j = (i + 1) % n
        area += points[i][0] * points[j][1]
        area -= points[j][0] * points[i][1]
    return abs(area) / 2.0

def read_dxf(uploaded_file):
    temp_file_path = f"temp_{uploaded_file.name}"
    with open(temp_file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    doc = ezdxf.readfile(temp_file_path)
    return doc, temp_file_path

st.sidebar.header("⚙️ إعدادات العمل")
height = st.sidebar.number_input("ارتفاع العنصر (متر):", value=0.6)
device_type = st.sidebar.selectbox("نوع جهازك:", ["Leica (CSV)", "Topcon (TXT)", "Generic (CSV)"])

uploaded_file = st.file_uploader("ارفع ملف الـ DXF:", type=["dxf"])

if uploaded_file:
    try:
        doc, path = read_dxf(uploaded_file)
        msp = doc.modelspace()
        
        all_points = []
        data_list = []
        
        for entity in msp.query('LWPOLYLINE'):
            layer = entity.dxf.layer
            # استخراج النقاط
            points = [(v[0], v[1]) for v in entity.get_points()]
            
            # حساب المساحة يدوياً
            if len(points) > 2:
                area = calculate_area(points)
                if area > 0:
                    data_list.append({"الطبقة": layer, "المساحة": area})
            
            # استخراج النقاط للتوقيع
            for i, p in enumerate(points):
                all_points.append({"Point_ID": f"{layer}_{i}", "North_Y": p[1], "East_X": p[0]})
        
        # النتائج
        df = pd.DataFrame(data_list)
        summary = df.groupby("الطبقة").agg({"المساحة": ["count", "sum"]})
        summary.columns = ["العدد", "إجمالي المساحة"]
        summary["الحجم (م³)"] = summary["إجمالي المساحة"] * height
        st.table(summary)
        
        # تحميل الملف
        df_points = pd.DataFrame(all_points).sort_values(by=["North_Y", "East_X"])
        sep = ',' if device_type != "Topcon (TXT)" else ' '
        csv_data = df_points.to_csv(index=False, sep=sep, header=False)
        st.download_button("📥 تحميل ملف التوقيع للجهاز", csv_data, "Staking_Points.txt")
        
        os.remove(path)
        st.success("✅ تم المعالجة بنجاح!")
    except Exception as e:
        st.error(f"حدث خطأ: {e}")
