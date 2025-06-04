import streamlit as st
import datetime
import pandas as pd
import plotly.express as px
import json
from uuid import uuid4
from typing import List, Dict, Optional
from io import BytesIO

# Constants
DEFAULT_SURVEY_SPEED = 5.0  # knots
DEFAULT_WEATHER_DOWNTIME = 15  # percentage
COLOR_MAP = {
    "Survey": "#2E86AB",
    "Task": "#F18F01",
    "Maintenance": "#A23B72",
    "Weather": "#3B1F2B",
    "Transit": "#3D5A6C",
    "Delay": "#DB504A",
    "Other": "#6B7280"
}

# --- Custom Theme and CSS ---
st.set_page_config(
    page_title="Hydrographic Survey Estimator Pro",
    layout="wide",
    page_icon="🌊"
)

st.markdown("""
    <style>
        :root {
            --primary: #1E40AF;
            --secondary: #0b1d3a;
            --accent: #1d4ed8;
        }
        html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
            background-color: var(--secondary) !important;
            color: white !important;
        }
        .stForm {
            background-color: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            border-left: 4px solid var(--accent);
        }
        .stButton > button {
            background-color: var(--primary);
            color: white;
            border: none;
            transition: all 0.3s;
        }
        .stButton > button:hover {
            background-color: var(--accent);
            transform: translateY(-1px);
        }
        .stAlert {
            background-color: rgba(30, 58, 138, 0.5) !important;
            border-left: 4px solid var(--accent);
        }
        .tooltip-icon {
            color: var(--accent);
            cursor: help;
        }
        .vessel-card {
            background: rgba(30, 64, 175, 0.2);
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 15px;
            border-left: 4px solid var(--accent);
            transition: all 0.3s;
        }
        .vessel-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }
    </style>
""", unsafe_allow_html=True)

# --- Data Models ---
class Vessel:
    def __init__(self, name: str, line_km: float, speed: float, start_date: datetime.date,
                 transit_days: float, weather_days: float, maintenance_days: float, id: Optional[str] = None):
        self.id = id or str(uuid4())
        self.name = name
        self.line_km = line_km
        self.speed = speed
        self.start_date = start_date
        self.transit_days = transit_days
        self.weather_days = weather_days
        self.maintenance_days = maintenance_days
        self.survey_days = self.calculate_survey_days()
        self.total_days = self.calculate_total_days()
        self.end_date = self.calculate_end_date()
        self.daily_progress = self.line_km / self.total_days if self.total_days > 0 else 0
    
    def calculate_survey_days(self) -> float:
        return round(self.line_km / (self.speed * 24), 2)
    
    def calculate_total_days(self) -> float:
        return round(self.survey_days + self.transit_days + self.weather_days + self.maintenance_days, 2)
    
    def calculate_end_date(self) -> datetime.date:
        return self.start_date + datetime.timedelta(days=self.total_days)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "line_km": self.line_km,
            "speed": self.speed,
            "start_date": str(self.start_date),
            "survey_days": self.survey_days,
            "transit_days": self.transit_days,
            "weather_days": self.weather_days,
            "maintenance_days": self.maintenance_days,
            "total_days": self.total_days,
            "end_date": str(self.end_date),
            "daily_progress": self.daily_progress
        }

class Task:
    def __init__(self, name: str, task_type: str, start_date: datetime.date, end_date: datetime.date,
                 vessel_id: Optional[str] = None, pause_survey: bool = False, cost: float = 0, id: Optional[str] = None):
        self.id = id or str(uuid4())
        self.name = name
        self.type = task_type
        self.start_date = start_date
        self.end_date = end_date
        self.vessel_id = vessel_id
        self.pause_survey = pause_survey
        self.cost = cost
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "start_date": str(self.start_date),
            "end_date": str(self.end_date),
            "vessel_id": self.vessel_id,
            "pause_survey": self.pause_survey,
            "cost": self.cost
        }

