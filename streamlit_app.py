from ast import literal_eval
import requests

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium

import streamlit as st
from streamlit_autorefresh import st_autorefresh

# Function to convert payload string into a dict
def parse_payload(payload):
    parts = payload.split('/')
    result = {}
    for part in parts:
        if ':' in part:
            key, value = part.split(':', 1)
            result[key.strip()] = value.strip()
        else:
            result['status'] = part.strip()
    return result

# Auto-refresh every 10 seconds
st_autorefresh(interval=10_000, key="api_refresh")

api_query = "https://beta.owldms.com/owl/api/userdata/getrawdata?start=1746153056&end=1846100000&papaId=UCONPAPA"

token_header = {
    'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1bmlxdWVfbmFtZSI6IjkyNSIsIm5iZiI6MTc0NjE1MjIzOCwiZXhwIjoxNzQ2MjM4NjM4LCJpYXQiOjE3NDYxNTIyMzh9.FJCm9cXKBXeIHu5aNmw1mVrop1UnORb1PxuhKeLMWK8'
}

def get_api_data():
    try:
        response = requests.get(api_query, headers=token_header)
        response.raise_for_status()
        data = response.json()
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Error fetching API data: {e}")
        return pd.DataFrame()

df = get_api_data()
df['payload'] = df['payload'].apply(lambda x: literal_eval(x))
df = pd.concat([df, df['payload'].apply(pd.Series)], axis=1)
df = df.drop(columns=['payload'])
df['createdAt'] = pd.to_datetime(df['createdAt'])


sensor_data = df.loc[df['eventType'] == 'sensor', ].copy()
parsed_df = sensor_data['Payload'].apply(parse_payload).apply(pd.Series)
sensor_data = pd.concat([sensor_data.drop(columns=['Payload']), parsed_df], axis=1)
sensor_data[['datetime_str', 'gps_status']] = sensor_data['date'].str.extract(r'(.*\+00:00)(.*)?')
sensor_data['datetime'] = pd.to_datetime(sensor_data['datetime_str'], errors='coerce')
sensor_data['date'] = sensor_data['datetime'].dt.date
sensor_data['time'] = sensor_data['datetime'].dt.time

health_data = df.loc[df['eventType'] == 'health', ].copy()
parsed_df = health_data['Payload'].apply(parse_payload).apply(pd.Series)
health_data = pd.concat([health_data.drop(columns=['Payload']), parsed_df], axis=1)

status_data = df.loc[df['eventType'] == 'status', ].copy()
parsed_df = status_data['Payload'].apply(parse_payload).apply(pd.Series)
status_data = pd.concat([status_data.drop(columns=['Payload']), parsed_df], axis=1)

# Create tabs
tab1, tab2 = st.tabs(["🦈 Shark Detection", "🦆 Duck Management System"])
with tab1:

    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("📋 Log")
        # Sort descending by time
        for _, row in sensor_data.iterrows():
            st.markdown(f"🦈 Confidence: {row['confidence']} \n Time:`{row['time']}`")
    with col2:
        if not df.empty:
            # st.dataframe(sensor_data, use_container_width=True)
            sensor_data['date'] = pd.to_datetime(sensor_data['date'], errors='coerce')
            sensor_data['hour'] = sensor_data['date'].dt.hour
            sensor_data['min'] = sensor_data['date'].dt.minute
            sensor_data['day'] = sensor_data['date'].dt.day_name()

            data = pd.DataFrame({
                'lat': [41.1092, 41.1100, 41.1080, 41.1111, 41.1120, 41.1130],
                'lon': [-72.8764, -72.8770, -72.8750, -72.8785, -72.8790, -72.8800],
            })

            # Create base map centered on your target location
            center = [41.109293605382845, -72.87647943062424]
            m = folium.Map(location=center, zoom_start=12)

            # Add HeatMap layer
            heat_data = [[row['lat'], row['lon']] for index, row in data.iterrows()]
            HeatMap(heat_data, radius=15).add_to(m)

            # Display in Streamlit
            st.title("Shark Detection Heatmap")
            st_folium(m)


        else:
            st.warning("No data returned from API.")

with tab2:
    fig, ax = plt.subplots(figsize=(10, 5), dpi=150)
    ax.plot(health_data['createdAt'], health_data['temp'])
    ax.set_xlabel('Time (GMT)')
    ax.set_ylabel('Temperature (C)')
    ax.set_title('Temperature over Time')
    ax.tick_params(axis='x', rotation=45)
    ax.grid(True)
    st.pyplot(fig)