"""
FS FilterLab - Optical Filter Analysis Tool
"""
# Standard library imports
from pathlib import Path

# Third-party imports
import streamlit as st

# Local imports
from models.constants import CACHE_DIR
from services.app_operations import initialize_application_data
from views.main_content import render_main_content
from views.sidebar import render_sidebar
from views.state import initialize_session_state, handle_app_actions
from views.ui_utils import apply_responsive_layout, handle_error

# Configure Streamlit
st.set_page_config(page_title="FS FilterLab", layout="wide")
apply_responsive_layout()
Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)


def main():
    """
    Main application entry point.
    
    Initializes the Streamlit application by:
    1. Loading and validating application data (filters, QE, illuminants)
    2. Setting up the unified state management system
    3. Rendering the sidebar with controls and filter selection
    4. Displaying the main content area with charts and analysis
    5. Handling user actions and interactions
    
    The application uses a modular architecture with separate services for
    data loading, calculations, and visualization.
    """
    # 1. Initialize data and state (using new unified state management)
    app_state = initialize_session_state()  # Returns StateManager directly
    with st.spinner("Loading filters, sensor profiles, illuminants, and reflectors..."):
        data = initialize_application_data()
    
    if not data:
        handle_error("❌ Failed to load application data. Check data files.", stop_execution=True)
        return
    
    # 2. Render sidebar
    sidebar_actions, workflow_snapshot = render_sidebar(app_state, data)
    
    # 3. Render main content  
    render_main_content(app_state, data, workflow_snapshot)
    
    # 4. Handle actions
    handle_app_actions(sidebar_actions, app_state, data, workflow_snapshot)


if __name__ == "__main__":
    main()