# --- Session State Initialization ---
def init_session_state():
    defaults = {
        "vessels": [],
        "tasks": [],
        "project_name": "",
        "unsurveyed_km": 0.0,
        "surveyed_km": 0.0,
        "weather_factor": DEFAULT_WEATHER_DOWNTIME,
        "day_rate": 25000
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# --- Helper Functions ---
def validate_vessel(name: str, line_km: float, speed: float, transit_days: float,
                   weather_days: float, maintenance_days: float) -> List[str]:
    errors = []
    if not name.strip():
        errors.append("Vessel name cannot be empty")
    if any(v['name'] == name for v in st.session_state.vessels):
        errors.append(f"Vessel '{name}' already exists")
    if line_km <= 0:
        errors.append("Line kilometers must be positive")
    if speed <= 0:
        errors.append("Speed must be positive")
    if transit_days < 0 or weather_days < 0 or maintenance_days < 0:
        errors.append("Contingency days cannot be negative")
    return errors

def validate_task(task: Dict) -> List[str]:
    errors = []
    if not task['name'].strip():
        errors.append("Task name cannot be empty")
    start_date = pd.to_datetime(task['start_date']).date()
    end_date = pd.to_datetime(task['end_date']).date()
    if start_date > end_date:
        errors.append("End date must be after start date")
    if task['vessel_id']:
        vessel = next((v for v in st.session_state.vessels if v['id'] == task['vessel_id']), None)
        if not vessel:
            errors.append("Assigned vessel does not exist")
        else:
            vessel_start = pd.to_datetime(vessel['start_date']).date()
            vessel_end = pd.to_datetime(vessel['end_date']).date()
            if start_date < vessel_start or end_date > vessel_end:
                errors.append("Task dates outside vessel's operational period")
    return errors

def calculate_surveyed_km():
    st.session_state.surveyed_km = sum(v['line_km'] for v in st.session_state.vessels)

def calculate_project_progress() -> float:
    total_surveyed = st.session_state.surveyed_km
    if st.session_state.unsurveyed_km > 0:
        return min(100, (total_surveyed / st.session_state.unsurveyed_km) * 100)
    return 0.0

def calculate_project_cost() -> float:
    vessel_days = sum(v['total_days'] for v in st.session_state.vessels)
    task_costs = sum(t['cost'] for t in st.session_state.tasks)
    return (vessel_days * st.session_state.day_rate) + task_costs

@st.cache_data
def build_timeline_data(vessels: List[Dict], tasks: List[Dict]) -> pd.DataFrame:
    timeline_data = []
    for vessel in vessels:
        survey_start = pd.to_datetime(vessel['start_date'])
        survey_end = pd.to_datetime(vessel['end_date'])
        pauses = sorted(
            [t for t in tasks if t['vessel_id'] == vessel['id'] and t['pause_survey']],
            key=lambda t: pd.to_datetime(t['start_date'])
        )
        if not pauses:
            timeline_data.append({
                "Task": f"Survey: {vessel['name']}",
                "Start": survey_start,
                "Finish": survey_end,
                "Resource": vessel['name'],
                "Type": "Survey",
                "Details": f"{vessel['line_km']} km at {vessel['speed']} knots",
                "Progress": 100
            })
        else:
            current_start = survey_start
            for pause in pauses:
                pause_start = pd.to_datetime(pause['start_date'])
                pause_end = pd.to_datetime(pause['end_date'])
                if pause_start > current_start:
                    timeline_data.append({
                        "Task": f"Survey: {vessel['name']}",
                        "Start": current_start,
                        "Finish": pause_start,
                        "Resource": vessel['name'],
                        "Type": "Survey",
                        "Details": f"{vessel['line_km']} km at {vessel['speed']} knots",
                        "Progress": 100
                    })
                timeline_data.append({
                    "Task": pause['name'],
                    "Start": pause_start,
                    "Finish": pause_end,
                    "Resource": vessel['name'],
                    "Type": pause['type'],
                    "Details": pause.get('notes', ''),
                    "Progress": 0
                })
                current_start = pause_end
            if current_start < survey_end:
                timeline_data.append({
                    "Task": f"Survey: {vessel['name']}",
                    "Start": current_start,
                    "Finish": survey_end,
                    "Resource": vessel['name'],
                    "Type": "Survey",
                    "Details": f"{vessel['line_km']} km at {vessel['speed']} knots",
                    "Progress": 100
                })
    for task in [t for t in tasks if not t['vessel_id']]:
        timeline_data.append({
            "Task": task['name'],
            "Start": pd.to_datetime(task['start_date']),
            "Finish": pd.to_datetime(task['end_date']),
            "Resource": "Unassigned",
            "Type": task['type'],
            "Details": task.get('notes', ''),
            "Progress": 0
        })
    return pd.DataFrame(timeline_data)

# --- UI Components ---
def show_project_header():
    st.title("🌊 Hydrographic Survey Estimator Pro")
    calculate_surveyed_km()
    progress = calculate_project_progress()
    total_cost = calculate_project_cost()
    total_days = sum(v['total_days'] for v in st.session_state.vessels)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Project Progress", f"{progress:.1f}%")
    with col2:
        st.metric("Surveyed Line Km", f"{st.session_state.surveyed_km:.1f} km")
    with col3:
        st.metric("Estimated Duration", f"{total_days:.1f} days")
    with col4:
        st.metric("Estimated Cost", f"${total_cost:,.2f}")
    st.progress(progress / 100)

def vessel_form(edit_vessel: Optional[Dict] = None):
    is_edit = edit_vessel is not None
    with st.expander(f"🚢 {'Edit Vessel' if is_edit else 'Add New Vessel'}", expanded=False):
        with st.form(f"vessel_form_{edit_vessel['id'] if is_edit else 'new'}"):
            col1, col2 = st.columns([3, 2])
            with col1:
                vessel_name = st.text_input("Vessel Name*", value=edit_vessel['name'] if is_edit else "", placeholder="e.g. Orca Explorer")
                line_km = st.number_input("Line Km*", min_value=0.1, step=1.0, value=edit_vessel['line_km'] if is_edit else 100.0)
            with col2:
                speed = st.number_input("Speed (knots)*", min_value=0.1, step=0.1, value=edit_vessel['speed'] if is_edit else DEFAULT_SURVEY_SPEED)
                start_date = st.date_input("Start Date*", value=pd.to_datetime(edit_vessel['start_date']).date() if is_edit else datetime.date.today())
            st.markdown("**Contingency Days**")
            col3, col4, col5 = st.columns(3)
            with col3:
                transit_days = st.number_input("Transit Days", min_value=0.0, step=0.5, value=edit_vessel['transit_days'] if is_edit else 2.0)
            with col4:
                weather_days = st.number_input("Weather Days", min_value=0.0, step=0.5, value=edit_vessel['weather_days'] if is_edit else 3.0)
            with col5:
                maintenance_days = st.number_input("Maintenance Days", min_value=0.0, step=0.5, value=edit_vessel['maintenance_days'] if is_edit else 1.0)
            
            submit_button = st.form_submit_button("Update Vessel" if is_edit else "Add Vessel")
            if submit_button:
                errors = validate_vessel(vessel_name, line_km, speed, transit_days, weather_days, maintenance_days)
                if is_edit:
                    errors = [e for e in errors if e != f"Vessel '{vessel_name}' already exists" or vessel_name != edit_vessel['name']]
                if errors:
                    for error in errors:
                        st.error(error)
                else:
                    vessel = Vessel(
                        name=vessel_name,
                        line_km=line_km,
                        speed=speed,
                        start_date=start_date,
                        transit_days=transit_days,
                        weather_days=weather_days,
                        maintenance_days=maintenance_days,
                        id=edit_vessel['id'] if is_edit else None
                    )
                    if is_edit:
                        st.session_state.vessels = [v for v in st.session_state.vessels if v['id'] != edit_vessel['id']]
                    st.session_state.vessels.append(vessel.to_dict())
                    st.success(f"Vessel '{vessel_name}' {'updated' if is_edit else 'added'} successfully!")
                    calculate_surveyed_km()
                    st.rerun()

def task_form(edit_task: Optional[Dict] = None):
    is_edit = edit_task is not None
    with st.expander(f"📝 {'Edit Task' if is_edit else 'Add New Task'}", expanded=False):
        with st.form(f"task_form_{edit_task['id'] if is_edit else 'new'}"):
            col1, col2 = st.columns(2)
            with col1:
                task_name = st.text_input("Task Name*", value=edit_task['name'] if is_edit else "", placeholder="e.g. Sediment Sampling")
                task_type = st.selectbox(
                    "Task Type*",
                    ["Survey", "Maintenance", "Weather", "Transit", "Delay", "Other"],
                    index=["Survey", "Maintenance", "Weather", "Transit", "Delay", "Other"].index(edit_task['type']) if is_edit else 0
                )
            with col2:
                start_date = st.date_input("Start Date*", value=pd.to_datetime(edit_task['start_date']).date() if is_edit else datetime.date.today())
                end_date = st.date_input("End Date*", value=pd.to_datetime(edit_task['end_date']).date() if is_edit else datetime.date.today() + datetime.timedelta(days=1))
            col3, col4 = st.columns(2)
            with col3:
                vessel_options = [("Unassigned", None)] + [(v['name'], v['id']) for v in st.session_state.vessels]
                selected_vessel = st.selectbox(
                    "Assigned Vessel",
                    vessel_options,
                    format_func=lambda x: x[0],
                    index=next((i for i, opt in enumerate(vessel_options) if opt[1] == edit_task['vessel_id']), 0) if is_edit else 0
                )
                vessel_id = selected_vessel[1]
            with col4:
                pause_survey = st.checkbox("Pause Survey Operations", value=edit_task['pause_survey'] if is_edit else False)
                cost = st.number_input("Estimated Cost (USD)", min_value=0.0, value=edit_task['cost'] if is_edit else 0.0, step=1000.0)
            
            submit_button = st.form_submit_button("Update Task" if is_edit else "Add Task")
            if submit_button:
                task = {
                    "id": edit_task['id'] if is_edit else str(uuid4()),
                    "name": task_name,
                    "type": task_type,
                    "start_date": str(start_date),
                    "end_date": str(end_date),
                    "vessel_id": vessel_id,
                    "pause_survey": pause_survey,
                    "cost": cost
                }
                errors = validate_task(task)
                if errors:
                    for error in errors:
                        st.error(error)
                else:
                    if is_edit:
                        st.session_state.tasks = [t for t in st.session_state.tasks if t['id'] != edit_task['id']]
                    st.session_state.tasks.append(task)
                    st.success(f"Task '{task_name}' {'updated' if is_edit else 'added'} successfully!")
                    st.rerun()

def show_vessels():
    if not st.session_state.vessels:
        st.info("No vessels added yet. Add your first vessel to begin.")
        return
    st.subheader("🚢 Vessel Fleet")
    for vessel in st.session_state.vessels:
        with st.container():
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.markdown(f"""
                <div class="vessel-card">
                    <h4>{vessel['name']}</h4>
                    <p><strong>Survey:</strong> {vessel['line_km']} km | {vessel['speed']} knots | {vessel['survey_days']} days</p>
                    <p><strong>Schedule:</strong> {vessel['start_date']} to {vessel['end_date']} ({vessel['total_days']} days total)</p>
                    <p><strong>Contingencies:</strong> Transit: {vessel['transit_days']}d | Weather: {vessel['weather_days']}d | Maint: {vessel['maintenance_days']}d</p>
                </div>
                """, unsafe_allow_html=True)
            with col2:
                if st.button("Edit", key=f"edit_vessel_{vessel['id']}"):
                    vessel_form(vessel)
            with col3:
                with st.form(f"delete_vessel_{vessel['id']}"):
                    st.form_submit_button("Delete", on_click=lambda: delete_vessel(vessel['id']))

def delete_vessel(vessel_id: str):
    st.session_state.vessels = [v for v in st.session_state.vessels if v['id'] != vessel_id]
    st.session_state.tasks = [t for t in st.session_state.tasks if t['vessel_id'] != vessel_id]
    calculate_surveyed_km()
    st.rerun()

def show_tasks():
    if not st.session_state.tasks:
        st.info("No tasks added yet. Add your first task to begin.")
        return
    st.subheader("📋 Task Register")
    col1, col2, col3 = st.columns(3)
    with col1:
        filter_type = st.selectbox("Filter by Type", ["All"] + sorted(list(set(t['type'] for t in st.session_state.tasks))))
    with col2:
        filter_vessel = st.selectbox("Filter by Vessel", ["All"] + [v['name'] for v in st.session_state.vessels])
    with col3:
        filter_date = st.selectbox("Filter by Date", ["All", "Upcoming", "Past", "Current"])
    
    filtered_tasks = st.session_state.tasks
    if filter_type != "All":
        filtered_tasks = [t for t in filtered_tasks if t['type'] == filter_type]
    if filter_vessel != "All":
        vessel_id = next((v['id'] for v in st.session_state.vessels if v['name'] == filter_vessel), None)
        filtered_tasks = [t for t in filtered_tasks if t['vessel_id'] == vessel_id]
    if filter_date != "All":
        today = datetime.date.today()
        if filter_date == "Upcoming":
            filtered_tasks = [t for t in filtered_tasks if pd.to_datetime(t['start_date']).date() > today]
        elif filter_date == "Past":
            filtered_tasks = [t for t in filtered_tasks if pd.to_datetime(t['end_date']).date() < today]
        elif filter_date == "Current":
            filtered_tasks = [t for t in filtered_tasks if pd.to_datetime(t['start_date']).date() <= today <= pd.to_datetime(t['end_date']).date()]
    
    for task in filtered_tasks:
        vessel_name = next((v['name'] for v in st.session_state.vessels if v['id'] == task['vessel_id']), "Unassigned")
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            st.markdown(f"""
            <div style="background: rgba(255,255,255,0.1); padding: 10px; border-radius: 5px; margin-bottom: 10px;">
                <strong>{task['name']}</strong> ({task['type']})<br>
                <small>{task['start_date']} to {task['end_date']} | Vessel: {vessel_name}</small><br>
                {f"<small>Cost: ${task['cost']:,.2f}</small>" if task['cost'] > 0 else ""}
                {"<small style='color: orange;'>⚠️ Pauses Survey</small>" if task['pause_survey'] else ""}
            </div>
            """, unsafe_allow_html=True)
        with col2:
            if st.button("Edit", key=f"edit_task_{task['id']}"):
                task_form(task)
        with col3:
            with st.form(f"delete_task_{task['id']}"):
                st.form_submit_button("Delete", on_click=lambda: delete_task(task['id']))

def delete_task(task_id: str):
    st.session_state.tasks = [t for t in st.session_state.tasks if t['id'] != task_id]
    st.rerun()

def show_timeline():
    if not st.session_state.vessels and not st.session_state.tasks:
        st.info("Add vessels and tasks to generate the project timeline")
        return
    st.subheader("📊 Project Timeline")
    df = build_timeline_data(st.session_state.vessels, st.session_state.tasks)
    if df.empty:
        st.warning("No timeline data available")
        return
    fig = px.timeline(
        df,
        x_start="Start",
        x_end="Finish",
        y="Resource",
        color="Type",
        color_discrete_map=COLOR_MAP,
        hover_name="Task",
        hover_data={"Details": True, "Progress": ":.0f%"},
        title="Survey Project Timeline"
    )
    fig.update_yaxes(autorange="reversed", title_text="")
    fig.update_xaxes(title_text="Timeline")
    fig.update_layout(
        height=max(400, len(st.session_state.vessels) * 100 + len(st.session_state.tasks) * 50),
        plot_bgcolor="rgba(255,255,255,0.1)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="white",
        legend_title_text="Activity Type",
        hoverlabel=dict(
            bgcolor="rgba(30, 64, 175, 0.8)",
            font_size=12,
            font_family="Arial"
        )
    )
    st.plotly_chart(fig, use_container_width=True)

def project_settings():
    with st.expander("⚙️ Project Settings", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.project_name = st.text_input(
                "Project Name",
                value=st.session_state.project_name,
                placeholder="e.g. Australia West Survey"
            )
            st.session_state.unsurveyed_km = st.number_input(
                "Total Unsurveyed Line Km",
                min_value=0.0,
                value=st.session_state.unsurveyed_km,
                step=1.0
            )
        with col2:
            st.session_state.weather_factor = st.number_input(
                "Weather Downtime Factor (%)",
                min_value=0.0,
                max_value=100.0,
                value=st.session_state.weather_factor,
                step=1.0
            )
            st.session_state.day_rate = st.number_input(
                "Daily Vessel Rate (USD)",
                min_value=0.0,
                value=st.session_state.day_rate,
                step=1000.0
            )

def data_management():
    with st.expander("💾 Data Management", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Export Project**")
            export_name = st.text_input("Export filename", value=st.session_state.project_name or "survey_project")
            if st.button("Export to JSON"):
                export_data = {
                    "project_name": st.session_state.project_name,
                    "unsurveyed_km": st.session_state.unsurveyed_km,
                    "weather_factor": st.session_state.weather_factor,
                    "day_rate": st.session_state.day_rate,
                    "vessels": st.session_state.vessels,
                    "tasks": st.session_state.tasks,
                }
                st.download_button(
                    label="Download JSON",
                    data=json.dumps(export_data, indent=2),
                    file_name=f"{export_name}.json",
                    mime="application/json"
                )
            if st.button("Export to Excel"):
                output = BytesIO()
                with pd.ExcelWriter(output, engine="openpyxl") as writer:
                    pd.DataFrame(st.session_state.vessels).to_excel(writer, sheet_name="Vessels", index=False)
                    pd.DataFrame(st.session_state.tasks).to_excel(writer, sheet_name="Tasks", index=False)
                    pd.DataFrame([{
                        "project_name": st.session_state.project_name,
                        "unsurveyed_km": st.session_state.unsurveyed_km,
                        "weather_factor": st.session_state.weather_factor,
                        "day_rate": st.session_state.day_rate
                    }]).to_excel(writer, sheet_name="Settings", index=False)
                st.download_button(
                    label="Download Excel",
                    data=output.getvalue(),
                    file_name=f"{export_name}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        with col2:
            st.markdown("**Import Project**")
            uploaded_file = st.file_uploader(
                "Upload project file",
                type=["json", "xlsx"],
                accept_multiple_files=False
            )
            if uploaded_file and st.button("Import Data"):
                try:
                    if uploaded_file.name.endswith(".json"):
                        data = json.load(uploaded_file)
                        required_fields = ["project_name", "unsurveyed_km", "weather_factor", "day_rate", "vessels", "tasks"]
                        if not all(field in data for field in required_fields):
                            raise ValueError("Missing required fields in JSON")
                        st.session_state.project_name = data["project_name"]
                        st.session_state.unsurveyed_km = float(data["unsurveyed_km"])
                        st.session_state.weather_factor = float(data["weather_factor"])
                        st.session_state.day_rate = float(data["day_rate"])
                        st.session_state.vessels = [
                            v for v in data["vessels"]
                            if all(k in v for k in ["id", "name", "line_km", "speed", "start_date", "transit_days", "weather_days", "maintenance_days"])
                        ]
                        st.session_state.tasks = [
                            t for t in data["tasks"]
                            if all(k in t for k in ["id", "name", "type", "start_date", "end_date", "vessel_id", "pause_survey", "cost"])
                        ]
                        calculate_surveyed_km()
                        st.success("Project imported successfully from JSON!")
                    elif uploaded_file.name.endswith(".xlsx"):
                        xls = pd.ExcelFile(uploaded_file)
                        if "Vessels" in xls.sheet_names:
                            st.session_state.vessels = xls.parse("Vessels").to_dict(orient="records")
                        if "Tasks" in xls.sheet_names:
                            st.session_state.tasks = xls.parse("Tasks").to_dict(orient="records")
                        if "Settings" in xls.sheet_names:
                            settings = xls.parse("Settings").iloc[0].to_dict()
                            st.session_state.project_name = settings.get("project_name", "")
                            st.session_state.unsurveyed_km = float(settings.get("unsurveyed_km", 0.0))
                            st.session_state.weather_factor = float(settings.get("weather_factor", DEFAULT_WEATHER_DOWNTIME))
                            st.session_state.day_rate = float(settings.get("day_rate", 25000))
                        calculate_surveyed_km()
                        st.success("Project data imported successfully from Excel!")
                except Exception as e:
                    st.error(f"Error importing project: {str(e)}")

# --- Main App Layout ---
def main():
    init_session_state()
    show_project_header()
    project_settings()
    data_management()
    col1, col2 = st.columns(2)
    with col1:
        vessel_form()
        show_vessels()
    with col2:
        task_form()
        show_tasks()
    show_timeline()

if __name__ == "__main__":
    main()