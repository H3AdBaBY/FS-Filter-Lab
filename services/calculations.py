"""
Mathematical calculations for FS FilterLab.

This module provides all mathematical computation functions for:
- Transmission calculations and filtering
- Color processing and RGB response
- Channel mixing transformations
- Metrics computation and formatting
- White balance calculations
- Deviation analysis
"""
# Third-party imports
import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Any

# Local imports
from models.constants import VEGETATION_PREVIEW_FILES
from models.core import FilterCollection, TargetProfile, ChannelMixerSettings, ReflectorCollection
from models import INTERP_GRID
from services.channel_mixer import apply_channel_mixing_to_responses, apply_channel_mixing_to_colors


@dataclass(frozen=True)
class EffectiveTransmissionResult:
    """Green-QE-weighted transmission with explicit domain coverage."""

    effective_transmission: float
    effective_stops: float
    coverage: float
    available: bool
    reason: Optional[str] = None


@dataclass(frozen=True)
class WhiteBalanceResult:
    """Sensor-response neutralization relative to the green channel."""

    balance_divisors: Dict[str, float]
    balance_multipliers: Dict[str, float]
    channel_responses: Dict[str, float]
    available: bool
    reason: Optional[str] = None


# ============================================================================
# TRANSMISSION CALCULATIONS
# ============================================================================

def compute_combined_transmission(transmission_values: List[np.ndarray], combine: bool = True) -> np.ndarray:
    """
    Compute combined transmission from multiple filter transmissions.
    
    Args:
        transmission_values: List of transmission arrays
        combine: Whether to combine the transmissions (multiply them)
    
    Returns:
        Combined transmission or first transmission if not combining
    """
    if not transmission_values:
        return np.ones_like(INTERP_GRID)
        
    if combine and len(transmission_values) > 1:
        stack = np.array(transmission_values)
        combined = np.nanprod(stack, axis=0)
        combined[np.any(np.isnan(stack), axis=0)] = np.nan
        return combined
    
    return transmission_values[0]


def compute_filter_transmission(
    filter_indices: List[int], 
    filter_matrix: np.ndarray
) -> Tuple[np.ndarray, str, Optional[np.ndarray]]:
    """
    Compute filter transmission from filter indices.
    
    Args:
        filter_indices: List of filter indices
        filter_matrix: Matrix of filter transmissions
    
    Returns:
        Tuple of (transmission, label, combined_transmission)
    """
    if not filter_indices:
        return np.ones_like(INTERP_GRID), "No Filter", None
    
    if len(filter_indices) > 1:
        transmissions = [filter_matrix[idx] for idx in filter_indices]
        combined = compute_combined_transmission(transmissions, combine=True)
        return combined, "Combined", combined
    
    transmission = filter_matrix[filter_indices[0]]
    return transmission, "Single", None


def compute_active_transmission(
    selected_filters: List[str],
    selected_indices: List[int],
    filter_matrix: np.ndarray
) -> np.ndarray:
    """
    Compute the active transmission based on selected filters.
    
    Args:
        selected_filters: List of selected filter display names
        selected_indices: List of corresponding filter indices
        filter_matrix: Matrix of filter transmissions
    
    Returns:
        Active transmission array
    """
    if selected_filters and selected_indices and filter_matrix is not None:
        transmissions = [filter_matrix[idx] for idx in selected_indices]
        return compute_combined_transmission(transmissions, combine=True)
    
    return np.ones_like(INTERP_GRID)  # Identity transmission (no filter effect)


def compute_selected_filter_indices(
    selected_filters: List[str],
    filter_multipliers: Dict[str, int],
    filter_collection: FilterCollection
) -> List[int]:
    """
    Compute indices of selected filters with their multipliers.
    
    Args:
        selected_filters: List of selected filter display names
        filter_multipliers: Dictionary mapping filter names to their multiplier counts
        filter_collection: Collection of available filters
    
    Returns:
        List of filter indices
    """
    if not selected_filters:
        return []
    
    display_to_index = filter_collection.get_display_to_index_map()
    selected_indices = []
    
    for name in selected_filters:
        if name not in display_to_index:
            continue
            
        idx = display_to_index[name]
        count = filter_multipliers.get(name, 1)
        selected_indices.extend([idx] * count)
        
    return selected_indices


