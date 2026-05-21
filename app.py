import streamlit as st
import ezdxf

st.title("🏗️ حاسب الكميات (الوضع الآمن)")

uploaded_file = st.file_uploader("ارفع ملف الـ DXF النظيف:", type=["dxf"])

if uploaded_file:
    try:
        doc = ezdxf.readfile(uploaded_file)
        msp = doc.modelspace()
        
        # قاموس لتجميع البيانات
        layers_data = {}
        
        # قراءة الأشكال الهندسية فقط وتجاهل البيانات الأخرى المسببة للأخطاء
        for entity in msp.query('LWPOLYLINE'):
            # استخدام getattr للتحقق من وجود 'layer' بدون التسبب في خطأ
            layer_name = getattr(entity.dxf, 'layer', 'Unknown')
            
            if layer_name not in layers_data:
                layers_data[layer_name] = 0
            layers_data[layer_name] += 1
            
        st.subheader("📊 تم العثور على العناصر التالية:")
        for layer, count in layers_data.items():
            st.write(f"✅ طبقة **{layer}**: تحتوي على {count} عنصر")
            
        st.success("تم مسح الملف بنجاح! إذا كانت الطبقات تظهر الآن، فالخطوة القادمة هي حساب الكميات.")

    except Exception as e:
        st.error(f"حدث خطأ: {e}. قد يكون الملف يحتاج إلى تنظيف إضافي في الأوتوكاد.")
