"""Disruption-risk model: probability that a scheduled flight is cancelled, diverted or arrives 15+ minutes late,
from information known when the schedule is published. Trained on the first 18 months, tested on the last 6.
"""
from __future__ import annotations

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.preprocessing import OneHotEncoder

from src import config

CATEGORICAL = ["carrier", "origin", "dest"]
NUMERIC = ["dep_hour", "arr_hour", "dow", "month", "distance", "crs_elapsed", "planned_turn", "planned_leg"]
PARAMS = {"objective": "binary", "learning_rate": 0.05, "num_leaves": 127, "min_data_in_leaf": 200,
          "feature_fraction": 0.9, "bagging_fraction": 0.8, "bagging_freq": 1, "lambda_l2": 1.0,
          "seed": config.SEED, "deterministic": True, "force_row_wise": True, "verbosity": -1}
ROUNDS = 400
TRAIN_ROWS = 5_000_000


def _prep(df: pd.DataFrame, cats: dict[str, pd.Index] | None = None) -> tuple[pd.DataFrame, dict]:
    X = df[CATEGORICAL + NUMERIC].copy()
    cats = cats or {c: pd.Index(sorted(X[c].dropna().unique())) for c in CATEGORICAL}
    for c in CATEGORICAL:
        X[c] = pd.Categorical(X[c], categories=cats[c])
    return X, cats


def fit_and_score(frame: pd.DataFrame) -> dict:
    frame = frame.copy()
    frame["flight_date"] = pd.to_datetime(frame.flight_date)
    test_mask = frame.flight_date >= config.MODEL_TEST_START
    train = frame[~test_mask]
    if len(train) > TRAIN_ROWS:
        train = train.sample(n=TRAIN_ROWS, random_state=config.SEED)
    test = frame[test_mask]
    Xtr, cats = _prep(train)
    Xte, _ = _prep(test, cats)
    booster = lgb.train(PARAMS, lgb.Dataset(Xtr, train.disrupted.to_numpy(), categorical_feature=CATEGORICAL),
                        num_boost_round=ROUNDS)
    p = booster.predict(Xte)
    y = test.disrupted.to_numpy()

    # baseline: logistic regression on carrier, departure hour and month only
    enc = OneHotEncoder(handle_unknown="ignore", min_frequency=50)
    base_cols = ["carrier", "dep_hour", "month"]
    lr = LogisticRegression(max_iter=300, C=1.0)
    sub = train.sample(n=min(len(train), 1_000_000), random_state=config.SEED)
    lr.fit(enc.fit_transform(sub[base_cols].astype(str)), sub.disrupted.to_numpy())
    p_base = lr.predict_proba(enc.transform(test[base_cols].astype(str)))[:, 1]

    deciles = pd.qcut(pd.Series(p).rank(method="first"), 10, labels=False) + 1
    dec = (pd.DataFrame({"decile": deciles, "y": y, "p": p}).groupby("decile")
           .agg(flights=("y", "size"), disruption_rate=("y", "mean"), predicted=("p", "mean")).reset_index())
    bins = pd.cut(p, np.linspace(0, 1, 21), include_lowest=True)
    cal = (pd.DataFrame({"bin": bins, "y": y, "p": p}).groupby("bin", observed=True)
           .agg(flights=("y", "size"), observed=("y", "mean"), predicted=("p", "mean")).reset_index())
    cal["bin"] = cal["bin"].astype(str)
    gain = booster.feature_importance("gain")
    imp = pd.DataFrame({"feature": booster.feature_name(), "gain": gain}).sort_values("gain", ascending=False)
    imp["share"] = imp.gain / imp.gain.sum()
    base_rate = float(y.mean())
    top = dec[dec.decile == 10].iloc[0]
    metrics = {"train_rows": int(len(train)), "test_rows": int(len(test)), "test_start": config.MODEL_TEST_START,
               "base_rate_test": base_rate, "auc": float(roc_auc_score(y, p)),
               "auc_baseline": float(roc_auc_score(y, p_base)), "brier": float(brier_score_loss(y, p)),
               "brier_climatology": float(brier_score_loss(y, np.full_like(p, train.disrupted.mean()))),
               "log_loss": float(log_loss(y, p)), "top_decile_rate": float(top.disruption_rate),
               "top_decile_lift": float(top.disruption_rate / base_rate),
               "bottom_decile_rate": float(dec[dec.decile == 1].iloc[0].disruption_rate),
               "rounds": ROUNDS, "params": {k: v for k, v in PARAMS.items() if k != "verbosity"}}
    return {"metrics": metrics, "deciles": dec, "calibration": cal, "importance": imp}