def is_valid_transmission(transmission: np.ndarray) -> bool:
    """
    Check if transmission array is valid for computation.
    
    Args:
        transmission: Transmission values to check
        
    Returns:
        True if transmission is valid, False otherwise
    """
    try:
        return (transmission is not None and 
                hasattr(transmission, '__len__') and
                len(transmission) > 0 and 
                np.any(np.isfinite(transmission)))
    except (TypeError, ValueError):
        # Handle cases where transmission is not array-like or has invalid shape
        return False


# ============================================================================
# METRICS CALCULATIONS
# ============================================================================

def compute_effective_stops(
    transmission: np.ndarray, 
    sensor_qe: np.ndarray,
    illuminant: Optional[np.ndarray] = None
) -> EffectiveTransmissionResult:
    """
    Compute effective stops from transmission, sensor QE, and illuminant.
    
    Args:
        transmission: Transmission values (0-1)
        sensor_qe: Sensor quantum efficiency values (%)
        illuminant: Illuminant spectrum (optional, defaults to uniform)
    
    Returns the approved green-QE-weighted metric, coverage, and availability.
    """
    # Ensure inputs are numpy arrays
    transmission = np.asarray(transmission, dtype=float)
    sensor_qe = np.asarray(sensor_qe, dtype=float)
    
    # Default to uniform illuminant if not provided
    if illuminant is None:
        illuminant = np.ones_like(transmission)
    else:
        illuminant = np.asarray(illuminant, dtype=float)

    unavailable = lambda reason: EffectiveTransmissionResult(
        np.nan, np.nan, 0.0, False, reason
    )
    if transmission.shape != sensor_qe.shape or transmission.shape != illuminant.shape:
        return unavailable("transmission, green QE, and illuminant shapes differ")

    weight_domain = np.isfinite(sensor_qe) & np.isfinite(illuminant)
    if np.any(sensor_qe[weight_domain] < 0) or np.any(illuminant[weight_domain] < 0):
        return unavailable("green QE and illuminant weights must be non-negative")

    weights = sensor_qe * illuminant
    positive_weight = weight_domain & (weights > 0)
    denominator = np.sum(weights[positive_weight])
    if not np.isfinite(denominator) or denominator <= 0:
        return unavailable("green QE and illuminant have no positive common weight")

    finite_transmission = np.isfinite(transmission)
    if np.any((transmission[finite_transmission] < 0) | (transmission[finite_transmission] > 1)):
        return unavailable("transmission must use physical fractional values in [0, 1]")

    valid = positive_weight & finite_transmission
    covered_weight = np.sum(weights[valid])
    coverage = float(covered_weight / denominator)
    if covered_weight <= 0:
        return unavailable("transmission has zero coverage of the positive weighting domain")

    effective_transmission = float(
        np.sum(transmission[valid] * weights[valid]) / covered_weight
    )
    stops = np.inf if effective_transmission == 0 else float(-np.log2(effective_transmission))
    return EffectiveTransmissionResult(
        effective_transmission, stops, coverage, True
    )


def calculate_transmission_deviation_metrics(
    transmission: np.ndarray,
    target_profile: Optional[TargetProfile],
    log_stops: bool = False
) -> Dict[str, Any]:
    """
    Calculate deviation metrics between transmission and target profile.
    
    Args:
        transmission: Transmission values
        target_profile: Target profile to compare against
        log_stops: Whether to calculate metrics in log space (stops)
    
    Returns:
        Dictionary of deviation metrics
    """
    if target_profile is None:
        return {}

    valid_t = ~np.isnan(transmission)
    valid_p = target_profile.valid
    
    overlap = valid_t & valid_p
    if not overlap.any():
        return {}

    if log_stops:
        dev = np.log2(transmission[overlap]) - np.log2(target_profile.values[overlap] / 100)
        unit = 'stops'
    else:
        dev = transmission[overlap] * 100 - target_profile.values[overlap]
        unit = '%'

    mae = np.mean(np.abs(dev))
    bias = np.mean(dev)
    maxd = np.max(np.abs(dev))
    rmse = np.sqrt(np.mean(dev**2))

    return {'MAE': mae, 'Bias': bias, 'MaxDev': maxd, 'RMSE': rmse, 'Unit': unit}


