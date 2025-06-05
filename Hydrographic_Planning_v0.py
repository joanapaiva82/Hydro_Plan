import streamlit as st
import datetime
import pandas as pd
import plotly.express as px
import json
from uuid import uuid4
from io import BytesIO
from typing import List, Dict, Optional

# ────────────────────────────────────────────────────────────────────────────────
# SESSION STATE INITIALIZATION
# ────────────────────────────────────────────────────────────────────────────────
def init_session_state():
    if "projects" not in st.session_state:
        st.session_state["projects"] = []  # List[Project]
    if "current_project_id" not in st.session_state:
        st.session_state["current_project_id"] = None
    if "editing_vessel" not in st.session_state:
        st.session_state["editing_vessel"] = None  # vessel_id being edited
    if "editing_task" not in st.session_state:
        st.session_state["editing_task"] = None  # task_id being edited

init_session_state()

# ────────────────────────────────────────────────────────────────────────────────
# CONSTANTS & COLOR MAP for the Gantt chart
# ────────────────────────────────────────────────────────────────────────────────
DEFAULT_SURVEY_SPEED = 5.0  # knots

COLOR_MAP = {
    "Survey": "#2E86AB",
    "Maintenance": "#A23B72",
    "Weather": "#3B1F2B",
    "Transit": "#3D5A6C",
    "Delay": "#DB504A",
    "Sediment Sample": "#F18F01",
    "Deployment": "#6A894A",
    "Recovery": "#7D3C98",
    "Other": "#6B7280",
}

# ────────────────────────────────────────────────────────────────────────────────
# CUSTOM CSS (injected once at the top)
# ────────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Hydrographic Survey Estimator",
    layout="wide",
    page_icon="🌊"
)

