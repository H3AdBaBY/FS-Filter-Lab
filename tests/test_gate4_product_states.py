from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

from models.constants import INTERP_GRID
from models.core import ChannelMixerSettings, Filter, FilterCollection
from services.app_operations import rebuild_application_cache
from services.workflow import build_workflow_snapshot
from views.ui_utils import apply_responsive_layout, is_dark_color


def _collection() -> FilterCollection:
    transmission = np.full(len(INTERP_GRID), 0.5)
    filter_object = Filter(
        name="Product state",
        number="G4-S",
        manufacturer="Fixture",
        hex_color="#777777",
        transmission=transmission,
        extrapolated_mask=np.zeros(len(INTERP_GRID), dtype=bool),
    )
    return FilterCollection(
        filters=[filter_object],
        df=pd.DataFrame(
            [
                {
                    "Filter Number": "G4-S",
                    "Filter Name": "Product state",
                    "Manufacturer": "Fixture",
                    "Hex Color": "#777777",
                }
            ]
        ),
        filter_matrix=transmission.reshape(1, -1),
        extrapolated_masks=np.zeros((1, len(INTERP_GRID)), dtype=bool),
    )


def _state(*, qe=True, illuminant=True) -> SimpleNamespace:
    identity = "Product state (G4-S, Fixture)"
    return SimpleNamespace(
        selected_filters=[identity],
        filter_multipliers={identity: 1},
        current_qe=(
            {channel: np.full(len(INTERP_GRID), 50.0) for channel in "RGB"}
            if qe
            else None
        ),
        selected_camera="Fixture QE" if qe else None,
        illuminant=(
            np.ones(len(INTERP_GRID), dtype=float) if illuminant else None
        ),
        illuminant_name="Fixture light" if illuminant else None,
        apply_white_balance=False,
        channel_mixer=ChannelMixerSettings(),
        rgb_channels_visibility={channel: True for channel in "RGB"},
        target_profile=None,
    )


def test_missing_qe_is_named_without_fabricated_sensor_response() -> None:
    snapshot = build_workflow_snapshot(_state(qe=False), _collection())

    assert not snapshot.qe_available
    assert snapshot.illuminant_available
    assert snapshot.channel_responses == {}
    assert not snapshot.effective_result.available
    assert not snapshot.balance_result.available


def test_missing_illuminant_is_named_without_uniform_fallback() -> None:
    snapshot = build_workflow_snapshot(_state(illuminant=False), _collection())

    assert snapshot.qe_available
    assert not snapshot.illuminant_available
    np.testing.assert_array_equal(snapshot.illuminant_curve, 0.0)
    assert not snapshot.effective_result.available
    assert not snapshot.balance_result.available


def test_responsive_fallback_stacks_columns_and_bounds_charts(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(
        "views.ui_utils.st.markdown",
        lambda body, **kwargs: calls.append((body, kwargs)),
    )

    apply_responsive_layout()

    assert len(calls) == 1
    css, options = calls[0]
    assert "@media (max-width: 768px)" in css
    assert 'data-testid="stHorizontalBlock"' in css
    assert 'data-testid="column"' in css
    assert 'data-testid="stPlotlyChart"' in css
    assert 'content: "Open filter controls"' in css
    assert 'content: "Close filter controls"' in css
    assert "width: 100% !important" in css
    assert options == {"unsafe_allow_html": True}


def test_text_color_choice_uses_wcag_relative_luminance() -> None:
    assert is_dark_color("#000000")
    assert not is_dark_color("#ffffff")
    assert is_dark_color("#666666")
    assert not is_dark_color("#00ff00")


def test_rebuild_cache_accepts_an_absent_cache_directory(tmp_path: Path) -> None:
    assert rebuild_application_cache(tmp_path / "not-created")
