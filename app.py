import streamlit as st
import ezdxf
import pandas as pd

st.title("🌐 مساعد المساح العالمي (Universal Surveyor)")

# اختيار نوع الجهاز
device_type = st.sidebar.selectbox("اختر نوع جهازك:", ["Leica (GSI/CSV)", "Topcon (CSV/TXT)", "Sokkia (SDR/CSV)", "Generic (X,Y,Z)"])

uploaded_file = st.file_uploader("ارفع مخطط الـ DXF:", type=["dxf"])

if uploaded_file:
    doc = ezdxf.readfile(uploaded_file)
    msp = doc.modelspace()
    
    all_points = []
    for entity in msp.query('LWPOLYLINE'):
        layer = entity.dxf.layer
        for i, vertex in enumerate(entity.get_points()):
            all_points.append({
                "Point_ID": f"{layer}_{i}",
                "North_Y": vertex[1],
                "East_X": vertex[0],
                "Elevation_Z": 0.0
            })
    
    if all_points:
        df = pd.DataFrame(all_points)
        df = df.sort_values(by=["North_Y", "East_X"])
        
        st.subheader("📋 بيانات جاهزة للتصدير:")
        st.dataframe(df)
        
        # تحويل البيانات حسب نوع الجهاز
        if device_type == "Leica (GSI/CSV)":
            csv_data = df.to_csv(index=False, sep=',', header=False) # تنسيق لايكا
        elif device_type == "Topcon (CSV/TXT)":
            csv_data = df.to_csv(index=False, sep=' ', header=False) # تنسيق توبكون
        else:
            csv_data = df.to_csv(index=False, header=True)
            
        st.download_button(f"📥 تحميل ملف التوقيع لـ {device_type}", csv_data, "Staking_Data.txt", "text/plain")
        
        st.success("✅ تم ضبط الملف بنجاح ليعمل على جهازك!")
