import streamlit as st
import ezdxf
import pandas as pd
import io

# إعداد واجهة البرنامج
st.set_page_config(page_title="المساح الذكي المحترف", layout="wide")
st.title("🏗️ نظام المساحة والحصر الآلي (Universal Surveyor)")

# قائمة جانبية للإعدادات
st.sidebar.header("⚙️ إعدادات العمل")
device_type = st.sidebar.selectbox("اختر نوع جهازك:", ["Leica (GSI/CSV)", "Topcon (CSV/TXT)", "Sokkia (SDR/CSV)", "Generic (X,Y,Z)"])
height = st.sidebar.number_input("ارتفاع الخرسانة (متر):", value=0.6, step=0.05)

# رفع الملف
uploaded_file = st.file_uploader("ارفع مخطط الـ DXF هنا:", type=["dxf"])

if uploaded_file:
    try:
        doc = ezdxf.readfile(uploaded_file)
        msp = doc.modelspace()
        
        # استخراج البيانات
        points_list = []
        for entity in msp.query('LWPOLYLINE'):
            layer = entity.dxf.layer
            for i, vertex in enumerate(entity.get_points()):
                points_list.append({
                    "Point_ID": f"{layer}_{i}",
                    "North_Y": round(vertex[1], 4),
                    "East_X": round(vertex[0], 4),
                    "Elevation_Z": 0.0,
                    "Layer": layer,
                    "Area": round(entity.area, 2)
                })
        
        if points_list:
            df = pd.DataFrame(points_list)
            
            # 1. الترتيب الذكي للمسار (لتقليل الحركة في الموقع)
            df = df.sort_values(by=["North_Y", "East_X"])
            
            # 2. عرض جدول الكميات
            st.subheader("📊 ملخص الكميات التقديري:")
            summary = df.groupby("Layer").agg({"Area": "max", "Point_ID": "count"})
            summary["حجم الخرسانة (م³)"] = summary["Area"] * height
            st.table(summary)
            
            # 3. تجهيز ملف التوقيع للأجهزة
            st.subheader("🛰️ ملف التوقيع المساحي:")
            
            # تنسيق الملف حسب الجهاز
            if device_type == "Topcon (CSV/TXT)":
                # تنسيق توبكون (N, E, Z, Code)
                final_df = df[["North_Y", "East_X", "Elevation_Z", "Point_ID"]]
                csv_data = final_df.to_csv(index=False, header=False, sep=' ')
            else:
                # تنسيق عام (ID, Y, X, Z)
                final_df = df[["Point_ID", "North_Y", "East_X", "Elevation_Z"]]
                csv_data = final_df.to_csv(index=False, header=False)
            
            st.download_button(
                label=f"📥 تحميل ملف التوقيع لـ {device_type}",
                data=csv_data,
                file_name="Stakeout_Points.csv",
                mime="text/csv"
            )
            
            st.success("✅ تم التحليل بنجاح! الملف جاهز لجهاز التوتال ستيشن.")
            
        else:
            st.warning("⚠️ لم يتم العثور على أشكال هندسية في الملف.")
            
    except Exception as e:
        st.error(f"حدث خطأ في قراءة الملف: {e}")

# صورة توضيحية لعملية التوقيع المساحي
st.write("---")
st.write("💡 **نصيحة:** عند استيراد الملف في جهاز التوتال ستيشن، تأكد من اختيار الترتيب (N, E, Z).")
