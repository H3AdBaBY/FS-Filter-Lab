"""
Main content display components for FS FilterLab.

This module consolidates all main content area UI components including
data displays, charts, and visualizations.
"""
# Third-party imports
import streamlit as st
import numpy as np
from typing import Dict, List, Optional, Any, Callable

# Local imports
from models.core import TargetProfile
from models.constants import UI_INFO_MESSAGES, UI_WARNING_MESSAGES, UI_CHART_TITLES, UI_SECTIONS, UI_LABELS

# ============================================================================
# CHART RENDERING UTILITIES
# ============================================================================

def _apply_chart_layout_and_display(fig: Any, width: str, height: Optional[int], description: Optional[str]) -> None:
    """Helper function to apply layout settings and display chart."""
    # Apply height if specified
    if height and hasattr(fig, "update_layout"):
        fig.update_layout(height=height)
        
    # Display the chart
    st.plotly_chart(fig, width=width)
    
    if description:
        st.markdown(description)


def render_chart(
    fig: Any, 
    title: Optional[str] = None, 
    description: Optional[str] = None,
    width: str = 'stretch',
    height: Optional[int] = None
) -> None:
    """Render a chart with optional title and description."""
    if title:
        st.subheader(title)
        
    _apply_chart_layout_and_display(fig, width, height, description)


def render_expandable_chart(
    fig: Any,
    title: str,
    expanded: bool = False,
    width: str = 'stretch',
    height: Optional[int] = None,
    description: Optional[str] = None
) -> None:
    """Render a chart within an expandable section."""
    with st.expander(title, expanded=expanded):
        _apply_chart_layout_and_display(fig, width, height, description)


def render_chart_with_controls(
    fig: Any,
    title: Optional[str] = None,
    control_elements: Dict[str, Callable] = None,
    width: str = 'stretch',
    height: Optional[int] = None,
    description: Optional[str] = None
) -> Dict[str, Any]:
    """Render a chart with control elements."""
    if title:
        st.subheader(title)
    
    # Handle controls
    control_values = {}
    if control_elements:
        cols = st.columns(len(control_elements))
        for i, (name, render_fn) in enumerate(control_elements.items()):
            with cols[i]:
                control_values[name] = render_fn()
    
    _apply_chart_layout_and_display(fig, width, height, description)
    
    return control_values

# ============================================================================
# DATA DISPLAY COMPONENTS
# ============================================================================

def transmission_metrics(
    trans: np.ndarray, 
    label: str, 
    sensor_qe: Optional[np.ndarray],
    illuminant: Optional[np.ndarray] = None,
    effective_result: Optional[Any] = None,
) -> None:
    """Display transmission metrics (light loss)."""
    from services.calculations import format_transmission_metrics
    from services import compute_effective_stops
    
    # Check if we have valid data
    valid = ~np.isnan(trans)
    if not valid.any():
        from views.ui_utils import show_warning_message
        show_warning_message(f"Cannot compute average transmission for {label}: insufficient data.")
        return
    
    # Check if we have sensor QE data
    if sensor_qe is None:
        from views.ui_utils import show_warning_message
        show_warning_message(f"Cannot compute light loss for {label}: no sensor QE data.")
        return
    
    # Calculate effective stops with illuminant weighting
    result = effective_result or compute_effective_stops(trans, sensor_qe, illuminant)
    if not result.available:
        from views.ui_utils import show_warning_message
        show_warning_message(f"Cannot compute green-channel effective stops for {label}: {result.reason}.")
        return
    
    # Format metrics
    metrics = format_transmission_metrics(
        trans, label, result.effective_transmission, result.effective_stops
    )
    coverage_note = "" if result.coverage == 1.0 else f", partial coverage: {result.coverage:.2%}"
    
    # Display results
    st.markdown(
        f"**Green-channel effective light loss ({metrics['label']}):** "
        f"{metrics['effective_stops']} stops  \n"
        f"(Green-QE-weighted transmission: {metrics['avg_transmission_pct']}{coverage_note})"
    )


