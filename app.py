import streamlit as st
import pandas as pd
import numpy as np
from shapely.geometry import Polygon
from fpdf import FPDF
import tempfile
import os
import ezdxf

st.set_page_config(page_title="مساحي مصغر", layout="wide", page_icon="📐")
st.title("📐 مساحي مصغر - مفصول بالأدوار")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["رفع النقاط", "الحسابات", "BM & الرفع", "التصدير", "التقرير PDF"])

if 'floors' not in st.session_state:
    st.session_state.floors = {}

def parse_dxf_with_layers(uploaded_file):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name

    try:
        try:
            from ezdxf.recovery import recover
            doc, auditor = recover.readfile(tmp_path)
        except ImportError:
            doc = ezdxf.readfile(tmp_path)

        msp = doc.modelspace()
        layers_data = {}

        for entity in msp:
            layer = entity.dxf.layer
            if layer not in layers_data:
                layers_data[layer] = []

            if entity.dxftype() == 'POINT':
                layers_data[layer].append({
                    'Point': f"P{len(layers_data[layer])+1}",
                    'Easting': entity.dxf.location.x,
                    'Northing': entity.dxf.location.y,
                    'Elevation': entity.dxf.location.z
                })
            elif entity.dxftype() in ['LWPOLYLINE', 'POLYLINE']:
                for i, pt in enumerate(entity.get_points()):
                    layers_data[layer].append({
                        'Point': f"PL{len(layers_data[layer])+1}",
                        'Easting': pt[0],
                        'Northing': pt[1],
                        'Elevation': pt[2] if len(pt) > 2 else 0
                    })

        # حول كل Layer لـ DataFrame
        for layer in layers_data:
            if layers_data[layer]:
                layers_data[layer] = pd.DataFrame(layers_data[layer])

        return layers_data

    except Exception as e:
        st.error(f"فشل قراءة ملف DXF: {e}")
        return None
    finally:
        os.unlink(tmp_path)

with tab1:
    uploaded = st.file_uploader("ارفع ملف النقاط CSV أو DXF", type=['csv','dxf'])

    if uploaded:
        with st.spinner("جاري فصل الأدوار..."):
            if uploaded.name.endswith('.csv'):
                df = pd.read_csv(uploaded)
                st.session_state.floors = {'ALL': df}
            elif uploaded.name.endswith('.dxf'):
                layers_data = parse_dxf_with_layers(uploaded)
                if layers_data:
                    st.session_state.floors = layers_data

        if st.session_state.floors:
            st.success(f"تم فصل الملف إلى {len(st.session_state.floors)} Layer")

            # عرض كل دور بجدول منفصل
            for layer_name, df in st.session_state.floors.items():
                with st.expander(f"📍 {layer_name} - {len(df)} نقطة", expanded=False):
                    st.dataframe(df.head(20), use_container_width=True)

                    # تخمين اسم الدور
                    floor_name = layer_name
                    if 'GROUND' in layer_name.upper() or 'GF' in layer_name.upper():
                        floor_name = "الدور الأرضي"
                    elif 'FIRST' in layer_name.upper() or 'F1' in layer_name.upper():
                        floor_name = "الدور الأول"
                    elif 'SECOND' in layer_name.upper() or 'F2' in layer_name.upper():
                        floor_name = "الدور الثاني"

                    st.info(f"الاسم المقترح: {floor_name}")

with tab2:
    if st.session_state.floors:
        st.subheader("اختر الدور للحساب")

        selected_floor = st.selectbox("الدور", list(st.session_state.floors.keys()))
        df = st.session_state.floors[selected_floor]

        st.write(f"تحسب على: **{selected_floor}** - {len(df)} نقطة")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("حساب المساحة"):
                try:
                    coords = list(zip(df['Easting'], df['Northing']))
                    poly = Polygon(coords)
                    area_m2 = poly.area
                    st.session_state.area = area_m2
                    st.metric("المساحة", f"{area_m2:.2f} م²", f"{area_m2/1000:.3f} دونم")
                except Exception as e:
                    st.error(f"النقاط لازم تكون مغلقة ومرتبة: {e}")

        with col2:
            design_level = st.number_input("منسوب التصميم", value=0.0)
            if st.button("احسب الكميات"):
                df['Cut_Fill'] = design_level - df['Elevation']
                cut_vol = df[df['Cut_Fill'] > 0]['Cut_Fill'].sum()
                fill_vol = df[df['Cut_Fill'] < 0]['Cut_Fill'].abs().sum()
                st.metric("الحفر", f"{cut_vol:.2f} م³")
                st.metric("الردم", f"{fill_vol:.2f} م³")
    else:
        st.warning("ارفع الملف أول من تبويب رفع النقاط")

with tab3:
    st.info("اختر الدور الأرضي من تبويب الحسابات عشان تطلع لك BM حقته")
    if 'floors' in st.session_state and st.session_state.floors:
        for layer_name in st.session_state.floors.keys():
            if 'GROUND' in layer_name.upper() or 'GF' in layer_name.upper():
                df = st.session_state.floors[layer_name]
                minx, maxx = df['Easting'].min(), df['Easting'].max()
                miny, maxy = df['Northing'].min(), df['Northing'].max()
                bm_points = pd.DataFrame({
                    'Point': ['BM-01','BM-02','BM-03','BM-04'],
                    'Easting': [minx, maxx, maxx, minx],
                    'Northing': [maxy, maxy, miny, miny],
                    'Elevation': 0,
                    'Note': ['NW','NE','SE','SW']
                })
                st.subheader(f"BM للدور الأرضي: {layer_name}")
                st.dataframe(bm_points, use_container_width=True)
                break

with tab4:
    if st.session_state.floors:
        for layer_name, df in st.session_state.floors.items():
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(f"تحميل {layer_name}.csv", csv, f"{layer_name}.csv", "text/csv")

with tab5:
    st.subheader("تصدير تقرير PDF")
    if st.session_state.floors:
        project_name = st.text_input("اسم المشروع", "مشروع الفيلا")

        if st.button("إنشاء التقرير"):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 10, txt=f"تقرير: {project_name}", ln=True, align='C')

            for layer_name, df in st.session_state.floors.items():
                pdf.cell(200, 10, txt=f"{layer_name}: {len(df)} نقطة", ln=True)

            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                pdf.output(tmp.name)
                with open(tmp.name, "rb") as f:
                    st.download_button("تحميل التقرير PDF", f, "Survey_Report.pdf", "application/pdf")
                os.unlink(tmp.name)

st.caption("مساحي مصغر v4.0 - فصل تلقائي للأدوار | 2026")
