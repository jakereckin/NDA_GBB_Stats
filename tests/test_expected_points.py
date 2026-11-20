import unittest

import numpy as np
import pandas as pd

from py.expected_points import (
    FEATURE_COLUMNS,
    build_pre_shot_features,
    predict_expected_points,
    train_expected_points_model,
)


def make_shots(game_count=15):
    rows = []
    for game_number in range(game_count):
        date = pd.Timestamp("2025-01-01") + pd.Timedelta(days=game_number * 3)
        for play_number in range(10):
            rows.append(
                {
                    "GAME_ID": game_number + 1,
                    "PLAYER_ID": (play_number % 3) + 1,
                    "SHOT_SPOT": "LEFT_2" if play_number % 2 else "RIGHT_3",
                    "SHOT_DEFENSE": "OPEN" if play_number % 2 else "GUARDED",
                    "MAKE_MISS": "Y" if (game_number + play_number) % 2 else "N",
                    "PLAY_NUM": play_number,
                    "XSPOT": -30 if play_number % 2 else 30,
                    "YSPOT": 10 + play_number,
                    "POINTS": 2 if play_number % 2 else 3,
                    "OPP_EXPECTED": 0.8 if play_number % 2 else 1.0,
                    "OPPONENT": "Test",
                    "LOCATION": "Home",
                    "DATE": date.strftime("%m/%d/%Y"),
                    "SEASON": 2025,
                }
            )
    return pd.DataFrame(rows)


class ExpectedPointsTests(unittest.TestCase):
    def test_features_for_a_shot_only_use_outcomes_from_prior_shots(self):
        shots = make_shots(game_count=2)
        features = build_pre_shot_features(shots)
        changed_future = shots.copy()
        changed_future.loc[changed_future["GAME_ID"] == 2, "MAKE_MISS"] = (
            changed_future.loc[
                changed_future["GAME_ID"] == 2, "MAKE_MISS"
            ].map({"Y": "N", "N": "Y"})
        )
        changed_features = build_pre_shot_features(changed_future)

        pd.testing.assert_series_equal(
            features.loc[features["GAME_ID"] == 1, "PLAYER_PRIOR_MAKE_RATE"]
            .reset_index(drop=True),
            changed_features.loc[
                changed_features["GAME_ID"] == 1, "PLAYER_PRIOR_MAKE_RATE"
            ].reset_index(drop=True),
        )
        self.assertAlmostEqual(
            features.loc[features["GAME_ID"] == 1, "PLAYER_PRIOR_MAKE_RATE"]
            .iloc[0],
            0.33,
        )

    def test_a_shot_and_later_outcomes_do_not_change_that_shots_features(self):
        shots = make_shots(game_count=2)
        original = build_pre_shot_features(shots)
        changed = shots.copy()
        changed.loc[changed.index == 9, "MAKE_MISS"] = "N"
        changed.loc[changed["GAME_ID"] == 2, "MAKE_MISS"] = (
            changed.loc[
                changed["GAME_ID"] == 2, "MAKE_MISS"
            ].map({"Y": "N", "N": "Y"})
        )
        updated = build_pre_shot_features(changed)

        before_last_play = original["GAME_ID"].eq(1) & original["PLAY_NUM"].lt(9)
        for column in (
            "ZONE_PRIOR_MAKE_RATE",
            "PLAYER_PRIOR_MAKE_RATE",
            "PLAYER_SPOT_PRIOR_MAKE_RATE",
        ):
            np.testing.assert_allclose(
                original.loc[before_last_play, column],
                updated.loc[before_last_play, column],
            )
        original_last = original.loc[
            original["GAME_ID"].eq(1) & original["PLAY_NUM"].eq(9)
        ].iloc[0]
        updated_last = updated.loc[
            updated["GAME_ID"].eq(1) & updated["PLAY_NUM"].eq(9)
        ].iloc[0]
        self.assertEqual(
            original_last["PLAYER_SPOT_PRIOR_MAKE_RATE"],
            updated_last["PLAYER_SPOT_PRIOR_MAKE_RATE"],
        )

    def test_model_uses_only_pre_shot_features_and_predicts_expected_points(self):
        shots = make_shots()
        result = train_expected_points_model(shots)
        features = build_pre_shot_features(shots)
        predictions = predict_expected_points(features, result.model)

        self.assertNotIn("MAKE", FEATURE_COLUMNS)
        self.assertNotIn("GAME_ID", FEATURE_COLUMNS)
        self.assertNotIn("OPP_EXPECTED", FEATURE_COLUMNS)
        self.assertTrue(
            predictions["EXPECTED_POINTS"].between(0, predictions["POINTS"]).all()
        )
        self.assertEqual(len(result.validation_scores), 2)
        self.assertGreater(result.holdout_metrics["expected_points_mae"], 0)
        self.assertIn(result.selected_model_name, result.validation_scores["model"].tolist())


if __name__ == "__main__":
    unittest.main()
