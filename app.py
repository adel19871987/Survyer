import streamlit as st
import pandas as pd
import tempfile
import os
import ezdxf
from shapely.geometry import Polygon

st.set_page_config(page_title="أداة المساحة", layout="wide", page_icon="📐")

# تفعيل العربية RTL
st.markdown("""
<style>
   .stApp {direction: rtl;}
   .st-emotion-cache-1y4p8pa {direction: rtl;}
</style>
""", unsafe_allow_html=True)

st.title("📐 أداة المساحة v4.7 - عربي")

if 'elements' not in st.session_state:
    st.session_state.elements = {}
if 'selected_points' not in st.session_state:
    st.session_state.selected_points = pd.DataFrame()

# خريطة تحويل أسماء الـ Layers للعناصر الإنشائية
ELEMENT_MAP = {
    'COLUMN': 'عمود', 'COL': 'عمود', 'COLUMNS': 'عمود',
    'BEAM': 'جسر', 'BEAMS': 'جسر', 'GIRDER': 'جسر',
    'FOOTING': 'قاعدة', 'FOOT': 'قاعدة', 'FOUNDATION': 'قاعدة',
    'SLAB': 'بلاطة', 'WALL': 'جدار',
    'STAIR': 'درج', 'STAIRS': 'درج',
    'LIFT': 'مصعد', 'ELEVATOR': 'مصعد',
    'PILE': 'خازوق', 'PILES': 'خازوق'
}

def get_element_name(layer_name):
    lname = layer_name.upper()
    for key, value in ELEMENT_MAP.items():
        if key in lname:
            return value
    return layer_name

def parse_dxf_elements(uploaded_file):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name
    try:
        doc = ezdxf.readfile(tmp_path)
        msp = doc.modelspace()
        elements_data = {}

        for entity in msp:
            if not hasattr(entity.dxf, 'layer'):
                continue

            layer = entity.dxf.layer
            element = get_element_name(layer)

            if element not in elements_data:
                elements_data[element] = []

            if entity.dxftype() in ['POINT', 'LWPOLYLINE', 'POLYLINE']:
                try:
                    pts = [entity.dxf.location] if entity.dxftype() == 'POINT' else entity.get_points()
                    for pt in pts:
                        elements_data[element].append({
                            'اختيار': False,
                            'رقم النقطة': f"{element[:2]}-{len(elements_data[element])+1:03d}",
                            'العنصر': element,
                            'الطبقة': layer,
                            'الإحداثي الشرقي': float(pt[0]),
                            'الإحداثي الشمالي': float(pt[1]),
                            'المنسوب': float(pt[2]) if len(pt) > 2 else 0.0
                        })
                except:
                    continue

        for name in elements_data:
            elements_data[name] = pd.DataFrame(elements_data[name])

        elements_data = {k: v for k, v in elements_data.items() if not v.empty}
        return elements_data
    except Exception as e:
        st.error(f"فشل قراءة ملف DXF: {e}")
        return None
    finally:
        os.unlink(tmp_path)

tab1, tab2, tab3, tab4 = st.tabs(["رفع وفصل", "اختيار النقاط", "الحسابات", "التصدير"])

with tab1:
    uploaded = st.file_uploader("ارفع ملف DXF", type=['dxf'])
    if uploaded:
        with st.spinner("جاري فصل العناصر..."):
            elements = parse_dxf_elements(uploaded)
            if elements:
                st.session_state.elements = elements
                st.session_state.selected_points = pd.DataFrame()
                total_points = sum(len(df) for df in elements.values())
                st.success(f"تم العثور على {len(elements)} عنصر يحتوي على {total_points} نقطة")
            else:
                st.error("لم يتم العثور على كيانات صالحة في ملف DXF")

    if st.session_state.elements:
        for element_name, df in st.session_state.elements.items():
            with st.expander(f"📍 {element_name} - {len(df)} نقطة", expanded=False):
                cols_to_show = ['رقم النقطة','العنصر','الطبقة','الإحداثي الشرقي','الإحداثي الشمالي','المنسوب']
                cols_exist = [c for c in cols_to_show if c in df.columns]
                if cols_exist:
                    st.dataframe(df[cols_exist].head(20), use_container_width=True, hide_index=True)

