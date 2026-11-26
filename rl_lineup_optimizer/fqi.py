"""Conservative fitted Q-iteration over historically observed lineups."""
from collections import Counter
from dataclasses import dataclass
import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesRegressor


def _lineup(value):
    return tuple(sorted(int(x) for x in value))


@dataclass
class FQIConfig:
    iterations: int = 8
    n_estimators: int = 150
    min_lineup_stints: int = 5
    gamma: float = 1.0
    random_state: int = 42
    min_samples_leaf: int = 2


class FittedQIteration:
    """Offline FQI; actions are limited to supported five-player lineups by season."""
    def __init__(self, config=None):
        self.config = config or FQIConfig()
        self.model = None
        self.players_by_season = {}
        self.lineups_by_season = {}
        self.support_by_season = {}
        self.seasons = []
        self.player_tokens = []
        self.season_index = {}
        self.is_fitted = False

    def _prepare(self, data):
        for season, group in data.groupby("SEASON"):
            season = str(season)
            counts = Counter(_lineup(x) for x in group.ACTION_LINEUP)
            eligible = {lineup: n for lineup,n in counts.items()
                        if n >= self.config.min_lineup_stints and len(lineup) == 5}
            if eligible:
                self.lineups_by_season[season] = sorted(eligible)
                self.support_by_season[season] = Counter(eligible)
                self.players_by_season[season] = sorted({p for lineup in eligible for p in lineup})
        self.seasons = sorted(self.lineups_by_season)
        self.season_index = {s:i for i,s in enumerate(self.seasons)}
        self.player_tokens = [(s,p) for s in self.seasons for p in self.players_by_season[s]]
        self.token_index = {token:i for i,token in enumerate(self.player_tokens)}

    def _features(self, season, score_diff, seconds, previous, action):
        season = str(season)
        x = np.zeros(3 + 2*len(self.player_tokens), dtype=float)
        x[0], x[1], x[2] = float(score_diff), float(seconds), self.season_index[season]
        offset = 3
        for player in _lineup(previous):
            idx = self.token_index.get((season,player))
            if idx is not None: x[offset+idx] = 1.0
        offset += len(self.player_tokens)
        for player in _lineup(action):
            idx = self.token_index.get((season,player))
            if idx is not None: x[offset+idx] = 1.0
        return x

    def fit(self, transitions):
        required = {"SEASON","SCORE_DIFF","SECONDS_REMAINING","PREVIOUS_LINEUP","ACTION_LINEUP",
                    "REWARD","NEXT_SCORE_DIFF","NEXT_SECONDS_REMAINING","NEXT_PREVIOUS_LINEUP","DONE"}
        missing = required - set(transitions.columns)
        if missing: raise ValueError("Missing transition columns: " + ", ".join(sorted(missing)))
        data = transitions.copy().reset_index(drop=True)
        if data.empty: raise ValueError("No transitions available.")
        data["SEASON"] = data.SEASON.astype(str)
        self._prepare(data)
        if not self.seasons: raise ValueError("No five-player lineups meet the minimum support threshold.")
        data = data[data.SEASON.isin(self.seasons)].copy().reset_index(drop=True)
        data["ACTION_LINEUP"] = data.ACTION_LINEUP.apply(_lineup)
        data = data[data.apply(lambda r: r.ACTION_LINEUP in self.lineups_by_season[r.SEASON],axis=1)].reset_index(drop=True)
        X = np.vstack([self._features(r.SEASON,r.SCORE_DIFF,r.SECONDS_REMAINING,r.PREVIOUS_LINEUP,r.ACTION_LINEUP)
                       for r in data.itertuples(index=False)])
        rewards = data.REWARD.to_numpy(dtype=float)
        targets = rewards.copy()
        self.model = ExtraTreesRegressor(n_estimators=self.config.n_estimators,
            min_samples_leaf=self.config.min_samples_leaf,max_features=1.0,
            random_state=self.config.random_state,n_jobs=-1)
        for iteration in range(max(1,self.config.iterations)):
            self.model.fit(X,targets)
            if iteration == self.config.iterations-1: break
            updated = rewards.copy()
            for i,r in enumerate(data.itertuples(index=False)):
                if bool(r.DONE): continue
                candidates = self.lineups_by_season[r.SEASON]
                next_x = np.vstack([self._features(r.SEASON,r.NEXT_SCORE_DIFF,
                    r.NEXT_SECONDS_REMAINING,r.NEXT_PREVIOUS_LINEUP,a) for a in candidates])
                updated[i] += self.config.gamma * float(np.max(self.model.predict(next_x)))
            targets = updated
        self.training_rows = len(data)
        self.is_fitted = True
        return self

    def recommend(self, season, score_diff, seconds_remaining, previous_lineup=(), top_k=5):
        if not self.is_fitted: raise RuntimeError("Fit the model first.")
        season = str(season)
        if season not in self.lineups_by_season: raise ValueError(f"No supported lineups for season {season}.")
        actions = self.lineups_by_season[season]
        X = np.vstack([self._features(season,score_diff,seconds_remaining,previous_lineup,a) for a in actions])
        values = self.model.predict(X)
        result = pd.DataFrame({"LINEUP":actions,"ESTIMATED_FUTURE_POINT_DIFFERENTIAL":values,
            "HISTORICAL_STINT_SUPPORT":[self.support_by_season[season][a] for a in actions]})
        result = result.sort_values("ESTIMATED_FUTURE_POINT_DIFFERENTIAL",ascending=False).head(max(1,int(top_k)))
        result["LINEUP"] = result.LINEUP.apply(lambda lineup:", ".join(f"#{p}" for p in lineup))
        return result.reset_index(drop=True)
