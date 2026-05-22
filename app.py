import streamlit as st
import pandas as pd
import numpy as np
from shapely.geometry import Polygon
from fpdf import FPDF
import tempfile
import os
import ezdxf

st.set_page_config(page_title="مساحي مصغر", layout="wide", page_icon="📐")
st.title("📐 مساحي مصغر - أدواتك بالموقع")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["رفع النقاط", "الحسابات", "BM & الرفع", "التصدير", "التقرير PDF"])

if 'df' not in st.session_state:
    st.session_state.df = None
if 'bm_points' not in st.session_state:
    st.session_state.bm_points = None

def parse_dxf(uploaded_file):
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
        points = []

        for entity in msp:
            if entity.dxftype() == 'POINT':
                points.append({
                    'Point': f"P{len(points)+1}",
                    'Easting': entity.dxf.location.x,
                    'Northing': entity.dxf.location.y,
                    'Elevation': entity.dxf.location.z
                })
            elif entity.dxftype() == 'TEXT':
                points.append({
                    'Point': entity.dxf.text,
                    'Easting': entity.dxf.insert.x,
                    'Northing': entity.dxf.insert.y,
                    'Elevation': entity.dxf.insert.z
                })
            elif entity.dxftype() in ['LWPOLYLINE', 'POLYLINE']:
                for i, pt in enumerate(entity.get_points()):
                    points.append({
                        'Point': f"PL{len(points)+1}",
                        'Easting': pt[0],
                        'Northing': pt[1],
                        'Elevation': pt[2] if len(pt) > 2 else 0
                    })

        if not points:
            return None
        return pd.DataFrame(points)

    except Exception as e:
        st.error(f"فشل قراءة ملف DXF: {e}")
        return None
    finally:
        os.unlink(tmp_path)

def normalize_columns(df):
    df.columns = [c.strip().lower() for c in df.columns]
    col_map = {}
    for col in df.columns:
        if col in ['easting', 'e', 'x', 'east']:
            col_map[col] = 'Easting'
        elif col in ['northing', 'n', 'y', 'north']:
            col_map[col] = 'Northing'
        elif col in ['elevation', 'z', 'elev', 'level']:
            col_map[col] = 'Elevation'
        elif col in ['point', 'name', 'id', 'pt']:
            col_map[col] = 'Point'
    df = df.rename(columns=col_map)

    if 'Point' not in df.columns:
        df['Point'] = [f"P{i+1}" for i in range(len(df))]
    if 'Elevation' not in df.columns:
        df['Elevation'] = 0
    return df

with tab1:
    uploaded = st.file_uploader("ارفع ملف النقاط CSV أو DXF", type=['csv','dxf'])

    if uploaded:
        with st.spinner("جاري قراءة الملف..."):
            if uploaded.name.endswith('.csv'):
                df = pd.read_csv(uploaded)
                df = normalize_columns(df)
            elif uploaded.name.endswith('.dxf'):
                df = parse_dxf(uploaded)
                if df is None:
                    st.stop()

        if df is None or df.empty:
            st.error("الملف فاضي أو ما فيه نقاط")
            st.stop()

        if 'Easting' not in df.columns or 'Northing' not in df.columns:
            st.error("الملف لازم يحتوي على أعمدة Easting/X و Northing/Y")
            st.stop()

        st.session_state.df = df

        # توليد BM تلقائي
        minx, maxx = df['Easting'].min(), df['Easting'].max()
        miny, maxy = df['Northing'].min(), df['Northing'].max()
        bm_points = pd.DataFrame({
            'Point': ['BM-01','BM-02','BM-03','BM-04','BM-05','BM-06'],
            'Easting': [minx, (minx+maxx)/2, maxx, maxx, (minx+maxx)/2, minx],
            'Northing': [maxy, maxy, maxy, miny, miny, miny],
            'Elevation': 0,
            'Note': ['NW','N Mid','NE','SE','S Mid','SW']
        })
        st.session_state.bm_points = bm_points

        st.success(f"تم رفع {len(df)} نقطة")
        st.dataframe(df.head(50), use_container_width=True)
        st.info("شلت الخريطة عشان التطبيق يكون أسرع. البيانات كلها بالجدول فوق.")

with tab2:
    if st.session_state.df is not None:
        df = st.session_state.df
        st.subheader("حسابات المساحة والكميات")

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
                st.session_state.cut_vol = cut_vol
                st.session_state.fill_vol = fill_vol
                st.metric("الحفر", f"{cut_vol:.2f} م³")
                st.metric("الردم", f"{fill_vol:.2f} م³")
    else:
        st.warning("ارفع الملف أول من تبويب رفع النقاط")

with tab3:
    if st.session_state.bm_points is not None:
        st.subheader("نقاط BM")
        st.dataframe(st.session_state.bm_points, use_container_width=True)
        st.subheader("خطة الرفع")
        st.write("1. نصب الجهاز على BM-01")
        st.write("2. اربط Backsight على BM-02")
        st.write("3. ابدأ الرفع من النقطة P1")
    else:
        st.warning("ارفع الملف أول")

with tab4:
    if st.session_state.df is not None:
        csv_all = st.session_state.df.to_csv(index=False).encode('utf-8')
        st.download_button("تحميل كل النقاط.csv", csv_all, "All_Points.csv", "text/csv")

        csv_bm = st.session_state.bm_points.to_csv(index=False).encode('utf-8')
        st.download_button("تحميل BM_Points.csv", csv_bm, "BM_Points.csv", "text/csv")

        st.info("الملفات بصيغة CSV وتشتغل على Sokkia, Leica, Trimble")
    else:
        st.warning("ارفع الملف أول")

with tab5:
    st.subheader("تصدير تقرير الموقع PDF")

    if st.session_state.df is not None:
        project_name = st.text_input("اسم المشروع", "مشروع الموقع")
        contractor = st.text_input("اسم المقاول", "اسمك")

        if st.button("إنشاء التقرير"):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)

            pdf.cell(200, 10, txt="تقرير مساحي ميداني", ln=True, align='C')
            pdf.ln(10)
            pdf.cell(200, 10, txt=f"المشروع: {project_name}", ln=True)
            pdf.cell(200, 10, txt=f"المقاول: {contractor}", ln=True)
            pdf.cell(200, 10, txt=f"عدد النقاط: {len(st.session_state.df)}", ln=True)

            if 'area' in st.session_state:
                pdf.cell(200, 10, txt=f"المساحة: {st.session_state.area:.2f} م²", ln=True)
            if 'cut_vol' in st.session_state:
                pdf.cell(200, 10, txt=f"الحفر: {st.session_state.cut_vol:.2f} م³", ln=True)
                pdf.cell(200, 10, txt=f"الردم: {st.session_state.fill_vol:.2f} م³", ln=True)

            pdf.ln(10)
            pdf.cell(200, 10, txt="جدول النقاط:", ln=True)

            for i, row in st.session_state.df.head(20).iterrows():
                pdf.cell(200, 8, txt=f"{row['Point']}: E={row['Easting']:.3f}, N={row['Northing']:.3f}", ln=True)

            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                pdf.output(tmp.name)
                with open(tmp.name, "rb") as f:
                    st.download_button("تحميل التقرير PDF", f, "Survey_Report.pdf", "application/pdf")
                os.unlink(tmp.name)
    else:
        st.warning("ارفع الملف أول")

st.markdown("---")
st.caption("مساحي مصغر v3.9 خفيف | 2026")