# ============================================================================
# COLOR PROCESSING AND RGB RESPONSE
# ============================================================================

def normalize_pixels(pixels: np.ndarray) -> np.ndarray:
    """
    Normalize pixel values to a 0-1 range.
    
    Args:
        pixels: RGB pixel values
        
    Returns:
        Normalized pixels
    """
    max_value = np.max(pixels)
    if max_value > 0:
        return pixels / max_value
    return pixels


def compute_rgb_response(
    transmission: np.ndarray,
    quantum_efficiency: Dict[str, np.ndarray],
    white_balance_gains: Dict[str, float],
    visible_channels: Dict[str, bool],
    channel_mixer: Optional[ChannelMixerSettings] = None
) -> Tuple[Dict[str, np.ndarray], np.ndarray, float]:
    """
    Compute RGB response from transmission and quantum efficiency.
    
    Args:
        transmission: Transmission values
        quantum_efficiency: Dictionary of quantum efficiency values by channel
        white_balance_gains: Balance divisors by channel
        visible_channels: Presentation-only visibility state (not applied here)
        channel_mixer: Optional channel mixer settings for RGB manipulation
    
    Returns:
        Tuple of (responses_by_channel, rgb_matrix, max_response)
    """
    # Create empty arrays for responses
    responses = {}
    rgb_stack = []
    
    # Get sample array size
    sample_size = next(iter(quantum_efficiency.values())).shape if quantum_efficiency else 0
    
    # Check for valid transmission data
    if not is_valid_transmission(transmission):
        zero_array = np.zeros(sample_size)
        for channel in ['R', 'G', 'B']:
            responses[channel] = zero_array
            rgb_stack.append(zero_array)
        return responses, np.stack(rgb_stack, axis=1) if rgb_stack else np.array([]), 0.0

    # Process each color channel
    max_response = 0.0
    for channel in ['R', 'G', 'B']:
        # Get quantum efficiency for this channel
        qe_curve = quantum_efficiency.get(channel)
        
        # Skip if no QE data or size mismatch
        if qe_curve is None or len(qe_curve) != len(transmission):
            responses[channel] = np.zeros_like(transmission)
            rgb_stack.append(responses[channel])
            continue

        divisor = white_balance_gains.get(channel, 1.0)
        if not np.isfinite(divisor) or divisor <= 0:
            weighted = np.full_like(transmission, np.nan, dtype=float)
        else:
            weighted = transmission * qe_curve / divisor
        finite = weighted[np.isfinite(weighted)]
        if finite.size:
            max_response = max(max_response, float(np.max(finite)))

        responses[channel] = weighted
        rgb_stack.append(responses[channel])
    
    # Apply channel mixing if enabled
    if channel_mixer is not None and channel_mixer.enabled:
        responses = apply_channel_mixing_to_responses(responses, channel_mixer)
        # Update rgb_stack with mixed responses
        rgb_stack = [responses['R'], responses['G'], responses['B']]

    # Scientific output remains linear and unfloored. Visibility and display
    # normalization are applied only by visualization functions.
    rgb_matrix = np.stack(rgb_stack, axis=1)

    return responses, rgb_matrix, max_response


