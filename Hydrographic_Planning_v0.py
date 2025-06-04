# Hydrographic Survey Estimator Tool
# Version: 1.2 (Dark Theme + Export/Import)
# Developed by: Joana Paiva
# Contact: joana.paiva82@outlook.com
# Description:
# This Streamlit app helps hydrographic survey teams plan, visualize, and manage vessel timelines and tasks.
# Supports intelligent Gantt charting and allows saving/loading project files (JSON or Excel).

import streamlit as st
import datetime
import pandas as pd
import plotly.express as px

# --- Custom Dark Theme ---
st.markdown("""
    <style>
        body {
            background-color: #0b1d3a;
        }
        .main {
            background-color: #0b1d3a;
        }
        section[data-testid="stSidebar"] {
            background-color: #102042;
        }
        h1, h2, h3, h4, h5, h6, .st-emotion-cache-10trblm {
            color: #ffffff;
        }
        .stTextInput > label, .stNumberInput > label, .stSelectbox > label, .stDateInput > label {
            color: #cdd6f4 !important;
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
    </style>
""", unsafe_allow_html=True)

# --- Page Config ---
st.set_page_config(page_title="Hydrographic Survey Estimator", layout="wide")
st.title("🌊 Hydrographic Survey Estimator")

# --- Session State ---
if "vessels" not in st.session_state:
    st.session_state.vessels = []
if "tasks" not in st.session_state:
    st.session_state.tasks = []

# --- Project Info ---
st.subheader("📁 Project Information")
col1, col2, col3 = st.columns([3, 2, 2])
project_name = col1.text_input("Project Name", placeholder="e.g. Australia West Survey")
unsurveyed_km = col2.number_input("Unsurveyed Line Km", min_value=0.0, step=0.1)
surveyed_km = col3.number_input("Surveyed Line Km", value=0.0, step=0.1, disabled=True)

# --- Vessel Form ---
st.subheader("🛥️ Add Vessel")
with st.form("vessel_form"):
    col1, col2 = st.columns([3, 2])
    vessel_name = col1.text_input("Vessel Name", placeholder="e.g. Orca Explorer")
    line_km = col2.number_input("Line Km", min_value=0.0, step=1.0)

    col3, col4 = st.columns(2)
    speed = col3.number_input("Speed (knots)", min_value=0.1, step=0.1)
    start_date = col4.date_input("Survey Start Date", value=datetime.date.today())

    col5, col6, col7 = st.columns(3)
    transit_days = col5.number_input("Transit Days", min_value=0.0, step=0.5)
    weather_days = col6.number_input("Weather Days", min_value=0.0, step=0.5)
    maintenance_days = col7.number_input("Maintenance Days", min_value=0.0, step=0.5)

    submitted = st.form_submit_button("Add Vessel")

    if submitted:
        if not vessel_name or line_km == 0 or speed == 0:
            st.warning("Please fill all required fields.")
        else:
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
            st.success(f"Vessel '{vessel_name}' added!")

# --- Display Vessels ---
if st.session_state.vessels:
    st.subheader("📋 Added Vessels")
    for v in st.session_state.vessels:
        st.markdown(f"""
        **🛥 {v['name']}**
        - Line Km: {v['line_km']}
        - Speed: {v['speed']} knots
        - Start: {v['start_date']} → End: {v['end_date']}
        - Survey: {v['survey_days']} d, Transit: {v['transit_days']} d, Weather: {v['weather_days']} d, Maintenance: {v['maintenance_days']} d
        - **Total:** {v['total_days']} days
        """)

# --- Task Form ---
st.subheader("📝 Add Task")
with st.form("task_form"):
    col1, col2 = st.columns(2)
    task_name = col1.text_input("Task Name", placeholder="e.g. Mobilisation")
    task_type = col2.selectbox("Task Type", options=["General", "Survey", "Maintenance", "Weather", "Transit"])

    col3, col4 = st.columns(2)
    task_start = col3.date_input("Task Start Date", value=datetime.date.today())
    task_end = col4.date_input("Task End Date", value=datetime.date.today() + datetime.timedelta(days=1))

    col5, col6 = st.columns(2)
    assigned_vessel = col5.selectbox("Assigned Vessel (optional)", options=[""] + [v["name"] for v in st.session_state.vessels])
    pause_survey = col6.selectbox("Pause Survey?", options=["No", "Yes"])

    submitted_task = st.form_submit_button("Add Task")

    if submitted_task:
        if not task_name or task_start >= task_end:
            st.warning("Please enter a valid task name and date range.")
        else:
            st.session_state.tasks.append({
                "name": task_name,
                "type": task_type,
                "start_date": str(task_start),
                "end_date": str(task_end),
                "vessel": assigned_vessel if assigned_vessel else None,
                "pause_survey": pause_survey
            })
            st.success(f"Task '{task_name}' added.")

