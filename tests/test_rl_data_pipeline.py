import pandas as pd
from rl_lineup_optimizer.data_pipeline import build_dataset


def game_frame(player_count=5):
    return pd.DataFrame([{
        "GAME_ID":1,"PLAYER_ID":p,"TIME_IN":2160,"TIME_OUT":0,
        "TEAM_POINT_IN":0,"TEAM_POINT_OUT":40,"OPP_POINT_IN":0,"OPP_POINT_OUT":35,
        "SEASON":"2026","GAME_DATE":"2026-01-01","OPPONENT":"Test"
    } for p in range(1,player_count+1)])


def test_full_game_reward_reconciles():
    stints, transitions, issues = build_dataset(game_frame())
    assert issues.empty
    assert len(stints) == 1
    assert stints.iloc[0].REWARD == 5
    assert len(transitions) == 1
    assert bool(transitions.iloc[0].DONE)
    assert transitions.iloc[0].ACTION_LINEUP == (1,2,3,4,5)


def test_non_five_player_game_is_excluded():
    stints, transitions, issues = build_dataset(game_frame(4))
    assert stints.empty and transitions.empty
    assert "LINEUP_SIZE" in set(issues.CODE)