def compute_white_balance(
    transmission: np.ndarray,
    quantum_efficiency: Dict[str, np.ndarray],
    illuminant: np.ndarray
) -> WhiteBalanceResult:
    """
    Compute green-referenced sensor-response balance on one common domain.
    
    Args:
        transmission: Transmission values
        quantum_efficiency: Dictionary of quantum efficiency values by channel
        illuminant: Illuminant curve
    
    Returns:
        Divisors, reciprocal multipliers, responses, and availability reason
    """
    channels = ("R", "G", "B")
    if not is_valid_transmission(transmission):
        return WhiteBalanceResult({}, {}, {}, False, "transmission is unavailable")
    if any(channel not in quantum_efficiency for channel in channels):
        return WhiteBalanceResult({}, {}, {}, False, "R, G, and B QE channels are required")

    transmission = np.asarray(transmission, dtype=float)
    illuminant = np.asarray(illuminant, dtype=float)
    qe_curves = {
        channel: np.asarray(quantum_efficiency[channel], dtype=float)
        for channel in channels
    }
    if any(curve.shape != transmission.shape for curve in qe_curves.values()) or illuminant.shape != transmission.shape:
        return WhiteBalanceResult({}, {}, {}, False, "transmission, QE, and illuminant shapes differ")

    common = np.isfinite(transmission) & np.isfinite(illuminant)
    for curve in qe_curves.values():
        common &= np.isfinite(curve)
    if not np.any(common):
        return WhiteBalanceResult({}, {}, {}, False, "common finite RGB support is empty")
    if np.any(transmission[common] < 0) or np.any(illuminant[common] < 0):
        return WhiteBalanceResult({}, {}, {}, False, "transmission and illuminant must be non-negative")
    if any(np.any(curve[common] < 0) for curve in qe_curves.values()):
        return WhiteBalanceResult({}, {}, {}, False, "QE values must be non-negative")

    responses = {
        channel: float(
            np.sum(transmission[common] * (curve[common] / 100.0) * illuminant[common])
        )
        for channel, curve in qe_curves.items()
    }
    green = responses["G"]
    if green <= 0:
        return WhiteBalanceResult({}, {}, responses, False, "green response is zero")

    divisors = {channel: response / green for channel, response in responses.items()}
    multipliers = {
        channel: (np.inf if divisor == 0 else 1.0 / divisor)
        for channel, divisor in divisors.items()
    }
    return WhiteBalanceResult(divisors, multipliers, responses, True)


def compute_white_balance_gains(
    transmission: np.ndarray,
    quantum_efficiency: Dict[str, np.ndarray],
    illuminant: np.ndarray,
) -> Dict[str, float]:
    """Compatibility adapter returning divisors or an explicit invalid error."""
    result = compute_white_balance(transmission, quantum_efficiency, illuminant)
    if not result.available:
        raise ValueError(f"sensor-response balance unavailable: {result.reason}")
    return result.balance_divisors


# ============================================================================
# REFLECTOR CALCULATIONS
# ============================================================================

def compute_reflector_color(
    reflector: np.ndarray,
    transmission: np.ndarray,
    quantum_efficiency: Dict[str, np.ndarray],
    illuminant: np.ndarray,
    channel_mixer: Optional[ChannelMixerSettings] = None
) -> np.ndarray:
    """
    Compute reflector color from reflector, transmission, QE, and illuminant.
    
    Args:
        reflector: Reflector spectrum
        transmission: Transmission values
        quantum_efficiency: Dictionary of quantum efficiency values by channel
        illuminant: Illuminant curve
        channel_mixer: Optional channel mixer settings for color manipulation
    
    Returns:
        RGB color as numpy array [R, G, B]
    """
    # Early exit for invalid data
    if not is_valid_transmission(transmission) or reflector is None:
        return np.zeros(3)
        
    balance = compute_white_balance(transmission, quantum_efficiency, illuminant)
    if not balance.available:
        return np.full(3, np.nan)

    # Process each channel
    rgb_resp = {}
    for ch in ['R', 'G', 'B']:
        qe_curve = quantum_efficiency.get(ch)
        if qe_curve is None:
            rgb_resp[ch] = 0.0
            continue

        # Find valid data points
        valid = (~np.isnan(transmission) & ~np.isnan(qe_curve) & 
                ~np.isnan(illuminant) & ~np.isnan(reflector))
                
        if not valid.any():
            rgb_resp[ch] = 0.0
            continue

        # Calculate channel response
        rgb_resp[ch] = np.nansum(
            reflector[valid] * 
            transmission[valid] * 
            (qe_curve[valid] / 100.0) * 
            illuminant[valid]
        )

    # Apply the approved multiplicative correction exactly once.
    rgb_values = np.zeros(3)
    for i, ch in enumerate(['R', 'G', 'B']):
        rgb_values[i] = rgb_resp.get(ch, 0.0) * balance.balance_multipliers[ch]
    
    # Apply channel mixing if enabled
    if channel_mixer is not None and channel_mixer.enabled:
        rgb_values = apply_channel_mixing_to_colors(rgb_values, channel_mixer)
            
    return rgb_values


