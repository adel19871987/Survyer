import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
from shapely.geometry import Polygon
from fpdf import FPDF
import tempfile
import os
import geopandas as gpd

st.set_page_config(page_title="مساحي مصغر", layout="wide", page_icon="📐")
st.title("📐 مساحي مصغر - أدواتك بالموقع")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["رفع النقاط", "الحسابات", "BM & الرفع", "التصدير", "التقرير PDF"])

if 'df' not in st.session_state:
    st.session_state.df = None
if 'bm_points' not in st.session_state:
    st.session_state.bm_points = None

with tab1:
    uploaded = st.file_uploader("ارفع ملف النقاط CSV, KML, GeoJSON", type=['csv','kml','geojson','json'])
    
    if uploaded:
        if uploaded.name.endswith('.csv'):
            df = pd.read_csv(uploaded)
            df.columns = [c.strip() for c in df.columns]
        else:
            gdf = gpd.read_file(uploaded)
            df = pd.DataFrame({
                'Point': [f"P{i+1}" for i in range(len(gdf))],
                'Easting': gdf.geometry.x,
                'Northing': gdf.geometry.y,
                'Elevation': 0
            })
        
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
        st.dataframe(df.head(20), use_container_width=True)
        
        m = folium.Map(location=[df['Northing'].mean(), df['Easting'].mean()], zoom_start=15)
        for _, row in df.iterrows():
            folium.CircleMarker([row['Northing'], row['Easting']], radius=3, popup=row['Point']).add_to(m)
        st_folium(m, width=700, height=400)

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
                except:
                    st.error("النقاط لازم تكون مغلقة ومرتبة")
        
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
st.caption("مساحي مصغر v3.0 | 2026")
