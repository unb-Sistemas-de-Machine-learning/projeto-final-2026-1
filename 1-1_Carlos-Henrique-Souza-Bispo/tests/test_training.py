from __future__ import annotations

import numpy as np
import pandas as pd

from app.training import choose_threshold


def test_threshold_is_valid_probability() -> None:
    target = pd.Series([0, 0, 1, 1])
    probabilities = np.array([0.1, 0.3, 0.6, 0.9])

    threshold = choose_threshold(target, probabilities)

    assert 0 < threshold < 1
