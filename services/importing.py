"""
Consolidated data importing utilities for FS FilterLab.

This module contains all data import functionality for filters, illuminants,
quantum efficiencies, and reflectance data with comprehensive error handling
and user-friendly validation.

Key Features:
- Robust CSV parsing with automatic separator detection
- Comprehensive data validation with descriptive error messages
- Consistent error handling across all import types
- File format validation and range checking
- Safe filename generation and file saving

Import Functions:
- import_filter_from_csv: Import optical filter transmission data
- import_illuminant_from_csv: Import illuminant spectral power distributions
- import_qe_from_csv: Import camera sensor quantum efficiency data
- import_reflectance_absorption_from_csv: Import surface reflectance/absorption spectra

All functions return (success: bool, message: str) tuples for consistent
error handling in the UI layer.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import os
from uuid import uuid4
from typing import Tuple, Dict, Any
import logging

from services.spectral_policy import prepare_spectrum
from services.data_locations import get_user_data_root

# Configure logging for debugging import issues
logger = logging.getLogger(__name__)

# ============================================================================
# COMMON UTILITIES
# ============================================================================

def safe_float(val):
    """Convert a value to float safely, handling various formats."""
    try:
        return float(str(val).replace(',', '.').strip())
    except Exception:
        return np.nan


def validate_wavelength_range(wavelengths: np.ndarray, data_type: str = "data") -> Tuple[bool, str]:
    """
    Validate wavelength range for spectral data.
    
    Args:
        wavelengths: Array of wavelength values
        data_type: Type of data being validated (for error messages)
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if wavelengths.size == 0:
        return False, f"Wavelength column is empty for {data_type}."
        
    min_wl, max_wl = wavelengths.min(), wavelengths.max()
    
    if min_wl < 200 or max_wl > 2000:
        return False, f"Wavelength range ({min_wl:.1f}-{max_wl:.1f} nm) seems invalid. Expected 200-2000 nm."
        
    if max_wl - min_wl < 50:
        return False, f"Wavelength range too narrow ({min_wl:.1f}-{max_wl:.1f} nm). Need at least 50nm range."
        
    return True, ""


