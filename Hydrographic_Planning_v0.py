import streamlit as st
import datetime
import pandas as pd
import plotly.express as px
import json
from uuid import uuid4
from io import BytesIO
from typing import List, Dict, Optional, Tuple
import math

# Constants
DEFAULT_SURVEY_SPEED = 5.0  # knots
DEFAULT_WEATHER_DOWNTIME = 15.0  # percentage
COLOR_MAP = {
    "Survey": "#2E86AB",
    "Maintenance": "#A23B72",
    "Delay": "#DB504A",
    "Sediment Sample": "#48A14D",
    "Deployment": "#6A4C93",
    "Recovery": "#8D6E63",
    "Other": "#6B7280",
    "Weather Downtime": "#3B1F2B",
    "Transit": "#3D5A6C"
}

# --- Custom Theme and CSS ---
st.set_page_config(
    page_title="Hydrographic Survey Estimator Pro",
    layout="wide",
    page_icon="🌊"
)

st.markdown("""
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
    <style>
        /* 1. Overall Dark-Navy Background & White Text */
        html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
            background: #0B1D3A;      /* very dark navy */
            color: #FFFFFF;           /* always white text */
            font-family: 'Arial', sans-serif;
        }

        /* 2. Header Styling */
        .header-container {
            width: 100%;
            background: linear-gradient(135deg, #1E40AF, #3B82F6);
            padding: 25px 40px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.2);
            border-radius: 8px;
            text-align: center;
        }
        .header-container h1 {
            margin: 0;
            font-size: 2.5rem;
            color: #FFFFFF;
        }
        .header-container p.subtitle {
            margin: 5px 0 0 0;
            font-size: 1.1rem;
            color: #E0E0E0;
        }

        /* 3. Metrics Container Flexbox */
        .metrics-container {
            display: flex;
            gap: 15px;
            justify-content: space-between;
            margin-bottom: 25px;
            flex-wrap: wrap;
        }
        .metric-card {
            background: rgba(255,255,255,0.08);
            padding: 15px;
            border-radius: 8px;
            flex: 1;
            min-width: 150px;
            text-align: center;
            transition: transform 0.2s;
            border-left: 4px solid #3B82F6;
        }
        .metric-card:hover {
            transform: scale(1.03);
        }
        .metric-card h3 {
            margin: 0 0 5px 0;
            font-size: 0.9rem;
            color: #E0E0E0;
        }
        .metric-card .value {
            font-size: 1.4rem;
            font-weight: bold;
            color: #FFFFFF;
        }
        .metric-card .subtext {
            font-size: 0.8rem;
            color: #B0B0B0;
            margin-top: 5px;
        }

        /* 4. Section Styling */
        .section {
            background: rgba(255,255,255,0.05);
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            border-left: 4px solid #1E40AF;
        }
        .section-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        .section-header h2 {
            margin: 0;
            color: #FFFFFF;
            font-size: 1.5rem;
        }
        .section-header .icon {
            font-size: 1.5rem;
            color: #3B82F6;
        }

        /* 5. Input Fields */
        .stTextInput > label, .stNumberInput > label, .stSelectbox > label, 
        .stDateInput > label, .stTextArea > label, .stCheckbox > label {
            color: #FFFFFF !important;
            font-size: 0.95rem;
            font-weight: 500;
        }
        .stTextInput input, .stNumberInput input, 
        .stSelectbox select, .stTextArea textarea {
            background: #F5F5F5 !important;
            color: #000000 !important;
            border: none !important;
            border-radius: 6px !important;
            padding: 10px !important;
        }
        .stDateInput input {
            background: #F5F5F5 !important;
            color: #000000 !important;
            border: none !important;
            border-radius: 6px !important;
            padding: 8px !important;
        }

        /* 6. Button Styling */
        .stButton > button {
            background: linear-gradient(135deg, #1E40AF, #3B82F6) !important;
            color: #FFFFFF !important;
            border: none !important;
            font-weight: 600;
            padding: 10px 20px !important;
            border-radius: 6px !important;
            transition: all 0.2s;
            width: 100%;
        }
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }
        .secondary-button {
            background: rgba(255,255,255,0.1) !important;
        }
        .danger-button {
            background: linear-gradient(135deg, #DC2626, #EF4444) !important;
        }

        /* 7. Card Styling */
        .card {
            background: rgba(255,255,255,0.08);
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 15px;
            border-left: 4px solid #3B82F6;
        }
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }
        .card-title {
            margin: 0;
            color: #FFFFFF;
            font-size: 1.1rem;
        }
        .card-body {
            color: #E0E0E0;
            font-size: 0.9rem;
        }
        .card-footer {
            margin-top: 10px;
            font-size: 0.8rem;
            color: #B0B0B0;
        }
        .card-actions {
            display: flex;
            gap: 8px;
        }

        /* 8. Timeline Styling */
        .timeline-container {
            margin-top: 20px;
        }
        .timeline-actions {
            display: flex;
            justify-content: flex-end;
            gap: 10px;
            margin-bottom: 10px;
        }

        /* 9. Tooltip Styling */
        .tooltip-icon {
            color: #3B82F6 !important;
            font-size: 1rem;
            margin-left: 5px;
            cursor: pointer;
        }

        /* 10. Responsive Adjustments */
        @media (max-width: 768px) {
            .metrics-container {
                flex-direction: column;
            }
            .metric-card {
                width: 100%;
                margin-bottom: 10px;
            }
        }
    </style>
""", unsafe_allow_html=True)

