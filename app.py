import streamlit as st
import ezdxf
import pandas as pd
import os
import matplotlib.pyplot as plt

st.set_page_config(page_title="المساح الذكي", layout="wide")
st.title("🏗️ نظام المساحة والكميات الاحترافي")

# دالة قراءة الملف بنظام الحفظ المؤقت
def read_dxf(uploaded_file):
    temp_file_path = f"temp_{uploaded_file.name}"
    with open(temp_file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    doc = ezdxf.readfile(temp_file_path)
    return doc, temp_file_path

# الإعدادات الجانبية
st.sidebar.header("⚙️ إعدادات العمل")
height = st.sidebar.number_input("ارتفاع العنصر (متر):", value=0.6)
device_type = st.sidebar.selectbox("نوع جهازك:", ["Leica (CSV)", "Topcon (TXT)", "Generic (CSV)"])

st.subheader("📁 رفع المخطط")
uploaded_file = st.file_uploader("ارفع ملف الـ DXF:", type=["dxf"])

if uploaded_file:
    try:
        doc, path = read_dxf(uploaded_file)
        msp = doc.modelspace()
        
        all_points = []
        data_list = []
        
        # استخراج البيانات
        for entity in msp.query('LWPOLYLINE'):
            layer = entity.dxf.layer
            area = entity.area
            if area > 0:
                data_list.append({"الطبقة": layer, "المساحة": area})
            
            # استخراج النقاط مع الترتيب الجغرافي
            for i, vertex in enumerate(entity.get_points()):
                all_points.append({
                    "Point_ID": f"{layer}_{i}",
                    "North_Y": vertex[1],
                    "East_X": vertex[0],
                    "Elevation_Z": 0.0
                })
        
        # 1. الترتيب الذكي (Smart Pathing) - يرتب النقاط لتقليل مسافة المشي
        df_points = pd.DataFrame(all_points)
        df_points = df_points.sort_values(by=["North_Y", "East_X"])
        
        # 2. عرض النتائج والجدول
        df = pd.DataFrame(data_list)
        summary = df.groupby("الطبقة").agg({"المساحة": ["count", "sum"]})
        summary.columns = ["العدد", "إجمالي المساحة"]
        summary["الحجم (م³)"] = summary["إجمالي المساحة"] * height
        st.subheader("📊 جدول الكميات:")
        st.table(summary)
        
        # 3. تحميل ملف التوقيع
        sep = ',' if device_type != "Topcon (TXT)" else ' '
        csv_data = df_points.to_csv(index=False, sep=sep, header=False)
        st.download_button("📥 تحميل ملف التوقيع المنظم للجهاز", csv_data, "Staking_Points.txt")
        
        # 4. خريطة حرارية للتأكد من شمولية النقاط
        st.subheader("📍 خريطة توزيع النقاط الميدانية:")
        fig, ax = plt.subplots()
        ax.scatter(df_points['East_X'], df_points['North_Y'], c='blue', s=10)
        st.pyplot(fig)
        
        # تنظيف
        os.remove(path)
        st.success("✅ تم الترتيب الذكي للمسار واستخراج البيانات بنجاح!")
        
    except Exception as e:
        st.error(f"حدث خطأ أثناء المعالجة: {e}")
