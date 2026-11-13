"""Report 5 model helpers on SYNTHETIC values: least squares, cross-validation, metrics, no price leakage."""
import numpy as np
import pandas as pd

from report5.model import cross_val_predict, features, kfold_indices, mae, ols_fit, r2, sign_accuracy


def test_least_squares_recovers_known_coefficients():
    rng = np.random.default_rng(0)
    x = rng.normal(size=(50, 2))
    y = 1.5 + 2.0 * x[:, 0] - 0.5 * x[:, 1]                     # exact line, no noise
    assert np.allclose(ols_fit(x, y), [1.5, 2.0, -0.5])


def test_folds_use_every_row_exactly_once():
    folds = kfold_indices(139, 5, 42)
    assert len(folds) == 5 and sorted(np.concatenate(folds).tolist()) == list(range(139))


def test_metrics_and_out_of_fold_baseline():
    y = np.array([0.1, -0.2, 0.3, 0.0, -0.1])
    assert r2(y, y) == 1 and abs(r2(y, np.full(5, y.mean()))) < 1e-12
    assert np.isclose(mae(y, np.zeros(5)), 0.14)
    assert sign_accuracy(y, np.array([1, -1, -1, 5, -1])) == 0.75          # the tie (y = 0) is left out
    pred = cross_val_predict(None, np.arange(10, dtype=float), k=5, seed=1)
    assert not np.any(pred == np.arange(10))                               # a row never predicts itself


def test_features_have_no_price_columns_and_promo_flags_are_correct():
    m = pd.DataFrame({"group": ["seasoning"] * 10 + ["personal_care"] * 2, "size_value": [100.0] * 12, "pack_count": [1] * 12,
                      "bhx_price_vnd": [9_000] + [10_000] * 11, "bhx_list_price_vnd": [10_000] * 12,
                      "winmart_price_vnd": [10_000] * 12, "winmart_list_price_vnd": [10_000] * 12})
    x = features(m, with_promo=True)
    assert not [c for c in x.columns if "price" in c]
    assert x["promo_bhx"].tolist() == [1.0] + [0.0] * 11 and x["promo_winmart"].sum() == 0
    assert "group_small_groups" not in x.columns or x.shape[1] == 5       # small group merged, one dummy at most