# --- Data Models ---
class Project:
    def __init__(self, name: str, line_km: float, infill_percent: float, id: Optional[str] = None):
        self.id = id or str(uuid4())
        self.name = name
        self.line_km = line_km
        self.infill_percent = infill_percent
        self.created_at = datetime.datetime.now().isoformat()
        self.updated_at = self.created_at

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "line_km": self.line_km,
            "infill_percent": self.infill_percent,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

class Vessel:
    def __init__(self, name: str, line_km: float, speed: float, start_date: datetime.date,
                 transit: float, transit_unit: str, weather: float, weather_unit: str, 
                 maintenance: float, maintenance_unit: str, id: Optional[str] = None):
        self.id = id or str(uuid4())
        self.name = name
        self.line_km = line_km
        self.speed = speed
        self.start_date = start_date
        
        # Convert all time units to days for calculations
        self.transit_days = self._convert_to_days(transit, transit_unit)
        self.weather_days = self._convert_to_days(weather, weather_unit)
        self.maintenance_days = self._convert_to_days(maintenance, maintenance_unit)
        
        self.survey_days = self.calculate_survey_days()
        self.total_days = self.calculate_total_days()
        self.end_date = self.calculate_end_date()
        self.daily_progress = self.line_km / self.total_days if self.total_days > 0 else 0

    def _convert_to_days(self, value: float, unit: str) -> float:
        if unit == "hours":
            return value / 24
        return value  # already in days

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
            "transit_days": self.transit_days,
            "weather_days": self.weather_days,
            "maintenance_days": self.maintenance_days,
            "survey_days": self.survey_days,
            "total_days": self.total_days,
            "end_date": str(self.end_date),
            "daily_progress": self.daily_progress
        }

class Task:
    def __init__(self, name: str, task_type: str, start_date: datetime.date, end_date: datetime.date,
                 vessel_id: Optional[str] = None, pause_survey: bool = False, notes: str = "", id: Optional[str] = None):
        self.id = id or str(uuid4())
        self.name = name
        self.type = task_type
        self.start_date = start_date
        self.end_date = end_date
        self.vessel_id = vessel_id
        self.pause_survey = pause_survey
        self.notes = notes
        self.duration = (end_date - start_date).days + 1

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "start_date": str(self.start_date),
            "end_date": str(self.end_date),
            "vessel_id": self.vessel_id,
            "pause_survey": self.pause_survey,
            "notes": self.notes,
            "duration": self.duration
        }

