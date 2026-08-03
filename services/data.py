"""
Data loading services for FS FilterLab.
"""
# Standard library imports
import pickle
import sys
import warnings
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional, TypeVar, Callable, Sequence

# Third-party imports
import numpy as np
import pandas as pd

# Local imports
from models import (
    Filter, FilterCollection, TargetProfile,
    ReflectorSpectrum, ReflectorCollection
)
from models.constants import CACHE_DIR, DEFAULT_HEX_COLOR, INTERP_GRID
from services.spectral_policy import PreparedSpectrum, prepare_spectrum
from services.data_locations import discover_tsv_files, get_collection_roots


def interpolate_to_standard_grid(wavelengths: np.ndarray, values: np.ndarray) -> np.ndarray:
    """
    Interpolate spectral data to the standard wavelength grid.
    
    Args:
        wavelengths: Input wavelength array
        values: Corresponding spectral values (transmission, power, reflectance, etc.)
        
    Returns:
        Interpolated values on the standard INTERP_GRID
    """
    return prepare_spectrum(wavelengths, values, "illuminant", unit="relative").raw_values


def interpolate_extrapolation_mask(
    wavelengths: np.ndarray,
    values: pd.Series,
) -> np.ndarray:
    """Load an explicit boolean mask onto the canonical grid."""
    normalized = values.map(
        lambda value: str(value).strip().lower() in {"true", "1", "yes"}
        if pd.notna(value)
        else False
    ).to_numpy(dtype=bool)
    order = np.argsort(wavelengths, kind="stable")
    return np.interp(
        INTERP_GRID,
        wavelengths[order],
        normalized[order].astype(float),
        left=0.0,
        right=0.0,
    ) > 0.5

# Ensure cache directory exists
Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)

# Generic type for cached data
T = TypeVar('T')
CACHE_SCHEMA_VERSION = 3
NORMALIZATION_POLICY_VERSION = "g4-user-data-2026-08-03"


def _coerce_data_dirs(data_folder: str | Path | Sequence[str | Path]) -> list[Path]:
    if isinstance(data_folder, (str, Path)):
        return [Path(data_folder)]
    return [Path(folder) for folder in data_folder]


def _cache_metadata(data_folders: Sequence[Path]) -> dict:
    source_state = []
    for root_index, data_dir in enumerate(data_folders):
        if not data_dir.exists():
            continue
        source_state.extend(
            {
                "path": f"{root_index}:{path.relative_to(data_dir).as_posix()}",
                "size": path.stat().st_size,
                "mtime_ns": path.stat().st_mtime_ns,
            }
            for path in sorted(
                data_dir.glob("**/*.tsv"), key=lambda item: item.as_posix()
            )
            if path.is_file()
        )
    return {
        "schema_version": CACHE_SCHEMA_VERSION,
        "normalization_policy_version": NORMALIZATION_POLICY_VERSION,
        "format_versions": {
            "python": f"{sys.version_info.major}.{sys.version_info.minor}",
            "numpy": np.__version__,
            "pandas": pd.__version__,
        },
        "source_roots": [folder.resolve().as_posix() for folder in data_folders],
        "source_state": source_state,
    }

def parse_tsv_file(file_path: str | Path) -> pd.DataFrame:
    """
    Parse a TSV file with standardized error handling.
    
    Args:
        file_path: Path to the TSV file
        
    Returns:
        DataFrame with parsed data, columns stripped of whitespace
    """
    path = Path(file_path) if isinstance(file_path, str) else file_path
    df = pd.read_csv(path, sep="\t")
    df.columns = [str(c).strip() for c in df.columns]
    return df


def cached_loader(cache_key: str, data_folder: str | Path | Sequence[str | Path],
                  load_function: Callable[[], T]) -> T:
    """
    Simple caching mechanism for data loading.
    
    Args:
        cache_key: Base name for the cache file (without extension)
        data_folder: Path to the folder containing source data files
        load_function: Function to call when cache is invalid or missing
        
    Returns:
        Data from cache or freshly loaded
    """
    data_dirs = _coerce_data_dirs(data_folder)
    cache_file = Path(CACHE_DIR) / f"{cache_key}.pkl"
    metadata = _cache_metadata(data_dirs)

    if cache_file.exists():
        try:
            with open(cache_file, 'rb') as f:
                envelope = pickle.load(f)
            if isinstance(envelope, dict) and envelope.get("metadata") == metadata:
                return envelope["payload"]
        except Exception as error:
            warnings.warn(
                f"cache_read_failed:{cache_file.as_posix()}:{type(error).__name__}: {error}",
                RuntimeWarning,
                stacklevel=2,
            )
    
    # Cache miss or invalid - load fresh data
    data = load_function()
    
    # Save to cache
    try:
        Path(CACHE_DIR).mkdir(exist_ok=True, parents=True)
        with open(cache_file, 'wb') as f:
            pickle.dump({"metadata": metadata, "payload": data}, f)
    except Exception as error:
        warnings.warn(
            f"cache_write_failed:{cache_file.as_posix()}:{type(error).__name__}: {error}",
            RuntimeWarning,
            stacklevel=2,
        )
        
    return data


