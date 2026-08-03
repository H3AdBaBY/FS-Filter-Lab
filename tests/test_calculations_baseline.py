import numpy as np

from models.constants import INTERP_GRID
from models.core import ChannelMixerSettings, Filter, FilterCollection
from services.calculations import (
    compute_active_transmission,
    compute_combined_transmission,
    compute_effective_stops,
    compute_filter_transmission,
    compute_reflector_preview_colors,
    compute_rgb_response,
    compute_selected_filter_indices,
    compute_single_reflector_color,
    compute_white_balance,
    compute_white_balance_gains,
)
from services.channel_mixer import (
    apply_channel_mixing_to_colors,
    apply_channel_mixing_to_responses,
)


def test_no_filter_is_identity_on_the_canonical_grid() -> None:
    transmission, label, combined = compute_filter_transmission([], np.empty((0, 801)))

    np.testing.assert_array_equal(transmission, np.ones_like(INTERP_GRID))
    assert label == "No Filter"
    assert combined is None


def test_single_stacked_and_repeated_filter_transmission() -> None:
    first = np.array([0.5, 0.25, np.nan])
    second = np.array([0.2, 0.8, 0.5])
    matrix = np.vstack([first, second])

    single, label, combined = compute_filter_transmission([0], matrix)
    np.testing.assert_array_equal(single, first)
    assert label == "Single"
    assert combined is None

    stacked, label, combined = compute_filter_transmission([0, 1], matrix)
    np.testing.assert_allclose(stacked[:2], [0.1, 0.2])
    assert np.isnan(stacked[2])
    assert label == "Combined"
    np.testing.assert_array_equal(stacked, combined)

    repeated, _, _ = compute_filter_transmission([0, 0], matrix)
    np.testing.assert_allclose(repeated[:2], [0.25, 0.0625])
    assert np.isnan(repeated[2])


def test_filter_multiplier_expands_to_repeated_indices() -> None:
    transmission = np.array([0.5, 0.25])
    filter_object = Filter(
        name="Synthetic",
        number="SYN",
        manufacturer="Fixture Lab",
        hex_color="#123456",
        transmission=transmission,
    )
    collection = FilterCollection(
        filters=[filter_object],
        df=None,
        filter_matrix=transmission.reshape(1, -1),
        extrapolated_masks=np.zeros((1, 2), dtype=bool),
    )
    display_name = str(filter_object)

    indices = compute_selected_filter_indices(
        [display_name], {display_name: 3}, collection
    )

    assert indices == [0, 0, 0]
    repeated, _, _ = compute_filter_transmission(indices, collection.filter_matrix)
    np.testing.assert_allclose(repeated, transmission**3)


def test_combination_and_active_paths_preserve_nan_without_clipping() -> None:
    first = np.array([0.0, 0.5, np.nan])
    second = np.array([0.5, 0.5, 0.5])

    combined = compute_combined_transmission([first, second])
    active = compute_active_transmission(["first", "second"], [0, 1], np.vstack([first, second]))

    np.testing.assert_array_equal(combined, active)
    assert combined[0] == 0.0
    assert combined[1] == 0.25
    assert np.isnan(combined[2])
    reverse = compute_combined_transmission([second, first])
    np.testing.assert_allclose(reverse, combined, equal_nan=True)


def test_effective_stops_use_illuminant_times_qe_weights() -> None:
    transmission = np.array([0.5, 0.25, np.nan])
    qe = np.array([100.0, 100.0, 100.0])
    illuminant = np.array([1.0, 3.0, 1.0])

    result = compute_effective_stops(transmission, qe, illuminant)

    assert result.available
    assert result.effective_transmission == 0.3125
    assert result.effective_stops == -np.log2(0.3125)
    assert result.coverage == 0.8


def test_effective_stops_preserve_zero_and_reject_zero_weights() -> None:
    result = compute_effective_stops(np.zeros(3), np.ones(3))
    assert result.available
    assert result.effective_transmission == 0.0
    assert np.isposinf(result.effective_stops)
    assert result.coverage == 1.0

    result = compute_effective_stops(np.ones(3), np.zeros(3))
    assert not result.available
    assert "positive common weight" in result.reason

    negative = compute_effective_stops(
        np.ones(3), np.array([1.0, -1.0, 1.0]), np.ones(3)
    )
    assert not negative.available
    assert "non-negative" in negative.reason

    no_overlap = compute_effective_stops(
        np.full(3, np.nan), np.ones(3), np.ones(3)
    )
    assert not no_overlap.available
    assert "zero coverage" in no_overlap.reason


def test_rgb_response_is_linear_unfloored_and_visibility_independent() -> None:
    transmission = np.array([1.0, 0.5, np.nan])
    qe = {
        "R": np.array([100.0, 100.0, 100.0]),
        "G": np.array([50.0, 50.0, 50.0]),
        "B": np.array([25.0, 25.0, 25.0]),
    }
    responses, rgb_matrix, maximum = compute_rgb_response(
        transmission,
        qe,
        {"R": 2.0, "G": 1.0, "B": 1.0},
        {"R": True, "G": False, "B": True},
    )

    np.testing.assert_allclose(responses["R"], [50.0, 25.0, np.nan], equal_nan=True)
    np.testing.assert_allclose(responses["G"], [50.0, 25.0, np.nan], equal_nan=True)
    np.testing.assert_allclose(responses["B"], [25.0, 12.5, np.nan], equal_nan=True)
    np.testing.assert_allclose(
        rgb_matrix,
        [
            [50.0, 50.0, 25.0],
            [25.0, 25.0, 12.5],
            [np.nan, np.nan, np.nan],
        ],
        equal_nan=True,
    )
    assert maximum == 50.0


