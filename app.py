import streamlit as st
import pandas as pd
import ezdxf  # المكتبة الاحترافية لقراءة DXF
import io

# إعدادات الصفحة
st.set_page_config(page_title="المساحة والكميات الذكي", page_icon="📐", layout="wide")
st.title("📐 تطبيق المساحة وحساب الكميات الذكي")

# 1. القائمة الجانبية
menu = st.sidebar.selectbox("العمليات:", [
    "4. حاسب الخرسانة الشامل (قواعد، لبشة، أعمدة، أسقف، درج)",
    "1. تصدير ونقاط الأجهزة", 
    "2. مطابقة الرفع الفعلي", 
    "3. حساب أعمال الحفر والدروب"
])

# 2. دالة قراءة DXF الاحترافية
def process_dxf_file(uploaded_file):
    try:
        # حفظ الملف مؤقتاً لقراءته عبر ezdxf
        temp_file = io.BytesIO(uploaded_file.getvalue())
        doc = ezdxf.read(temp_file)
        msp = doc.modelspace()
        
        # استخراج العناصر (كمثال: عدّ القواعد أو الأعمدة)
        entities_count = len(msp.query('LWPOLYLINE')) 
        return True, entities_count
    except Exception as e:
        return False, str(e)

# 3. المنطق البرمجي
if menu == "4. حاسب الخرسانة الشامل (قواعد، لبشة، أعمدة، أسقف، درج)":
    st.header("🧱 حاسبة الخرسانة")
    element = st.radio("العنصر:", ["قواعد منفصلة", "لبشة خرسانية", "أعمدة", "أسقف وجسور ودرج"], horizontal=True)
    
    con_file = st.file_uploader("ارفع مخطط DXF:", type=["dxf"])
    
    calc = 0.0
    if con_file:
        success, count = process_dxf_file(con_file)
        if success:
            st.success(f"✅ تم قراءة الملف بنجاح! تم رصد {count} عنصر هندسي.")
            # حسابات بناءً على العناصر المرصودة
            if element == "قواعد منفصلة": calc = count * 2.5
            elif element == "لبشة خرسانية": calc = count * 50.0
            elif element == "أعمدة": calc = count * 0.5
            else: calc = count * 10.0
        else:
            st.error(f"❌ تعذر قراءة الملف: {count}")
    
    final_vol = st.number_input("التكعيب النهائي (م³):", value=float(calc), step=1.0)
    if st.button("حساب التكلفة"):
        st.metric("الفاتورة الإجمالية", f"{final_vol * 22:,.1f} KD")

# باقي الخيارات كما هي (تصدير، مطابقة، حفر)