def deviation_metrics(
    transmission: np.ndarray, 
    combined: Optional[np.ndarray], 
    target_profile: Optional[TargetProfile]
) -> None:
    """Display deviation metrics from target profile."""
    from services.calculations import format_deviation_metrics, calculate_transmission_deviation_metrics
    
    if target_profile is None:
        return
    
    # Use combined transmission if available
    trans_for_dev = combined if combined is not None else transmission
    
    # Calculate metrics
    metrics = calculate_transmission_deviation_metrics(trans_for_dev, target_profile)
    
    if not metrics:
        if target_profile:
            from views.ui_utils import show_info_message
            show_info_message(UI_INFO_MESSAGES['no_target_overlap'])
        return    # Format metrics for display
    formatted = format_deviation_metrics(metrics, target_profile)
    
    # Display metrics
    st.markdown(
        f"**Deviation from target ({formatted['target_name']}):**  \n"
        f"- MAE: `{formatted['mae']}`  \n"
        f"- Bias: `{formatted['bias']}`  \n"
        f"- Max Dev: `{formatted['max_dev']}`  \n"
        f"- RMSE: `{formatted['rmse']}`"
    )


def white_balance_display(
    white_balance_gains: Dict[str, float],
    selected_filters: List[str],
    applied: bool,
) -> None:
    """Display applied sensor-response balance multipliers in the UI."""
    from services.calculations import format_white_balance_data
    
    # Format white balance data
    wb_data = format_white_balance_data(white_balance_gains, selected_filters)
    
    # Add a note if no filters are selected
    no_filter_note = " (No filter selected)" if not wb_data["has_filters"] else ""
    
    status = "applied" if applied else "not applied"
    st.markdown(
        f"**Sensor-Response Balance Multipliers{no_filter_note}:** "
        f"({status}; Green = 1.000):  \n"
        f"R: {wb_data['intensities']['R']}   "
        f"G: {wb_data['intensities']['G']}   "
        f"B: {wb_data['intensities']['B']}"
    )


def raw_qe_and_illuminant(app_state, data) -> None:
    """Display raw quantum efficiency and illuminant data charts."""
    """Display reflectance and illuminant curves in Streamlit expander."""
    from models.constants import INTERP_GRID
    from services.visualization import create_illuminant_figure, create_leaf_reflectance_figure, create_single_reflectance_figure
    
    # Extract needed data
    reflector_collection = data['reflector_collection']
    illuminant_metadata = data['illuminant_metadata']
    
    with st.expander(UI_SECTIONS['reflectance_illuminant_curves']):
        # Show leaf reflectance spectra if available
        if (reflector_collection and 
            hasattr(reflector_collection, 'reflector_matrix') and 
            len(reflector_collection.reflector_matrix) >= 4):
            
            fig_leaves = create_leaf_reflectance_figure(
                INTERP_GRID, 
                reflector_collection.reflector_matrix, 
                reflector_collection
            )
            
            if fig_leaves is not None:
                render_chart(fig_leaves, UI_CHART_TITLES['leaf_reflectance'])
            else:
                from views.ui_utils import show_info_message
                show_info_message(UI_INFO_MESSAGES['leaf_data_required'])
        
        # Show selected reflectance spectrum if available
        selected_reflector_idx = st.session_state.get("selected_reflector_idx", None)
        if (reflector_collection and 
            hasattr(reflector_collection, 'reflector_matrix') and
            selected_reflector_idx is not None and 
            selected_reflector_idx != "None" and 
            isinstance(selected_reflector_idx, int) and 
            selected_reflector_idx < len(reflector_collection.reflector_matrix)):
            
            fig_single = create_single_reflectance_figure(
                INTERP_GRID,
                reflector_collection.reflector_matrix,
                reflector_collection,
                selected_reflector_idx
            )
            
            if fig_single is not None:
                render_chart(fig_single)
        
        # Show illuminant curve
        if app_state.illuminant is not None and app_state.illuminant_name is not None:
            fig_illum = create_illuminant_figure(INTERP_GRID, app_state.illuminant, app_state.illuminant_name)
            
            # Description for the illuminant
            if app_state.illuminant_name in illuminant_metadata:
                description = f"**Description:** {illuminant_metadata[app_state.illuminant_name]}"
                st.markdown(description)
                
            render_chart(
                fig_illum, 
                f"Illuminant: {app_state.illuminant_name}"
            )
        else:
            from views.ui_utils import show_info_message
            show_info_message(UI_INFO_MESSAGES['no_illuminant'])


def filter_response_display(fig) -> None:
    """Display filter response chart in an expandable section."""
    """Display filter response plot."""
    render_chart(fig, title=UI_CHART_TITLES['combined_filter_response'])