st.markdown(
    """
    <link rel="stylesheet"
          href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
    <style>
        /* ─────────────────────────────────────────────────────────────────────────── */
        /* 0. Force all st.info() text to white */
        .stInfo * {
            color: #FFFFFF !important;
        }

        /* 1. Force all checkbox labels to white */
        .stCheckbox, .stCheckbox * {
            color: #FFFFFF !important;
        }

        /* 2. Overall Dark‐Navy Background & White Text */
        html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
            background: #0B1D3A;      /* very dark navy */
            color: #FFFFFF;           /* white text */
            font-family: 'Arial', sans-serif;
        }

        /* 3. Header Styling (white background + navy‐blue text) */
        .stHeader {
            width: 100%;
            background: #FFFFFF;        
            padding: 25px 40px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            border-radius: 8px;
        }
        .stHeader h1 {
            margin: 0;
            font-size: 2.5rem;
            color: #0B1D3A;             /* navy‐blue text */
            text-align: center;
            font-weight: 600;
        }

        /* 4. Project Selector Styling (selectbox labels + box) */
        .project-selectbox > label {
            color: #FFFFFF !important;
            font-size: 1rem;
            font-weight: 500;
            margin-bottom: 4px;
        }
        .project-selectbox select {
            background: #F5F5F5 !important;
            color: #000000 !important;
            border-radius: 6px !important;
            padding: 8px !important;
            width: 100% !important;
        }

        /* 5. Section Titles */
        .section-header {
            font-size: 1.3rem;
            font-weight: 600;
            margin-top: 30px;
            margin-bottom: 10px;
            color: #FFFFFF;
            border-left: 4px solid #1D4ED8;
            padding-left: 10px;
        }

        /* 6. Input Fields: White Labels, Light‐Gray Boxes */
        .stTextInput > label,
        .stNumberInput > label,
        .stDateInput > label,
        .stSelectbox > label {
            color: #FFFFFF !important;
            font-size: 0.95rem;
            font-weight: 500;
            margin-bottom: 4px;
        }
        .stTextInput input[type="text"],
        .stNumberInput input[type="number"],
        .stDateInput input[type="text"],
        .stSelectbox select {
            background: #F5F5F5 !important;
            color: #000000 !important;
            border: none !important;
            border-radius: 6px !important;
            padding: 8px !important;
            width: 100% !important;
        }

        /* 7. Button Styling */
        /*   a) “Add Vessel” / “Add Task” (inside .add-form-button container) */
        .add-form-button .stButton > button {
            background: #FFFFFF !important;  
            color: #0B1D3A !important;        /* dark‐navy text */
            border: 1px solid #0B1D3A !important;  /* dark‐navy border */
            font-weight: 600 !important;
            padding: 12px 24px !important;
            border-radius: 6px !important;
            transition: transform 0.2s, border-color 0.2s;
        }
        .add-form-button .stButton > button:hover {
            border: 1px solid #DB504A !important;  /* red border on hover */
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }

        /*   b) All other standard buttons (Create, Clear, Export/Import, Edit, Delete) */
        .stButton > button {
            background: linear-gradient(135deg, #1E40AF, #3B82F6) !important;
            color: #FFFFFF !important;
            border: none !important;
            font-weight: 600 !important;
            padding: 12px 24px !important;
            border-radius: 6px !important;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }

        /* 8. Cards for Vessels/Tasks */
        .card {
            background: rgba(255,255,255,0.1);
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 12px;
            border-left: 4px solid #1D4ED8;
        }
        .card h4 {
            margin: 0 0 6px 0;
            color: #FFFFFF;
        }
        .card p, .card small {
            color: #E0E0E0;
            margin: 2px 0;
        }

        /* 9. Expander Styling */
        .stExpander > button {
            background: rgba(255,255,255,0.1) !important;
            border: none;
            color: #FFFFFF !important;
            font-weight: bold !important;
            padding: 14px 20px !important;
            border-radius: 6px !important;
            margin-bottom: 10px;
        }
        .stExpander > div {
            background: rgba(255,255,255,0.05) !important;
            border-radius: 8px !important;
            padding: 20px !important;
        }
        .stExpander .css-ocqkz7 {
            color: #FFFFFF !important;
            font-weight: 500 !important;
        }

        /* 10. Plotly Timeline Legend & Text Contrast */
        .js-plotly-plot .legendtext {
            fill: #FFFFFF !important;
        }
        .js-plotly-plot .traces text {
            fill: #FFFFFF !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# ────────────────────────────────────────────────────────────────────────────────
# DATA MODELS
# ────────────────────────────────────────────────────────────────────────────────
class Vessel:
    def __init__(
        self,
        name: str,
        vessel_km: float,
        start_date: datetime.date,
        transit: float,
        transit_unit: str,
        weather: float,
        weather_unit: str,
        maintenance: float,
        maintenance_unit: str,
        id: Optional[str] = None
    ):
        self.id = id or str(uuid4())
        self.name = name
        self.vessel_km = vessel_km
        self.start_date = start_date

        # Convert to days if unit is hours
        self.transit_days = self._convert_to_days(transit, transit_unit)
        self.weather_days = self._convert_to_days(weather, weather_unit)
        self.maintenance_days = self._convert_to_days(maintenance, maintenance_unit)

        # Survey days = (vessel_km) / (speed * 24)
        self.survey_days = round(self.vessel_km / (DEFAULT_SURVEY_SPEED * 24), 2)
        self.total_days = round(
            self.survey_days + self.transit_days + self.weather_days + self.maintenance_days, 2
        )
        self.end_date = self.start_date + datetime.timedelta(days=self.total_days)

    def _convert_to_days(self, val: float, unit: str) -> float:
        return round(val / 24, 2) if unit == "hours" else val

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "vessel_km": self.vessel_km,
            "start_date": str(self.start_date),
            "transit_days": self.transit_days,
            "weather_days": self.weather_days,
            "maintenance_days": self.maintenance_days,
            "survey_days": self.survey_days,
            "total_days": self.total_days,
            "end_date": str(self.end_date),
        }

    @staticmethod
    def from_dict(d: Dict) -> "Vessel":
        v = Vessel(
            name=d["name"],
            vessel_km=float(d["vessel_km"]),
            start_date=pd.to_datetime(d["start_date"]).date(),
            transit=float(d["transit_days"]),
            transit_unit="days",
            weather=float(d["weather_days"]),
            weather_unit="days",
            maintenance=float(d["maintenance_days"]),
            maintenance_unit="days",
            id=d["id"],
        )
        return v

class Task:
    def __init__(
        self,
        name: str,
        task_type: str,
        start_date: datetime.date,
        end_date: datetime.date,
        vessel_id: Optional[str] = None,
        pause_survey: bool = False,
        id: Optional[str] = None
    ):
        self.id = id or str(uuid4())
        self.name = name
        self.task_type = task_type
        self.start_date = start_date
        self.end_date = end_date
        self.vessel_id = vessel_id
        self.pause_survey = pause_survey

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "task_type": self.task_type,
            "start_date": str(self.start_date),
            "end_date": str(self.end_date),
            "vessel_id": self.vessel_id,
            "pause_survey": self.pause_survey,
        }

    @staticmethod
    def from_dict(d: Dict) -> "Task":
        t = Task(
            name=d["name"],
            task_type=d["task_type"],
            start_date=pd.to_datetime(d["start_date"]).date(),
            end_date=pd.to_datetime(d["end_date"]).date(),
            vessel_id=d["vessel_id"],
            pause_survey=bool(d["pause_survey"]),
            id=d["id"]
        )
        return t

class Project:
    def __init__(
        self,
        name: str,
        total_line_km: float,
        infill_pct: float,
        id: Optional[str] = None
    ):
        self.id = id or str(uuid4())
        self.name = name
        self.total_line_km = total_line_km
        self.infill_pct = infill_pct
        self.vessels: List[Vessel] = []
        self.tasks: List[Task] = []

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "total_line_km": self.total_line_km,
            "infill_pct": self.infill_pct,
            "vessels": [v.to_dict() for v in self.vessels],
            "tasks": [t.to_dict() for t in self.tasks],
        }

    @staticmethod
    def from_dict(d: Dict) -> "Project":
        p = Project(
            name=d["name"],
            total_line_km=float(d["total_line_km"]),
            infill_pct=float(d["infill_pct"]),
            id=d["id"]
        )
        p.vessels = [Vessel.from_dict(v) for v in d.get("vessels", [])]
        p.tasks = [Task.from_dict(t) for t in d.get("tasks", [])]
        return p

# ────────────────────────────────────────────────────────────────────────────────
# HELPER: get_current_project()
# ────────────────────────────────────────────────────────────────────────────────
def get_current_project() -> Optional[Project]:
    pid = st.session_state.get("current_project_id")
    if pid is None:
        return None
    for p in st.session_state.get("projects", []):
        if p.id == pid:
            return p
    return None

# ────────────────────────────────────────────────────────────────────────────────
# SECTION 1) PROJECT CREATION / SELECTION
# ────────────────────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="stHeader"><h1><i class="fas fa-water"></i> Hydrographic Survey Estimator</h1></div>',
    unsafe_allow_html=True
)

st.markdown('<div class="section-header">1) Create / Select Project</div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns([2, 2, 1])
with col1:
    st.markdown('<div class="project-selectbox">', unsafe_allow_html=True)
    project_names = [p.name for p in st.session_state.get("projects", [])]
    project_options = ["➕ New Project"] + project_names
    idx = 0
    if st.session_state.get("current_project_id") is not None:
        cp = get_current_project()
        if cp is not None and cp.name in project_names:
            idx = project_names.index(cp.name) + 1

    sel = st.selectbox(
        "Select Project",
        options=project_options,
        index=idx,
        key="project_select"
    )
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    if sel == "➕ New Project":
        new_name = st.text_input("New Project Name", value="", placeholder="e.g. Gulf Survey 2025")
        new_line_km = st.number_input("Total Line Km to Survey", min_value=0.0, step=1.0, value=0.0)
        new_infill = st.number_input("Infill %", min_value=0.0, max_value=100.0, step=1.0, value=0.0)
        if st.button("Create Project", key="create_project"):
            if not new_name.strip():
                st.error("Project name cannot be empty.")
            else:
                proj = Project(name=new_name.strip(), total_line_km=new_line_km, infill_pct=new_infill)
                st.session_state["projects"].append(proj)
                st.session_state["current_project_id"] = proj.id
    else:
        # User selected an existing project
        chosen = sel
        for p in st.session_state.get("projects", []):
            if p.name == chosen:
                st.session_state["current_project_id"] = p.id

with col3:
    if st.button("Clear Project", key="clear_project"):
        st.session_state["current_project_id"] = None
        st.session_state["editing_vessel"] = None
        st.session_state["editing_task"] = None

current_project = get_current_project()
if current_project is None:
    st.markdown(
        '<span style="color:#FFFFFF;">No project selected. Create a new project above to begin.</span>',
        unsafe_allow_html=True
    )
    st.stop()

# ────────────────────────────────────────────────────────────────────────────────
# SECTION 2) ADD / EDIT / DELETE VESSELS
# ────────────────────────────────────────────────────────────────────────────────
st.markdown(
    f'<div class="section-header">2) Vessel Fleet (for “{current_project.name}”)</div>',
    unsafe_allow_html=True
)

# — Add New Vessel Form (inside .add-form-button container)
with st.expander("🚢 Add New Vessel", expanded=False):
    st.markdown('<div class="add-form-button">', unsafe_allow_html=True)
    with st.form("vessel_form"):
        colA, colB, colC = st.columns([3, 2, 1])
        with colA:
            vessel_name = st.text_input("Vessel Name*", placeholder="e.g. Orca Explorer")
            vessel_km = st.number_input("Line Km for this Vessel*", min_value=0.1, step=1.0, value=0.1)
            start_date = st.date_input("Start Date*", value=datetime.date.today())
        with colB:
            transit_val = st.number_input(
                "Transit Duration*", min_value=0.0, step=0.5, value=0.0, key="transit_val"
            )
            weather_val = st.number_input(
                "Weather Downtime*", min_value=0.0, step=0.5, value=0.0, key="weather_val"
            )
            maintenance_val = st.number_input(
                "Maintenance*", min_value=0.0, step=0.5, value=0.0, key="maintenance_val"
            )
        with colC:
            transit_unit = st.selectbox("Unit", ["days", "hours"], index=0, key="transit_unit")
            weather_unit = st.selectbox("", ["days", "hours"], index=0, key="weather_unit")
            maintenance_unit = st.selectbox("", ["days", "hours"], index=0, key="maintenance_unit")

        submitted = st.form_submit_button("Add Vessel")
        if submitted:
            errs = []
            if not vessel_name.strip():
                errs.append("Vessel name cannot be empty.")
            if vessel_km <= 0:
                errs.append("Line Km must be positive.")
            if errs:
                for e in errs:
                    st.error(e)
            else:
                new_v = Vessel(
                    name=vessel_name.strip(),
                    vessel_km=vessel_km,
                    start_date=start_date,
                    transit=transit_val,
                    transit_unit=transit_unit,
                    weather=weather_val,
                    weather_unit=weather_unit,
                    maintenance=maintenance_val,
                    maintenance_unit=maintenance_unit
                )
                current_project.vessels.append(new_v)
                st.success(f"Vessel '{vessel_name.strip()}' added!")
    st.markdown('</div>', unsafe_allow_html=True)

# — Display Existing Vessels, plus Edit/Delete buttons
for v in current_project.vessels:
    with st.container():
        c1, c2, c3 = st.columns([3, 1, 1])
        with c1:
            st.markdown(
                f"""
                <div class="card">
                    <h4><i class="fas fa-ship"></i> {v.name}</h4>
                    <p><strong>Survey:</strong> {v.vessel_km} km</p>
                    <p><strong>Schedule:</strong> {v.start_date} &rarr; {v.end_date} ({v.total_days} days)</p>
                    <p><strong>Breakdown:</strong> Survey: {v.survey_days} d |
                      Transit: {v.transit_days} d |
                      Weather: {v.weather_days} d |
                      Maint: {v.maintenance_days} d
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )
        with c2:
            if st.button("✏️ Edit", key=f"edit_v_{v.id}"):
                st.session_state["editing_vessel"] = v.id
        with c3:
            if st.button("🗑️ Delete", key=f"del_v_{v.id}"):
                current_project.vessels = [x for x in current_project.vessels if x.id != v.id]
                current_project.tasks = [t for t in current_project.tasks if t.vessel_id != v.id]
                st.success(f"Deleted vessel '{v.name}'.")

