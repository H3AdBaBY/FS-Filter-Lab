from pathlib import Path
import sys
import types

import numpy as np
import pytest


# The production services package eagerly imports Streamlit and visualization
# modules. Gate 1 loads the numerical service modules directly so its clean test
# environment needs only their NumPy/Pandas dependencies.
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
services_package = types.ModuleType("services")
services_package.__path__ = [str(REPOSITORY_ROOT / "services")]
sys.modules["services"] = services_package

from models.core import ReflectorCollection, ReflectorSpectrum


@pytest.fixture
def fixture_dir() -> Path:
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def three_sample_qe() -> dict[str, np.ndarray]:
    return {
        "R": np.array([100.0, 0.0, 0.0]),
        "G": np.array([0.0, 100.0, 0.0]),
        "B": np.array([0.0, 0.0, 100.0]),
    }


@pytest.fixture
def leaf_collection() -> ReflectorCollection:
    names = ["Leaf 1", "Leaf 2", "Leaf 3", "Leaf 4"]
    matrix = np.array(
        [
            [0.1, 0.2, 0.3],
            [0.2, 0.3, 0.4],
            [0.3, 0.4, 0.5],
            [0.4, 0.5, 0.6],
        ]
    )
    return ReflectorCollection(
        reflectors=[
            ReflectorSpectrum(name=name, values=values)
            for name, values in zip(names, matrix)
        ],
        reflector_matrix=matrix,
    )
