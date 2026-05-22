import streamlit as st
import ezdxf
import io # استيراد مكتبة التعامل مع الذاكرة

# ... (باقي الكود) ...

if uploaded_file:
    try:
        # الحل: قراءة الملف كبايتات من الذاكرة
        bytes_data = uploaded_file.getvalue()
        # استخدام stream لقراءة البيانات
        doc = ezdxf.read(io.BytesIO(bytes_data)) 
        msp = doc.modelspace()
        
        # ... (باقي الكود كما هو) ...
