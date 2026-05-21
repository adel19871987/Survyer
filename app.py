import streamlit as st
import pandas as pd
import math
import io

# إعدادات الصفحة الافتراضية
st.set_page_config(page_title="المساحة وحساب الكميات الذكي", page_icon="📐", layout="wide")

# واجهة التطبيق الرئيسية
st.title("📐 تطبيق المساحة وحساب الكميات الذكي")
st.subheader("الإصدار المطور والمخصص للمشاريع في دولة الكويت 🇰🇼")

# القائمة الجانبية للتحكم
with st.sidebar:
    st.header("📋 قائمة التحكم")
    option = st.selectbox(
        "اختر العملية الهندسية:",
        [
            "1. تصدير ونقاط الأجهزة الفرز التلقائي",
            "2. مطابقة الرفع الفعلي (As-Built)",
            "3. حساب أعمال الحفر والدروب",
            "4. حاسب الخرسانة والأسعار"
        ]
    )
    st.write("---")
    st.caption("تطوير المهندس عادل المفتوح © 2026")

# ---------------------------------------------------------
# الخيار الأول: تصدير وفرز نقاط الأجهزة تلقائياً
# ---------------------------------------------------------
if option == "1. تصدير ونقاط الأجهزة الفرز التلقائي":
    st.header("📥 استخراج، فرز وتصدير النقاط تلقائياً")
    
    device = st.selectbox("اختر جهاز التوتال ستيشن / الـ GPS الميداني:", ["Leica", "Topcon", "Sokkia", "Trimble"])
    
    st.markdown("### 📁 ارفع المخطط الرقمي ليقوم التطبيق بالفرز:")
    uploaded_file = st.file_uploader("ارفع ملف المخطط بصيغة (DXF) أو ملف نقاط (CSV / TXT):", type=["dxf", "csv", "txt"])
    
    df_points = pd.DataFrame(columns=["Point_ID", "Easting_X", "Northing_Y", "Elevation_Z", "Type_النوع"])
    
    if uploaded_file is not None:
        file_ext = uploaded_file.name.split(".")[-1].lower()
        
        # 1. قراءة وفرز ملفات CSV أو TXT
        if file_ext in ["csv", "txt"]:
            try:
                df_uploaded = pd.read_csv(uploaded_file, header=None, names=["Point_ID", "Easting_X", "Northing_Y", "Elevation_Z", "Type_النوع"])
                # إذا لم يحتوي الملف على عمود النوع، نقوم بفرزه بناءً على كود التسمية تلقائياً
                if "Type_النوع" not in df_uploaded.columns or df_uploaded["Type_النوع"].isnull().all():
                    types = []
                    for idx, row in df_uploaded.iterrows():
                        pid = str(row["Point_ID"]).upper()
                        if "F" in pid or "ق" in pid: types.append("قواعد (Footings)")
                        elif "C" in pid or "ع" in pid: types.append("أعمدة (Columns)")
                        elif "B" in pid or "ح" in pid: types.append("حدود الأرض (Boundary)")
                        else: types.append("نقاط عامة (General)")
                    df_uploaded["Type_النوع"] = types
                df_points = df_uploaded
                st.success(f"✅ تم قراءة وفرز ملف النقاط بنجاح! تم العثور على {len(df_points)} نقطة.")
            except Exception as e:
                st.error("❌ تأكد من تنسيق ملف الـ CSV/TXT")
        
        # 2. قراءة وفرز ملفات DXF (الأوتوكاد) ذكياً بناءً على الطبقات Layers
        elif file_ext == "dxf":
            try:
                dxf_content = uploaded_file.read().decode("utf-8", errors="ignore")
                extracted_points = []
                lines = dxf_content.splitlines()
                
                current_layer = "General"
                for i in range(len(lines) - 2):
                    # معرفة اسم الطبقة الحالية في الأوتوكاد
                    if lines[i].strip() == "8":
                        current_layer = lines[i+1].strip().upper()
                    
                    if lines[i].strip() == "POINT" or lines[i].strip() == "TEXT":
                        x, y, z = 0.0, 0.0, 0.0
                        for j in range(i, min(i+50, len(lines)-1)):
                            if lines[j].strip() == "10": x = float(lines[j+1].strip())
                            if lines[j].strip() == "20": y = float(lines[j+1].strip())
                            if lines[j].strip() == "30": z = float(lines[j+1].strip())
                        
                        # الفرز الذكي والفرعي بناءً على اسم الطبقة في المخطط
                        if "FOOTING" in current_layer or "FOUNDATION" in current_layer or "قواعد" in current_layer:
                            pt_type = "قواعد (Footings)"
                        elif "COLUMN" in current_layer or "أعمدة" in current_layer or "AXIS" in current_layer:
                            pt_type = "أعمدة (Columns)"
                        elif "BOUNDARY" in current_layer or "حدود" in current_layer or "PLOT" in current_layer:
                            pt_type = "حدود الأرض (Boundary)"
                        else:
                            pt_type = "نقاط عامة (General)"
                            
                        extracted_points.append([f"P_{len(extracted_points)+1}", x, y, z, pt_type])
                
                if extracted_points:
                    df_points = pd.DataFrame(extracted_points, columns=["Point_ID", "Easting_X", "Northing_Y", "Elevation_Z", "Type_النوع"])
                    st.success(f"✅ تم معالجة المخطط وفرز العناصر تلقائياً بنجاح!")
                else:
                    st.warning("⚠️ لم يتم العثور على نقاط مباشرة بالطبقات، يمكنك إدخال البيانات بالجدول وتصنيفها.")
            except Exception as e:
                st.error("❌ حدث خطأ أثناء معالجة ملف DXF.")

    # عرض الجداول المفروزة "كل شيء لحال"
    if not df_points.empty:
        st.markdown("---")
        st.markdown("## 📊 الفرز والتقسيم التلقائي للمخطط:")
        
        # الحصول على التصنيفات الفرعية الموجودة في الملف
        unique_types = df_points["Type_النوع"].unique()
        
        for p_type in unique_types:
            # فصل كل نوع في جدول منفصل تماماً
            type_df = df_points[df_points["Type_النوع"] == p_type]
            
            with st.expander(f"📂 {p_type} - عدد النقاط: ({len(type_df)})", expanded=True):
                # تنسيق الترتيب حسب جهاز الموقع المختار
                if device == "Leica":
                    final_df = type_df[["Point_ID", "Easting_X", "Northing_Y", "Elevation_Z"]]
                elif device in ["Topcon", "Sokkia"]:
                    final_df = type_df[["Point_ID", "Northing_Y", "Easting_X", "Elevation_Z"]]
                else:
                    final_df = type_df[["Point_ID", "Easting_X", "Northing_Y", "Elevation_Z"]]
                
                st.dataframe(final_df, use_container_width=True)
                
                # تحميل هذا الجزء المفروز لحاله ملف منفصل للجهاز
                csv_buffer = io.StringIO()
                final_df.to_csv(csv_buffer, index=False, header=False)
                st.download_button(
                    label=f"💾 تحميل جدول {p_type} فقط لجهاز {device}",
                    data=csv_buffer.getvalue(),
                    file_name=f"{p_type}_{device}.csv",
                    mime="text/csv",
                    key=f"btn_{p_type}"
                )
    else:
        st.info("💡 بانتظار رفع المخطط لتفجيره وفرز القواعد والأعمدة والحدود كلٌ على حدة.")

