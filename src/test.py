"""Unit testing
author: steeve laquitaine
usage:
    pytest src/test.py
"""

import numpy as np

from src.nodes.data import VonMises
from src.nodes.utils import is_all_in


def test_VonMises():
    vmises = VonMises(p=True).get(
        v_x=np.arange(0, 360, 1),
        v_u=np.arange(0, 360, 1),
        v_k=[0.5, 1],
    )
    # check shape
    assert vmises.shape == (
        360,
        720,
    ), "measure density's shape is wrong"

    # check normalization
    assert all(
        sum(vmises)
    ), "VonMises are not probabilities"


def test_is_all_in():
    """unit-test "is_all_in"
    """
    assert (
        is_all_in({0, 1, 2, 3}, {0, 1, 2, 3}) == True
    ), "is_all_in is flawed"

    assert (
        is_all_in({4}, {0, 1, 2, 3}) == False
    ), "is_all_in is flawed"