with tab2:
    if st.session_state.elements:
        st.subheader("اختر النقاط للتصدير")
        st.info("ضع علامة صح على خانة 'اختيار' للنقاط التي تريد تصديرها")

        selected_elements = st.multiselect(
            "اختر العناصر للعرض",
            list(st.session_state.elements.keys()),
            default=list(st.session_state.elements.keys())[:3] if len(st.session_state.elements) >= 3 else list(st.session_state.elements.keys())
        )

        all_selected = []
        for elem in selected_elements:
            df = st.session_state.elements[elem].copy()

            if df.empty:
                continue

            st.write(f"**{elem}** - {len(df)} نقطة")
            edited_df = st.data_editor(
                df,
                column_config={
                    "اختيار": st.column_config.CheckboxColumn("اختيار"),
                    "رقم النقطة": st.column_config.TextColumn("رقم النقطة", disabled=True),
                    "العنصر": st.column_config.TextColumn("العنصر", disabled=True),
                    "الطبقة": st.column_config.TextColumn("الطبقة", disabled=True),
                    "الإحداثي الشرقي": st.column_config.NumberColumn("الإحداثي الشرقي", format="%.3f", disabled=True),
                    "الإحداثي الشمالي": st.column_config.NumberColumn("الإحداثي الشمالي", format="%.3f", disabled=True),
                    "المنسوب": st.column_config.NumberColumn("المنسوب", format="%.3f", disabled=True)
                },
                use_container_width=True,
                hide_index=True,
                key=f"editor_{elem}"
            )

            selected_rows = edited_df[edited_df['اختيار'] == True]
            if not selected_rows.empty:
                all_selected.append(selected_rows.drop(columns=['اختيار']))

        if all_selected:
            st.session_state.selected_points = pd.concat(all_selected, ignore_index=True)
            st.success(f"✅ تم اختيار {len(st.session_state.selected_points)} نقطة")
            if not st.session_state.selected_points.empty:
                st.dataframe(st.session_state.selected_points, use_container_width=True, hide_index=True)
        else:
            st.session_state.selected_points = pd.DataFrame()
            st.warning("لم يتم اختيار أي نقطة بعد")

with tab3:
    if not st.session_state.selected_points.empty:
        df = st.session_state.selected_points
        st.write(f"**الحساب على {len(df)} نقطة مختارة**")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("حساب المساحة"):
                try:
                    coords = list(zip(df['الإحداثي الشرقي'], df['الإحداثي الشمالي']))
                    if len(coords) >= 3:
                        poly = Polygon(coords)
                        area = poly.area
                        st.metric("المساحة", f"{area:.2f} م²")
                    else:
                        st.error("تحتاج 3 نقاط على الأقل لحساب المساحة")
                except Exception as e:
                    st.error(f"خطأ: {e}")

        with col2:
            design_level = st.number_input("منسوب التصميم", value=0.0, step=0.1, format="%.3f")
            if st.button("حساب الحفر والردم"):
                df_calc = df.copy()
                df_calc['حفر_ردم'] = design_level - df_calc['المنسوب']
                cut = df_calc[df_calc['حفر_ردم'] > 0]['حفر_ردم'].sum()
                fill = df_calc[df_calc['حفر_ردم'] < 0]['حفر_ردم'].abs().sum()
                st.metric("الحفر", f"{cut:.2f} م³")
                st.metric("الردم", f"{fill:.2f} م³")
    else:
        st.warning("اذهب لتبويب 'اختيار النقاط' واختر النقاط أولاً")

with tab4:
    if not st.session_state.selected_points.empty:
        st.subheader("تصدير النقاط المختارة")
        csv_all = st.session_state.selected_points.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            "📥 تحميل جميع النقاط المختارة",
            csv_all,
            "النقاط_المختارة.csv",
            "text/csv",
            use_container_width=True
        )

        if st.checkbox("تصدير كل عنصر بملف منفصل"):
            for elem in st.session_state.selected_points['العنصر'].unique():
                df_elem = st.session_state.selected_points[st.session_state.selected_points['العنصر'] == elem]
                csv_elem = df_elem.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    f"📥 تحميل {elem} ({len(df_elem)} نقطة)",
                    csv_elem,
                    f"{elem}.csv",
                    "text/csv",
                    use_container_width=True
                )
    else:
        st.warning("لم يتم اختيار أي نقاط بعد")

st.caption("v4.7 - التطبيق بالعربي. يدعم التصدير لـ Sokkia, Leica, Trimble")
