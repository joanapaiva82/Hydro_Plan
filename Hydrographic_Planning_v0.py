import streamlit as st
import datetime
import pandas as pd
import plotly.express as px
import json
from uuid import uuid4
from typing import List, Dict, Optional
import io

# Constants
DEFAULT_SURVEY_SPEED = 5.0  # knots
DEFAULT_WEATHER_DOWNTIME = 15  # percentage
COLOR_MAP = {
    "Survey": "#2E86AB",
    "Task": "#F18F01",
    "Maintenance": "#A23B72",
    "Weather": "#3B1F2B",
    "Transit": "#3D5A6C",
    "Delay": "#DB504A"
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
                 transit_days: float, weather_days: float, maintenance_days: float):
        self.id = str(uuid4())
        self.name = name
        self.line_km = line_km
        self.speed = speed
        self.start_date = start_date
        self.transit_days = transit_days
        self.weather_days = weather_days
        self.maintenance_days = maintenance_days
        
        # Calculated properties
        self.survey_days = self.calculate_survey_days()
        self.total_days = self.calculate_total_days()
        self.end_date = self.calculate_end_date()
        self.daily_progress = self.line_km / self.total_days if self.total_days > 0 else 0
    
    def calculate_survey_days(self) -> float:
        """Calculate required survey days based on line km and speed"""
        return round(self.line_km / (self.speed * 24), 2)
    
    def calculate_total_days(self) -> float:
        """Calculate total project days including contingencies"""
        return round(self.survey_days + self.transit_days + self.weather_days + self.maintenance_days, 2)
    
    def calculate_end_date(self) -> datetime.date:
        """Calculate end date based on start date and total days"""
        return self.start_date + datetime.timedelta(days=self.total_days)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "line_km": self.line_km,
            "speed": self.speed,
            "start_date": self.start_date.isoformat(),
            "survey_days": self.survey_days,
            "transit_days": self.transit_days,
            "weather_days": self.weather_days,
            "maintenance_days": self.maintenance_days,
            "total_days": self.total_days,
            "end_date": self.end_date.isoformat(),
            "daily_progress": self.daily_progress
        }

class Task:
    def __init__(self, name: str, task_type: str, start_date: datetime.date, end_date: datetime.date,
                 vessel_id: Optional[str] = None, pause_survey: bool = False, cost: float = 0):
        self.id = str(uuid4())
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
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "vessel_id": self.vessel_id,
            "pause_survey": self.pause_survey,
            "cost": self.cost
        }

# --- Session State Initialization ---
def init_session_state():
    if "vessels" not in st.session_state:
        st.session_state.vessels = []
    if "tasks" not in st.session_state:
        st.session_state.tasks = []
    if "project_name" not in st.session_state:
        st.session_state.project_name = ""
    if "unsurveyed_km" not in st.session_state:
        st.session_state.unsurveyed_km = 0.0
    if "surveyed_km" not in st.session_state:
        st.session_state.surveyed_km = 0.0
    if "weather_factor" not in st.session_state:
        st.session_state.weather_factor = DEFAULT_WEATHER_DOWNTIME
    if "day_rate" not in st.session_state:
        st.session_state.day_rate = 25000  # USD

init_session_state()

# --- Helper Functions ---
def validate_vessel(name: str) -> List[str]:
    """Validate vessel data before adding"""
    errors = []
    if not name.strip():
        errors.append("Vessel name cannot be empty")
    if any(v['name'] == name for v in st.session_state.vessels):
        errors.append(f"Vessel '{name}' already exists")
    return errors