def find_vegetation_preview_reflectors(reflector_collection: ReflectorCollection) -> Optional[List[int]]:
    """
    Find the exact 4 hardcoded leaf reflectors for vegetation preview.
    
    Returns indices of these specific files in order:
    1. Leaf_1_reflectance_extrapolated_1100.tsv
    2. Leaf_2_reflectance_extrapolated_1100.tsv 
    3. Leaf_3_reflectance_extrapolated_1100.tsv
    4. Leaf_4_reflectance_extrapolated_1100.tsv
    
    Args:
        reflector_collection: The reflector collection to search
        
    Returns:
        List of 4 indices if all files found, None if any are missing
    """
    if not reflector_collection or not hasattr(reflector_collection, 'reflectors'):
        return None
        
    # Use filenames from constants (without .tsv extension)
    required_names = VEGETATION_PREVIEW_FILES
    
    indices = []
    
    # Find each required reflector by exact name match
    for required_name in required_names:
        found_idx = None
        
        for i, reflector in enumerate(reflector_collection.reflectors):
            # Check if reflector name matches exactly (handles both with/without .tsv)
            if (reflector.name == required_name or 
                reflector.name == f"{required_name}.tsv" or
                reflector.name.replace('.tsv', '') == required_name):
                found_idx = i
                break
                
        if found_idx is None:
            # Missing required file - return None to indicate failure
            return None
            
        indices.append(found_idx)
    
    return indices


def compute_reflector_preview_colors(
    reflector_matrix: np.ndarray, 
    transmission: np.ndarray,
    qe_data: Dict[str, np.ndarray],
    illuminant: np.ndarray,
    reflector_collection: ReflectorCollection = None,
    channel_mixer: Optional[ChannelMixerSettings] = None
) -> Optional[np.ndarray]:
    """
    Compute colors for vegetation preview using hardcoded leaf files only.
    
    Uses these exact files in a 2x2 grid:
    - Leaf_1_reflectance_extrapolated_1100.tsv
    - Leaf_2_reflectance_extrapolated_1100.tsv
    - Leaf_3_reflectance_extrapolated_1100.tsv 
    - Leaf_4_reflectance_extrapolated_1100.tsv
    
    Args:
        reflector_matrix: Matrix of reflector data
        transmission: Transmission values
        qe_data: Quantum efficiency data
        illuminant: Illuminant curve
        reflector_collection: ReflectorCollection with reflector names
        channel_mixer: Optional channel mixer settings for color manipulation
        
    Returns:
        Array of RGB pixel values or None if hardcoded files not found
    """
    # Find the exact hardcoded leaf files
    if reflector_collection is None:
        return None
        
    leaf_indices = find_vegetation_preview_reflectors(reflector_collection)
    
    if leaf_indices is None:
        # Required leaf files not found - return None to show warning
        return None
    
    # Create a 2x2 grid using only the hardcoded leaf files
    pixels = np.zeros((2, 2, 3))
    for i in range(2):
        for j in range(2):
            grid_idx = i * 2 + j
            reflector_idx = leaf_indices[grid_idx]
            reflector = reflector_matrix[reflector_idx]
            pixels[i, j] = compute_reflector_color(reflector, transmission, qe_data, illuminant, channel_mixer)
    
    # Replace any NaN values with zeros
    pixels = np.nan_to_num(pixels)
    
    # Return None if all values are zero
    if not np.any(pixels):
        return None
        
    return pixels


