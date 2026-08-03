"""Approved Gate 2 policies for preparing one-dimensional spectral data."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

import numpy as np

from models.constants import INTERP_GRID


Quantity = Literal["transmission", "reflectance", "qe", "illuminant"]
Unit = Literal["fraction", "percent", "relative"]


@dataclass(frozen=True)
class SpectralDiagnostic:
    code: str
    severity: Literal["warning", "error"]
    message: str
    source: Optional[str] = None


@dataclass(frozen=True)
class PreparedSpectrum:
    raw_values: np.ndarray
    physical_values: np.ndarray
    unit: Unit
    diagnostics: tuple[SpectralDiagnostic, ...]
    measured_mask: np.ndarray
    extrapolated_mask: np.ndarray


def infer_legacy_unit(values: np.ndarray, quantity: Quantity) -> Unit:
    """Infer a legacy file's unit and return the approved internal convention."""
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        raise ValueError("spectrum has no finite values")
    if quantity == "illuminant":
        return "relative"
    if quantity == "qe":
        return "fraction" if np.max(finite) <= 1.0 else "percent"
    return "fraction" if np.max(finite) <= 1.0 else "percent"


def _normalize_values(values: np.ndarray, quantity: Quantity, unit: Unit) -> np.ndarray:
    normalized = np.array(values, dtype=float, copy=True)
    if quantity in ("transmission", "reflectance") and unit == "percent":
        normalized /= 100.0
    elif quantity == "qe" and unit == "fraction":
        normalized *= 100.0
    return normalized


def _physical_bounds(quantity: Quantity) -> tuple[float, Optional[float]]:
    if quantity in ("transmission", "reflectance"):
        return 0.0, 1.0
    if quantity == "qe":
        return 0.0, 100.0
    return 0.0, None


def prepare_spectrum(
    wavelengths: np.ndarray,
    values: np.ndarray,
    quantity: Quantity,
    *,
    unit: Optional[Unit] = None,
    source: Optional[str] = None,
    extrapolation: Literal["none", "constant"] = "none",
    target_grid: Optional[np.ndarray] = None,
) -> PreparedSpectrum:
    """Validate, normalize, interpolate, and derive physical calculation values."""
    wavelengths = np.array(wavelengths, dtype=float, copy=True)
    values = np.array(values, dtype=float, copy=True)
    grid = np.array(INTERP_GRID if target_grid is None else target_grid, dtype=float, copy=True)
    if wavelengths.ndim != 1 or values.ndim != 1 or len(wavelengths) != len(values):
        raise ValueError("wavelength and value arrays must be one-dimensional and equal length")
    if len(wavelengths) < 2:
        raise ValueError("spectrum requires at least two samples")
    if not np.all(np.isfinite(wavelengths)):
        raise ValueError("wavelength samples must be finite")
    if grid.ndim != 1 or not np.all(np.isfinite(grid)) or np.any(np.diff(grid) <= 0):
        raise ValueError("target wavelength grid must be finite and strictly ascending")

    diagnostics: list[SpectralDiagnostic] = []
    order = np.argsort(wavelengths, kind="stable")
    if not np.array_equal(order, np.arange(len(wavelengths))):
        diagnostics.append(
            SpectralDiagnostic(
                code="wavelengths_sorted",
                severity="warning",
                message="wavelength samples were stable-sorted into ascending order",
                source=source,
            )
        )
        wavelengths = wavelengths[order]
        values = values[order]

    if np.any(np.diff(wavelengths) == 0):
        raise ValueError("duplicate wavelength samples are not allowed")

    allowed_units: dict[Quantity, tuple[Unit, ...]] = {
        "transmission": ("fraction", "percent"),
        "reflectance": ("fraction", "percent"),
        "qe": ("fraction", "percent"),
        "illuminant": ("relative",),
    }
    if unit is not None and unit not in allowed_units[quantity]:
        raise ValueError(f"{quantity} does not support {unit} units")
    if extrapolation not in ("none", "constant"):
        raise ValueError(f"unsupported extrapolation policy: {extrapolation}")

    selected_unit = unit or infer_legacy_unit(values, quantity)
    diagnostics.append(
        SpectralDiagnostic(
            code="unit_interpretation",
            severity="warning",
            message=f"{quantity} interpreted as {selected_unit}",
            source=source,
        )
    )
    normalized = _normalize_values(values, quantity, selected_unit)
    lower, upper = _physical_bounds(quantity)
    finite = np.isfinite(normalized)
    out_of_bounds = finite & (normalized < lower)
    if upper is not None:
        out_of_bounds |= finite & (normalized > upper)
    if np.any(out_of_bounds):
        affected_wavelengths = wavelengths[out_of_bounds]
        diagnostics.append(
            SpectralDiagnostic(
                code="physical_bounds_clipped",
                severity="warning",
                message=(
                    f"clipped {len(affected_wavelengths)} sample(s) outside physical bounds; "
                    f"source range {np.min(normalized[finite]):.6g} to "
                    f"{np.max(normalized[finite]):.6g}; wavelengths "
                    f"{affected_wavelengths[0]:.6g} to {affected_wavelengths[-1]:.6g} nm"
                ),
                source=source,
            )
        )
    if np.any(~finite):
        diagnostics.append(
            SpectralDiagnostic(
                code="nonfinite_values_preserved",
                severity="warning",
                message=f"preserved {np.count_nonzero(~finite)} non-finite sample(s) as unknown",
                source=source,
            )
        )

    measured_mask = (grid >= wavelengths[0]) & (grid <= wavelengths[-1])
    extrapolated_mask = ~measured_mask if extrapolation == "constant" else np.zeros_like(grid, dtype=bool)
    left = normalized[0] if extrapolation == "constant" else np.nan
    right = normalized[-1] if extrapolation == "constant" else np.nan
    raw_interpolated = np.interp(
        grid, wavelengths, normalized, left=left, right=right
    )
    if upper is None:
        physical_interpolated = np.maximum(raw_interpolated, lower)
    else:
        physical_interpolated = np.clip(raw_interpolated, lower, upper)
    return PreparedSpectrum(
        raw_values=raw_interpolated,
        physical_values=physical_interpolated,
        unit=selected_unit,
        diagnostics=tuple(diagnostics),
        measured_mask=measured_mask,
        extrapolated_mask=extrapolated_mask,
    )