def validate_task(task: Dict) -> List[str]:
    """Validate task data before adding"""
    errors = []
    if not task['name'].strip():
        errors.append("Task name cannot be empty")
    
    if pd.to_datetime(task['start_date']) > pd.to_datetime(task['end_date']):
        errors.append("End date must be after start date")
    
    if task['vessel_id']:
        vessel = next((v for v in st.session_state.vessels if v['id'] == task['vessel_id']), None)
        if vessel:
            vessel_start = pd.to_datetime(vessel['start_date'])
            vessel_end = pd.to_datetime(vessel['end_date'])
            task_start = pd.to_datetime(task['start_date'])
            task_end = pd.to_datetime(task['end_date'])
            
            if task_start < vessel_start or task_end > vessel_end:
                errors.append("Task dates outside vessel's operational period")
    
    return errors

def calculate_project_progress() -> float:
    """Calculate overall project progress"""
    total_surveyed = sum(v['line_km'] for v in st.session_state.vessels)
    if st.session_state.unsurveyed_km > 0:
        return min(100, (total_surveyed / st.session_state.unsurveyed_km) * 100)
    return 0.0

def calculate_project_cost() -> float:
    """Calculate total project cost"""
    vessel_days = sum(v['total_days'] for v in st.session_state.vessels)
    task_costs = sum(t['cost'] for t in st.session_state.tasks)
    return (vessel_days * st.session_state.day_rate) + task_costs

def build_timeline_data() -> pd.DataFrame:
    """Build timeline data for Gantt chart"""
    timeline_data = []
    
    # Add vessel survey periods
    for vessel in st.session_state.vessels:
        survey_start = pd.to_datetime(vessel['start_date'])
        survey_end = pd.to_datetime(vessel['end_date'])
        
        # Get tasks that pause survey for this vessel
        pauses = [t for t in st.session_state.tasks 
                 if t['vessel_id'] == vessel['id'] and t['pause_survey']]
        pauses = sorted(pauses, key=lambda t: pd.to_datetime(t['start_date']))
        
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
            # Handle survey segments around pauses
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
                
                # Add the pause period
                timeline_data.append({
                    "Task": pause['name'],
                    "Start": pause_start,
                    "Finish": pause_end,
                    "Resource": vessel['name'],
                    "Type": pause['type'],
                    "Details": f"Cost: ${pause['cost']:,.2f}" if pause['cost'] > 0 else "",
                    "Progress": 0
                })
                
                current_start = pause_end
            
            # Add remaining survey period after last pause
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
    
    # Add standalone tasks
    for task in [t for t in st.session_state.tasks if not t['vessel_id']]:
        timeline_data.append({
            "Task": task['name'],
            "Start": pd.to_datetime(task['start_date']),
            "Finish": pd.to_datetime(task['end_date']),
            "Resource": "Unassigned",
            "Type": task['type'],
            "Details": f"Cost: ${task['cost']:,.2f}" if task['cost'] > 0 else "",
            "Progress": 0
        })
    
    return pd.DataFrame(timeline_data)

# --- UI Components ---
def show_project_header():
    """Display project header with key metrics"""
    st.title("🌊 Hydrographic Survey Estimator Pro")
    
    progress = calculate_project_progress()
    total_cost = calculate_project_cost()
    total_days = sum(v['total_days'] for v in st.session_state.vessels)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Project Progress", f"{progress:.1f}%")
    with col2:
        st.metric("Surveyed Line Km", f"{sum(v['line_km'] for v in st.session_state.vessels):.1f} km")
    with col3:
        st.metric("Estimated Duration", f"{total_days:.1f} days")
    with col4:
        st.metric("Estimated Cost", f"${total_cost:,.2f}")
    
    st.progress(progress / 100)