# --- Session State Initialization ---
def init_session_state():
    defaults = {
        "projects": [],
        "current_project": None,
        "vessels": [],
        "tasks": [],
        "day_rate": 25000.0,
        "show_project_form": False,
        "show_vessel_form": False,
        "show_task_form": False
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# --- Helper Functions ---
def validate_project(name: str, line_km: float, infill_percent: float) -> List[str]:
    errors = []
    if not name.strip():
        errors.append("Project name cannot be empty")
    if line_km <= 0:
        errors.append("Line kilometers must be positive")
    if infill_percent < 0 or infill_percent > 100:
        errors.append("Infill percentage must be between 0 and 100")
    return errors

def validate_vessel(name: str, line_km: float, speed: float) -> List[str]:
    errors = []
    if not name.strip():
        errors.append("Vessel name cannot be empty")
    if line_km <= 0:
        errors.append("Line kilometers must be positive")
    if speed <= 0:
        errors.append("Speed must be positive")
    return errors

def validate_task(name: str, start_date: datetime.date, end_date: datetime.date) -> List[str]:
    errors = []
    if not name.strip():
        errors.append("Task name cannot be empty")
    if start_date > end_date:
        errors.append("End date must be after start date")
    return errors

def calculate_surveyed_km() -> float:
    return sum(v['line_km'] for v in st.session_state.vessels)

def calculate_project_progress() -> float:
    if not st.session_state.current_project:
        return 0.0
    total_surveyed = calculate_surveyed_km()
    total_required = st.session_state.current_project['line_km'] * (1 + st.session_state.current_project['infill_percent'] / 100)
    if total_required > 0:
        return min(100, (total_surveyed / total_required) * 100)
    return 0.0

def calculate_project_cost() -> float:
    vessel_days = sum(v['total_days'] for v in st.session_state.vessels)
    return vessel_days * st.session_state.day_rate

def calculate_project_duration() -> Tuple[float, datetime.date, datetime.date]:
    if not st.session_state.vessels:
        return 0.0, None, None
    
    start_dates = [pd.to_datetime(v['start_date']).date() for v in st.session_state.vessels]
    end_dates = [pd.to_datetime(v['end_date']).date() for v in st.session_state.vessels]
    
    project_start = min(start_dates)
    project_end = max(end_dates)
    total_days = (project_end - project_start).days + 1
    
    return total_days, project_start, project_end

def get_vessel_name(vessel_id: str) -> str:
    if not vessel_id:
        return "Unassigned"
    vessel = next((v for v in st.session_state.vessels if v['id'] == vessel_id), None)
    return vessel['name'] if vessel else "Unknown Vessel"

@st.cache_data
def build_timeline_data(vessels: List[Dict], tasks: List[Dict]) -> pd.DataFrame:
    timeline_data = []
    
    # Add vessel operations first
    for vessel in vessels:
        survey_start = pd.to_datetime(vessel['start_date'])
        survey_end = pd.to_datetime(vessel['end_date'])
        
        # Add transit time if it exists
        if vessel['transit_days'] > 0:
            transit_end = survey_start + datetime.timedelta(days=vessel['transit_days'])
            timeline_data.append({
                "Task": f"Transit: {vessel['name']}",
                "Start": survey_start,
                "Finish": transit_end,
                "Resource": vessel['name'],
                "Type": "Transit",
                "Details": f"Transit to survey area",
                "Duration": vessel['transit_days']
            })
            survey_start = transit_end
        
        # Gather any tasks that pause this vessel's survey
        pauses = sorted(
            [t for t in tasks if t['vessel_id'] == vessel['id'] and t['pause_survey']],
            key=lambda t: pd.to_datetime(t['start_date'])
        )

        current_start = survey_start
        for pause in pauses:
            pause_start = pd.to_datetime(pause['start_date'])
            pause_end = pd.to_datetime(pause['end_date'])
            
            # Add survey segment before pause if it exists
            if pause_start > current_start:
                survey_segment_days = (pause_start - current_start).days
                timeline_data.append({
                    "Task": f"Survey: {vessel['name']}",
                    "Start": current_start,
                    "Finish": pause_start,
                    "Resource": vessel['name'],
                    "Type": "Survey",
                    "Details": f"{vessel['line_km']} km at {vessel['speed']} knots",
                    "Duration": survey_segment_days
                })
            
            # Add the pause task
            timeline_data.append({
                "Task": pause['name'],
                "Start": pause_start,
                "Finish": pause_end,
                "Resource": vessel['name'],
                "Type": pause['type'],
                "Details": pause.get('notes', ''),
                "Duration": pause['duration']
            })
            current_start = pause_end
        
        # Add remaining survey segment after pauses
        if current_start < survey_end:
            remaining_survey_days = (survey_end - current_start).days
            timeline_data.append({
                "Task": f"Survey: {vessel['name']}",
                "Start": current_start,
                "Finish": survey_end,
                "Resource": vessel['name'],
                "Type": "Survey",
                "Details": f"{vessel['line_km']} km at {vessel['speed']} knots",
                "Duration": remaining_survey_days
            })

    # Add unassigned tasks
    for task in [t for t in tasks if not t['vessel_id']]:
        timeline_data.append({
            "Task": task['name'],
            "Start": pd.to_datetime(task['start_date']),
            "Finish": pd.to_datetime(task['end_date']),
            "Resource": "Unassigned",
            "Type": task['type'],
            "Details": task.get('notes', ''),
            "Duration": task['duration']
        })

    return pd.DataFrame(timeline_data)

def export_to_json() -> str:
    export_data = {
        "project": st.session_state.current_project,
        "vessels": st.session_state.vessels,
        "tasks": st.session_state.tasks,
        "day_rate": st.session_state.day_rate,
        "exported_at": datetime.datetime.now().isoformat()
    }
    return json.dumps(export_data, indent=2)

def export_to_excel() -> BytesIO:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        # Project sheet
        project_df = pd.DataFrame([st.session_state.current_project])
        project_df.to_excel(writer, sheet_name="Project", index=False)
        
        # Vessels sheet
        vessels_df = pd.DataFrame(st.session_state.vessels)
        vessels_df.to_excel(writer, sheet_name="Vessels", index=False)
        
        # Tasks sheet
        tasks_df = pd.DataFrame(st.session_state.tasks)
        tasks_df.to_excel(writer, sheet_name="Tasks", index=False)
        
        # Settings sheet
        settings_df = pd.DataFrame([{"day_rate": st.session_state.day_rate}])
        settings_df.to_excel(writer, sheet_name="Settings", index=False)
    
    return output.getvalue()

def import_from_json(uploaded_file):
    try:
        data = json.load(uploaded_file)
        
        required_project_fields = ["id", "name", "line_km", "infill_percent"]
        if not all(field in data.get("project", {}) for field in required_project_fields):
            raise ValueError("Invalid project data in JSON")
        
        st.session_state.current_project = data["project"]
        st.session_state.vessels = data.get("vessels", [])
        st.session_state.tasks = data.get("tasks", [])
        st.session_state.day_rate = data.get("day_rate", 25000.0)
        
        st.success("Project imported successfully!")
        st.experimental_rerun()
    except Exception as e:
        st.error(f"Error importing project: {str(e)}")

def import_from_excel(uploaded_file):
    try:
        xls = pd.ExcelFile(uploaded_file)
        
        # Load project
        if "Project" in xls.sheet_names:
            project_df = xls.parse("Project")
            st.session_state.current_project = project_df.iloc[0].to_dict()
        
        # Load vessels
        if "Vessels" in xls.sheet_names:
            vessels_df = xls.parse("Vessels")
            st.session_state.vessels = vessels_df.to_dict(orient="records")
        
        # Load tasks
        if "Tasks" in xls.sheet_names:
            tasks_df = xls.parse("Tasks")
            st.session_state.tasks = tasks_df.to_dict(orient="records")
        
        # Load settings
        if "Settings" in xls.sheet_names:
            settings_df = xls.parse("Settings")
            st.session_state.day_rate = settings_df.iloc[0].get("day_rate", 25000.0)
        
        st.success("Project imported successfully!")
        st.experimental_rerun()
    except Exception as e:
        st.error(f"Error importing project: {str(e)}")

# --- UI Components ---
def show_project_header():
    st.markdown("""
        <div class="header-container">
            <h1><i class="fas fa-water"></i> Hydrographic Survey Estimator</h1>
            <p class="subtitle">Plan and optimize your hydrographic survey operations</p>
        </div>
    """, unsafe_allow_html=True)

def show_project_metrics():
    surveyed_km = calculate_surveyed_km()
    progress = calculate_project_progress()
    total_cost = calculate_project_cost()
    total_days, start_date, end_date = calculate_project_duration()
    
    st.markdown('<div class="metrics-container">', unsafe_allow_html=True)
    
    # Project Progress
    st.markdown(f"""
        <div class="metric-card">
            <h3>Project Progress</h3>
            <div class="value">{progress:.1f}%</div>
            <div class="subtext">{surveyed_km:.1f} km of {st.session_state.current_project['line_km'] * (1 + st.session_state.current_project['infill_percent']/100):.1f} km</div>
        </div>
    """, unsafe_allow_html=True)
    
    # Estimated Cost
    st.markdown(f"""
        <div class="metric-card">
            <h3>Estimated Cost</h3>
            <div class="value">${total_cost:,.0f}</div>
            <div class="subtext">Day rate: ${st.session_state.day_rate:,.0f}</div>
        </div>
    """, unsafe_allow_html=True)
    
    # Project Duration
    duration_text = f"{total_days} days" if total_days > 0 else "N/A"
    date_range = f"{start_date.strftime('%b %d')} - {end_date.strftime('%b %d')}" if start_date and end_date else "N/A"
    st.markdown(f"""
        <div class="metric-card">
            <h3>Project Duration</h3>
            <div class="value">{duration_text}</div>
            <div class="subtext">{date_range}</div>
        </div>
    """, unsafe_allow_html=True)
    
    # Vessels Count
    st.markdown(f"""
        <div class="metric-card">
            <h3>Vessels</h3>
            <div class="value">{len(st.session_state.vessels)}</div>
            <div class="subtext">{len(st.session_state.tasks)} tasks scheduled</div>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

def project_form(edit_project: Optional[Dict] = None):
    is_edit = edit_project is not None
    title = "Edit Project" if is_edit else "Create New Project"
    
    with st.form(f"project_form_{edit_project['id']}" if is_edit else "project_form_new"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input(
                "Project Name*",
                value=edit_project['name'] if is_edit else "",
                placeholder="e.g. North Sea Survey 2025"
            )
        with col2:
            line_km = st.number_input(
                "Total Line Km*",
                min_value=0.1,
                step=1.0,
                value=float(edit_project['line_km']) if is_edit else 100.0
            )
        
        infill_percent = st.slider(
            "Infill Percentage",
            min_value=0,
            max_value=100,
            value=int(edit_project['infill_percent']) if is_edit else 10,
            help="Additional coverage percentage to account for re-surveys and quality control"
        )
        
        submit_button = st.form_submit_button("Save Project" if is_edit else "Create Project")
        
        if submit_button:
            errors = validate_project(name, line_km, infill_percent)
            if errors:
                for err in errors:
                    st.error(err)
            else:
                project = Project(name, line_km, infill_percent, edit_project['id'] if is_edit else None)
                if is_edit:
                    # Update existing project
                    st.session_state.projects = [
                        p for p in st.session_state.projects 
                        if p['id'] != edit_project['id']
                    ]
                    st.session_state.projects.append(project.to_dict())
                    st.session_state.current_project = project.to_dict()
                else:
                    # Add new project
                    st.session_state.projects.append(project.to_dict())
                    st.session_state.current_project = project.to_dict()
                
                st.success(f"Project '{name}' {'updated' if is_edit else 'created'} successfully!")
                st.session_state.show_project_form = False
                st.experimental_rerun()

def vessel_form(edit_vessel: Optional[Dict] = None):
    is_edit = edit_vessel is not None
    title = "Edit Vessel" if is_edit else "Add New Vessel"
    
    with st.form(f"vessel_form_{edit_vessel['id']}" if is_edit else "vessel_form_new"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input(
                "Vessel Name*",
                value=edit_vessel['name'] if is_edit else "",
                placeholder="e.g. Ocean Explorer"
            )
            speed = st.number_input(
                "Survey Speed (knots)*",
                min_value=0.1,
                step=0.1,
                value=float(edit_vessel['speed']) if is_edit else DEFAULT_SURVEY_SPEED
            )
        with col2:
            line_km = st.number_input(
                "Line Km to Survey*",
                min_value=0.1,
                step=1.0,
                value=float(edit_vessel['line_km']) if is_edit else 100.0
            )
            start_date = st.date_input(
                "Start Date*",
                value=pd.to_datetime(edit_vessel['start_date']).date() if is_edit else datetime.date.today()
            )
        
        st.markdown("**Contingency Time**")
        col3, col4, col5 = st.columns(3)
        with col3:
            transit = st.number_input(
                "Transit Time",
                min_value=0.0,
                step=0.5,
                value=1.0
            )
            transit_unit = st.selectbox(
                "Transit Unit",
                ["days", "hours"],
                index=0
            )
        with col4:
            weather = st.number_input(
                "Weather Downtime",
                min_value=0.0,
                step=0.5,
                value=3.0
            )
            weather_unit = st.selectbox(
                "Weather Unit",
                ["days", "hours"],
                index=0
            )
        with col5:
            maintenance = st.number_input(
                "Maintenance Time",
                min_value=0.0,
                step=0.5,
                value=1.0
            )
            maintenance_unit = st.selectbox(
                "Maintenance Unit",
                ["days", "hours"],
                index=0
            )
        
        submit_button = st.form_submit_button("Update Vessel" if is_edit else "Add Vessel")
        
        if submit_button:
            errors = validate_vessel(name, line_km, speed)
            if errors:
                for err in errors:
                    st.error(err)
            else:
                vessel = Vessel(
                    name=name,
                    line_km=line_km,
                    speed=speed,
                    start_date=start_date,
                    transit=transit,
                    transit_unit=transit_unit,
                    weather=weather,
                    weather_unit=weather_unit,
                    maintenance=maintenance,
                    maintenance_unit=maintenance_unit,
                    id=edit_vessel['id'] if is_edit else None
                )
                
                if is_edit:
                    st.session_state.vessels = [
                        v for v in st.session_state.vessels
                        if v['id'] != edit_vessel['id']
                    ]
                
                st.session_state.vessels.append(vessel.to_dict())
                st.success(f"Vessel '{name}' {'updated' if is_edit else 'added'} successfully!")
                st.session_state.show_vessel_form = False
                st.experimental_rerun()

def task_form(edit_task: Optional[Dict] = None):
    is_edit = edit_task is not None
    title = "Edit Task" if is_edit else "Add New Task"
    
    with st.form(f"task_form_{edit_task['id']}" if is_edit else "task_form_new"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input(
                "Task Name*",
                value=edit_task['name'] if is_edit else "",
                placeholder="e.g. Sediment Sampling"
            )
            
            task_type = st.selectbox(
                "Task Type*",
                ["Survey", "Maintenance", "Delay", "Sediment Sample", "Deployment", "Recovery", "Other"],
                index=0
            )
        with col2:
            start_date = st.date_input(
                "Start Date*",
                value=pd.to_datetime(edit_task['start_date']).date() if is_edit else datetime.date.today()
            )
            end_date = st.date_input(
                "End Date*",
                value=pd.to_datetime(edit_task['end_date']).date() if is_edit else datetime.date.today() + datetime.timedelta(days=1)
            )
        
        # Vessel assignment
        vessel_options = [("Unassigned", None)] + [(v['name'], v['id']) for v in st.session_state.vessels]
        default_index = 0
        if is_edit:
            for i, opt in enumerate(vessel_options):
                if opt[1] == edit_task.get('vessel_id'):
                    default_index = i
                    break
        
        selected_vessel = st.selectbox(
            "Assigned Vessel",
            vessel_options,
            index=default_index,
            format_func=lambda x: x[0]
        )
        vessel_id = selected_vessel[1]
        
        pause_survey = st.checkbox(
            "Pause Survey Operations",
            value=edit_task.get('pause_survey', False) if is_edit else False,
            help="If checked, survey operations will be paused during this task"
        )
        
        notes = st.text_area(
            "Notes",
            value=edit_task.get('notes', '') if is_edit else "",
            placeholder="Additional details about this task..."
        )
        
        submit_button = st.form_submit_button("Update Task" if is_edit else "Add Task")
        
        if submit_button:
            errors = validate_task(name, start_date, end_date)
            if errors:
                for err in errors:
                    st.error(err)
            else:
                task = Task(
                    name=name,
                    task_type=task_type,
                    start_date=start_date,
                    end_date=end_date,
                    vessel_id=vessel_id,
                    pause_survey=pause_survey,
                    notes=notes,
                    id=edit_task['id'] if is_edit else None
                )
                
                if is_edit:
                    st.session_state.tasks = [
                        t for t in st.session_state.tasks
                        if t['id'] != edit_task['id']
                    ]
                
                st.session_state.tasks.append(task.to_dict())
                st.success(f"Task '{name}' {'updated' if is_edit else 'added'} successfully!")
                st.session_state.show_task_form = False
                st.experimental_rerun()

def show_projects_section():
    with st.container():
        st.markdown('<div class="section">', unsafe_allow_html=True)
        st.markdown("""
            <div class="section-header">
                <h2><i class="fas fa-folder-open"></i> Projects</h2>
            </div>
        """, unsafe_allow_html=True)
        
        if st.session_state.current_project:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"""
                    <div class="card">
                        <div class="card-header">
                            <h3 class="card-title">{st.session_state.current_project['name']}</h3>
                        </div>
                        <div class="card-body">
                            <strong>Line Km:</strong> {st.session_state.current_project['line_km']:.1f} km<br>
                            <strong>Infill:</strong> {st.session_state.current_project['infill_percent']}%<br>
                            <strong>Total Required:</strong> {st.session_state.current_project['line_km'] * (1 + st.session_state.current_project['infill_percent']/100):.1f} km
                        </div>
                        <div class="card-footer">
                            Created: {pd.to_datetime(st.session_state.current_project['created_at']).strftime('%Y-%m-%d')}
                        </div>
                    </div>
                """, unsafe_allow_html=True)
            with col2:
                if st.button("Edit Project", key="edit_project_btn"):
                    st.session_state.show_project_form = True
                if st.button("New Project", key="new_project_btn"):
                    st.session_state.current_project = None
                    st.session_state.vessels = []
                    st.session_state.tasks = []
                    st.session_state.show_project_form = True
        else:
            if st.button("Create New Project", key="create_project_btn"):
                st.session_state.show_project_form = True
        
        if st.session_state.show_project_form:
            project_form(st.session_state.current_project if st.session_state.current_project else None)
        
        st.markdown('</div>', unsafe_allow_html=True)

def show_vessels_section():
    with st.container():
        st.markdown('<div class="section">', unsafe_allow_html=True)
        st.markdown("""
            <div class="section-header">
                <h2><i class="fas fa-ship"></i> Vessels</h2>
                <button class="stButton" onclick="window.streamlitSessionState.set({'show_vessel_form': true});">Add Vessel</button>
            </div>
        """, unsafe_allow_html=True)
        
        if st.session_state.show_vessel_form:
            vessel_form({} if not st.session_state.vessels else None)
        
        if not st.session_state.vessels:
            st.info("No vessels added yet. Add your first vessel to begin.")
        else:
            for vessel in st.session_state.vessels:
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(f"""
                        <div class="card">
                            <div class="card-header">
                                <h3 class="card-title">{vessel['name']}</h3>
                            </div>
                            <div class="card-body">
                                <strong>Survey:</strong> {vessel['line_km']:.1f} km at {vessel['speed']} knots<br>
                                <strong>Schedule:</strong> {vessel['start_date']} to {vessel['end_date']} ({vessel['total_days']} days)<br>
                                <strong>Contingencies:</strong> Transit: {vessel['transit_days']}d | Weather: {vessel['weather_days']}d | Maint: {vessel['maintenance_days']}d
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                with col2:
                    if st.button("Edit", key=f"edit_vessel_{vessel['id']}"):
                        st.session_state.show_vessel_form = True
                        st.session_state.editing_vessel = vessel
                    if st.button("Delete", key=f"delete_vessel_{vessel['id']}"):
                        st.session_state.vessels = [v for v in st.session_state.vessels if v['id'] != vessel['id']]
                        st.session_state.tasks = [t for t in st.session_state.tasks if t['vessel_id'] != vessel['id']]
                        st.success(f"Vessel '{vessel['name']}' deleted successfully!")
                        st.experimental_rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)

def show_tasks_section():
    with st.container():
        st.markdown('<div class="section">', unsafe_allow_html=True)
        st.markdown("""
            <div class="section-header">
                <h2><i class="fas fa-tasks"></i> Tasks</h2>
                <button class="stButton" onclick="window.streamlitSessionState.set({'show_task_form': true});">Add Task</button>
            </div>
        """, unsafe_allow_html=True)
        
        if st.session_state.show_task_form:
            task_form({} if not st.session_state.tasks else None)
        
        if not st.session_state.tasks:
            st.info("No tasks added yet. Add your first task to begin.")
        else:
            # Filters
            col1, col2, col3 = st.columns(3)
            with col1:
                filter_type = st.selectbox("Filter by Type", ["All"] + sorted(list({t['type'] for t in st.session_state.tasks})))
            with col2:
                filter_vessel = st.selectbox("Filter by Vessel", ["All"] + [v['name'] for v in st.session_state.vessels])
            with col3:
                filter_date = st.selectbox("Filter by Date", ["All", "Upcoming", "Past", "Current"])
            
            # Apply filters
            filtered_tasks = st.session_state.tasks.copy()
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
            
            # Display filtered tasks
            for task in filtered_tasks:
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(f"""
                        <div class="card">
                            <div class="card-header">
                                <h3 class="card-title">{task['name']}</h3>
                                <span style="color: {COLOR_MAP.get(task['type'], '#6B7280')}; font-weight: 500;">{task['type']}</span>
                            </div>
                            <div class="card-body">
                                <strong>Dates:</strong> {task['start_date']} to {task['end_date']} ({task['duration']} days)<br>
                                <strong>Vessel:</strong> {get_vessel_name(task['vessel_id'])}<br>
                                {task['notes'] if task['notes'] else ''}
                            </div>
                            <div class="card-footer">
                                {("⚠️ Pauses Survey Operations" if task['pause_survey'] else "")}
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                with col2:
                    if st.button("Edit", key=f"edit_task_{task['id']}"):
                        st.session_state.show_task_form = True
                        st.session_state.editing_task = task
                    if st.button("Delete", key=f"delete_task_{task['id']}"):
                        st.session_state.tasks = [t for t in st.session_state.tasks if t['id'] != task['id']]
                        st.success(f"Task '{task['name']}' deleted successfully!")
                        st.experimental_rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)

def show_timeline_section():
    with st.container():
        st.markdown('<div class="section">', unsafe_allow_html=True)
        st.markdown("""
            <div class="section-header">
                <h2><i class="fas fa-chart-gantt"></i> Project Timeline</h2>
            </div>
        """, unsafe_allow_html=True)
        
        if not st.session_state.vessels and not st.session_state.tasks:
            st.info("Add vessels and tasks to generate the project timeline")
        else:
            df = build_timeline_data(st.session_state.vessels, st.session_state.tasks)
            
            # Timeline controls
            col1, col2 = st.columns([1, 3])
            with col1:
                timeline_mode = st.selectbox("View Mode", ["Days", "Weeks", "Months"], index=0)
            with col2:
                st.markdown('<div class="timeline-actions">', unsafe_allow_html=True)
                if st.button("Zoom to Fit"):
                    pass  # Would be implemented with Plotly
                if st.button("Export Image"):
                    pass  # Would be implemented with Plotly
                st.markdown('</div>', unsafe_allow_html=True)
            
            # Generate the Gantt chart
            fig = px.timeline(
                df,
                x_start="Start",
                x_end="Finish",
                y="Resource",
                color="Type",
                color_discrete_map=COLOR_MAP,
                hover_name="Task",
                hover_data={"Details": True, "Duration": True},
                title="Hydrographic Survey Timeline"
            )
            
            # Update layout for better visualization
            fig.update_yaxes(
                autorange="reversed",
                title_text="",
                showgrid=True,
                gridcolor="rgba(255,255,255,0.1)"
            )
            
            fig.update_xaxes(
                title_text="Timeline",
                showgrid=True,
                gridcolor="rgba(255,255,255,0.1)"
            )
            
            fig.update_layout(
                height=max(400, len(st.session_state.vessels) * 80 + len(st.session_state.tasks) * 30),
                plot_bgcolor="rgba(255,255,255,0.05)",
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="white",
                legend_title_text="Activity Type",
                hoverlabel=dict(
                    bgcolor="rgba(30, 64, 175, 0.9)",
                    font_size=12,
                    font_family="Arial"
                ),
                margin=dict(l=0, r=0, t=40, b=20)
            )
            
            # Adjust timeline view based on selection
            if timeline_mode == "Weeks":
                fig.update_xaxes(
                    tickformat="%Y-%m-%d",
                    dtick="W1"
                )
            elif timeline_mode == "Months":
                fig.update_xaxes(
                    tickformat="%Y-%m",
                    dtick="M1"
                )
            
            st.plotly_chart(fig, use_container_width=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

def show_data_management_section():
    with st.container():
        st.markdown('<div class="section">', unsafe_allow_html=True)
        st.markdown("""
            <div class="section-header">
                <h2><i class="fas fa-database"></i> Data Management</h2>
            </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Export Project**")
            export_name = st.text_input(
                "Export filename",
                value=st.session_state.current_project['name'] if st.session_state.current_project else "survey_project"
            )
            
            # JSON Export
            json_data = export_to_json()
            st.download_button(
                label="Export to JSON",
                data=json_data,
                file_name=f"{export_name}.json",
                mime="application/json"
            )
            
            # Excel Export
            excel_data = export_to_excel()
            st.download_button(
                label="Export to Excel",
                data=excel_data,
                file_name=f"{export_name}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        
        with col2:
            st.markdown("**Import Project**")
            uploaded_file = st.file_uploader(
                "Choose a file",
                type=["json", "xlsx"],
                accept_multiple_files=False,
                key="import_uploader"
            )
            
            if uploaded_file:
                if st.button("Import Project Data"):
                    if uploaded_file.name.endswith(".json"):
                        import_from_json(uploaded_file)
                    elif uploaded_file.name.endswith(".xlsx"):
                        import_from_excel(uploaded_file)
        
        st.markdown('</div>', unsafe_allow_html=True)

# --- Main App Layout ---
def main():
    init_session_state()
    show_project_header()
    
    if st.session_state.current_project:
        show_project_metrics()
        show_projects_section()
        show_vessels_section()
        show_tasks_section()
        show_timeline_section()
        show_data_management_section()
    else:
        show_projects_section()

if __name__ == "__main__":
    main()