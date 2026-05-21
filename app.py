import streamlit as st
import ezdxf
import tempfile
import os
import pandas as pd

st.set_page_config(page_title="حاسبة فيلا 3 أدوار", layout="wide")
st.title("🏗️ تقرير كميات الفيلا (مفرز آلياً)")

uploaded_file = st.file_uploader("ارفع ملف الـ DXF المحول:", type=["dxf"])

if uploaded_file:
    tfile = tempfile.NamedTemporaryFile(delete=False, suffix=".dxf")
    tfile.write(uploaded_file.getvalue())
    tfile.close()

    try:
        doc = ezdxf.readfile(tfile.name)
        msp = doc.modelspace()
        
        # قائمة لتخزين النتائج
        data = []
        
        # فرز العناصر حسب الطبقة (Layer)
        for entity in msp.query('LWPOLYLINE'):
            layer = entity.dxf.layer
            area = entity.area
            data.append({"الطبقة (العنصر)": layer, "المساحة (م²)": round(area, 2)})
            
        # تحويل البيانات إلى جدول
        df = pd.DataFrame(data)
        
        # تجميع البيانات (حساب العدد والمساحة لكل طبقة)
        summary = df.groupby("الطبقة (العنصر)").agg(
            العدد=("المساحة (م²)", "count"),
            إجمالي_المساحة=("المساحة (م²)", "sum")
        ).reset_index()
        
        st.subheader("📊 جدول الكميات المستخرج:")
        st.dataframe(summary, use_container_width=True)
        
        # زر لتحميل الجدول كملف Excel
        csv = summary.to_csv(index=False).encode('utf-8')
        st.download_button("📥 تحميل الجدول كملف Excel/CSV", csv, "Quantities.csv", "text/csv")
        
        st.success("✅ تم استخراج الكميات بنجاح! راجع الطبقات في الجدول.")

    except Exception as e:
        st.error(f"خطأ في قراءة ملف DXF: {e}")
    
    os.remove(tfile.name)
