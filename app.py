import streamlit as st
import pandas as pd
import tempfile
import os
import ezdxf
from shapely.geometry import Polygon

st.set_page_config(page_title="Survey Tool", layout="wide", page_icon="📐")
st.title("📐 Survey Tool v4.5 - Select & Export Points")

if 'elements' not in st.session_state:
    st.session_state.elements = {}
if 'selected_points' not in st.session_state:
    st.session_state.selected_points = pd.DataFrame()

# Map layer names to engineering elements
ELEMENT_MAP = {
    'COLUMN': 'Column', 'COL': 'Column', 'COLUMNS': 'Column',
    'BEAM': 'Beam', 'BEAMS': 'Beam', 'GIRDER': 'Beam',
    'FOOTING': 'Footing', 'FOOT': 'Footing', 'FOUNDATION': 'Footing',
    'SLAB': 'Slab', 'WALL': 'Wall',
    'STAIR': 'Stair', 'STAIRS': 'Stair',
    'LIFT': 'Lift', 'ELEVATOR': 'Lift',
    'PILE': 'Pile', 'PILES': 'Pile',
    'BOUNDARY': 'Boundary', 'BUILDING': 'Building'
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
            layer = entity.dxf.layer
            element = get_element_name(layer)

            if element not in elements_data:
                elements_data[element] = []

            if entity.dxftype() in ['POINT', 'LWPOLYLINE', 'POLYLINE']:
                pts = [entity.dxf.location] if entity.dxftype() == 'POINT' else entity.get_points()
                for pt in pts:
                    elements_data[element].append({
                        'Select': False,
                        'Point_ID': f"{element[:3].upper()}-{len(elements_data[element])+1:03d}",
                        'Element': element,
                        'Layer': layer,
                        'Easting': pt[0],
                        'Northing': pt[1],
                        'Elevation': pt[2] if len(pt) > 2 else 0.0
                    })

        for name in elements_data:
            elements_data[name] = pd.DataFrame(elements_data[name])

        return elements_data
    except Exception as e:
        st.error(f"Failed to read DXF: {e}")
        return None
    finally:
        os.unlink(tmp_path)

tab1, tab2, tab3, tab4 = st.tabs(["Upload & Split", "Select Points", "Calculations", "Export"])

with tab1:
    uploaded = st.file_uploader("Upload DXF File", type=['dxf'])
    if uploaded:
        with st.spinner("Splitting elements..."):
            elements = parse_dxf_elements(uploaded)
            if elements:
                st.session_state.elements = elements
                st.session_state.selected_points = pd.DataFrame()
                st.success(f"Split into {len(elements)} elements")

    if st.session_state.elements:
        for element_name, df in st.session_state.elements.items():
            with st.expander(f"📍 {element_name} - {len(df)} points", expanded=False):
                st.dataframe(df[['Point_ID','Element','Layer','Easting','Northing','Elevation']].head(20),
                             use_container_width=True)

with tab2:
    if st.session_state.elements:
        st.subheader("Select Points to Export")
        st.info("Tick the 'Select' checkbox for points you want to export")

        selected_elements = st.multiselect(
            "Choose Elements to Show",
            list(st.session_state.elements.keys()),
            default=list(st.session_state.elements.keys())[:3]
        )

        all_selected = []
        for elem in selected_elements:
            df = st.session_state.elements[elem].copy()

            st.write(f"**{elem}** - {len(df)} points")
            edited_df = st.data_editor(
                df,
                column_config={
                    "Select": st.column_config.CheckboxColumn("Select", help="Tick to include"),
                    "Point_ID": st.column_config.TextColumn("Point ID", disabled=True),
                    "Element": st.column_config.TextColumn("Element", disabled=True),
                    "Layer": st.column_config.TextColumn("Layer", disabled=True),
                    "Easting": st.column_config.NumberColumn("Easting", format="%.3f", disabled=True),
                    "Northing": st.column_config.NumberColumn("Northing", format="%.3f", disabled=True),
                    "Elevation": st.column_config.NumberColumn("Elevation", format="%.3f", disabled=True)
                },
                use_container_width=True,
                hide_index=True,
                key=f"editor_{elem}"
            )

            selected_rows = edited_df[edited_df['Select'] == True]
            if not selected_rows.empty:
                all_selected.append(selected_rows.drop(columns=['Select']))

        if all_selected:
            st.session_state.selected_points = pd.concat(all_selected, ignore_index=True)
            st.success(f"✅ Selected {len(st.session_state.selected_points)} points total")
            st.dataframe(st.session_state.selected_points,
                         use_container_width=True, hide_index=True)
        else:
            st.session_state.selected_points = pd.DataFrame()
            st.warning("No points selected yet")

with tab3:
    if not st.session_state.selected_points.empty:
        df = st.session_state.selected_points
        st.write(f"**Calculating on {len(df)} selected points**")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Calculate Area"):
                try:
                    coords = list(zip(df['Easting'], df['Northing']))
                    if len(coords) >= 3:
                        poly = Polygon(coords)
                        area = poly.area
                        st.metric("Area", f"{area:.2f} m²")
                    else:
                        st.error("Need at least 3 points for area")
                except Exception as e:
                    st.error(f"Error: {e}")

        with col2:
            design_level = st.number_input("Design Level", value=0.0, step=0.1, format="%.3f")
            if st.button("Calculate Cut & Fill"):
                df_calc = df.copy()
                df_calc['Cut_Fill'] = design_level - df_calc['Elevation']
                cut = df_calc[df_calc['Cut_Fill'] > 0]['Cut_Fill'].sum()
                fill = df_calc[df_calc['Cut_Fill'] < 0]['Cut_Fill'].abs().sum()
                st.metric("Cut", f"{cut:.2f} m³")
                st.metric("Fill", f"{fill:.2f} m³")
    else:
        st.warning("Go to 'Select Points' tab and choose points first")

with tab4:
    if not st.session_state.selected_points.empty:
        st.subheader("Export Selected Points")

        csv_all = st.session_state.selected_points.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Download All Selected Points",
            csv_all,
            "Selected_Points.csv",
            "text/csv",
            use_container_width=True
        )

        if st.checkbox("Export each element separately"):
            for elem in st.session_state.selected_points['Element'].unique():
                df_elem = st.session_state.selected_points[st.session_state.selected_points['Element'] == elem]
                csv_elem = df_elem.to_csv(index=False).encode('utf-8')
                st.download_button(
                    f"📥 Download {elem} ({len(df_elem)} pts)",
                    csv_elem,
                    f"{elem}.csv",
                    "text/csv",
                    use_container_width=True
                )
    else:
        st.warning("No points selected yet")

st.caption("v4.5 - Select any points you want and export for Sokkia, Leica, Trimble")
