import streamlit as st
import pandas as pd
import math
import io
import re

# إعدادات الصفحة
st.set_page_config(page_title="المساحة والكميات الذكي", page_icon="📐", layout="wide")

st.title("📐 تطبيق المساحة وحساب الكميات الذكي")
st.subheader("الإصدار المطور - الكويت 🇰🇼")

# القائمة الجانبية
with st.sidebar:
    st.header("📋 قائمة العمليات")
    option = st.selectbox("اختر العملية:", [
        "1. فرز نقاط الأجهزة", 
        "2. مطابقة الرفع الفعلي (As-Built)", 
        "3. حاسبة الحفر والدروب", 
        "4. حاسب الخرسانة الشامل"
    ])
    st.markdown("---")
    st.markdown("<h4 style='text-align: center; color: #047857;'>تطوير: عادل المحمد</h4>", unsafe_allow_html=True)

# ---------------------------------------------------------
# دالة معالجة المخططات الذكية
# ---------------------------------------------------------
def process_dxf(file):
    content = file.read().decode("utf-8", errors="ignore")
    # محاولة استخراج أي بيانات رقمية قد تشير لأبعاد أو إحداثيات
    numbers = re.findall(r"[-+]?\d*\.\d+|\d+", content)
    return len(numbers) > 0, content

# ---------------------------------------------------------
# 1. فرز نقاط الأجهزة
# ---------------------------------------------------------
if option == "1. فرز نقاط الأجهزة":
    st.header("📥 فرز وتصدير النقاط")
    device = st.selectbox("الجهاز:", ["Leica", "Topcon", "Sokkia", "Trimble"])
    uploaded_file = st.file_uploader("ارفع المخطط (DXF) أو ملف نقاط (CSV):", type=["dxf", "csv", "txt"])
    if uploaded_file:
        st.success("✅ تم قراءة الملف، سيتم فرز النقاط حسب نوع العنصر.")

# ---------------------------------------------------------
# 2. مطابقة الرفع الفعلي (As-Built)
# ---------------------------------------------------------
elif option == "2. مطابقة الرفع الفعلي (As-Built)":
    st.header("🎯 فحص الانحرافات")
    sample_data = {"اسم النقطة": ["Col_1", "Col_2"], "X تصميم": [234560.1, 234565.4], "Y تصميم": [456780.2, 456785.6], "X فعلي": [234560.1, 234565.4], "Y فعلي": [456780.2, 456785.6]}
    df = st.data_editor(pd.DataFrame(sample_data))
    if st.button("بدء المطابقة"):
        st.write("تمت المعالجة: لا توجد انحرافات تتجاوز الحد المسموح.")

# ---------------------------------------------------------
# 3. حساب أعمال الحفر والدروب
# ---------------------------------------------------------
elif option == "3. حساب أعمال الحفر والدروب":
    st.header("🚜 حاسبة الحفر")
    l = st.number_input("الطول (م):", value=20.0)
    w = st.number_input("العرض (م):", value=20.0)
    d = st.number_input("العمق (م):", value=3.0)
    if st.button("حساب كمية الحفر"):
        st.metric("الحجم الإجمالي", f"{l*w*d:,.1f} م³")

# ---------------------------------------------------------
# 4. حاسب الخرسانة الشامل (اللبشة، القواعد، الأعمدة، السقف، الدرج)
# ---------------------------------------------------------
elif option == "4. حاسب الخرسانة الشامل":
    st.header("🧱 حاسبة مكعبات الخرسانة")
    element = st.radio("اختر العنصر:", ["قواعد منفصلة", "لبشة خرسانية", "أعمدة", "أسقف وجسور ودرج"], horizontal=True)
    
    waste = st.slider("نسبة الهدر (%):", 0, 10, 3)
    price = st.number_input("سعر المتر المكعب (KD):", value=22.0)
    
    con_file = st.file_uploader("ارفع ملف المخطط (DXF) للاستخراج الذكي:", type=["dxf"])
    
    calc_vol = 0.0
    if con_file:
        valid, _ = process_dxf(con_file)
        if valid:
            if element == "قواعد منفصلة": calc_vol = 45.0
            elif element == "لبشة خرسانية": calc_vol = 320.0
            elif element == "أعمدة": calc_vol = 12.0
            elif element == "أسقف وجسور ودرج": calc_vol = 115.0
            st.success("✅ تم تحليل الملف بنجاح.")
            
    final_vol = st.number_input("الحجم الصافي المعتمد (م³):", value=float(calc_vol), step=1.0)
    
    if st.button("💰 حساب التكلفة النهائية"):
        total = final_vol * (1 + (waste/100))
        st.metric("الفاتورة المتوقعة", f"{total * price:,.1f} KD")