def invalidate_collection_cache(cache_key: str) -> None:
    """Invalidate one generated collection cache after a successful import."""
    cache_file = Path(CACHE_DIR) / f"{cache_key}.pkl"
    if cache_file.exists():
        cache_file.unlink()


# Helper functions for empty collection creation
def create_empty_filter_collection() -> FilterCollection:
    """Create an empty filter collection."""
    return FilterCollection(
        filters=[],
        df=pd.DataFrame(),
        filter_matrix=np.empty((0, len(INTERP_GRID))),
        extrapolated_masks=np.empty((0, len(INTERP_GRID)), dtype=bool)
    )

def create_empty_reflector_collection() -> ReflectorCollection:
    """Create an empty reflector collection."""
    return ReflectorCollection(
        reflectors=[],
        reflector_matrix=np.empty((0, len(INTERP_GRID)))
    )

def safely_load_file(path: Path, processor_func: Callable) -> Optional[Any]:
    """
    Load and process a file with standardized error handling.
    
    Args:
        path: Path to the file to load
        processor_func: Function to process the file contents
        
    Returns:
        Processed file contents or None if loading failed
    """
    try:
        return processor_func(path)
    except Exception:
        return None


def _process_filter_file(path: Path) -> Optional[Tuple[dict, np.ndarray, np.ndarray, Filter]]:
    """
    Process a single filter file and return its data components.
    
    Args:
        path: Path to the filter file
        
    Returns:
        Tuple of (metadata, transmission, mask, filter) or None if invalid
    """
    df = parse_tsv_file(path)
    
    # Check if file has required columns
    if "Wavelength" not in df.columns or "Transmittance" not in df.columns:
        return None
    
    filename = path.name
    is_lee = 'LeeFilters' in filename
    
    # Extract metadata from first row
    first_row = df.iloc[0]
    
    fn = str(first_row.get('Filter Number', path.stem))
    name_raw = first_row.get('Name')
    name = str(name_raw).strip() if pd.notnull(name_raw) and str(name_raw).strip() else path.stem
    manufacturer = first_row.get('Manufacturer', 'Unknown')
    hex_color_raw = first_row.get('hex_color', DEFAULT_HEX_COLOR)
    hex_color = str(hex_color_raw).strip() if pd.notnull(hex_color_raw) and str(hex_color_raw).strip().startswith("#") else DEFAULT_HEX_COLOR
    
    # Extract wavelength and transmittance values
    wavelengths = df["Wavelength"].to_numpy(dtype=float, copy=True)
    transmittance = df["Transmittance"].to_numpy(dtype=float, copy=True)
    prepared = prepare_spectrum(
        wavelengths,
        transmittance,
        "transmission",
        source=path.as_posix(),
        extrapolation="constant" if is_lee else "none",
    )
    interp_vals = prepared.physical_values
    if "Extrapolated" in df.columns:
        extrap_mask = interpolate_extrapolation_mask(
            wavelengths, df["Extrapolated"]
        )
    else:
        extrap_mask = prepared.extrapolated_mask
    
    metadata = {
        'Filter Number': fn,
        'Filter Name': name,
        'Manufacturer': manufacturer,
        'Hex Color': hex_color,
        'is_lee': is_lee,
        'Unit Interpretation': prepared.unit,
        'Diagnostics': prepared.diagnostics,
    }
    
    filter_obj = Filter(
        name=name,
        number=fn,
        manufacturer=manufacturer,
        hex_color=hex_color,
        transmission=interp_vals,
        extrapolated_mask=extrap_mask,
        raw_transmission=prepared.raw_values,
        unit_interpretation=prepared.unit,
        diagnostics=list(prepared.diagnostics),
    )
    
    return metadata, interp_vals, extrap_mask, filter_obj

