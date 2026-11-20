from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Any

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    brier_score_loss,
    log_loss,
    mean_absolute_error,
    mean_squared_error,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


BASE_MAKE_RATE = 0.33
PRIOR_STRENGTH = 20.0
NUMERIC_FEATURES = (
    "XSPOT",
    "YSPOT",
    "SHOT_DISTANCE",
    "SHOT_ANGLE",
    "POINTS",
    "ZONE_PRIOR_MAKE_RATE",
    "PLAYER_PRIOR_MAKE_RATE",
    "PLAYER_SPOT_PRIOR_MAKE_RATE",
)
CATEGORICAL_FEATURES = ("SPOT", "SHOT_DEFENSE", "LOCATION")
FEATURE_COLUMNS = list(NUMERIC_FEATURES + CATEGORICAL_FEATURES)
TARGET_COLUMN = "MAKE"
EXPECTED_POINTS_COLUMN = "EXPECTED_POINTS"


@dataclass
class ExpectedPointsTrainingResult:
    model: Pipeline
    selected_model_name: str
    validation_scores: pd.DataFrame
    holdout_metrics: dict[str, float]
    feature_columns: tuple[str, ...]


def _date_values(values: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(values, format="mixed", errors="coerce")
    if parsed.isna().any():
        raise ValueError("Every shot must have a valid game date.")
    return parsed


def _prior_rates(
    frame: pd.DataFrame,
    group_columns: list[str],
    prior_rate: pd.Series,
    prefix: str,
) -> tuple[pd.Series, pd.Series]:
    grouped = frame.groupby(group_columns, sort=False, dropna=True)
    observed_attempt = frame["_OBSERVED_MAKE"].notna().astype(float)
    observed_make = frame["_OBSERVED_MAKE"].fillna(0.0)
    attempts_before = grouped["_OBSERVED_ATTEMPT"].cumsum() - observed_attempt
    makes_before = grouped["_OBSERVED_MAKE"].cumsum() - observed_make
    rates = (
        makes_before + PRIOR_STRENGTH * prior_rate
    ) / (attempts_before + PRIOR_STRENGTH)
    return rates.rename(f"{prefix}_MAKE_RATE"), attempts_before.rename(
        f"{prefix}_ATTEMPTS"
    )


def build_pre_shot_features(shots: pd.DataFrame) -> pd.DataFrame:
    """Create shot features using only context and outcomes observed earlier."""
    if not isinstance(shots, pd.DataFrame):
        if hasattr(shots, "to_pandas"):
            shots = shots.to_pandas()
        else:
            shots = pd.DataFrame(shots)

    required = {
        "GAME_ID",
        "DATE",
        "PLAY_NUM",
        "PLAYER_ID",
        "SEASON",
        "SHOT_SPOT",
        "SHOT_DEFENSE",
        "LOCATION",
        "XSPOT",
        "YSPOT",
        "POINTS",
    }
    missing = required - set(shots.columns)
    if missing:
        raise ValueError(
            "Shot data is missing required columns: "
            + ", ".join(sorted(missing))
        )

    frame = shots.copy()
    frame["_SOURCE_ORDER"] = np.arange(len(frame))
    frame["_GAME_DATE"] = _date_values(frame["DATE"])

    if "MAKE" in frame:
        observed_make = pd.to_numeric(frame["MAKE"], errors="coerce")
    elif "MAKE_MISS" in frame:
        observed_make = (
            frame["MAKE_MISS"]
            .astype("string")
            .str.strip()
            .str.upper()
            .map({"Y": 1.0, "N": 0.0})
        )
    else:
        observed_make = pd.Series(np.nan, index=frame.index, dtype=float)
    invalid_labels = observed_make.dropna().loc[
        ~observed_make.dropna().isin([0, 1])
    ]
    if not invalid_labels.empty:
        raise ValueError("Observed shot outcomes must be binary values 0 or 1.")
    frame["_OBSERVED_MAKE"] = observed_make
    frame["_OBSERVED_ATTEMPT"] = observed_make.notna().astype(float)
    frame["MAKE"] = observed_make
    frame["POINTS"] = pd.to_numeric(frame["POINTS"], errors="coerce")

    frame = frame.sort_values(
        ["_GAME_DATE", "GAME_ID", "PLAY_NUM", "_SOURCE_ORDER"],
        kind="mergesort",
    ).reset_index(drop=True)
    frame["XSPOT"] = pd.to_numeric(frame["XSPOT"], errors="coerce")
    frame["YSPOT"] = pd.to_numeric(frame["YSPOT"], errors="coerce")
    frame["SHOT_DISTANCE"] = np.hypot(frame["XSPOT"], frame["YSPOT"])
    frame["SHOT_ANGLE"] = np.arctan2(frame["XSPOT"], frame["YSPOT"])
    frame["SPOT"] = frame["SHOT_SPOT"].astype("string").fillna("UNKNOWN")
    frame["SHOT_DEFENSE"] = (
        frame["SHOT_DEFENSE"].astype("string").str.strip().str.upper()
        .replace({
            "OPEN": "OPEN",
            "GUARDED": "GUARDED",
            "HEAVILY GUARDED": "HEAVILY_GUARDED",
        })
        .fillna("UNKNOWN")
    )
    frame["LOCATION"] = (
        frame["LOCATION"]
        .astype("string")
        .str.strip()
        .str.upper()
        .fillna("UNKNOWN")
    )

    zone_rate, _ = _prior_rates(
        frame,
        ["SPOT"],
        pd.Series(BASE_MAKE_RATE, index=frame.index),
        "ZONE_PRIOR",
    )
    frame["ZONE_PRIOR_MAKE_RATE"] = zone_rate

    player_key = frame["PLAYER_ID"].astype("string")
    unknown_player = pd.to_numeric(frame["PLAYER_ID"], errors="coerce").eq(0)
    player_key = player_key.mask(unknown_player)
    frame["_PLAYER_KEY"] = player_key
    frame["_SEASON_KEY"] = frame["SEASON"].astype("string")

    player_rate, _ = _prior_rates(
        frame,
        ["_PLAYER_KEY", "_SEASON_KEY"],
        frame["ZONE_PRIOR_MAKE_RATE"],
        "PLAYER_PRIOR",
    )
    frame["PLAYER_PRIOR_MAKE_RATE"] = player_rate.fillna(
        frame["ZONE_PRIOR_MAKE_RATE"]
    )

    player_spot_rate, _ = _prior_rates(
        frame,
        ["_PLAYER_KEY", "_SEASON_KEY", "SPOT"],
        frame["ZONE_PRIOR_MAKE_RATE"],
        "PLAYER_SPOT_PRIOR",
    )
    frame["PLAYER_SPOT_PRIOR_MAKE_RATE"] = player_spot_rate.fillna(
        frame["ZONE_PRIOR_MAKE_RATE"]
    )

    frame["ACTUAL_POINTS"] = frame["MAKE"] * frame["POINTS"]
    frame["ATTEMPT"] = 1
    frame["TEAM"] = np.where(unknown_player, "OPPONENT", "NDA")
    frame = frame.sort_values("_SOURCE_ORDER", kind="mergesort").drop(
        columns=[
            "_SOURCE_ORDER",
            "_GAME_DATE",
            "_OBSERVED_MAKE",
            "_OBSERVED_ATTEMPT",
            "_PLAYER_KEY",
            "_SEASON_KEY",
        ]
    )
    return frame.reset_index(drop=True)


def make_expected_points_model(model_name: str) -> Pipeline:
    numeric_pipeline = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical_pipeline = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )
    preprocessor = ColumnTransformer(
        [
            ("numeric", numeric_pipeline, list(NUMERIC_FEATURES)),
            ("categorical", categorical_pipeline, list(CATEGORICAL_FEATURES)),
        ],
        remainder="drop",
    )

    if model_name == "regularized_logistic":
        estimator: Any = LogisticRegression(
            C=0.1,
            max_iter=2000,
            random_state=42,
        )
    elif model_name == "shallow_lightgbm":
        estimator = LGBMClassifier(
            n_estimators=120,
            learning_rate=0.03,
            num_leaves=7,
            max_depth=3,
            min_child_samples=35,
            reg_lambda=5.0,
            verbosity=-1,
            random_state=42,
            n_jobs=1,
        )
    else:
        raise ValueError(f"Unknown expected-points model: {model_name}")

    return Pipeline(
        [
            ("preprocessor", preprocessor),
            ("classifier", estimator),
        ]
    )