# — If a vessel is being edited, show a full-width expander for editing
if st.session_state.get("editing_vessel"):
    edit_id = st.session_state["editing_vessel"]
    to_edit = next((x for x in current_project.vessels if x.id == edit_id), None)
    if to_edit is not None:
        with st.expander(f"✏️ Edit Vessel: {to_edit.name}", expanded=True):
            st.markdown('<div class="add-form-button">', unsafe_allow_html=True)
            with st.form(f"vessel_edit_form_{to_edit.id}"):
                eA, eB, eC = st.columns([3, 2, 1])
                with eA:
                    new_name = st.text_input("Vessel Name*", value=to_edit.name)
                    new_km = st.number_input(
                        "Line Km*", min_value=0.1, step=1.0, value=to_edit.vessel_km
                    )
                    new_start = st.date_input(
                        "Start Date*", value=pd.to_datetime(to_edit.start_date).date()
                    )
                with eB:
                    new_transit = st.number_input(
                        "Transit Duration*",
                        min_value=0.0,
                        step=0.5,
                        value=to_edit.transit_days,
                        key=f"et_{to_edit.id}_transit"
                    )
                    new_weather = st.number_input(
                        "Weather Downtime*",
                        min_value=0.0,
                        step=0.5,
                        value=to_edit.weather_days,
                        key=f"ew_{to_edit.id}_weather"
                    )
                    new_maint = st.number_input(
                        "Maintenance*",
                        min_value=0.0,
                        step=0.5,
                        value=to_edit.maintenance_days,
                        key=f"em_{to_edit.id}_maint"
                    )
                with eC:
                    new_transit_unit = st.selectbox(
                        "Unit", ["days", "hours"], index=0, key=f"et_{to_edit.id}_tunit"
                    )
                    new_weather_unit = st.selectbox(
                        "", ["days", "hours"], index=0, key=f"ew_{to_edit.id}_wunit"
                    )
                    new_maint_unit = st.selectbox(
                        "", ["days", "hours"], index=0, key=f"em_{to_edit.id}_munit"
                    )

                update_button = st.form_submit_button("Update Vessel")
                if update_button:
                    errs = []
                    if not new_name.strip():
                        errs.append("Vessel name cannot be empty.")
                    if new_km <= 0:
                        errs.append("Line Km must be positive.")
                    if errs:
                        for e in errs:
                            st.error(e)
                    else:
                        updated_v = Vessel(
                            name=new_name.strip(),
                            vessel_km=new_km,
                            start_date=new_start,
                            transit=new_transit,
                            transit_unit=new_transit_unit,
                            weather=new_weather,
                            weather_unit=new_weather_unit,
                            maintenance=new_maint,
                            maintenance_unit=new_maint_unit,
                            id=to_edit.id
                        )
                        current_project.vessels = [
                            x for x in current_project.vessels if x.id != to_edit.id
                        ] + [updated_v]
                        st.success(f"Vessel '{new_name.strip()}' updated!")
                        st.session_state["editing_vessel"] = None
            st.markdown('</div>', unsafe_allow_html=True)