def _load_filter_collection_from_files() -> FilterCollection:
    """
    Load filter data from files without using cache.
    
    Returns:
        FilterCollection object
    """
    files = discover_tsv_files("filters_data", recursive=True)
    meta_list, matrix, masks = [], [], []
    filters = []
    identities = set()
    
    for path in files:
        result = safely_load_file(path, _process_filter_file)
        if result:
            metadata, transmission, mask, filter_obj = result
            identity = str(filter_obj)
            if identity in identities:
                continue
            identities.add(identity)
            meta_list.append(metadata)
            matrix.append(transmission)
            masks.append(mask)
            filters.append(filter_obj)

    # Return empty collection if no valid data found
    if not matrix:
        return create_empty_filter_collection()
    
    try:
        df_result = pd.DataFrame(meta_list)
        matrix_result = np.vstack(matrix)
        masks_result = np.vstack(masks)
        
        return FilterCollection(
            filters=filters,
            df=df_result,
            filter_matrix=matrix_result,
            extrapolated_masks=masks_result
        )
    except Exception:
        return create_empty_filter_collection()


def load_filter_collection() -> FilterCollection:
    """Load filter data and return a FilterCollection object."""
    def _create_cached_data() -> Tuple[pd.DataFrame, np.ndarray, np.ndarray, List[Filter]]:
        """Load fresh filter data for caching"""
        collection = _load_filter_collection_from_files()
        return (collection.df, collection.filter_matrix, collection.extrapolated_masks, collection.filters)
    
    # Load data using cache wrapper
    try:
        cached_data = cached_loader(
            cache_key="filter_data",
            data_folder=get_collection_roots("filters_data"),
            load_function=_create_cached_data
        )
        
        # Unpack cached data
        df, matrix, masks, filters = cached_data
        
        return FilterCollection(
            filters=filters,
            df=df,
            filter_matrix=matrix,
            extrapolated_masks=masks
        )
    except Exception:
        return _load_filter_collection_from_files()


def _process_qe_file(path: Path) -> Optional[Tuple[str, Dict[str, np.ndarray], bool, dict]]:
    """
    Process a quantum efficiency file.
    
    Args:
        path: Path to the QE file
        
    Returns:
        Tuple of (sensor_key, channel_data, is_default) or None if invalid
    """
    df = parse_tsv_file(path)
    
    # Check if file has required columns
    if 'Wavelength' not in df.columns or not any(col in df.columns for col in ['R', 'G', 'B']):
        return None
    
    # Extract sensor info
    brand = df['Manufacturer'].iloc[0].strip() if 'Manufacturer' in df.columns else "Generic"
    model = df['Name'].iloc[0].strip() if 'Name' in df.columns else path.stem
    key = f"{brand} {model}"
    
    # Process channels
    channel_data = {}
    diagnostics = []
    wavelength = df['Wavelength'].to_numpy(dtype=float, copy=True)

    combined_values = np.concatenate([
        df[channel].to_numpy(dtype=float, copy=True)
        for channel in ['R', 'G', 'B'] if channel in df.columns
    ])
    qe_unit = "fraction" if np.nanmax(combined_values) <= 1.0 else "percent"
    
    for channel in ['R', 'G', 'B']:
        if channel not in df.columns:
            continue
            
        valid_mask = ~pd.isna(df[channel])
        if not valid_mask.any():
            continue
            
        channel_values = df[channel].to_numpy(dtype=float, copy=True)
        prepared = prepare_spectrum(
            wavelength, channel_values, "qe", unit=qe_unit, source=path.as_posix()
        )
        channel_data[channel[0]] = prepared.physical_values
        diagnostics.extend(prepared.diagnostics)
    
    # Check if this is the default QE file
    is_default = (path.name == 'Default_QE.tsv')
    
    return key, channel_data, is_default, {
        "unit_interpretation": qe_unit,
        "diagnostics": tuple(diagnostics),
    }


def _load_quantum_efficiencies_from_files() -> Tuple[List[str], Dict[str, Dict[str, np.ndarray]], Optional[str]]:
    """
    Load quantum efficiency data from files without using cache.
    
    Returns:
        Tuple of (qe_keys, qe_data, default_key)
    """
    files = discover_tsv_files("QE_data")
    qe_dict = {}
    default_key = None

    for path in files:
        result = safely_load_file(path, _process_qe_file)
        if result:
            key, channel_data, is_default, _diagnostic_metadata = result
            if key in qe_dict:
                continue
            qe_dict[key] = channel_data
            if is_default and default_key is None:
                default_key = key

    return (sorted(qe_dict.keys()), qe_dict, default_key)


def load_quantum_efficiencies() -> Tuple[List[str], Dict[str, Dict[str, np.ndarray]], Optional[str]]:
    """Load quantum efficiency data for camera sensors."""
    return cached_loader(
        cache_key="qe_data",
        data_folder=get_collection_roots("QE_data"),
        load_function=_load_quantum_efficiencies_from_files
    )


