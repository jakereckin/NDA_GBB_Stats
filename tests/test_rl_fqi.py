import pandas as pd
from rl_lineup_optimizer.fqi import FQIConfig, FittedQIteration


def test_model_uses_only_supported_lineups():
    rows=[]
    lineups=[(1,2,3,4,5),(1,2,3,4,6)]
    for game in range(6):
        for i,lineup in enumerate(lineups):
            rows.append({"GAME_ID":game,"SEASON":"2026","SCORE_DIFF":0,
                "SECONDS_REMAINING":1800-i*60,"PREVIOUS_LINEUP":(),
                "ACTION_LINEUP":lineup,"REWARD":1 if lineup[-1]==5 else 0,
                "NEXT_SCORE_DIFF":1,"NEXT_SECONDS_REMAINING":1740-i*60,
                "NEXT_PREVIOUS_LINEUP":lineup,"DONE":True})
    model=FittedQIteration(FQIConfig(iterations=2,n_estimators=10,min_lineup_stints=2)).fit(pd.DataFrame(rows))
    recs=model.recommend("2026",0,1200,top_k=5)
    assert len(recs)==2
    assert set(recs.HISTORICAL_STINT_SUPPORT)=={6}
    assert all(len(lineup.split(", "))==5 for lineup in recs.LINEUP)