# ---------------------------------------------------------
# باقي الخيارات (كما هي للحفاظ على عمل السيرفر المستقر)
# ---------------------------------------------------------
elif option == "2. مطابقة الرفع الفعلي (As-Built)":
    st.header("🎯 فحص ومطابقة الرفع الفعلي (As-Built) وتحديد الانحرافات")
    sample_data = {"اسم النقطة": ["Column_1", "Column_2"], "X تصميمي": [234560.15, 234565.40], "Y تصميمي": [456780.20, 456785.60], "X موقع (فعلي)": [234560.17, 234565.45], "Y موقع (فعلي)": [456780.21, 456785.52]}
    input_df = st.data_editor(pd.DataFrame(sample_data), num_rows="dynamic", use_container_width=True)
    tolerance = st.slider("الحد المسموح (سم):", 1, 10, 3)
    if st.button("📊 ابدأ الفحص والمطابقة"):
        results = []
        for index, row in input_df.iterrows():
            try:
                dx = row["X موقع (فعلي)"] - row["X تصميمي"]
                dy = row["Y موقع (فعلي)"] - row["Y تصميمي"]
                dev_cm = math.sqrt(dx**2 + dy**2) * 100
                results.append({"النقطة": row["اسم النقطة"], "الفرق X (سم)": round(dx*100, 1), "الفرق Y (سم)": round(dy*100, 1), "الانحراف (سم)": round(dev_cm, 1), "القرار": "✅ مقبول" if dev_cm <= tolerance else "❌ مرفوض"})
            except: pass
        if results: st.dataframe(pd.DataFrame(results), use_container_width=True)

elif option == "3. حساب أعمال الحفر والدروب":
    st.header("🚜 حاسبة أعمال الحفر والدروب")
    l = st.number_input("الطول (متر):", value=20.0)
    w = st.number_input("العرض (متر):", value=20.0)
    d = st.number_input("العمق (متر):", value=3.0)
    swell = st.slider("معامل الانتفاش:", 1.10, 1.40, 1.25)
    cap = st.selectbox("حمولة الشاحنة (م³):", [16, 32, 45])
    price = st.number_input("تكلفة الدرب (KD):", value=15.0)
    if st.button("🧮 حساب الكميات"):
        vol = l * w * d
        act_vol = vol * swell
        trucks = math.ceil(act_vol / cap)
        st.metric("حجم الحفر الإجمالي", f"{vol:,.1f} م³")
        st.metric("عدد الدروب المطلوبة", f"{trucks} درب")
        st.metric("التكلفة التقديرية", f"{trucks * price:,.1f} KD")

elif option == "4. حاسب الخرسانة والأسعار":
    st.header("🧱 حاسبة مكعبات الخرسانة والأسعار")
    v = st.number_input("حجم الخرسانة الصافي (م³):", value=100.0)
    waste = st.slider("نسبة الهدر (%):", 0, 10, 3)
    p = st.number_input("سعر المتر (KD):", value=22.0)
    if st.button("💰 حساب الميزانية"):
        tot_v = v * (1 + (waste / 100))
        st.metric("الكمية شاملة الهدر", f"{tot_v:,.1f} م³")
        st.metric("الفاتورة المتوقعة", f"{tot_v * p:,.1f} KD")