def sensor_response_display(fig) -> None:
    """Display sensor response chart in an expandable section."""
    """Display sensor response plot with white balance toggle."""
    
    # White balance toggle is widget-controlled and accessed through app_state
    st.checkbox(
        UI_LABELS['apply_white_balance'], 
        key="apply_white_balance_toggle"
    )
    
    # Display the chart
    render_chart(fig, title=UI_CHART_TITLES['sensor_weighted_response'])


def render_main_content(app_state, data, workflow_snapshot):
    """
    Render the main content area of the application.
    
    Args:
        app_state: Application state manager
        data: Application data dictionary containing collections and calculations
    """
    """
    Render the main content area of the application.
    
    Args:
        app_state: Application state object (now using unified StateManager under the hood)
        data: Dictionary containing loaded application data
    """
    import streamlit as st
    
    from views.forms import import_data_form, advanced_filter_search
    from views.channel_mixer import render_channel_mixer_panel
    
    # Extract data  
    filter_collection = data['filter_collection']
    # Show import dialog if needed
    if app_state.show_import_data:
        import_data_form()
    
    selected_indices = list(workflow_snapshot.selected_indices)
    
    # Header
    st.markdown("""
    <div style='display: flex; justify-content: space-between; align-items: center;'>
        <h4 style='margin: 0;'>FS FilterLab</h4>
    </div>
    """, unsafe_allow_html=True)
    
    # Filter transmission plots and metrics
    if selected_indices:
        _render_filter_analysis(
            app_state, filter_collection, selected_indices, workflow_snapshot
        )
    
    # Sensor response and white balance
    if app_state.current_qe:
        _render_sensor_analysis(app_state, data, workflow_snapshot)
    
    # Raw QE and illuminant curves
    raw_qe_and_illuminant(app_state, data)
    
    # Advanced search UI
    if app_state.show_advanced_search:
        advanced_filter_search(filter_collection.df, filter_collection.filter_matrix)
    
    # Channel mixer UI
    if app_state.show_channel_mixer:
        app_state.channel_mixer = render_channel_mixer_panel(app_state.channel_mixer)


def _render_filter_analysis(
    app_state, filter_collection, selected_indices, workflow_snapshot
):
    """Render filter analysis plots and metrics."""
    from models.constants import INTERP_GRID
    from services import create_filter_response_plot
    
    trans = workflow_snapshot.transmission
    label = workflow_snapshot.transmission_label
    combined = workflow_snapshot.combined_transmission
    
    # Update combined transmission in state
    app_state.combined_transmission = combined if combined is not None else trans
    
    # Display transmission metrics using raw QE data and illuminant
    raw_qe = app_state.current_qe.get('G') if app_state.current_qe else None
    transmission_metrics(
        trans,
        label,
        raw_qe,
        app_state.illuminant,
        workflow_snapshot.effective_result,
    )
    
    # Create and display filter response plot
    filter_names = [filter.name for filter in filter_collection.filters]
    filter_hex_colors = [filter.hex_color for filter in filter_collection.filters]
    
    fig = create_filter_response_plot(
        interp_grid=INTERP_GRID,
        filter_matrix=filter_collection.filter_matrix,
        masks=filter_collection.extrapolated_masks,
        selected_indices=selected_indices,
        combined=combined,
        target_profile=app_state.target_profile,
        log_stops=app_state.log_view,
        filter_names=filter_names,
        filter_hex_colors=filter_hex_colors
    )
    filter_response_display(fig)
    
    # Display deviation metrics
    deviation_metrics(trans, combined, app_state.target_profile)


def _render_sensor_response_plot(app_state, workflow_snapshot) -> None:
    """Create and display the sensor response plot."""
    from models.constants import INTERP_GRID
    from services import create_sensor_response_plot
    
    fig_response = create_sensor_response_plot(
        interp_grid=INTERP_GRID,
        transmission=workflow_snapshot.active_transmission,
        qe_data=app_state.current_qe,
        visible_channels=app_state.rgb_channels_visibility,
        white_balance_gains=(
            workflow_snapshot.balance_result.balance_divisors
            if workflow_snapshot.balance_result.available
            else {"R": 1.0, "G": 1.0, "B": 1.0}
        ),
        apply_white_balance=app_state.apply_white_balance,
        target_profile=app_state.target_profile,
        channel_mixer=app_state.channel_mixer,
        channel_responses=workflow_snapshot.channel_responses,
    )
    
    sensor_response_display(fig_response)