def vessel_form():
    """Form for adding new vessels"""
    with st.expander("🚢 Add New Vessel", expanded=False):
        with st.form("vessel_form"):
            col1, col2 = st.columns([3, 2])
            with col1:
                vessel_name = st.text_input("Vessel Name*", placeholder="e.g. Orca Explorer")
                st.markdown('<span class="tooltip-icon" title="Unique name for the survey vessel">ℹ️</span>', unsafe_allow_html=True)
                line_km = st.number_input("Line Km*", min_value=0.0, step=1.0, value=100.0)
                st.markdown('<span class="tooltip-icon" title="Total kilometers to be surveyed by this vessel">ℹ️</span>', unsafe_allow_html=True)
            
            with col2:
                speed = st.number_input("Speed (knots)*", min_value=0.1, step=0.1, value=DEFAULT_SURVEY_SPEED)
                st.markdown('<span class="tooltip-icon" title="Average survey speed in knots">ℹ️</span>', unsafe_allow_html=True)
                start_date = st.date_input("Start Date*", value=datetime.date.today())
                st.markdown('<span class="tooltip-icon" title="Planned start date for survey operations">ℹ️</span>', unsafe_allow_html=True)
            
            st.markdown("**Contingency Days**")
            col3, col4, col5 = st.columns(3)
            with col3:
                transit_days = st.number_input("Transit Days", min_value=0.0, step=0.5, value=2.0)
                st.markdown('<span class="tooltip-icon" title="Days required for vessel transit to/from survey area">ℹ️</span>', unsafe_allow_html=True)
            with col4:
                weather_days = st.number_input("Weather Days", min_value=0.0, step=0.5, value=3.0)
                st.markdown('<span class="tooltip-icon" title="Estimated weather downtime based on historical data">ℹ️</span>', unsafe_allow_html=True)
            with col5:
                maintenance_days = st.number_input("Maintenance Days", min_value=0.0, step=0.5, value=1.0)
                st.markdown('<span class="tooltip-icon" title="Scheduled maintenance and equipment checks">ℹ️</span>', unsafe_allow_html=True)
            
            if st.form_submit_button("Add Vessel"):
                errors = validate_vessel(vessel_name)
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
                        maintenance_days=maintenance_days
                    )
                    st.session_state.vessels.append(vessel.to_dict())
                    st.success(f"Vessel '{vessel_name}' added successfully!")
                    st.session_state.surveyed_km += line_km

def task_form():
    """Form for adding new tasks"""
    with st.expander("📝 Add New Task", expanded=False):
        with st.form("task_form"):
            col1, col2 = st.columns(2)
            with col1:
                task_name = st.text_input("Task Name*", placeholder="e.g. Sediment Sampling")
                st.markdown('<span class="tooltip-icon" title="Descriptive name for the task">ℹ️</span>', unsafe_allow_html=True)
                task_type = st.selectbox(
                    "Task Type*",
                    ["Survey", "Maintenance", "Weather", "Transit", "Delay", "Other"],
                    index=0
                )
                st.markdown('<span class="tooltip-icon" title="Category of task for reporting and visualization">ℹ️</span>', unsafe_allow_html=True)
            
            with col2:
                start_date = st.date_input("Start Date*", value=datetime.date.today())
                st.markdown('<span class="tooltip-icon" title="Planned start date for the task">ℹ️</span>', unsafe_allow_html=True)
                end_date = st.date_input("End Date*", value=datetime.date.today() + datetime.timedelta(days=1))
                st.markdown('<span class="tooltip-icon" title="Planned completion date for the task">ℹ️</span>', unsafe_allow_html=True)
            
            col3, col4 = st.columns(2)
            with col3:
                vessel_options = [("Unassigned", None)] + [(v['name'], v['id']) for v in st.session_state.vessels]
                selected_vessel = st.selectbox(
                    "Assigned Vessel",
                    vessel_options,
                    format_func=lambda x: x[0],
                    index=0
                )
                vessel_id = selected_vessel[1]
                st.markdown('<span class="tooltip-icon" title="Vessel responsible for this task (if applicable)">ℹ️</span>', unsafe_allow_html=True)
            
            with col4:
                pause_survey = st.checkbox("Pause Survey Operations", value=False)
                st.markdown('<span class="tooltip-icon" title="Does this task pause the vessel\'s survey operations?">ℹ️</span>', unsafe_allow_html=True)
                cost = st.number_input("Estimated Cost (USD)", min_value=0.0, value=0.0, step=1000.0)
                st.markdown('<span class="tooltip-icon" title="Additional cost associated with this task">ℹ️</span>', unsafe_allow_html=True)
            
            if st.form_submit_button("Add Task"):
                task = {
                    "name": task_name,
                    "type": task_type,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "vessel_id": vessel_id,
                    "pause_survey": pause_survey,
                    "cost": cost
                }
                
                errors = validate_task(task)
                if errors:
                    for error in errors:
                        st.error(error)
                else:
                    st.session_state.tasks.append(task)
                    st.success(f"Task '{task_name}' added successfully!")