def validate_spectral_values(values: np.ndarray, value_type: str, min_val: float = 0, max_val: float = None) -> Tuple[bool, str]:
    """
    Validate spectral values (transmission, reflectance, QE, etc.).
    
    Args:
        values: Array of spectral values
        value_type: Type of values being validated
        min_val: Minimum allowed value
        max_val: Maximum allowed value (None for no limit)
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if values.size == 0:
        return False, f"{value_type} column is empty or contains no valid numbers."
        
    if values.min() < min_val:
        return False, f"{value_type} values cannot be below {min_val} (found: {values.min():.3f})."
        
    if max_val is not None and values.max() > max_val:
        return False, f"{value_type} values seem too high (max: {values.max():.3f}). Expected 0-{max_val}."
        
    return True, ""


def safe_file_save(df: pd.DataFrame, file_path: Path, data_type: str) -> Tuple[bool, str]:
    """
    Safely save a DataFrame to a file with error handling.
    
    Args:
        df: DataFrame to save
        file_path: Path to save the file
        data_type: Type of data being saved (for error messages)
        
    Returns:
        Tuple of (success, message)
    """
    try:
        # Ensure directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save the file
        df.to_csv(file_path, sep='\\t', index=False)
        return True, f"{data_type} data saved successfully to {file_path}"
        
    except PermissionError:
        return False, f"Permission denied: Cannot write to {file_path}. File may be open in another application."
    except OSError as e:
        return False, f"File system error: {str(e)}"
    except Exception as e:
        return False, f"Failed to save file to {file_path}: {str(e)}"


IMPORT_CACHE_KEYS = {
    "filter": "filter_data",
    "illuminant": "illuminants",
    "qe": "qe_data",
    "reflector": "reflectors",
}


def _validate_explicit_unit(unit: str | None, quantity: str) -> str:
    if unit not in {"fraction", "percent"}:
        raise ValueError(
            f"Explicit {quantity} unit is required: choose fraction or percent."
        )
    return unit


def _identity_exists(data_type: str, identity: str) -> bool:
    """Check stable identities across bundled and user collections."""
    from services.data import (
        load_filter_collection,
        load_illuminant_collection,
        load_quantum_efficiencies,
        load_reflector_collection,
    )

    if data_type == "filter":
        return identity in load_filter_collection().get_display_to_index_map()
    if data_type == "illuminant":
        illuminants, _ = load_illuminant_collection()
        return identity in illuminants
    if data_type == "qe":
        camera_keys, _, _ = load_quantum_efficiencies()
        return identity in camera_keys
    if data_type == "reflector":
        collection = load_reflector_collection()
        return identity in {item.name for item in collection.reflectors}
    raise ValueError(f"Unknown import data type: {data_type}")


def _publish_user_dataset(
    frame: pd.DataFrame,
    relative_directory: Path,
    filename: str,
    data_type: str,
    identity: str,
) -> Path:
    """Atomically publish a validated import without overwriting any dataset."""
    destination = get_user_data_root() / relative_directory / filename
    if destination.exists() or _identity_exists(data_type, identity):
        raise FileExistsError(
            f"A {data_type} dataset with identity '{identity}' already exists; "
            "imports never overwrite existing data."
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.{uuid4().hex}.tmp")
    try:
        frame.to_csv(temporary, sep="\t", index=False)
        os.link(temporary, destination)
    except FileExistsError:
        raise FileExistsError(
            f"Import destination already exists: {destination.as_posix()}"
        )
    finally:
        if temporary.exists():
            temporary.unlink()

    from services.data import invalidate_collection_cache

    invalidate_collection_cache(IMPORT_CACHE_KEYS[data_type])
    return destination


def parse_csv(file, separator=';', fallback_separator=','):
    """Parse a CSV file with auto-detection of separator and better error handling."""
    try:
        # Try primary separator first
        raw_data = pd.read_csv(file, sep=separator, header=None, engine='python')
        
        # If we don't have enough columns, try fallback separator
        if raw_data.shape[1] < 2:
            file.seek(0)  # Reset file position for re-reading
            raw_data = pd.read_csv(file, sep=fallback_separator, header=None, engine='python')
        
        # Final validation
        if raw_data.shape[1] < 2:
            raise ValueError(f"CSV file must have at least 2 columns. Found {raw_data.shape[1]} columns.")
            
        if raw_data.shape[0] == 0:
            raise ValueError("CSV file is empty or contains no data rows.")
        
        # Convert to float with better error reporting
        try:
            raw_data = raw_data.map(safe_float)  # Use map instead of deprecated applymap
        except AttributeError:
            # Fallback for older pandas versions
            raw_data = raw_data.applymap(safe_float)
        
        # Accept one optional header row, but no ambiguous non-numeric body rows.
        if len(raw_data) > 1 and raw_data.iloc[0].isna().all():
            raw_data = raw_data.iloc[1:].reset_index(drop=True)

        # Check for too many NaN values
        nan_count = raw_data.isna().sum().sum()
        total_count = raw_data.size
        if nan_count > total_count * 0.5:
            raise ValueError(f"Too many invalid values in CSV ({nan_count}/{total_count}). Check data format.")
            
        return raw_data
        
    except pd.errors.EmptyDataError:
        raise ValueError("CSV file is empty.")
    except pd.errors.ParserError as e:
        raise ValueError(f"CSV parsing error: {str(e)}")
    except Exception as e:
        raise ValueError(f"Failed to read CSV file: {str(e)}")


def extract_spectral_columns(
    raw_data: pd.DataFrame,
    value_column_count: int,
) -> tuple[np.ndarray, ...]:
    """Extract aligned spectral columns without dropping unknown samples."""
    required_columns = value_column_count + 1
    if raw_data.shape[1] < required_columns:
        raise ValueError(
            f"Expected at least {required_columns} spectral columns, "
            f"found {raw_data.shape[1]}."
        )

    arrays = tuple(
        raw_data.iloc[:, index].to_numpy(dtype=float, copy=True)
        for index in range(required_columns)
    )
    wavelengths = arrays[0]
    if wavelengths.size < 2:
        raise ValueError("Spectrum requires at least two wavelength samples.")
    if not np.all(np.isfinite(wavelengths)):
        raise ValueError("Wavelength samples must be finite numeric values.")
    for index, values in enumerate(arrays[1:], start=1):
        if not np.any(np.isfinite(values)):
            raise ValueError(f"Spectral value column {index} has no finite samples.")
    return arrays


def format_import_diagnostics(*prepared_spectra) -> str:
    """Return deterministic, de-duplicated diagnostics for an import result."""
    messages = []
    seen = set()
    for prepared in prepared_spectra:
        for diagnostic in prepared.diagnostics:
            key = (diagnostic.code, diagnostic.message)
            if key in seen:
                continue
            seen.add(key)
            messages.append(f"{diagnostic.code}: {diagnostic.message}")
    return "; ".join(messages)


def get_wavelength_range(wavelengths, extrap_lower=False, extrap_upper=False):
    """Determine the wavelength range based on data and extrapolation settings."""
    base_min = int(np.ceil(wavelengths.min() / 5.0)) * 5
    base_max = int(np.floor(wavelengths.max() / 5.0)) * 5
    
    min_wl = 300 if extrap_lower else base_min
    max_wl = 1100 if extrap_upper else min(1100, base_max)
    
    if min_wl > max_wl:
        raise ValueError("Data range is outside allowable bounds.")
        
    return min_wl, max_wl


def interpolate_spectrum(
    wavelengths,
    values,
    target_wavelengths,
    extrap_lower=False,
    extrap_upper=False,
    quantity="transmission",
):
    """Use the same validated interpolation policy as production loaders."""
    prepared = prepare_spectrum(
        wavelengths,
        values,
        quantity,
        extrapolation="constant" if extrap_lower or extrap_upper else "none",
        target_grid=target_wavelengths,
    )
    return prepared.physical_values


def sanitize_filename(name):
    """Convert a string to a valid filename."""
    return ''.join(c for c in name if c.isalnum() or c in (' ', '_')).rstrip().replace(' ', '_')


def get_extrapolation_suffix(extrap_lower, extrap_upper):
    """Get a standardized suffix for extrapolated files."""
    suffix_parts = []
    if extrap_lower: suffix_parts.append("300")
    if extrap_upper: suffix_parts.append("1100")
    return f"_extrapolated_{'_'.join(suffix_parts)}" if suffix_parts else ""

# ============================================================================
# FILTER IMPORT
# ============================================================================

def import_filter_from_csv(
    uploaded_file, meta, extrap_lower, extrap_upper, unit: str | None = None
):
    """
    Import filter data from a CSV file and save it to the data directory.
    
    Args:
        uploaded_file: The uploaded CSV file
        meta: Dictionary containing filter metadata
        extrap_lower: Whether to extrapolate to 300nm
        extrap_upper: Whether to extrapolate to 1100nm
        
    Returns:
        Tuple of (success, message)
    """
    try:   
        # Validate inputs
        if uploaded_file is None:
            return False, "No file provided for import."
            
        if not meta or not isinstance(meta, dict):
            return False, "Invalid metadata provided."
            
        required_keys = ['manufacturer', 'filter_name', 'filter_number', 'hex_color']
        missing_keys = [key for key in required_keys if key not in meta or not meta[key]]
        if missing_keys:
            return False, f"Missing required metadata: {', '.join(missing_keys)}"
        
        unit = _validate_explicit_unit(unit, "transmission")

        # Parse the CSV with detailed error handling
        try:
            raw_data = parse_csv(uploaded_file)
        except ValueError as e:
            return False, f"CSV parsing failed: {str(e)}"
            
        wavelengths, transmissions = extract_spectral_columns(raw_data, 1)
            
        # Check wavelength range validity
        min_wl, max_wl = wavelengths.min(), wavelengths.max()
        if min_wl < 200 or max_wl > 2000:
            return False, f"Wavelength range ({min_wl:.1f}-{max_wl:.1f} nm) seems invalid. Expected 200-2000 nm."
            
        if max_wl - min_wl < 50:
            return False, f"Wavelength range too narrow ({min_wl:.1f}-{max_wl:.1f} nm). Need at least 50nm range."
        
        # Determine wavelength range
        min_wl, max_wl = get_wavelength_range(wavelengths, extrap_lower, extrap_upper)
        new_wavelengths = np.arange(min_wl, max_wl + 1, 1)
        
        # Interpolate to the new wavelength grid
        prepared = prepare_spectrum(
            wavelengths,
            transmissions,
            "transmission",
            unit=unit,
            extrapolation="constant" if extrap_lower or extrap_upper else "none",
            target_grid=new_wavelengths,
        )
        # Persist the normalized raw curve so the loader can retain excursions
        # while deriving the separate physical calculation curve.
        interpolated = prepared.raw_values

        # Create DataFrame in tall format
        output_df = pd.DataFrame({
            'Wavelength': new_wavelengths,
            'Transmittance': interpolated,
            'Extrapolated': prepared.extrapolated_mask,
            'hex_color': meta["hex_color"],
            'Manufacturer': meta["manufacturer"],
            'Name': meta["filter_name"],
            'Filter Number': meta["filter_number"],
            'Source File': getattr(uploaded_file, "name", "uploaded.csv")
        })

        # Generate filename and save
        base = f"{meta['manufacturer']}_{meta['filter_number']}_{meta['filter_name']}"
        sanitized = sanitize_filename(base)
        suffix = get_extrapolation_suffix(extrap_lower, extrap_upper)
        filename = f"{sanitized}{suffix}.tsv"
        
        identity = (
            f"{meta['filter_name']} ({meta['filter_number']}, "
            f"{meta['manufacturer']})"
        )
        out_path = _publish_user_dataset(
            output_df,
            Path("filters_data") / sanitize_filename(meta["manufacturer"]),
            filename,
            "filter",
            identity,
        )

        diagnostic_summary = format_import_diagnostics(prepared)
        return True, (
            f"Filter data saved successfully to {out_path}. "
            f"Diagnostics: {diagnostic_summary}."
        )
        
    except (ValueError, FileExistsError) as e:
        # These are validation errors we want to show to the user
        return False, str(e)
    except Exception as e:
        # Unexpected errors - log them for debugging
        import logging
        logging.exception(f"Unexpected error in filter import: {str(e)}")
        return False, f"Unexpected error during import: {str(e)}. Please check the file format and try again."

# ============================================================================
# ILLUMINANT IMPORT
# ============================================================================

def import_illuminant_from_csv(uploaded_file, description):
    """
    Import illuminant data from a CSV file and save it to the data directory.
    
    Args:
        uploaded_file: The uploaded CSV file
        description: Illuminant description
        
    Returns:
        Tuple of (success, message)
    """
    try:
        # Validate inputs
        if uploaded_file is None:
            return False, "No file provided for import."
            
        if not description or not description.strip():
            return False, "Description cannot be empty."
        
        # Parse CSV data with error handling
        try:
            raw_data = parse_csv(uploaded_file)
        except ValueError as e:
            return False, f"CSV parsing failed: {str(e)}"
            
        wavelengths, intensity = extract_spectral_columns(raw_data, 1)
            
        # Check wavelength range validity
        min_wl, max_wl = wavelengths.min(), wavelengths.max()
        if min_wl < 200 or max_wl > 2000:
            return False, f"Wavelength range ({min_wl:.1f}-{max_wl:.1f} nm) seems invalid. Expected 200-2000 nm."
            
        if max_wl - min_wl < 50:
            return False, f"Wavelength range too narrow ({min_wl:.1f}-{max_wl:.1f} nm). Need at least 50nm range."
        
        # Validate intensity values
        finite_intensity = intensity[np.isfinite(intensity)]
        if np.any(finite_intensity < 0):
            return False, (
                "Intensity values cannot be negative "
                f"(min: {np.min(finite_intensity):.2f})."
            )

        # Target wavelength range: 300–1100 nm
        full_range = np.arange(300, 1101, 1)
        prepared = prepare_spectrum(
            wavelengths,
            intensity,
            "illuminant",
            unit="relative",
            target_grid=full_range,
        )
        intensity_interp = prepared.physical_values

        # Normalize to 0–100 scale
        max_val = np.nanmax(intensity_interp)
        if max_val > 0:
            intensity_rel = np.round((intensity_interp / max_val) * 100, 3)
        else:
            intensity_rel = intensity_interp

        # Create output DataFrame
        df_out = pd.DataFrame({
            "Wavelength (nm)": full_range,
            "Relative Power": intensity_rel,
            "Name": description,
            "Description": description,
            "Normalization": "Peak normalized to 100",
            "Source File": getattr(uploaded_file, "name", "uploaded.csv"),
        })

        # Save file
        filename = sanitize_filename(description) + ".tsv"
        out_path = _publish_user_dataset(
            df_out,
            Path("illuminants"),
            filename,
            "illuminant",
            description,
        )

        return True, (
            f"Illuminant data saved successfully to {out_path}. "
            "Normalization: peak normalized to 100. "
            f"Diagnostics: {format_import_diagnostics(prepared)}."
        )
        
    except (ValueError, FileExistsError) as e:
        # These are validation errors we want to show to the user
        return False, str(e)
    except Exception as e:
        # Unexpected errors - log them for debugging
        import logging
        logging.exception(f"Unexpected error in illuminant import: {str(e)}")
        return False, f"Unexpected error during import: {str(e)}. Please check the file format and try again."

# ============================================================================
# QUANTUM EFFICIENCY IMPORT
# ============================================================================

def import_qe_from_csv(uploaded_file, brand, model, unit: str | None = None):
    """
    Import quantum efficiency data from a CSV file.
    
    Args:
        uploaded_file: The uploaded CSV file
        brand: Camera brand
        model: Camera model
        
    Returns:
        Tuple of (success, message)
    """
    try:
        # Validate inputs
        if uploaded_file is None:
            return False, "No file provided for import."
            
        if not brand or not brand.strip():
            return False, "Camera brand cannot be empty."
            
        if not model or not model.strip():
            return False, "Camera model cannot be empty."
        
        unit = _validate_explicit_unit(unit, "QE")

        # Parse the CSV with error handling
        try:
            raw_data = parse_csv(uploaded_file)
        except ValueError as e:
            return False, f"CSV parsing failed: {str(e)}"
        
        if raw_data.shape[1] < 4:
            return False, f"Expected at least 4 columns (Wavelength, R, G, B), found {raw_data.shape[1]} columns."

        wavelengths, r_qe, g_qe, b_qe = extract_spectral_columns(raw_data, 3)
        
        # Check wavelength range validity
        min_wl, max_wl = wavelengths.min(), wavelengths.max()
        if min_wl < 200 or max_wl > 2000:
            return False, f"Wavelength range ({min_wl:.1f}-{max_wl:.1f} nm) seems invalid. Expected 200-2000 nm."
            
        if max_wl - min_wl < 50:
            return False, f"Wavelength range too narrow ({min_wl:.1f}-{max_wl:.1f} nm). Need at least 50nm range."
        
        # Validate QE values
        for channel, values in [("R", r_qe), ("G", g_qe), ("B", b_qe)]:
            finite_values = values[np.isfinite(values)]
            if np.any(finite_values < 0):
                return False, f"{channel} channel QE values cannot be negative (min: {np.min(finite_values):.3f})."

        # Interpolate to standard grid (300-1100nm)
        target_wl = np.arange(300, 1101, 1)
        r_prepared = prepare_spectrum(
            wavelengths, r_qe, "qe", unit=unit, target_grid=target_wl
        )
        g_prepared = prepare_spectrum(
            wavelengths, g_qe, "qe", unit=unit, target_grid=target_wl
        )
        b_prepared = prepare_spectrum(
            wavelengths, b_qe, "qe", unit=unit, target_grid=target_wl
        )
        r_interp = r_prepared.physical_values
        g_interp = g_prepared.physical_values
        b_interp = b_prepared.physical_values

        # Create output DataFrame
        output_df = pd.DataFrame({
            'Wavelength': target_wl,
            'R': r_interp,
            'G': g_interp,
            'B': b_interp,
            'Manufacturer': brand,
            'Name': model,
            'Source File': getattr(uploaded_file, "name", "uploaded.csv"),
        })

        # Save file
        filename = f"{sanitize_filename(brand)}_{sanitize_filename(model)}_QE.tsv"
        identity = f"{brand} {model}"
        out_path = _publish_user_dataset(
            output_df,
            Path("QE_data"),
            filename,
            "qe",
            identity,
        )
            
        return True, (
            f"QE data saved successfully to {out_path}. "
            f"Diagnostics: {format_import_diagnostics(r_prepared, g_prepared, b_prepared)}."
        )
        
    except (ValueError, FileExistsError) as e:
        # These are validation errors we want to show to the user
        return False, str(e)
    except Exception as e:
        # Unexpected errors - log them for debugging
        import logging
        logging.exception(f"Unexpected error in QE import: {str(e)}")
        return False, f"Unexpected error during import: {str(e)}. Please check the file format and try again."

# ============================================================================
# REFLECTANCE/ABSORPTION IMPORT
# ============================================================================

def import_reflectance_absorption_from_csv(
    uploaded_file,
    meta,
    extrap_lower,
    extrap_upper,
    unit: str | None = None,
):
    """
    Import reflectance or absorption data from a CSV file.
    
    Args:
        uploaded_file: The uploaded CSV file
        meta: Dictionary containing metadata
        extrap_lower: Whether to extrapolate to 300nm
        extrap_upper: Whether to extrapolate to 1100nm
        
    Returns:
        Tuple of (success, message)
    """
    try:
        # Validate inputs
        if uploaded_file is None:
            return False, "No file provided for import."
            
        if not meta or not isinstance(meta, dict):
            return False, "Invalid metadata provided."
            
        data_type = meta.get("data_type", "Reflectance")
        if data_type.lower() != "reflectance":
            return False, (
                "Absorption cannot be imported as reflectance because no "
                "conversion measurement model is approved."
            )
        unit = _validate_explicit_unit(unit, "reflectance")

        # Parse the CSV with detailed error handling
        try:
            raw_data = parse_csv(uploaded_file)
        except ValueError as e:
            return False, f"CSV parsing failed: {str(e)}"
            
        wavelengths, values = extract_spectral_columns(raw_data, 1)
            
        # Check wavelength range validity
        min_wl, max_wl = wavelengths.min(), wavelengths.max()
        if min_wl < 200 or max_wl > 2000:
            return False, f"Wavelength range ({min_wl:.1f}-{max_wl:.1f} nm) seems invalid. Expected 200-2000 nm."
            
        if max_wl - min_wl < 50:
            return False, f"Wavelength range too narrow ({min_wl:.1f}-{max_wl:.1f} nm). Need at least 50nm range."

        # Determine wavelength range
        min_wl, max_wl = get_wavelength_range(wavelengths, extrap_lower, extrap_upper)
        new_wavelengths = np.arange(min_wl, max_wl + 1, 1)
        
        # Interpolate
        prepared = prepare_spectrum(
            wavelengths,
            values,
            "reflectance",
            unit=unit,
            extrapolation="constant" if extrap_lower or extrap_upper else "none",
            target_grid=new_wavelengths,
        )
        interpolated = prepared.raw_values

        # Create DataFrame
        # Create name and description arrays - only fill the first row, leave others empty
        name_array = [""] * len(new_wavelengths)
        description_array = [""] * len(new_wavelengths)
        name_array[0] = meta.get("name", "Unknown")  # Only first row gets the name
        description_array[0] = meta.get("description", "")  # Only first row gets the description
        
        output_df = pd.DataFrame({
            'Wavelength': new_wavelengths,
            data_type: interpolated,
            'Extrapolated': prepared.extrapolated_mask,
            'Name': name_array,
            'Description': description_array,
            'Source File': getattr(uploaded_file, "name", "uploaded.csv"),
        })

        # Save file
        base_name = meta.get("name", "spectrum")
        sanitized = sanitize_filename(base_name)
        suffix = get_extrapolation_suffix(extrap_lower, extrap_upper)
        filename = f"{sanitized}{suffix}.tsv"
        
        folder = "plant" if "plant" in meta.get("category", "").lower() else "other"
        out_path = _publish_user_dataset(
            output_df,
            Path("reflectors") / folder,
            filename,
            "reflector",
            meta.get("name", "Unknown"),
        )
            
        return True, (
            f"{data_type} data saved successfully to {out_path}. "
            f"Diagnostics: {format_import_diagnostics(prepared)}."
        )
        
    except (ValueError, FileExistsError) as e:
        # These are validation errors we want to show to the user
        return False, str(e)
    except Exception as e:
        # Unexpected errors - log them for debugging
        import logging
        logging.exception(f"Unexpected error in reflectance import: {str(e)}")
        return False, f"Unexpected error during import: {str(e)}. Please check the file format and try again."

# ============================================================================
# All import functions are defined above and can be imported individually
# The UI components have been moved to views/forms.py
# ============================================================================
