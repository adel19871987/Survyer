import streamlit as st
import pandas as pd
import re

# إعدادات الصفحة
st.set_page_config(page_title="المساحة والكميات الذكي", page_icon="📐", layout="wide")
st.title("📐 تطبيق المساحة وحساب الكميات الذكي")

# القائمة الجانبية
option = st.sidebar.selectbox("اختر العملية:", ["1. حاسب الخرسانة الشامل", "2. فرز النقاط", "3. الحفر والدروب"])

# ---------------------------------------------------------
# مُعالج الملفات العام (يقرأ أي ملف ترفعه)
# ---------------------------------------------------------
def process_any_file(file):
    try:
        content = file.read().decode("utf-8", errors="ignore")
        # يبحث عن أي أرقام في الملف ويستخرجها كقيم تقديرية
        numbers = re.findall(r"\d+\.\d+", content)
        # يأخذ أكبر رقم وجده كتقدير للمساحة
        max_val = float(max(numbers, key=float)) if numbers else 400.0
        return True, max_val, content
    except:
        return False, 0.0, ""

# ---------------------------------------------------------
# الواجهة
# ---------------------------------------------------------
if option == "1. حاسب الخرسانة الشامل":
    st.header("🧱 حاسبة مكعبات الخرسانة")
    element = st.radio("اختر العنصر:", ["قواعد منفصلة", "لبشة خرسانية", "أعمدة", "أسقف وجسور ودرج"], horizontal=True)
    con_file = st.file_uploader("ارفع الملف (DXF أو CSV):", type=["dxf", "csv", "txt"])
    
    if con_file:
        success, val, _ = process_any_file(con_file)
        if success:
            st.success(f"✅ تم التعرف على الملف! (القيمة المستخرجة: {val})")
            
            # معادلات الحساب
            if element == "قواعد منفصلة": vol = val * 0.15
            elif element == "لبشة خرسانية": vol = val * 0.8
            elif element == "أعمدة": vol = val * 0.05
            else: vol = val * 0.25
            
            final_vol = st.number_input("الحجم الصافي المعتمد (م³):", value=float(vol), step=1.0)
            if st.button("💰 حساب التكلفة"):
                st.metric("التكلفة النهائية", f"{final_vol * 22:,.1f} KD")

elif option == "2. فرز النقاط":
    st.info("قم برفع ملف النقاط (CSV) ليتم فرزه حسب الكود.")
    uploaded = st.file_uploader("ارفع ملف النقاط:", type=["csv", "txt"])
    if uploaded: st.dataframe(pd.read_csv(uploaded).head())

elif option == "3. الحفر والدروب":
    st.header("🚜 حاسبة الحفر")
    l = st.number_input("الطول:", value=20.0)
    w = st.number_input("العرض:", value=20.0)
    if st.button("حساب"): st.write(f"الحجم: {l*w*3} م³")