def show_vessels():
    """Display all vessels with detailed information"""
    if not st.session_state.vessels:
        st.info("No vessels added yet. Add your first vessel to begin.")
        return
    
    st.subheader("🚢 Vessel Fleet")
    for vessel in st.session_state.vessels:
        with st.container():
            col1, col2 = st.columns([3, 1])
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
                if st.button(f"Delete {vessel['name']}", key=f"del_{vessel['id']}"):
                    st.session_state.vessels = [v for v in st.session_state.vessels if v['id'] != vessel['id']]
                    st.session_state.surveyed_km -= vessel['line_km']
                    st.rerun()

def show_tasks():
    """Display all tasks with filtering options"""
    if not st.session_state.tasks:
        st.info("No tasks added yet. Add your first task to begin.")
        return
    
    st.subheader("📋 Task Register")
    
    # Filter options
    col1, col2, col3 = st.columns(3)
    with col1:
        filter_type = st.selectbox("Filter by Type", ["All"] + sorted(list(set(t['type'] for t in st.session_state.tasks))))
    with col2:
        filter_vessel = st.selectbox("Filter by Vessel", ["All"] + [v['name'] for v in st.session_state.vessels])
    with col3:
        filter_date = st.selectbox("Filter by Date", ["All", "Upcoming", "Past", "Current"])
    
    # Apply filters
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
    
    # Display tasks
    for task in filtered_tasks:
        vessel_name = next((v['name'] for v in st.session_state.vessels if v['id'] == task['vessel_id']), "Unassigned")
        
        col1, col2 = st.columns([4, 1])
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
            if st.button("Delete", key=f"del_task_{task['id']}"):
                st.session_state.tasks = [t for t in st.session_state.tasks if t['id'] != task['id']]
                st.rerun()

def show_timeline():
    """Display interactive Gantt chart"""
    if not st.session_state.vessels and not st.session_state.tasks:
        st.info("Add vessels and tasks to generate the project timeline")
        return
    
    st.subheader("📊 Project Timeline")
    
    df = build_timeline_data()
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
        height=600,
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
    """Project configuration settings"""
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
    """Data import/export functionality"""
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
                vessel_df = pd.DataFrame(st.session_state.vessels)
                task_df = pd.DataFrame(st.session_state.tasks)
                
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    vessel_df.to_excel(writer, sheet_name="Vessels", index=False)
                    task_df.to_excel(writer, sheet_name="Tasks", index=False)
                
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
                        st.session_state.project_name = data.get("project_name", "")
                        st.session_state.unsurveyed_km = data.get("unsurveyed_km", 0.0)
                        st.session_state.weather_factor = data.get("weather_factor", DEFAULT_WEATHER_DOWNTIME)
                        st.session_state.day_rate = data.get("day_rate", 25000)
                        st.session_state.vessels = data.get("vessels", [])
                        st.session_state.tasks = data.get("tasks", [])
                        st.success("Project imported successfully from JSON!")
                    
                    elif uploaded_file.name.endswith(".xlsx"):
                        xls = pd.ExcelFile(uploaded_file)
                        
                        if "Vessels" in xls.sheet_names:
                            st.session_state.vessels = xls.parse("Vessels").to_dict(orient="records")
                        
                        if "Tasks" in xls.sheet_names:
                            st.session_state.tasks = xls.parse("Tasks").to_dict(orient="records")
                        
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