# ────────────────────────────────────────────────────────────────────────────────
# SECTION 3) ADD / EDIT / DELETE TASKS
# ────────────────────────────────────────────────────────────────────────────────
st.markdown(
    f'<div class="section-header">3) Task Register (for “{current_project.name}”)</div>',
    unsafe_allow_html=True
)

with st.expander("📝 Add New Task", expanded=False):
    st.markdown('<div class="add-form-button">', unsafe_allow_html=True)
    with st.form("task_form"):
        t1, t2 = st.columns(2)
        with t1:
            task_name = st.text_input("Task Name*", placeholder="e.g. Sediment Sampling")
            task_type = st.selectbox(
                "Task Type*",
                options=[
                    "Survey", "Maintenance", "Weather", "Transit", "Delay",
                    "Sediment Sample", "Deployment", "Recovery", "Other"
                ],
                index=0,
                key="new_task_type"
            )
            if task_type == "Other":
                other_label = st.text_input("Specify “Other” Task Type*", placeholder="Enter custom task type here")
        with t2:
            start_date_t = st.date_input("Start Date*")
            end_date_t = st.date_input("End Date*", value=datetime.date.today() + datetime.timedelta(days=1))
            vessel_options = [("Unassigned", None)] + [
                (v.name, v.id) for v in current_project.vessels
            ]
            sel_vessel = st.selectbox(
                "Assign to Vessel",
                options=vessel_options,
                format_func=lambda x: x[0]
            )
            pause_survey = st.checkbox("Pause Survey Operations", value=False)

        add_task_btn = st.form_submit_button("Add Task")
        if add_task_btn:
            errs = []
            if not task_name.strip():
                errs.append("Task name cannot be empty.")
            if start_date_t > end_date_t:
                errs.append("End date must be on or after start date.")
            chosen_type = task_type if task_type != "Other" else other_label.strip()
            if task_type == "Other" and not chosen_type:
                errs.append("You selected “Other”. Please specify the task type.")
            if errs:
                for e in errs:
                    st.error(e)
            else:
                new_task = Task(
                    name=task_name.strip(),
                    task_type=chosen_type,
                    start_date=start_date_t,
                    end_date=end_date_t,
                    vessel_id=sel_vessel[1],
                    pause_survey=pause_survey
                )
                current_project.tasks.append(new_task)
                st.success(f"Task '{task_name.strip()}' added!")
    st.markdown('</div>', unsafe_allow_html=True)

