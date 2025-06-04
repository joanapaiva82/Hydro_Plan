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

# --- Display Vessels ---
st.subheader("📋 Added Vessels")
if st.session_state.vessels:
    for v in st.session_state.vessels:
        st.markdown(f"""
        **🛥 {v['name']}**
        - Line Km: {v['line_km']}
        - Speed: {v['speed']} knots
        - Start: {v['start_date']} → End: {v['end_date']}
        - Survey: {v['survey_days']} d, Transit: {v['transit_days']} d, Weather: {v['weather_days']} d, Maintenance: {v['maintenance_days']} d
        - **Total:** {v['total_days']} days
        """)
else:
    st.markdown("_No vessels added yet._")

# --- Add Task ---
st.subheader("📝 Add Task")
with st.form("task_form"):
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Task Name**", unsafe_allow_html=True)
        task_name = st.text_input("", placeholder="e.g. Sediment Sample")
    with col2:
        st.markdown("**Task Type**", unsafe_allow_html=True)
        task_type = st.selectbox("", ["General", "Survey", "Maintenance", "Weather", "Transit"])

    col3, col4 = st.columns(2)
    with col3:
        st.markdown("**Start Date**", unsafe_allow_html=True)
        task_start = st.date_input("", value=datetime.date.today())
    with col4:
        st.markdown("**End Date**", unsafe_allow_html=True)
        task_end = st.date_input("", value=datetime.date.today() + datetime.timedelta(days=1))

    col5, col6 = st.columns(2)
    with col5:
        st.markdown("**Assigned Vessel (optional)**", unsafe_allow_html=True)
        assigned_vessel = st.selectbox("", [""] + [v["name"] for v in st.session_state.vessels])
    with col6:
        st.markdown("**Pause Survey?**", unsafe_allow_html=True)
        pause_survey = st.selectbox("", ["No", "Yes"])

    if st.form_submit_button("Add Task"):
        st.session_state.tasks.append({
            "name": task_name,
            "type": task_type,
            "start_date": str(task_start),
            "end_date": str(task_end),
            "vessel": assigned_vessel or None,
            "pause_survey": pause_survey
        })
        st.success(f"Task '{task_name}' added.")

# --- Display Tasks ---
st.subheader("📌 Current Tasks")
if st.session_state.tasks:
    for t in st.session_state.tasks:
        st.markdown(
            f"<p><b>{t['name']}</b> ({t['type']}) | {t['start_date']} to {t['end_date']} | Vessel: {t.get('vessel', 'N/A')} | Pause: {t['pause_survey']}</p>",
            unsafe_allow_html=True
        )
else:
    st.markdown("_No tasks added yet._")

# --- Save/Load Project ---
st.subheader("💾 Save or Load Project")
col1, col2 = st.columns(2)

if col1.button("📤 Export Project (JSON)"):
    export_data = {
        "project_name": project_name,
        "unsurveyed_km": unsurveyed_km,
        "vessels": st.session_state.vessels,
        "tasks": st.session_state.tasks,
    }
    st.download_button("Download JSON", data=json.dumps(export_data, indent=2), file_name="project.json")

if col2.button("📤 Export Project (CSV Excel)"):
    vessel_df = pd.DataFrame(st.session_state.vessels)
    task_df = pd.DataFrame(st.session_state.tasks)
    with pd.ExcelWriter("project_data.xlsx") as writer:
        vessel_df.to_excel(writer, sheet_name="Vessels", index=False)
        task_df.to_excel(writer, sheet_name="Tasks", index=False)
    with open("project_data.xlsx", "rb") as f:
        st.download_button("Download Excel", f, file_name="project_data.xlsx")

uploaded_file = st.file_uploader("📥 Load Project (JSON or Excel)", type=["json", "xlsx"])
if uploaded_file:
    try:
        if uploaded_file.name.endswith(".json"):
            data = json.load(uploaded_file)
            st.session_state.vessels.clear()
            st.session_state.vessels.extend(data.get("vessels", []))
            st.session_state.tasks.clear()
            st.session_state.tasks.extend(data.get("tasks", []))
            st.success("✅ Project loaded from JSON successfully!")
        elif uploaded_file.name.endswith(".xlsx"):
            xls = pd.ExcelFile(uploaded_file)
            st.session_state.vessels = xls.parse("Vessels").to_dict(orient="records")
            st.session_state.tasks = xls.parse("Tasks").to_dict(orient="records")
            st.success("✅ Project loaded from Excel successfully!")
    except Exception as e:
        st.error(f"❌ Error loading project: {e}")

# --- Build Timeline ---
def build_timeline(vessels, tasks):
    timeline_data = []
    for task in tasks:
        timeline_data.append({
            "Type": f"Task: {task['name']}",
            "Start": task["start_date"],
            "End": task["end_date"],
            "Group": task.get("vessel", "Unassigned"),
            "Color": "Task"
        })
    for vessel in vessels:
        survey_start = pd.to_datetime(vessel["start_date"])
        survey_end = pd.to_datetime(vessel["end_date"])
        pauses = [t for t in tasks if t.get("vessel") == vessel["name"] and t.get("pause_survey") == "Yes"]
        pauses = sorted(pauses, key=lambda t: pd.to_datetime(t["start_date"]))
        if not pauses:
            timeline_data.append({
                "Type": f"Survey: {vessel['name']}",
                "Start": survey_start,
                "End": survey_end,
                "Group": vessel["name"],
                "Color": "Survey"
            })
        else:
            current_start = survey_start
            for pause in pauses:
                pause_start = pd.to_datetime(pause["start_date"])
                pause_end = pd.to_datetime(pause["end_date"])
                if pause_start > current_start:
                    timeline_data.append({
                        "Type": f"Survey (part): {vessel['name']}",
                        "Start": current_start,
                        "End": pause_start,
                        "Group": vessel["name"],
                        "Color": "Survey"
                    })
                current_start = pause_end
            if current_start < survey_end:
                timeline_data.append({
                    "Type": f"Survey (resumed): {vessel['name']}",
                    "Start": current_start,
                    "End": survey_end + datetime.timedelta(days=len(pauses)),
                    "Group": vessel["name"],
                    "Color": "Survey"
                })
    return pd.DataFrame(timeline_data)

# --- Show Gantt Chart ---
st.subheader("📊 Project Timeline")
df = build_timeline(st.session_state.vessels, st.session_state.tasks)
if not df.empty:
    fig = px.timeline(df, x_start="Start", x_end="End", y="Group", color="Color", text="Type")
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(
        height=600,
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        font_color="#000000",
        title_font_size=20
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No timeline data to display.")
