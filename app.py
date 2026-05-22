import streamlit as st
import ezdxf
import pandas as pd
import io
import matplotlib.pyplot as plt

# إعدادات الواجهة
st.set_page_config(page_title="المهندس الرقمي - بو عابد", layout="wide")
st.title("🏗️ المهندس الرقمي (نظام المساحة والكميات)")

# دالة القراءة الذكية للملف من الذاكرة
def read_dxf_from_memory(uploaded_file):
    bytes_data = uploaded_file.getvalue()
    return ezdxf.read(io.BytesIO(bytes_data))

# القائمة الجانبية (إعداداتك الميدانية)
st.sidebar.header("⚙️ إعدادات الموقع")
height = st.sidebar.number_input("ارتفاع الخرسانة (متر):", min_value=0.1, value=0.6, step=0.05)
device = st.sidebar.selectbox("اختر نوع جهازك المساحي:", ["Leica (CSV)", "Topcon (TXT)", "Generic (CSV)"])

# منطقة رفع المخططات
col1, col2 = st.columns(2)
file_old = col1.file_uploader("ارفع المخطط القديم (للتحليل):", type=["dxf"])
file_new = col2.file_uploader("ارفع المخطط الحالي:", type=["dxf"])

if file_new:
    doc = read_dxf_from_memory(file_new)
    msp = doc.modelspace()
    
    st.divider()
    
    # معالجة بيانات الكميات والإحداثيات
    quantities = []
    points = []
    for entity in msp.query('LWPOLYLINE'):
        layer = entity.dxf.layer
        area = entity.area
        if area > 0:
            quantities.append({"الطبقة": layer, "المساحة": area})
        for i, v in enumerate(entity.get_points()):
            points.append({"ID": f"{layer}_{i}", "N": v[1], "E": v[0], "Z": 0.0})

    # 1. جدول الكميات
    df_q = pd.DataFrame(quantities)
    if not df_q.empty:
        summary = df_q.groupby("الطبقة").agg({"المساحة": ["count", "sum"]})
        summary.columns = ["العدد", "إجمالي المساحة"]
        summary["الحجم (م³)"] = summary["إجمالي المساحة"] * height
        st.subheader("📊 جدول الكميات:")
        st.table(summary.round(2))
    
    # 2. ملف التوقيع (التوتال ستيشن)
    df_p = pd.DataFrame(points).sort_values(by=["N", "E"])
    st.subheader("📍 التوقيع المساحي:")
    csv = df_p.to_csv(index=False, header=False, sep=',' if "CSV" in device else ' ')
    st.download_button("📥 تحميل ملف النقاط لجهازك", csv, "Staking_Points.txt")
    
    # 3. التحليل البصري
    st.subheader("📍 خريطة توزيع العناصر:")
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.scatter(df_p['E'], df_p['N'], c='red', s=2)
    st.pyplot(fig)

    st.success("✅ النظام جاهز ومكتمل يا بو عابد!")

# شرح بصري لآلية العمل
st.markdown("---")
st.write("### كيف يعمل نظامك:")