# — Display Existing Tasks + Edit/Delete Buttons
for t in current_project.tasks:
    with st.container():
        d1, d2, d3 = st.columns([3, 1, 1])
        assigned_name = next(
            (v.name for v in current_project.vessels if v.id == t.vessel_id),
            "Unassigned"
        )
        with d1:
            st.markdown(
                f"""
                <div class="card">
                  <strong><i class="fas fa-tasks"></i> {t.name}</strong> ({t.task_type})<br>
                  <small>{t.start_date} &rarr; {t.end_date} | Vessel: {assigned_name}</small><br>
                  {("<small style='color:orange;'>⚠️ Pauses Survey</small>" if t.pause_survey else "")}
                </div>
                """,
                unsafe_allow_html=True
            )
        with d2:
            if st.button("✏️ Edit", key=f"edit_t_{t.id}"):
                st.session_state["editing_task"] = t.id
        with d3:
            if st.button("🗑️ Delete", key=f"del_t_{t.id}"):
                current_project.tasks = [x for x in current_project.tasks if x.id != t.id]
                st.success(f"Deleted task '{t.name}'.")

# — If a task is being edited, show a full-width expander for editing
if st.session_state.get("editing_task"):
    edit_tid = st.session_state["editing_task"]
    to_edit_t = next((x for x in current_project.tasks if x.id == edit_tid), None)
    if to_edit_t is not None:
        with st.expander(f"✏️ Edit Task: {to_edit_t.name}", expanded=True):
            st.markdown('<div class="add-form-button">', unsafe_allow_html=True)
            with st.form(f"task_edit_form_{to_edit_t.id}"):
                et1, et2 = st.columns(2)
                with et1:
                    new_name = st.text_input("Task Name*", value=to_edit_t.name)
                    new_type = st.selectbox(
                        "Task Type*",
                        options=[
                            "Survey", "Maintenance", "Weather", "Transit", "Delay",
                            "Sediment Sample", "Deployment", "Recovery", "Other"
                        ],
                        index=(
                            ["Survey","Maintenance","Weather","Transit","Delay",
                             "Sediment Sample","Deployment","Recovery"]
                            .index(to_edit_t.task_type)
                            if to_edit_t.task_type in [
                                "Survey","Maintenance","Weather","Transit","Delay",
                                "Sediment Sample","Deployment","Recovery"
                            ] else 8
                        ),
                        key=f"et_ttype_{to_edit_t.id}"
                    )
                    if new_type == "Other":
                        new_other = st.text_input(
                            "Specify “Other” Type*",
                            value=(
                                to_edit_t.task_type
                                if to_edit_t.task_type not in [
                                    "Survey","Maintenance","Weather","Transit","Delay",
                                    "Sediment Sample","Deployment","Recovery"
                                ] else ""
                            )
                        )
                with et2:
                    new_start = st.date_input("Start Date*", value=to_edit_t.start_date, key=f"et_start_{to_edit_t.id}")
                    new_end = st.date_input("End Date*", value=to_edit_t.end_date, key=f"et_end_{to_edit_t.id}")
                    vessel_options_edit = [("Unassigned", None)] + [
                        (v.name, v.id) for v in current_project.vessels
                    ]
                    default_idx = 0
                    for i, opt in enumerate(vessel_options_edit):
                        if opt[1] == to_edit_t.vessel_id:
                            default_idx = i
                            break
                    new_vessel = st.selectbox(
                        "Assign to Vessel",
                        options=vessel_options_edit,
                        index=default_idx,
                        format_func=lambda x: x[0],
                        key=f"et_vessel_{to_edit_t.id}"
                    )
                    new_pause = st.checkbox(
                        "Pause Survey Operations",
                        value=to_edit_t.pause_survey,
                        key=f"et_pause_{to_edit_t.id}"
                    )

                update_task_btn = st.form_submit_button("Update Task")
                if update_task_btn:
                    errs = []
                    if not new_name.strip():
                        errs.append("Task name cannot be empty.")
                    if new_start > new_end:
                        errs.append("End date must be on or after start date.")
                    chosen_t = new_type if new_type != "Other" else new_other.strip()
                    if new_type == "Other" and not chosen_t:
                        errs.append("You selected “Other”. Please specify the task type.")
                    if errs:
                        for e in errs:
                            st.error(e)
                    else:
                        updated_t = Task(
                            name=new_name.strip(),
                            task_type=chosen_t,
                            start_date=new_start,
                            end_date=new_end,
                            vessel_id=new_vessel[1],
                            pause_survey=new_pause,
                            id=to_edit_t.id
                        )
                        current_project.tasks = [
                            x for x in current_project.tasks if x.id != to_edit_t.id
                        ] + [updated_t]
                        st.success(f"Task '{new_name.strip()}' updated!")
                        st.session_state["editing_task"] = None
            st.markdown('</div>', unsafe_allow_html=True)

