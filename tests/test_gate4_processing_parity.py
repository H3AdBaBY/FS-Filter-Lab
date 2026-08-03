from types import SimpleNamespace

import numpy as np
import pandas as pd

from models.constants import INTERP_GRID
from models.core import ChannelMixerSettings, Filter, FilterCollection
from services.calculations import (
    compute_reflector_color,
    compute_reflector_preview_colors,
    compute_white_balance,
)
from services.visualization import create_sensor_response_plot
from services.workflow import build_workflow_snapshot


def _swap_mixer() -> ChannelMixerSettings:
    return ChannelMixerSettings(
        red_r=0.0,
        red_b=1.0,
        green_g=1.0,
        blue_r=1.0,
        blue_b=0.0,
        enabled=True,
    )


def test_reflector_processing_order_is_optional_balance_then_mixer() -> None:
    transmission = np.ones(3)
    illuminant = np.ones(3)
    reflector = np.array([0.1, 0.4, 0.9])
    qe = {
        "R": np.array([50.0, 0.0, 0.0]),
        "G": np.array([0.0, 100.0, 0.0]),
        "B": np.array([0.0, 0.0, 25.0]),
    }
    balance = compute_white_balance(transmission, qe, illuminant)
    assert balance.available

    unbalanced_mixed = compute_reflector_color(
        reflector,
        transmission,
        qe,
        illuminant,
        _swap_mixer(),
        balance.balance_divisors,
        False,
    )
    balanced_mixed = compute_reflector_color(
        reflector,
        transmission,
        qe,
        illuminant,
        _swap_mixer(),
        balance.balance_divisors,
        True,
    )

    np.testing.assert_allclose(unbalanced_mixed, [0.225, 0.4, 0.05])
    np.testing.assert_allclose(balanced_mixed, [0.9, 0.4, 0.1])


def test_vegetation_preview_keeps_order_with_shared_processing(
    leaf_collection,
) -> None:
    transmission = np.ones(3)
    illuminant = np.ones(3)
    qe = {
        "R": np.array([50.0, 0.0, 0.0]),
        "G": np.array([0.0, 100.0, 0.0]),
        "B": np.array([0.0, 0.0, 25.0]),
    }
    balance = compute_white_balance(transmission, qe, illuminant)
    pixels = compute_reflector_preview_colors(
        leaf_collection.reflector_matrix,
        transmission,
        qe,
        illuminant,
        leaf_collection,
        _swap_mixer(),
        balance.balance_divisors,
        True,
    )

    np.testing.assert_allclose(
        pixels,
        [
            [[0.3, 0.2, 0.1], [0.4, 0.3, 0.2]],
            [[0.5, 0.4, 0.3], [0.6, 0.5, 0.4]],
        ],
    )


def test_visibility_is_presentation_only_for_workflow_and_plot() -> None:
    transmission = np.linspace(0.2, 0.8, len(INTERP_GRID))
    filter_object = Filter(
        name="Visibility",
        number="G4-V",
        manufacturer="Fixture",
        hex_color="#808080",
        transmission=transmission,
        extrapolated_mask=np.zeros(len(INTERP_GRID), dtype=bool),
    )
    collection = FilterCollection(
        filters=[filter_object],
        df=pd.DataFrame(
            [
                {
                    "Filter Number": "G4-V",
                    "Filter Name": "Visibility",
                    "Manufacturer": "Fixture",
                    "Hex Color": "#808080",
                }
            ]
        ),
        filter_matrix=transmission.reshape(1, -1),
        extrapolated_masks=np.zeros((1, len(INTERP_GRID)), dtype=bool),
    )
    qe = {
        "R": np.full(len(INTERP_GRID), 50.0),
        "G": np.full(len(INTERP_GRID), 75.0),
        "B": np.full(len(INTERP_GRID), 25.0),
    }
    state = SimpleNamespace(
        selected_filters=[str(filter_object)],
        filter_multipliers={str(filter_object): 1},
        current_qe=qe,
        selected_camera="Fixture Camera",
        illuminant=np.ones(len(INTERP_GRID)),
        illuminant_name="Uniform",
        apply_white_balance=True,
        channel_mixer=ChannelMixerSettings(enabled=True),
        rgb_channels_visibility={"R": True, "G": False, "B": False},
        target_profile=None,
    )
    snapshot = build_workflow_snapshot(state, collection)

    assert set(snapshot.channel_responses) == {"R", "G", "B"}
    assert set(snapshot.plotted_channel_responses) == {"R"}
    np.testing.assert_allclose(
        snapshot.channel_responses["R"],
        transmission * qe["R"] / snapshot.balance_result.balance_divisors["R"],
    )

    figure = create_sensor_response_plot(
        INTERP_GRID,
        snapshot.active_transmission,
        qe,
        snapshot.visible_channels,
        snapshot.balance_result.balance_divisors,
        True,
        channel_mixer=snapshot.channel_mixer,
        channel_responses=snapshot.plotted_channel_responses,
    )
    assert [trace.name for trace in figure.data] == ["R Channel"]
    assert "Mixer Enabled: Identity" in figure.layout.title.text


def test_custom_mixer_is_labeled_without_clipping() -> None:
    responses = {
        "R": np.array([-1.0, 2.0]),
        "G": np.array([0.5, 0.5]),
        "B": np.array([3.0, -2.0]),
    }
    figure = create_sensor_response_plot(
        np.array([400.0, 500.0]),
        np.ones(2),
        {channel: np.ones(2) for channel in "RGB"},
        {channel: True for channel in "RGB"},
        {channel: 1.0 for channel in "RGB"},
        False,
        channel_mixer=_swap_mixer(),
        channel_responses=responses,
    )
    assert "Channel Mixed" in figure.layout.title.text
    np.testing.assert_array_equal(figure.data[0].y, responses["R"])