def _process_illuminant_file(path: Path) -> Optional[Tuple[str, np.ndarray, Optional[str], PreparedSpectrum]]:
    """
    Process an illuminant file.
    
    Args:
        path: Path to the illuminant file
        
    Returns:
        Tuple of (name, interpolated_data, description) or None if invalid
    """
    df = parse_tsv_file(path)
    
    if df.shape[1] < 2:
        return None
    
    # Extract wavelength and power data from the first two columns
    wl = df.iloc[:, 0].to_numpy(dtype=float, copy=True)
    power = df.iloc[:, 1].to_numpy(dtype=float, copy=True)
    
    # Interpolate to standard grid
    prepared = prepare_spectrum(
        wl, power, "illuminant", unit="relative", source=path.as_posix()
    )
    interp = prepared.physical_values
    name = path.stem
    if 'Name' in df.columns and not df['Name'].dropna().empty:
        candidate = str(df['Name'].dropna().iloc[0]).strip()
        if candidate:
            name = candidate
    
    # Extract description if available
    description = None
    if 'Description' in df.columns and not df['Description'].dropna().empty:
        description = df['Description'].dropna().iloc[0]
    
    return name, interp, description, prepared


def _load_illuminant_collection_from_files() -> Tuple[Dict[str, np.ndarray], Dict[str, str]]:
    """
    Load illuminant data from files without using cache.
    
    Returns:
        Tuple of (illuminants, metadata)
    """
    illum, meta = {}, {}
    
    for path in discover_tsv_files("illuminants"):
        result = safely_load_file(path, _process_illuminant_file)
        if result:
            name, interp, description, _prepared = result
            if name in illum:
                continue
            illum[name] = interp
            if description:
                meta[name] = description

    return (illum, meta)


def load_illuminant_collection() -> Tuple[Dict[str, np.ndarray], Dict[str, str]]:
    """Load illuminant collection."""
    return cached_loader(
        cache_key="illuminants",
        data_folder=get_collection_roots("illuminants"),
        load_function=_load_illuminant_collection_from_files
    )


def _process_reflector_file(path: Path) -> Optional[Tuple[str, PreparedSpectrum]]:
    """
    Process a reflector file.
    
    Args:
        path: Path to the reflector file
        
    Returns:
        Tuple of (name, interpolated_data) or None if invalid
    """
    df = parse_tsv_file(path)
    
    # Check for required columns
    if "Wavelength" not in df.columns or "Reflectance" not in df.columns:
        return None
    
    # Extract name from the first row if present, else use filename
    name = None
    if "Name" in df.columns:
        name_values = df["Name"].dropna()
        if len(name_values) > 0:
            name = name_values.iloc[0]
    
    if not name:
        name = path.stem
    
    # Process wavelength and reflectance data
    wl = df["Wavelength"].to_numpy(dtype=float, copy=True)
    refl = df["Reflectance"].to_numpy(dtype=float, copy=True)
    
    # Check for sufficient valid data points
    valid_mask = ~np.isnan(refl)
    if np.sum(valid_mask) < 2:
        return None
        
    prepared = prepare_spectrum(
        wl, refl, "reflectance", source=path.as_posix()
    )
    if "Extrapolated" in df.columns:
        extrapolated_mask = interpolate_extrapolation_mask(
            wl, df["Extrapolated"]
        )
        prepared = PreparedSpectrum(
            raw_values=prepared.raw_values,
            physical_values=prepared.physical_values,
            unit=prepared.unit,
            diagnostics=prepared.diagnostics,
            measured_mask=prepared.measured_mask,
            extrapolated_mask=extrapolated_mask,
        )
    return name, prepared


def _load_reflector_collection_from_files() -> ReflectorCollection:
    """
    Load reflector data from files without using cache.
    
    Returns:
        ReflectorCollection object
    """
    files = discover_tsv_files("reflectors", recursive=True)
    reflectors = []
    matrix = []
    identities = set()

    for path in files:
        result = safely_load_file(path, _process_reflector_file)
        if result:
            name, prepared = result
            if name in identities:
                continue
            identities.add(name)
            reflectors.append(ReflectorSpectrum(
                name=name,
                values=prepared.physical_values,
                raw_values=prepared.raw_values,
                extrapolated_mask=prepared.extrapolated_mask,
                unit_interpretation=prepared.unit,
                diagnostics=list(prepared.diagnostics),
            ))
            matrix.append(prepared.physical_values)

    if not matrix:
        return create_empty_reflector_collection()
    
    reflector_matrix = np.vstack(matrix)
    return ReflectorCollection(reflectors=reflectors, reflector_matrix=reflector_matrix)


def load_reflector_collection() -> ReflectorCollection:
    """Load reflector collection."""
    return cached_loader(
        cache_key="reflectors",
        data_folder=get_collection_roots("reflectors"),
        load_function=_load_reflector_collection_from_files
    )