def _ordered_dates(frame: pd.DataFrame) -> list[pd.Timestamp]:
    return sorted(pd.to_datetime(frame["_GAME_DATE"]).drop_duplicates().tolist())


def _chronological_folds(
    frame: pd.DataFrame, n_splits: int
) -> list[tuple[list[pd.Timestamp], list[pd.Timestamp]]]:
    game_dates = _ordered_dates(frame)
    test_size = max(1, len(game_dates) // (n_splits + 1))
    first_test = len(game_dates) - test_size * n_splits
    if first_test < 3:
        raise ValueError(
            "Not enough distinct game dates for chronological validation; "
            "collect more games or reduce n_splits."
        )

    folds = []
    for split_number in range(n_splits):
        start = first_test + split_number * test_size
        end = start + test_size
        folds.append((game_dates[:start], game_dates[start:end]))
    return folds


def _model_metrics(
    y_true: pd.Series,
    probabilities: np.ndarray,
    points: pd.Series,
) -> dict[str, float]:
    probabilities = np.clip(
        np.asarray(probabilities, dtype=float), 1e-6, 1 - 1e-6
    )
    actual_points = y_true.to_numpy(dtype=float) * points.to_numpy(dtype=float)
    expected_points = probabilities * points.to_numpy(dtype=float)
    result = {
        "expected_points_mae": float(
            mean_absolute_error(actual_points, expected_points)
        ),
        "expected_points_rmse": float(
            np.sqrt(mean_squared_error(actual_points, expected_points))
        ),
        "make_brier": float(brier_score_loss(y_true, probabilities)),
        "make_log_loss": float(
            log_loss(y_true, probabilities, labels=[0, 1])
        ),
    }
    if y_true.nunique() == 2:
        result["make_roc_auc"] = float(roc_auc_score(y_true, probabilities))
    else:
        result["make_roc_auc"] = float("nan")
    return result


def train_expected_points_model(
    shots: pd.DataFrame,
    n_splits: int = 3,
    holdout_fraction: float = 0.2,
) -> ExpectedPointsTrainingResult:
    """Select by expanding-window validation, report a final future-game holdout."""
    if not 0 < holdout_fraction < 1:
        raise ValueError("holdout_fraction must be between 0 and 1.")
    featured = build_pre_shot_features(shots)
    labeled = featured.loc[
        featured["MAKE"].notna() & featured["POINTS"].notna()
    ].copy()
    if labeled.empty:
        raise ValueError("No labeled shot outcomes are available for training.")

    dates = _date_values(labeled["DATE"])
    labeled["_GAME_DATE"] = dates
    ordered_dates = _ordered_dates(labeled)
    holdout_count = max(1, ceil(len(ordered_dates) * holdout_fraction))
    if len(ordered_dates) - holdout_count < n_splits + 3:
        raise ValueError(
            "Not enough distinct game dates for a future holdout and "
            "chronological validation."
        )
    development_dates = ordered_dates[:-holdout_count]
    holdout_dates = ordered_dates[-holdout_count:]
    development = labeled.loc[
        labeled["_GAME_DATE"].isin(development_dates)
    ].copy()
    holdout = labeled.loc[labeled["_GAME_DATE"].isin(holdout_dates)].copy()

    folds = _chronological_folds(development, n_splits)
    candidate_names = ("regularized_logistic", "shallow_lightgbm")
    validation_rows: list[dict[str, Any]] = []
    for candidate_name in candidate_names:
        fold_metrics = []
        for train_dates, validation_dates in folds:
            fold_train = development.loc[
                development["_GAME_DATE"].isin(train_dates)
            ]
            fold_validation = development.loc[
                development["_GAME_DATE"].isin(validation_dates)
            ]
            candidate = make_expected_points_model(candidate_name)
            candidate.fit(
                fold_train.loc[:, FEATURE_COLUMNS],
                fold_train["MAKE"].astype(int),
            )
            probabilities = candidate.predict_proba(
                fold_validation.loc[:, FEATURE_COLUMNS]
            )[:, 1]
            fold_metrics.append(
                _model_metrics(
                    fold_validation["MAKE"].astype(int),
                    probabilities,
                    fold_validation["POINTS"],
                )
            )
        validation_rows.append(
            {
                "model": candidate_name,
                "cv_expected_points_mae": float(
                    np.mean(
                        [
                            metrics["expected_points_mae"]
                            for metrics in fold_metrics
                        ]
                    )
                ),
                "cv_expected_points_rmse": float(
                    np.mean(
                        [
                            metrics["expected_points_rmse"]
                            for metrics in fold_metrics
                        ]
                    )
                ),
                "cv_make_brier": float(
                    np.mean(
                        [metrics["make_brier"] for metrics in fold_metrics]
                    )
                ),
                "cv_make_log_loss": float(
                    np.mean(
                        [metrics["make_log_loss"] for metrics in fold_metrics]
                    )
                ),
            }
        )

    validation_scores = pd.DataFrame(validation_rows).sort_values(
        ["cv_expected_points_mae", "cv_make_brier"],
        kind="mergesort",
    ).reset_index(drop=True)
    selected_name = str(validation_scores.iloc[0]["model"])
    validation_model = make_expected_points_model(selected_name)
    validation_model.fit(
        development.loc[:, FEATURE_COLUMNS],
        development["MAKE"].astype(int),
    )
    holdout_probabilities = validation_model.predict_proba(
        holdout.loc[:, FEATURE_COLUMNS]
    )[:, 1]
    holdout_metrics = _model_metrics(
        holdout["MAKE"].astype(int),
        holdout_probabilities,
        holdout["POINTS"],
    )
    actual_holdout_points = holdout["MAKE"] * holdout["POINTS"]
    zone_prior_expected_points = (
        holdout["ZONE_PRIOR_MAKE_RATE"] * holdout["POINTS"]
    )
    holdout_metrics["prior_zone_expected_points_mae"] = float(
        mean_absolute_error(
            actual_holdout_points,
            zone_prior_expected_points,
        )
    )

    final_model = make_expected_points_model(selected_name)
    final_model.fit(
        labeled.loc[:, FEATURE_COLUMNS],
        labeled["MAKE"].astype(int),
    )
    return ExpectedPointsTrainingResult(
        model=final_model,
        selected_model_name=selected_name,
        validation_scores=validation_scores,
        holdout_metrics=holdout_metrics,
        feature_columns=tuple(FEATURE_COLUMNS),
    )


def predict_expected_points(
    featured_shots: pd.DataFrame,
    model: Pipeline,
) -> pd.DataFrame:
    """Return prospective probabilities and expected points for shot rows."""
    result = featured_shots.copy()
    probabilities = model.predict_proba(result.loc[:, FEATURE_COLUMNS])[:, 1]
    result["PROB"] = probabilities
    result[EXPECTED_POINTS_COLUMN] = probabilities * result["POINTS"]
    result["ACTUAL_POINTS"] = result["MAKE"] * result["POINTS"]
    result["LABEL"] = (
        result["OPPONENT"].astype(str) + " - " + result["DATE"].astype(str)
    )
    result["TEAM"] = np.where(
        pd.to_numeric(result["PLAYER_ID"], errors="coerce").eq(0),
        "OPPONENT",
        "NDA",
    )
    result["ATTEMPT"] = 1
    return result
