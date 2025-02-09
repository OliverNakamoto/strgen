import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import requests

# ---------------------------
# Helper Functions
# ---------------------------


def geocode_location(query):
    """
    Geocode a location name to latitude and longitude using Nominatim.
    """
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": query, "format": "json", "limit": 1}
    try:
        response = requests.get(
            url, params=params, headers={"User-Agent": "Streamlit-App"}
        )
        response.raise_for_status()  # Raise an error for bad status codes
        data = response.json()
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
        else:
            return None
    except requests.RequestException as e:
        st.error(f"Error during geocoding: {e}")
        return None


def reverse_geocode(lat, lon):
    """
    Reverse geocode latitude and longitude to a location name using Nominatim.
    """
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {
        "lat": lat,
        "lon": lon,
        "format": "json",
        "zoom": 10,  # Adjust zoom level to control detail (10 = city level)
        "addressdetails": 1,
    }
    try:
        response = requests.get(
            url, params=params, headers={"User-Agent": "Streamlit-App"}
        )
        response.raise_for_status()
        data = response.json()
        if "error" not in data:
            address = data.get("display_name", "Unknown location")
            return address
        else:
            return "Unknown location"
    except requests.RequestException as e:
        st.error(f"Error during reverse geocoding: {e}")
        return "Unknown location"


# ---------------------------
# Initialize Session State
# ---------------------------
if "markers" not in st.session_state:
    st.session_state["markers"] = []

if "map_center" not in st.session_state:
    # Default center (e.g., London)
    st.session_state["map_center"] = [51.505, -0.09]

# ---------------------------
# Streamlit App Layout
# ---------------------------
st.set_page_config(page_title="Interactive Map App", layout="wide")

# Custom CSS for better appearance
st.markdown(
    """
    <style>
    .main .block-container{
        padding-top: 1rem;
        padding-left: 2rem;
        padding-right: 2rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Title
st.title("🗺️ Interactive Map Application")

# Sidebar for Controls
st.sidebar.header("🔍 Search and Controls")

# Search Functionality
with st.sidebar:
    search_query = st.text_input("🔎 Search Location", "")
    if st.button("Search"):
        if search_query:
            location = geocode_location(search_query)
            if location:
                st.session_state["map_center"] = list(location)
                st.success(
                    f"Location found: {search_query} ({location[0]:.5f}, {location[1]:.5f})"
                )
            else:
                st.error("Location not found. Please try a different query.")
        else:
            st.warning("Please enter a location to search.")

    st.markdown("---")

    # Clear Markers Button
    if st.sidebar.button("🗑️ Clear All Markers"):
        st.session_state["markers"] = []
        st.success("All markers have been cleared.")

    st.markdown("---")

    # Generate File Button (Placeholder)
    if st.sidebar.button("📄 Generate File"):
        st.info("Generate File button clicked. Functionality to be implemented.")

# Main Layout: Map and Marker Table
map_col, table_col = st.columns([3, 1])

# ---------------------------
# Map Column
# ---------------------------
with map_col:
    st.subheader("📍 Click on the map to add markers")

    # Initialize Folium map
    m = folium.Map(
        location=st.session_state["map_center"], zoom_start=13, tiles="OpenStreetMap"
    )

    # Add existing markers to the map
    for idx, marker in enumerate(st.session_state["markers"]):
        folium.Marker(
            location=[marker["lat"], marker["lon"]],
            popup=folium.Popup(
                f"<b>Marker {idx + 1}</b><br>{marker['address']}<br>({marker['lat']:.5f}, {marker['lon']:.5f})",
                max_width=300,
            ),
            tooltip=marker["address"],
            icon=folium.Icon(color="blue", icon="info-sign"),
        ).add_to(m)

    # Display the map and capture click events
    map_response = st_folium(
        m, width="100%", height=600, returned_objects=["last_clicked"]
    )

    # If a new click is detected, add the marker
    if map_response and map_response.get("last_clicked"):
        clicked_location = map_response["last_clicked"]
        lat = clicked_location["lat"]
        lon = clicked_location["lng"]
        address = reverse_geocode(lat, lon)
        new_marker = {"lat": lat, "lon": lon, "address": address}
        st.session_state["markers"].append(new_marker)
        st.success(
            f"Added Marker {len(st.session_state['markers'])}: {address} ({lat:.5f}, {lon:.5f})"
        )

# ---------------------------
# Table Column
# ---------------------------
with table_col:
    st.subheader("📄 List of Markers")

    if st.session_state["markers"]:
        # Create a DataFrame from markers
        df = pd.DataFrame(st.session_state["markers"])
        # Ensure correct column order and naming
        df = df[["address", "lat", "lon"]]
        df.columns = ["Location", "Latitude", "Longitude"]
        df.index += 1  # Start index at 1 for readability

        # Display the table
        st.table(df)

        st.markdown("### 📤 Export Coordinates")

        # Download as CSV Button
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download as CSV",
            data=csv,
            file_name="markers.csv",
            mime="text/csv",
        )

        # Show JSON Coordinates Button
        json_button = st.button("📄 Show JSON Coordinates")
        if json_button:
            st.json(df.to_dict(orient="records"))
    else:
        st.info("No markers added yet. Click on the map to add markers.")

# ---------------------------
# Footer
# ---------------------------
st.markdown("---")
st.markdown("© 2024 Interactive Map App | Built with ❤️ using Streamlit and Folium")
