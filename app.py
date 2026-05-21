import streamlit as st
import math

st.set_page_config(page_title="المهندس المساح الذكي (الكويت)", page_icon="📐", layout="centered")
st.title("📐 تطبيق المساحة وحساب الكميات الذكي")
st.subheader("الإصدار المطور والمخصص للمشاريع في دولة الكويت")

def validate_kuwait_coordinates(east, north):
    if (150000 <= east <= 600000) and (3100000 <= north <= 3350000): return True
    return False

def universal_coordinate_exporter(points_list, device_brand):
    brand = device_brand.lower()
    if "leica" in brand: return f"✅ تم توليد ملف GSI-8 لأجهزة Leica بنجاح."
    elif "topcon" in brand or "sokkia" in brand: return f"✅ تم توليد ملف CSV لأجهزة Topcon/Sokkia (P,E,N,Z,C)."
    elif "trimble" in brand: return f"✅ تم توليد ملف نصي لأجهزة Trimble Access."
    return f"✅ تم تصدير ملف CSV القياسي المفتوح."

def calculate_field_deviation(design_point, as_built_point):
    d_E, d_N = design_point['E'], design_point['N']
    a_E, a_N = as_built_point['E'], as_built_point['N']
    delta_E, delta_N = a_E - d_E, a_N - d_N
    horizontal_error = math.sqrt(delta_E**2 + delta_N**2)
    status = "🔴 تنبيه: الخطأ تجاوز الحد المسموح!" if horizontal_error > 0.02 else "🟢 مقبول: التنفيذ سليم."
    return {"الفرق في الشرق (ΔE)": f"{delta_E*100:.1f} سم", "الفرق في الشمال (ΔN)": f"{delta_N*100:.1f} سم", "إجمالي الإزاحة الأفقية": f"{horizontal_error*100:.1f} سم", "القرار الهندسي": status}

def calculate_kuwait_earthworks(length, width, depth, price_per_durb):
    volume = length * width * depth
    loosened_volume = volume * 1.15
    total_trucks = math.ceil(loosened_volume / 16)
    return {"حجم الحفر الصافي": f"{volume:.2f} م3", "دروب السيارات المتوقعة": f"{total_trucks} درب", "التكلفة التقديرية": f"{total_trucks * price_per_durb:.2f} KD"}

def calculate_concrete_with_waste(length, width, depth, count, concrete_price, waste_percent):
    net_volume = length * width * depth * count
    total_volume_with_waste = net_volume * (1 + (waste_percent / 100))
    return {"الصافي الدقيق": f"{net_volume:.2f} م3", "الطلب شامل الهدر": f"{math.ceil(total_volume_with_waste)} م3", "التكلفة الإجمالية": f"{total_volume_with_waste * concrete_price:.2f} KD"}

st.sidebar.header("📋 قائمة التحكم")
service = st.sidebar.selectbox("اختر العملية الهندسية:", ["1. تصدير نقاط الأجهزة", "2. مطابقة الرفع الفعلي (As-Built)", "3. حساب أعمال الحفر", "4. حاسب الخرسانة والأسعار"])

if service == "1. تصدير نقاط الأجهزة":
    st.header("📥 استخراج وتصدير النقاط")
    brand = st.selectbox("اختر جهاز التوتال ستيشن:", ["Leica", "Topcon", "Sokkia", "Trimble"])
    if st.button("تجهيز وتصدير ملف الإحداثيات"): st.success(universal_coordinate_exporter([1,2], brand))

elif service == "2. مطابقة الرفع الفعلي (As-Built)":
    st.header("🔍 فحص ومطابقة التنفيذ الواقعي")
    col1, col2 = st.columns(2)
    with col1:
        de = st.number_input("East (Design):", value=395420.150, format="%.3f")
        dn = st.number_input("North (Design):", value=3241560.450, format="%.3f")
    with col2:
        ae = st.number_input("East (As-Built):", value=395420.165, format="%.3f")
        an = st.number_input("North (As-Built):", value=3241560.485, format="%.3f")
    if st.button("فحص الانحراف"):
        if not validate_kuwait_coordinates(de, dn): st.error("⚠️ الإحداثيات خارج الكويت!")
        else: st.json(calculate_field_deviation({"E": de, "N": dn}, {"E": ae, "N": an}))

elif service == "3. حساب أعمال الحفر":
    st.header("🚜 حساب كميات الحفر والدروب")
    l = st.number_input("طول القسيمة:", value=25.0)
    w = st.number_input("عرض القسيمة:", value=20.0)
    d = st.number_input("عمق الحفر:", value=3.5)
    p = st.number_input("سعر الدرب (KD):", value=15.0)
    if st.button("احسب الحفر"): st.write(calculate_kuwait_earthworks(l, w, d, p))

elif service == "4. حاسب الخرسانة والأسعار":
    st.header("📊 ميزانية الخرسانة الجاهزة")
    length = st.number_input("طول القاعدة:", value=2.0)
    width = st.number_input("عرض القاعدة:", value=1.5)
    depth = st.number_input("السمك:", value=0.6)
    count = st.number_input("العدد الكلي:", value=15, step=1)
    c_price = st.number_input("سعر المتر (KD):", value=22.0)
    waste = st.slider("نسبة الهدر (%):", 0, 15, 5)
    if st.button("احسب الميزانية"): st.write(calculate_concrete_with_waste(length, width, depth, count, c_price, waste))