# ────────────────────────────────────────────────────────────────────────────────
# SECTION 4) DATA MANAGEMENT (EXPORT / IMPORT)
# ────────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">4) Data Management</div>', unsafe_allow_html=True)

with st.expander("💾 Export / Import Projects", expanded=False):
    ex_col1, ex_col2 = st.columns(2)
    with ex_col1:
        st.markdown("**Export All Projects**")
        export_filename = st.text_input(
            "Filename (no extension)",
            value="hydro_projects_export",
            key="export_name"
        )
        if st.button("Export to JSON", key="export_json"):
            data_out = {"projects": [p.to_dict() for p in st.session_state.get("projects", [])]}
            raw = json.dumps(data_out, indent=2)
            st.download_button(
                label="Download JSON",
                data=raw,
                file_name=f"{export_filename}.json",
                mime="application/json"
            )

        if st.button("Export to Excel", key="export_excel"):
            output = BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                proj_rows = []
                for p in st.session_state.get("projects", []):
                    proj_rows.append({
                        "project_id": p.id,
                        "name": p.name,
                        "total_line_km": p.total_line_km,
                        "infill_pct": p.infill_pct
                    })
                pd.DataFrame(proj_rows).to_excel(writer, sheet_name="Projects", index=False)

                vessel_rows = []
                for p in st.session_state.get("projects", []):
                    for v in p.vessels:
                        vr = v.to_dict()
                        vr["project_id"] = p.id
                        vessel_rows.append(vr)
                if vessel_rows:
                    pd.DataFrame(vessel_rows).to_excel(writer, sheet_name="Vessels", index=False)

                task_rows = []
                for p in st.session_state.get("projects", []):
                    for t in p.tasks:
                        tr = t.to_dict()
                        tr["project_id"] = p.id
                        task_rows.append(tr)
                if task_rows:
                    pd.DataFrame(task_rows).to_excel(writer, sheet_name="Tasks", index=False)

            st.download_button(
                label="Download Excel",
                data=output.getvalue(),
                file_name=f"{export_filename}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    with ex_col2:
        st.markdown("**Import Projects**")
        uploaded_file = st.file_uploader(
            "Upload JSON or Excel", type=["json", "xlsx"], accept_multiple_files=False
        )
        if uploaded_file is not None and st.button("Import Data", key="import_data"):
            try:
                if uploaded_file.name.lower().endswith(".json"):
                    raw = uploaded_file.read().decode("utf-8")
                    data_in = json.loads(raw)
                    proj_dicts = data_in.get("projects", [])
                    new_projects = [Project.from_dict(d) for d in proj_dicts]
                    st.session_state["projects"] = new_projects
                    if new_projects:
                        st.session_state["current_project_id"] = new_projects[0].id
                    else:
                        st.session_state["current_project_id"] = None
                    st.success("Imported from JSON successfully!")

                elif uploaded_file.name.lower().endswith(".xlsx"):
                    xls = pd.ExcelFile(uploaded_file)
                    if "Projects" not in xls.sheet_names:
                        raise ValueError("Excel must contain a sheet named 'Projects'.")
                    proj_df = xls.parse("Projects")
                    new_projects = []
                    for idx, row in proj_df.iterrows():
                        p = Project(
                            name=row["name"],
                            total_line_km=float(row["total_line_km"]),
                            infill_pct=float(row["infill_pct"]),
                            id=str(row["project_id"])
                        )
                        new_projects.append(p)

                    if "Vessels" in xls.sheet_names:
                        ves_df = xls.parse("Vessels")
                        for idx, row in ves_df.iterrows():
                            pid = str(row["project_id"])
                            v = Vessel.from_dict({
                                "id": str(row["id"]),
                                "name": row["name"],
                                "vessel_km": row["vessel_km"],
                                "start_date": row["start_date"],
                                "transit_days": row["transit_days"],
                                "weather_days": row["weather_days"],
                                "maintenance_days": row["maintenance_days"]
                            })
                            for p in new_projects:
                                if p.id == pid:
                                    p.vessels.append(v)
                                    break

                    if "Tasks" in xls.sheet_names:
                        task_df = xls.parse("Tasks")
                        for idx, row in task_df.iterrows():
                            pid = str(row["project_id"])
                            t = Task.from_dict({
                                "id": str(row["id"]),
                                "name": row["name"],
                                "task_type": row["task_type"],
                                "start_date": row["start_date"],
                                "end_date": row["end_date"],
                                "vessel_id": row["vessel_id"],
                                "pause_survey": bool(row["pause_survey"])
                            })
                            for p in new_projects:
                                if p.id == pid:
                                    p.tasks.append(t)
                                    break

                    st.session_state["projects"] = new_projects
                    if new_projects:
                        st.session_state["current_project_id"] = new_projects[0].id
                    else:
                        st.session_state["current_project_id"] = None
                    st.success("Imported from Excel successfully!")

                else:
                    st.error("Unsupported file type. Please upload .json or .xlsx.")
            except Exception as e:
                st.error(f"Error importing: {e}")

# ────────────────────────────────────────────────────────────────────────────────
# SECTION 5) GANTT CHART FOR CURRENT PROJECT
# ────────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">5) Project Timeline (Gantt Chart)</div>', unsafe_allow_html=True)

proj = get_current_project()
if proj is None:
    st.stop()

def build_timeline_df(vessels: List[Vessel], tasks: List[Task]) -> pd.DataFrame:
    rows = []
    for v in vessels:
        survey_start = pd.to_datetime(v.start_date)
        survey_end = pd.to_datetime(v.end_date)

        # gather pause tasks for this vessel
        pauses = sorted(
            [t for t in tasks if (t.vessel_id == v.id and t.pause_survey)],
            key=lambda t: pd.to_datetime(t.start_date)
        )

        cur_start = survey_start
        for t in pauses:
            t_start = pd.to_datetime(t.start_date)
            t_end = pd.to_datetime(t.end_date)
            if t_start > cur_start:
                rows.append({
                    "Task": f"Survey ► {v.name}",
                    "Start": cur_start,
                    "Finish": t_start,
                    "Resource": v.name,
                    "Type": "Survey"
                })
            rows.append({
                "Task": t.name,
                "Start": t_start,
                "Finish": t_end,
                "Resource": v.name,
                "Type": t.task_type
            })
            cur_start = t_end
        if cur_start < survey_end:
            rows.append({
                "Task": f"Survey ► {v.name}",
                "Start": cur_start,
                "Finish": survey_end,
                "Resource": v.name,
                "Type": "Survey"
            })

    # unassigned tasks
    for t in tasks:
        if t.vessel_id is None:
            rows.append({
                "Task": t.name,
                "Start": pd.to_datetime(t.start_date),
                "Finish": pd.to_datetime(t.end_date),
                "Resource": "Unassigned",
                "Type": t.task_type
            })

    return pd.DataFrame(rows)

timeline_df = build_timeline_df(proj.vessels, proj.tasks)

if timeline_df.empty:
    st.markdown(
        '<span style="color:#FFFFFF;">No timeline data available for this project. Add vessels/tasks above.</span>',
        unsafe_allow_html=True
    )
else:
    fig = px.timeline(
        timeline_df,
        x_start="Start",
        x_end="Finish",
        y="Resource",
        color="Type",
        color_discrete_map=COLOR_MAP,
        hover_name="Task",
        title=f"Gantt Chart ► {proj.name}"
    )

    # Y-axis reversed, white ticks
    fig.update_yaxes(
        autorange="reversed",
        title_text="",
        tickfont=dict(color="white"),
        title_font=dict(color="white")
    )
    # X-axis (dates) with white ticks
    fig.update_xaxes(
        title_text="Date",
        tickfont=dict(color="white"),
        title_font=dict(color="white")
    )

    # Legend & Title styling
    fig.update_layout(
        height=max(400, len(proj.vessels) * 100 + len(proj.tasks) * 50),
        plot_bgcolor="rgba(255,255,255,0.1)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="white",                           # default font
        title_font=dict(color="white", size=20),      # chart title in white
        legend_title_text="Activity Type",
        legend_font=dict(color="white"),               # legend labels in white
        hoverlabel=dict(
            bgcolor="rgba(30, 64, 175, 0.8)",
            font_size=12,
            font_family="Arial"
        )
    )

    st.plotly_chart(fig, use_container_width=True)
