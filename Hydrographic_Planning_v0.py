import streamlit as st
import datetime
import pandas as pd
import plotly.express as px
import json
from uuid import uuid4
from io import BytesIO
from typing import List, Dict, Optional

# Constants
DEFAULT_SURVEY_SPEED = 5.0  # knots
DEFAULT_WEATHER_DOWNTIME = 15.0  # percentage, as float
COLOR_MAP = {
    "Survey": "#2E86AB",
    "Task": "#F18F01",
    "Maintenance": "#A23B72",
    "Weather": "#3B1F2B",
    "Transit": "#3D5A6C",
    "Delay": "#DB504A",
    "Other": "#6B7280"
}

# --- Page Configuration and CSS ---
st.set_page_config(
    page_title="Hydrographic Survey Estimator Pro",
    layout="wide",
    page_icon="🌊"
)

st.markdown("""
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
    <style>
        :root {
            --primary: #1E3A8A; /* Deep blue for headers and accents */
            --secondary: #F1F5F9; /* Light gray for background */
            --accent: #3B82F6; /* Bright blue for highlights */
            --text: #1F2937; /* Dark gray for text */
            --card-bg: #FFFFFF; /* White for card backgrounds */
            --shadow: rgba(0, 0, 0, 0.1);
        }

        html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
            background: var(--secondary);
            color: var(--text);
            font-family: 'Inter', 'Arial', sans-serif;
        }

        /* Header Styling */
        .stHeader {
            background: var(--primary);
            padding: 20px;
            border-radius: 8px;
            color: white;
            text-align: center;
            box-shadow: 0 4px 12px var(--shadow);
            margin-bottom: 20px;
        }

        /* Metrics Section */
        .stMetric {
            background: var(--card-bg);
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 8px var(--shadow);
            transition: transform 0.2s ease;
            margin-bottom: 15px;
        }
        .stMetric:hover {
            transform: translateY(-2px);
        }
        .progress-bar {
            height: 8px;
            background: var(--accent);
            border-radius: 4px;
            transition: width 0.5s ease;
        }

        /* Forms and Expanders */
        .stForm, .stExpander {
            background: var(--card-bg);
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 8px var(--shadow);
            margin-bottom: 20px;
            border-left: 4px solid var(--accent);
        }

        /* Buttons */
        .stButton > button {
            background: var(--accent);
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            transition: all 0.3s ease;
        }
        .stButton > button:hover {
            background: var(--primary);
            transform: translateY(-2px);
            box-shadow: 0 2px 4px var(--shadow);
        }

        /* Cards for Vessels and Tasks */
        .card {
            background: var(--card-bg);
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 15px;
            box-shadow: 0 2px 8px var(--shadow);
            transition: transform 0.2s ease;
        }
        .card:hover {
            transform: translateY(-2px);
        }

        /* Sidebar */
        .sidebar {
            background: var(--primary);
            padding: 20px;
            border-radius: 8px;
            color: white;
            box-shadow: 0 4px 12px var(--shadow);
            height: 100vh;
            position: fixed;
            width: 220px;
        }
        .sidebar button {
            background: var(--accent);
            color: white;
            border: none;
            padding: 10px;
            border-radius: 5px;
            width: 100%;
            margin-bottom: 10px;
            transition: all 0.3s ease;
        }
        .sidebar button:hover {
            background: white;
            color: var(--primary);
        }

        /* Timeline and Legend */
        .timeline-container {
            background: var(--card-bg);
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 8px var(--shadow);
            margin-bottom: 20px;
        }
        .legend {
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            padding: 10px;
            background: var(--card-bg);
            border-radius: 8px;
            box-shadow: 0 2px 8px var(--shadow);
            margin-top: 15px;
        }
        .legend-item {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 14px;
        }
        .legend-color {
            width: 16px;
            height: 16px;
            border-radius: 4px;
        }

        /* Responsive Design */
        @media (max-width: 768px) {
            .sidebar {
                position: static;
                width: 100%;
                height: auto;
                margin-bottom: 20px;
            }
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
        "weather_factor": float(DEFAULT_WEATHER_DOWNTIME),
        "day_rate": 25000.0
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def load_sample_data():
    st.session_state.vessels = [
        Vessel("Orca Explorer", 100.0, 5.0, datetime.date(2025, 6, 4), 2.0, 3.0, 1.0).to_dict(),
        Vessel("Sea Hawk", 150.0, 4.5, datetime.date(2025, 6, 5), 1.5, 2.5, 0.5).to_dict()
    ]
    st.session_state.tasks = [
        Task("Sediment Sampling", "Survey", datetime.date(2025, 6, 4), datetime.date(2025, 6, 5), st.session_state.vessels[0]["id"], True, 5000.0).to_dict(),
        Task("Equipment Check", "Maintenance", datetime.date(2025, 6, 6), datetime.date(2025, 6, 6), st.session_state.vessels[1]["id"], False, 2000.0).to_dict()
    ]
    st.session_state.project_name = "Sample Survey"
    st.session_state.unsurveyed_km = 250.0
    calculate_surveyed_km()
    st.rerun()

def reset_session():
    init_session_state()
    st.cache_data.clear()  # Clear cached data
    st.rerun()

# --- Helper Functions ---
def validate_vessel(name: str, line_km: float, speed: float, transit_days: float,
                   weather_days: float, maintenance_days: float) -> List[str]:
    errors = []
    if not name.strip():
        errors.append("Vessel name cannot be empty.")
    if any(v['name'] == name for v in st.session_state.vessels):
        errors.append(f"Vessel '{name}' already exists.")
    if line_km <= 0:
        errors.append("Line kilometers must be positive.")
    if speed <= 0:
        errors.append("Speed must be positive.")
    if transit_days < 0 or weather_days < 0 or maintenance_days < 0:
        errors.append("Contingency days cannot be negative.")
    return errors

def validate_task(task: Dict) -> List[str]:
    errors = []
    if not task['name'].strip():
        errors.append("Task name cannot be empty.")
    start_date = pd.to_datetime(task['start_date'], errors='coerce').date()
    end_date = pd.to_datetime(task['end_date'], errors='coerce').date()
    if pd.isna(start_date) or pd.isna(end_date):
        errors.append("Invalid date format.")
    elif start_date > end_date:
        errors.append("End date must be after start date.")
    if task['vessel_id']:
        vessel = next((v for v in st.session_state.vessels if v['id'] == task['vessel_id']), None)
        if not vessel:
            errors.append("Assigned vessel does not exist.")
        else:
            vessel_start = pd.to_datetime(vessel['start_date'], errors='coerce').date()
            vessel_end = pd.to_datetime(vessel['end_date'], errors='coerce').date()
            if pd.isna(vessel_start) or pd.isna(vessel_end):
                errors.append("Invalid vessel date format.")
            elif start_date < vessel_start or end_date > vessel_end:
                errors.append("Task dates outside vessel's operational period.")
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
def build_timeline_data(vessels: List[Dict], tasks: List[Dict], _cache_key: str) -> pd.DataFrame:
    timeline_data = []
    for vessel in vessels:
        survey_start = pd.to_datetime(vority['start_date'], errors='coerce')
        survey_end = pd.to_datetime(vessel['end_date'], errors='coerce')
        if pd.isna(survey_start) or pd.isna(survey_end):
            continue
        pauses = sorted(
            [t for t in tasks if t['vessel_id'] == vessel['id'] and t['pause_survey']],
            key=lambda t: pd.to_datetime(t['start_date'])
        )
        current_start = survey_start
        for pause in pauses:
            pause_start = pd.to_datetime(pause['start_date'], errors='coerce')
            pause_end = pd.to_datetime(pause['end_date'], errors='coerce')
            if pd.isna(pause_start) or pd.isna(pause_end):
                continue
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
        start = pd.to_datetime(task['start_date'], errors='coerce')
        end = pd.to_datetime(task['end_date'], errors='coerce')
        if pd.isna(start) or pd.isna(end):
            continue
        timeline_data.append({
            "Task": task['name'],
            "Start": start,
            "Finish": end,
            "Resource": "Unassigned",
            "Type": task['type'],
            "Details": task.get('notes', ''),
            "Progress": 0
        })
    return pd.DataFrame(timeline_data)

# --- UI Components ---
def show_project_header():
    st.markdown('<div class="stHeader"><h1><i class="fas fa-water"></i> Hydrographic Survey Estimator Pro</h1></div>', unsafe_allow_html=True)
    calculate_surveyed_km()
    progress = calculate_project_progress()
    total_cost = calculate_project_cost()
    total_days = sum(v['total_days'] for v in st.session_state.vessels)

    cols = st.columns(4)
    with cols[0]:
        st.markdown('<div class="stMetric">', unsafe_allow_html=True)
        st.metric("Project Progress", f"{progress:.1f}%")
        st.markdown(f'<div class="progress-bar" style="width: {progress}%;"></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with cols[1]:
        st.markdown('<div class="stMetric">', unsafe_allow_html=True)
        st.metric("Surveyed Line Km", f"{st.session_state.surveyed_km:.1f} km")
        st.markdown('</div>', unsafe_allow_html=True)
    with cols[2]:
        st.markdown('<div class="stMetric">', unsafe_allow_html=True)
        st.metric("Estimated Duration", f"{total_days:.1f} days")
        st.markdown('</div>', unsafe_allow_html=True)
    with cols[3]:
        st.markdown('<div class="stMetric">', unsafe_allow_html=True)
        st.metric("Estimated Cost", f"${total_cost:,.2f}")
        st.markdown('</div>', unsafe_allow_html=True)

def vessel_form(edit_vessel: Optional[Dict] = None):
    is_edit = edit_vessel is not None
    with st.expander(f"🚢 {'Edit Vessel' if is_edit else 'Add New Vessel'}", expanded=False):
        with st.form(f"vessel_form_{edit_vessel['id'] if is_edit else 'new'}"):
            col1, col2 = st.columns([3, 2])
            with col1:
                vessel_name = st.text_input("Vessel Name*", value=edit_vessel['name'] if is_edit else "", placeholder="e.g. Orca Explorer")
                line_km = st.number_input("Line Km*", min_value=0.1, step=1.0, value=float(edit_vessel['line_km']) if is_edit else 100.0)
            with col2:
                speed = st.number_input("Speed (knots)*", min_value=0.1, step=0.1, value=float(edit_vessel['speed'] if is_edit else DEFAULT_SURVEY_SPEED))
                start_date = st.date_input("Start Date*", value=pd.to_datetime(edit_vessel['start_date']).date() if is_edit else datetime.datetime.now().date())
            st.markdown("**Contingency Days**")
            col3, col4, col5 = st.columns(3)
            with col3:
                transit_days = st.number_input("Transit Days", min_value=0.0, step=0.5, value=float(edit_vessel['transit_days'] if is_edit else 2.0))
            with col4:
                weather_days = st.number_input("Weather Days", min_value=0.0, step=0.5, value=float(edit_vessel['weather_days'] if is_edit else 3.0))
            with col5:
                maintenance_days = st.number_input("Maintenance Days", min_value=0.0, step=0.5, value=float(edit_vessel['maintenance_days'] if is_edit else 1.0))

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
                start_date = st.date_input("Start Date*", value=pd.to_datetime(edit_task['start_date']).date() if is_edit else datetime.datetime.now().date())
                end_date = st.date_input("End Date*", value=pd.to_datetime(edit_task['end_date']).date() if is_edit else datetime.datetime.now().date() + datetime.timedelta(days=1))
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
                pause_survey = st.checkbox("Pause Survey Operations