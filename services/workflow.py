"""Deterministic state snapshot for one FS FilterLab calculation rerun."""

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import numpy as np

from models.constants import INTERP_GRID
from models.core import ChannelMixerSettings, FilterCollection
from services.calculations import (
    EffectiveTransmissionResult,
    WhiteBalanceResult,
    compute_effective_stops,
    compute_filter_transmission,
    compute_rgb_response,
    compute_selected_filter_indices,
    compute_white_balance,
)


@dataclass(frozen=True)
class WorkflowSnapshot:
    """All scientific and identity state consumed during one application rerun."""

    selected_filters: Tuple[str, ...]
    expanded_filters: Tuple[str, ...]
    filter_counts: Tuple[Tuple[str, int], ...]
    selected_indices: Tuple[int, ...]
    transmission_label: str
    transmission: np.ndarray
    combined_transmission: Optional[np.ndarray]
    active_transmission: np.ndarray
    effective_result: EffectiveTransmissionResult
    balance_result: WhiteBalanceResult
    channel_responses: Dict[str, np.ndarray]
    current_qe: Dict[str, np.ndarray]
    camera_name: str
    illuminant_name: str
    illuminant_curve: np.ndarray
    apply_white_balance: bool
    channel_mixer: ChannelMixerSettings
    visible_channels: Dict[str, bool]
    target_name: Optional[str]
    diagnostics: Tuple[str, ...]

    @property
    def has_filters(self) -> bool:
        return bool(self.selected_indices)

    @property
    def plotted_channel_responses(self) -> Dict[str, np.ndarray]:
        """Presentation-only visibility applied to analytical responses."""
        return {
            channel: values
            for channel, values in self.channel_responses.items()
            if self.visible_channels.get(channel, True)
        }

    @property
    def identity(self) -> Tuple[Any, ...]:
        """Stable identity used to prevent stale report downloads."""
        mixer_identity = tuple(sorted(self.channel_mixer.to_dict().items()))
        visibility_identity = tuple(
            (channel, bool(self.visible_channels.get(channel, True)))
            for channel in ("R", "G", "B")
        )
        return (
            self.filter_counts,
            self.camera_name,
            self.illuminant_name,
            self.apply_white_balance,
            mixer_identity,
            visibility_identity,
            self.target_name,
        )

    def report_metadata(self) -> Dict[str, Any]:
        """Return inspectable report state without duplicating calculations."""
        effective = self.effective_result
        balance = self.balance_result
        return {
            "filter_counts": dict(self.filter_counts),
            "selected_indices": list(self.selected_indices),
            "camera_name": self.camera_name,
            "illuminant_name": self.illuminant_name,
            "transmission_label": self.transmission_label,
            "effective_transmission": effective.effective_transmission,
            "effective_stops": effective.effective_stops,
            "coverage": effective.coverage,
            "balance_divisors": dict(balance.balance_divisors),
            "balance_multipliers": dict(balance.balance_multipliers),
            "balance_applied": self.apply_white_balance,
            "mixer_enabled": self.channel_mixer.enabled,
            "mixer_identity": bool(
                np.allclose(self.channel_mixer.to_matrix(), np.eye(3))
            ),
            "workflow_identity": self.identity,
        }


def build_workflow_snapshot(
    app_state: Any,
    filter_collection: FilterCollection,
) -> WorkflowSnapshot:
    """Resolve selection state and compute each shared scientific result once."""
    selected_filters = tuple(app_state.selected_filters)
    counts = tuple(
        (name, int(app_state.filter_multipliers.get(name, 1)))
        for name in selected_filters
    )
    expanded_filters = tuple(
        name for name, count in counts for _ in range(max(count, 0))
    )
    selected_indices = tuple(
        compute_selected_filter_indices(
            list(selected_filters), dict(counts), filter_collection
        )
    )
    transmission, label, combined = compute_filter_transmission(
        list(selected_indices), filter_collection.filter_matrix
    )
    active = combined if combined is not None else transmission

    current_qe = app_state.current_qe or {}
    illuminant = (
        np.asarray(app_state.illuminant, dtype=float)
        if app_state.illuminant is not None
        else np.ones_like(INTERP_GRID, dtype=float)
    )
    green_qe = current_qe.get("G", np.zeros_like(active, dtype=float))
    effective = compute_effective_stops(active, green_qe, illuminant)
    balance = compute_white_balance(active, current_qe, illuminant)

    apply_balance = bool(app_state.apply_white_balance)
    response_divisors = (
        balance.balance_divisors
        if apply_balance and balance.available
        else {"R": 1.0, "G": 1.0, "B": 1.0}
    )
    mixer = app_state.channel_mixer
    visibility = dict(app_state.rgb_channels_visibility)
    if current_qe:
        all_responses, _, _ = compute_rgb_response(
            active, current_qe, response_divisors, visibility, mixer
        )
        responses = all_responses
    else:
        responses = {}

    display_map = filter_collection.get_display_to_index_map()
    diagnostics = tuple(
        f"Unknown filter identity: {name}"
        for name in selected_filters
        if name not in display_map
    )
    target = app_state.target_profile

    return WorkflowSnapshot(
        selected_filters=selected_filters,
        expanded_filters=expanded_filters,
        filter_counts=counts,
        selected_indices=selected_indices,
        transmission_label=label,
        transmission=transmission,
        combined_transmission=combined,
        active_transmission=active,
        effective_result=effective,
        balance_result=balance,
        channel_responses=responses,
        current_qe=current_qe,
        camera_name=app_state.selected_camera or "UnknownCamera",
        illuminant_name=app_state.illuminant_name or "UnknownIlluminant",
        illuminant_curve=illuminant,
        apply_white_balance=apply_balance,
        channel_mixer=mixer,
        visible_channels=visibility,
        target_name=getattr(target, "name", None),
        diagnostics=diagnostics,
    )