def compute_single_reflector_color(
    reflector_matrix: np.ndarray,
    selected_idx: int,
    transmission: np.ndarray,
    qe_data: Dict[str, np.ndarray],
    illuminant: np.ndarray,
    channel_mixer: Optional[ChannelMixerSettings] = None
) -> Optional[np.ndarray]:
    """
    Compute color for a single selected reflector.
    
    Args:
        reflector_matrix: Matrix of reflector data
        selected_idx: Index of the selected reflector
        transmission: Transmission values
        qe_data: Quantum efficiency data
        illuminant: Illuminant curve
        channel_mixer: Optional channel mixer settings for color manipulation
        
    Returns:
        Array with single RGB pixel value or None if computation failed
    """
    # Check if we have valid data and index
    if (reflector_matrix is None or 
        selected_idx is None or 
        selected_idx >= len(reflector_matrix) or 
        selected_idx < 0):
        return None
    
    # Compute color for the selected reflector
    reflector = reflector_matrix[selected_idx]
    color = compute_reflector_color(reflector, transmission, qe_data, illuminant, channel_mixer)
    
    # Replace any NaN values with zeros
    color = np.nan_to_num(color)
    
    # Return None if all values are zero
    if not np.any(color):
        return None
    
    # Return as 1x1x3 array for image display
    return color.reshape(1, 1, 3)


def is_reflector_data_valid(reflector_collection: ReflectorCollection) -> bool:
    """
    Check if the reflector collection is valid for color preview.
    """
    return (reflector_collection is not None and
            hasattr(reflector_collection, "reflector_matrix") and
            len(reflector_collection.reflector_matrix) > 0)


def check_reflector_wavelength_validity(reflector_matrix: np.ndarray) -> bool:
    """
    Check if reflector data has sufficient valid wavelengths (minimum 10).
    """
    if reflector_matrix is None:
        return False
        
    # Count valid wavelengths for each reflector
    num_valid_wavelengths = np.sum(~np.isnan(reflector_matrix), axis=1)
    
    # Require at least 10 valid wavelengths
    return not np.any(num_valid_wavelengths < 10)


# ============================================================================
# FORMATTING FUNCTIONS
# ============================================================================

def format_transmission_metrics(
    trans: np.ndarray, 
    label: str, 
    avg_trans: float, 
    effective_stops: float
) -> Dict[str, str]:
    """
    Format transmission metrics for display.
    
    Args:
        trans: Transmission values
        label: Label for the transmission
        avg_trans: Average transmission (0-1)
        effective_stops: Effective light loss in stops
        
    Returns:
        Dictionary containing formatted metrics
    """
    return {
        "label": label,
        "effective_stops": "∞" if np.isposinf(effective_stops) else f"{effective_stops:.2f}",
        "avg_transmission_pct": f"{avg_trans * 100:.1f}%"
    }


def format_deviation_metrics(
    metrics: Optional[Dict[str, float]],
    target_profile: TargetProfile
) -> Optional[Dict[str, str]]:
    """
    Format deviation metrics for display.
    
    Args:
        metrics: Metrics dictionary from compute_deviation_metrics
        target_profile: Target profile
        
    Returns:
        Dictionary containing formatted metrics or None if metrics is None
    """
    if not metrics:
        return None
    
    return {
        "target_name": target_profile.name,
        "mae": f"{metrics['MAE']:.2f} {metrics['Unit']}",
        "bias": f"{metrics['Bias']:.2f} {metrics['Unit']}",
        "max_dev": f"{metrics['MaxDev']:.2f} {metrics['Unit']}",
        "rmse": f"{metrics['RMSE']:.2f} {metrics['Unit']}"
    }


def format_white_balance_data(
    white_balance_gains: Dict[str, float],
    selected_filters: List[str]
) -> Dict[str, Any]:
    """
    Format white balance data for display.
    
    Args:
        white_balance_gains: Dictionary of white balance gains by channel
        selected_filters: List of selected filter names
        
    Returns:
        Dictionary with formatted white balance data
    """
    # Convert stored divisors to the multipliers actually applied.
    multipliers = {
        k: (1.0 / v if v != 0 else 0.0)
        for k, v in white_balance_gains.items()
    }
    
    # Add a note if no filters are selected
    has_filters = len(selected_filters) > 0
    
    return {
        "has_filters": has_filters,
        "intensities": {
            "R": f"{multipliers['R']:.3f}",
            "G": f"{multipliers['G']:.3f}",
            "B": f"{multipliers['B']:.3f}"
        }
    }