def _render_vegetation_preview(app_state, trans_interp, reflector_collection) -> Optional[np.ndarray]:
    """Render vegetation color preview and return pixels for normalization."""
    from services.calculations import compute_reflector_preview_colors
    from views.sidebar import reflector_preview
    from views.ui_utils import show_warning_message
    
    reflector_matrix = reflector_collection.reflector_matrix
    
    if len(reflector_matrix) >= 4:
        pixels = compute_reflector_preview_colors(
            reflector_matrix, trans_interp, app_state.current_qe, 
            app_state.illuminant, reflector_collection, app_state.channel_mixer
        )
        
        if pixels is not None:
            reflector_preview(pixels)
            return pixels
        else:
            show_warning_message(UI_WARNING_MESSAGES['vegetation_preview_required'])
    else:
        show_warning_message(UI_WARNING_MESSAGES['vegetation_preview_required'])
    
    return None


def _render_single_reflector_preview(app_state, trans_interp, reflector_collection, pixels) -> None:
    """Render single reflector preview if one is selected."""
    import streamlit as st
    
    from services.calculations import compute_single_reflector_color
    from views.sidebar import single_reflector_preview
    from views.ui_utils import show_info_message
    
    reflector_matrix = reflector_collection.reflector_matrix
    selected_reflector_idx = st.session_state.get("selected_reflector_idx", None)
    
    # Validate selection
    if (selected_reflector_idx is not None and 
        selected_reflector_idx != "None" and 
        isinstance(selected_reflector_idx, int) and 
        selected_reflector_idx < len(reflector_matrix)):
        
        single_color = compute_single_reflector_color(
            reflector_matrix, selected_reflector_idx, trans_interp, 
            app_state.current_qe, app_state.illuminant, app_state.channel_mixer
        )
        
        if single_color is not None:
            reflector_name = reflector_collection.reflectors[selected_reflector_idx].name
            
            # Determine global normalization scale
            if pixels is not None:
                global_max = np.max(pixels)
            else:
                # Compute global max from available reflectors
                all_colors = []
                for i in range(min(len(reflector_matrix), 4)):
                    color = compute_single_reflector_color(
                        reflector_matrix, i, trans_interp,
                        app_state.current_qe, app_state.illuminant, app_state.channel_mixer
                    )
                    if color is not None:
                        all_colors.append(color)
                global_max = np.max(all_colors) if all_colors else np.max(single_color)
            
            single_reflector_preview(single_color, reflector_name, global_max)
        else:
            show_info_message(UI_INFO_MESSAGES['color_compute_failed'])


def _render_reflector_previews(app_state, trans_interp, reflector_collection) -> None:
    """Render all reflector color previews."""
    from services.calculations import (
        is_reflector_data_valid,
        check_reflector_wavelength_validity
    )
    from views.ui_utils import show_warning_message
    
    # Check if we have the basic requirements for reflector previews
    if not (app_state.current_qe is not None and 
            app_state.illuminant is not None and 
            hasattr(reflector_collection, 'reflector_matrix')):
        return
    
    if not is_reflector_data_valid(reflector_collection):
        return
        
    reflector_matrix = reflector_collection.reflector_matrix
    
    if not check_reflector_wavelength_validity(reflector_matrix):
        show_warning_message(UI_WARNING_MESSAGES['incomplete_reflector_data'])
    
    # Render vegetation preview first (returns pixels for normalization)
    pixels = _render_vegetation_preview(app_state, trans_interp, reflector_collection)
    
    # Render single reflector preview using the same normalization
    _render_single_reflector_preview(app_state, trans_interp, reflector_collection, pixels)


def _render_sensor_analysis(app_state, data, workflow_snapshot):
    """Render sensor response analysis and reflector previews."""
    from views.ui_utils import show_info_message
    
    # Extract data
    reflector_collection = data['reflector_collection']
    
    trans_interp = workflow_snapshot.active_transmission
    balance = workflow_snapshot.balance_result
    if balance.available:
        app_state.white_balance_gains = balance.balance_divisors
    
    # Render sensor response plot
    _render_sensor_response_plot(app_state, workflow_snapshot)
    
    # Render reflector previews
    _render_reflector_previews(app_state, trans_interp, reflector_collection)
    
    # Display white balance information
    if balance.available:
        white_balance_display(
            balance.balance_divisors,
            app_state.selected_filters,
            workflow_snapshot.apply_white_balance,
        )
    else:
        show_info_message(f"Sensor-response balance unavailable: {balance.reason}.")