# --- Display Tasks ---
if st.session_state.tasks:
    st.subheader("📌 Current Tasks")
    for t in st.session_state.tasks:
        st.markdown(f"- **{t['name']}** ({t['type']}) | {t['start_date']} to {t['end_date']} | Vessel: {t.get('vessel', 'N/A')} | Pause: {t['pause_survey']}")
else:
    st.info("No tasks added yet.")

# --- Save / Load Project ---
st.subheader("💾 Save or Load Project")
col1, col2 = st.columns(2)

if col1.button("📤 Export Project (JSON)"):
    export_data = {
        "project_name": project_name,
        "unsurveyed_km": unsurveyed_km,
        "vessels": st.session_state.vessels,
        "tasks": st.session_state.tasks,
    }
    st.download_button(
        label="Download JSON",
        data=str.encode(pd.Series(export_data).to_json()),
        file_name=f"{project_name or 'project'}.json",
        mime="application/json"
    )

if col2.button("📤 Export Project (CSV Excel)"):
    vessel_df = pd.DataFrame(st.session_state.vessels)
    task_df = pd.DataFrame(st.session_state.tasks)
    with pd.ExcelWriter("project_data.xlsx", engine="xlsxwriter") as writer:
        vessel_df.to_excel(writer, sheet_name="Vessels", index=False)
        task_df.to_excel(writer, sheet_name="Tasks", index=False)
    with open("project_data.xlsx", "rb") as f:
        st.download_button("Download Excel", f, file_name="project_data.xlsx", mime="application/vnd.ms-excel")

uploaded_file = st.file_uploader("📥 Load Project (JSON or Excel)", type=["json", "xlsx", "csv"])
if uploaded_file:
    try:
        if uploaded_file.name.endswith(".json"):
            raw = uploaded_file.read()
            data = pd.read_json(raw, typ="series")
            st.session_state.vessels = data["vessels"]
            st.session_state.tasks = data["tasks"]
            st.success("✅ Project loaded from JSON successfully!")

        elif uploaded_file.name.endswith(".xlsx"):
            xls = pd.ExcelFile(uploaded_file)
            st.session_state.vessels = xls.parse("Vessels").to_dict(orient="records")
            st.session_state.tasks = xls.parse("Tasks").to_dict(orient="records")
            st.success("✅ Project loaded from Excel successfully!")

        elif uploaded_file.name.endswith(".csv"):
            st.warning("⚠️ CSV support is limited to Excel with sheets. Use JSON or XLSX for full support.")

    except Exception as e:
        st.error(f"Error loading project: {e}")

# --- Gantt Chart ---
st.subheader("📊 Project Timeline")

timeline_data = []

# 1. Tasks
for task in st.session_state.tasks:
    timeline_data.append({
        "Type": f"Task: {task['name']}",
        "Start": task["start_date"],
        "End": task["end_date"],
        "Group": task.get("vessel", "Unassigned"),
        "Color": "Task"
    })

# 2. Surveys (pause-aware)
for vessel in st.session_state.vessels:
    survey_start = pd.to_datetime(vessel["start_date"])
    survey_end = pd.to_datetime(vessel["end_date"])
    pauses = [t for t in st.session_state.tasks if t.get("vessel") == vessel["name"] and t.get("pause_survey") == "Yes"]
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

# 3. Plot
if timeline_data:
    df = pd.DataFrame(timeline_data)
    fig = px.timeline(df, x_start="Start", x_end="End", y="Group", color="Color", text="Type")
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(
        height=600,
        title="Survey & Task Timeline",
        plot_bgcolor="#0b1d3a",
        paper_bgcolor="#0b1d3a",
        font_color="#ffffff",
        legend_title_text="",
        title_font_size=20
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No timeline data to display.")
