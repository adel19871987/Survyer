import streamlit as st
import ezdxf

st.title("🏗️ حاسب كميات الفيلا (3 أدوار)")

# تحميل الملف
uploaded_file = st.file_uploader("تم تحميل ملف الفيلا، اضغط هنا للمسح:", type=["dxf"])

if uploaded_file:
    try:
        doc = ezdxf.readfile(uploaded_file)
        msp = doc.modelspace()
        
        # حصر العناصر حسب الطبقات (Layers)
        layers_count = {}
        for entity in msp:
            layer_name = entity.dxf.layer
            layers_count[layer_name] = layers_count.get(layer_name, 0) + 1
            
        st.subheader("📊 العناصر الموجودة في المخطط:")
        for layer, count in layers_count.items():
            if count > 5: # إظهار الطبقات الرئيسية فقط لتجنب الزحمة
                st.write(f"🔹 الطبقة: **{layer}** | عدد العناصر: {count}")
        
        st.success("✅ تم مسح المخطط بنجاح! الآن يمكنك تحديد الطبقة التي تريد حساب تكعيبها.")
        
    except Exception as e:
        st.error(f"حدث خطأ أثناء قراءة المخطط: {e}")