def test_white_balance_returns_channel_response_ratios_to_green() -> None:
    gains = compute_white_balance_gains(
        np.ones(3),
        {
            "R": np.full(3, 100.0),
            "G": np.full(3, 50.0),
            "B": np.full(3, 25.0),
        },
        np.ones(3),
    )

    assert gains == {"R": 2.0, "G": 1.0, "B": 0.5}

    result = compute_white_balance(
        np.ones(3),
        {
            "R": np.full(3, 100.0),
            "G": np.full(3, 50.0),
            "B": np.full(3, 25.0),
        },
        np.ones(3),
    )
    assert result.available
    assert result.balance_divisors == {"R": 2.0, "G": 1.0, "B": 0.5}
    assert result.balance_multipliers == {"R": 0.5, "G": 1.0, "B": 2.0}


def test_white_balance_requires_common_rgb_support_and_nonzero_green() -> None:
    missing = compute_white_balance(
        np.ones(2), {"R": np.ones(2), "G": np.ones(2)}, np.ones(2)
    )
    assert not missing.available
    assert "R, G, and B" in missing.reason

    zero_green = compute_white_balance(
        np.ones(2),
        {"R": np.ones(2), "G": np.zeros(2), "B": np.ones(2)},
        np.ones(2),
    )
    assert not zero_green.available
    assert zero_green.reason == "green response is zero"
    with np.testing.assert_raises_regex(ValueError, "green response is zero"):
        compute_white_balance_gains(
            np.ones(2),
            {"R": np.ones(2), "G": np.zeros(2), "B": np.ones(2)},
            np.ones(2),
        )


def test_white_balance_uses_one_common_partial_domain() -> None:
    result = compute_white_balance(
        np.array([1.0, 1.0, 1.0]),
        {
            "R": np.array([100.0, np.nan, 100.0]),
            "G": np.array([50.0, 50.0, 50.0]),
            "B": np.array([25.0, 25.0, np.nan]),
        },
        np.ones(3),
    )

    assert result.available
    assert result.channel_responses == {"R": 1.0, "G": 0.5, "B": 0.25}
    assert result.balance_divisors == {"R": 2.0, "G": 1.0, "B": 0.5}


def test_channel_mixer_identity_and_red_blue_swap() -> None:
    responses = {
        "R": np.array([1.0, 2.0]),
        "G": np.array([3.0, 4.0]),
        "B": np.array([5.0, 6.0]),
    }
    identity = ChannelMixerSettings(enabled=True)
    mixed_identity = apply_channel_mixing_to_responses(responses, identity)
    for channel in ("R", "G", "B"):
        np.testing.assert_array_equal(mixed_identity[channel], responses[channel])

    swap = ChannelMixerSettings(
        red_r=0.0,
        red_b=1.0,
        green_g=1.0,
        blue_r=1.0,
        blue_b=0.0,
        enabled=True,
    )
    mixed = apply_channel_mixing_to_responses(responses, swap)
    np.testing.assert_array_equal(mixed["R"], responses["B"])
    np.testing.assert_array_equal(mixed["G"], responses["G"])
    np.testing.assert_array_equal(mixed["B"], responses["R"])
    np.testing.assert_array_equal(
        apply_channel_mixing_to_colors(np.array([1.0, 2.0, 3.0]), swap),
        [3.0, 2.0, 1.0],
    )

    invalid = ChannelMixerSettings(red_r=np.nan, enabled=True)
    with np.testing.assert_raises_regex(ValueError, "must be finite"):
        apply_channel_mixing_to_responses(responses, invalid)

    extended = ChannelMixerSettings(red_r=-1.0, red_g=2.0, enabled=True)
    extended_values = apply_channel_mixing_to_colors(
        np.array([1.0, 2.0, 3.0]), extended
    )
    np.testing.assert_array_equal(extended_values, [3.0, 2.0, 3.0])


def test_reflector_previews_preserve_leaf_order_and_apply_channel_mixing(
    leaf_collection, three_sample_qe
) -> None:
    transmission = np.ones(3)
    illuminant = np.ones(3)
    pixels = compute_reflector_preview_colors(
        leaf_collection.reflector_matrix,
        transmission,
        three_sample_qe,
        illuminant,
        leaf_collection,
    )
    np.testing.assert_allclose(
        pixels,
        [
            [[0.1, 0.2, 0.3], [0.2, 0.3, 0.4]],
            [[0.3, 0.4, 0.5], [0.4, 0.5, 0.6]],
        ],
    )

    swap = ChannelMixerSettings(
        red_r=0.0,
        red_b=1.0,
        green_g=1.0,
        blue_r=1.0,
        blue_b=0.0,
        enabled=True,
    )
    single = compute_single_reflector_color(
        leaf_collection.reflector_matrix,
        0,
        transmission,
        three_sample_qe,
        illuminant,
        swap,
    )
    np.testing.assert_allclose(single, [[[0.3, 0.2, 0.1]]])
