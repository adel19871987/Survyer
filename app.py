import streamlit as st
import ezdxf
import pandas as pd
import os

st.set_page_config(page_title="المساح الذكي", layout="centered")
st.title("🛰️ نظام المساحة والكميات")

def read_dxf(uploaded_file):
    temp_file_path = f"temp_{uploaded_file.name}"
    with open(temp_file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    doc = ezdxf.readfile(temp_file_path)
    return doc, temp_file_path

device_type = st.selectbox("نوع جهازك:", ["Leica (CSV)", "Topcon (TXT)", "Generic (CSV)"])
uploaded_file = st.file_uploader("ارفع المخطط:", type=["dxf"])

if uploaded_file:
    try:
        doc, path = read_dxf(uploaded_file)
        msp = doc.modelspace()
        
        all_points = []
        data_list = []
        
        for entity in msp.query('LWPOLYLINE'):
            layer = entity.dxf.layer
            area = entity.area
            if area > 0:
                data_list.append({"الطبقة": layer, "المساحة": area})
            for i, vertex in enumerate(entity.get_points()):
                all_points.append({
                    "ID": f"{layer}_{i}",
                    "North_Y": vertex[1],
                    "East_X": vertex[0],
                    "Elevation": 0.0
                })
        
        df_points = pd.DataFrame(all_points).sort_values(by=["North_Y", "East_X"])
        
        # جدول الكميات
        df = pd.DataFrame(data_list)
        summary = df.groupby("الطبقة").agg({"المساحة": ["count", "sum"]})
        st.table(summary)
        
        # ملف التوقيع
        sep = ',' if device_type != "Topcon (TXT)" else ' '
        csv_data = df_points.to_csv(index=False, sep=sep, header=False)
        st.download_button("📥 تحميل ملف التوقيع", csv_data, "Staking.txt")
        
        os.remove(path)
        st.success("تمت المعالجة!")
    except Exception as e:
        st.error(f"خطأ: {e}")
