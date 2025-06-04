import streamlit as st
import datetime
import pandas as pd
import plotly.express as px
import json

st.set_page_config(page_title="Hydrographic Survey Estimator", layout="wide")

# --- Custom Dark Theme and CSS Fixes ---
st.markdown("""
    <style>
        html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
            background-color: #0b1d3a !important;
        }
        section.main {
            background-color: #0b1d3a !important;
        }
        h1, h2, h3, h4, h5, h6 {
            color: #ffffff !important;
            font-weight: 700;
        }
        .stForm label,
        div[data-testid="stForm"] label,
        div[data-baseweb="form-control"] label {
            display: none !important;
        }
        .stTextInput input, .stNumberInput input, .stDateInput input {
            background-color: #ffffff !important;
            color: #000000 !important;
        }
        .stSelectbox div[data-baseweb="select"] {
            background-color: #ffffff !important;
            color: #000000 !important;
        }
        .stForm {
            background-color: #ffffff;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
        }
        .stButton > button {
            background-color: #1e40af;
            color: white;
        }
        .stButton > button:hover {
            background-color: #1d4ed8;
        }
        .stMarkdown p, .stMarkdown ul, .stMarkdown li, .stMarkdown strong {
            color: #ffffff !important;
        }
        div[data-testid="stAlert"] {
            color: #ffffff !important;
            background-color: #1e3a8a !important;
            border-radius: 8px;
            font-weight: 500;
        }
        div[data-testid="stAlert"] > div {
            color: #ffffff !important;
        }
    </style>
""", unsafe_allow_html=True)

# --- Init Session State ---
if "vessels" not in st.session_state: st.session_state.vessels = []
if "tasks" not in st.session_state: st.session_state.tasks = []

st.title("🌊 Hydrographic Survey Estimator")

# --- Project Info ---
st.subheader("📁 Project Information")
col1, col2, col3 = st.columns([3, 2, 2])
with col1:
    st.markdown("**Project Name**", unsafe_allow_html=True)
    project_name = st.text_input("", placeholder="e.g. Australia West Survey")
with col2:
    st.markdown("**Unsurveyed Line Km**", unsafe_allow_html=True)
    unsurveyed_km = st.number_input("", min_value=0.0, step=0.1)
with col3:
    st.markdown("**Surveyed Line Km**", unsafe_allow_html=True)
    surveyed_km = st.number_input("", value=0.0, step=0.1, disabled=True)

# --- Add Vessel ---
st.subheader("🚢 Add Vessel")
with st.form("vessel_form"):
    col1, col2 = st.columns([3, 2])
    with col1:
        st.markdown("**Vessel Name**", unsafe_allow_html=True)
        vessel_name = st.text_input("", placeholder="e.g. Orca Explorer")
    with col2:
        st.markdown("**Line Km**", unsafe_allow_html=True)
        line_km = st.number_input("", min_value=0.0, step=1.0)

    col3, col4 = st.columns(2)
    with col3:
        st.markdown("**Speed (knots)**", unsafe_allow_html=True)
        speed = st.number_input("", min_value=0.1, step=0.1)
    with col4:
        st.markdown("**Survey Start Date**", unsafe_allow_html=True)
        start_date = st.date_input("", value=datetime.date.today())

    col5, col6, col7 = st.columns(3)
    with col5:
        st.markdown("**Transit Days**", unsafe_allow_html=True)
        transit_days = st.number_input("", min_value=0.0, step=0.5)
    with col6:
        st.markdown("**Weather Days**", unsafe_allow_html=True)
        weather_days = st.number_input("", min_value=0.0, step=0.5)
    with col7:
        st.markdown("**Maintenance Days**", unsafe_allow_html=True)
        maintenance_days = st.number_input("", min_value=0.0, step=0.5)

    if st.form_submit_button("Add Vessel"):
        survey_days = line_km / (speed * 24)
        total_days = survey_days + transit_days + weather_days + maintenance_days
        end_date = start_date + datetime.timedelta(days=total_days)
        st.session_state.vessels.append({
            "name": vessel_name,
            "line_km": line_km,
            "speed": speed,
            "start_date": str(start_date),
            "survey_days": round(survey_days, 2),
            "transit_days": transit_days,
            "weather_days": weather_days,
            "maintenance_days": maintenance_days,
            "total_days": round(total_days, 2),
            "end_date": str(end_date)
        })
        st.success(f"Vessel '{vessel_name}' added.")
