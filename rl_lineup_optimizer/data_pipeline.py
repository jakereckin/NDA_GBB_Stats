"""Validated conversion of historical MINUTES rows into lineup stints."""
import pandas as pd

REQUIRED = {"GAME_ID","PLAYER_ID","TIME_IN","TIME_OUT","TEAM_POINT_IN","TEAM_POINT_OUT",
            "OPP_POINT_IN","OPP_POINT_OUT","SEASON","GAME_DATE","OPPONENT"}


def fetch_minutes(connection):
    from py import data_source
    query = """
    SELECT M.GAME_ID, M.PLAYER_ID, M.TIME_IN, M.TIME_OUT,
           M.TEAM_POINT_IN, M.TEAM_POINT_OUT, M.OPP_POINT_IN, M.OPP_POINT_OUT,
           G.DATE AS GAME_DATE, G.SEASON, G.OPPONENT
      FROM MINUTES M
      JOIN GAMES G ON G.GAME_ID=M.GAME_ID
      JOIN PLAYERS P ON P.NUMBER=M.PLAYER_ID AND P.YEAR=G.SEASON
    """
    return data_source.run_query(sql=query, connection=connection)


def _snapshot(group, clock, entering):
    clock_col = "TIME_IN" if entering else "TIME_OUT"
    a, b = (("TEAM_POINT_IN","OPP_POINT_IN") if entering
            else ("TEAM_POINT_OUT","OPP_POINT_OUT"))
    rows = group.loc[group[clock_col] == clock, [a,b]]
    if rows.empty or rows.isna().any().any():
        return None
    rows = rows.drop_duplicates()
    if len(rows) != 1:
        return None
    return int(rows.iloc[0][a]), int(rows.iloc[0][b])


def build_stints(minutes, game_end_sec=2160):
    missing = REQUIRED - set(minutes.columns)
    if missing:
        raise ValueError("Missing columns: " + ", ".join(sorted(missing)))
    if game_end_sec <= 0:
        raise ValueError("game_end_sec must be positive")
    output, issues = [], []
    for game_id, source in minutes.groupby("GAME_ID", sort=False):
        g = source.copy().reset_index(drop=True)
        bad = []
        for col in ["TIME_IN","TIME_OUT","TEAM_POINT_IN","TEAM_POINT_OUT","OPP_POINT_IN","OPP_POINT_OUT"]:
            g[col] = pd.to_numeric(g[col], errors="coerce")
        if g[["TIME_IN","TIME_OUT"]].isna().any().any():
            bad.append(("INVALID_CLOCK","Null or nonnumeric clock values."))
        elif ((g.TIME_IN < 0) | (g.TIME_IN > game_end_sec) |
              (g.TIME_OUT < 0) | (g.TIME_OUT > game_end_sec) |
              (g.TIME_IN <= g.TIME_OUT)).any():
            bad.append(("INVALID_INTERVAL","Invalid descending-clock interval."))
        if g.PLAYER_ID.isna().any():
            bad.append(("INVALID_PLAYER","Null player ID."))
        for player, pg in g.groupby("PLAYER_ID"):
            intervals = pg[["TIME_IN","TIME_OUT"]].dropna().sort_values("TIME_IN", ascending=False).to_numpy()
            for i in range(1, len(intervals)):
                if intervals[i,0] > intervals[i-1,1]:
                    bad.append(("OVERLAPPING_PLAYER_INTERVAL",f"Player {player} has overlapping shifts."))
                    break
        if bad:
            issues.extend({"GAME_ID":game_id,"CODE":c,"DETAIL":d} for c,d in bad)
            continue
        bounds = sorted(set([game_end_sec,0] + g.TIME_IN.astype(int).tolist() + g.TIME_OUT.astype(int).tolist()), reverse=True)
        rows = []
        for start,end in zip(bounds[:-1],bounds[1:]):
            active = g[(g.TIME_IN >= start) & (g.TIME_OUT <= end)]
            players = tuple(sorted(pd.to_numeric(active.PLAYER_ID).astype(int).tolist()))
            if len(players) != 5 or len(set(players)) != 5:
                bad.append(("LINEUP_SIZE",f"{start}->{end}: expected five distinct players, found {len(players)}."))
                continue
            score0, score1 = _snapshot(g,start,True), _snapshot(g,end,False)
            if score0 is None or score1 is None:
                bad.append(("MISSING_SCORE_SNAPSHOT",f"{start}->{end}: missing/conflicting boundary score."))
                continue
            t0,o0 = score0
            t1,o1 = score1
            if min(t0,o0,t1,o1) < 0 or t1 < t0 or o1 < o0:
                bad.append(("INVALID_SCORE",f"{start}->{end}: negative or decreasing score."))
                continue
            first = g.iloc[0]
            rows.append({"GAME_ID":game_id,"SEASON":str(first.SEASON),"GAME_DATE":first.GAME_DATE,
                         "OPPONENT":first.OPPONENT,"TIME_IN":int(start),"TIME_OUT":int(end),
                         "SECONDS_PLAYED":int(start-end),"LINEUP":players,
                         "TEAM_POINT_IN":t0,"TEAM_POINT_OUT":t1,"OPP_POINT_IN":o0,
                         "OPP_POINT_OUT":o1,"REWARD":int((t1-t0)-(o1-o0))})
        if not bad:
            if not rows or rows[0]["TIME_IN"] != game_end_sec or rows[-1]["TIME_OUT"] != 0:
                bad.append(("INCOMPLETE_COVERAGE","Stints do not span full game clock."))
            for left,right in zip(rows[:-1],rows[1:]):
                if left["TIME_OUT"] != right["TIME_IN"]:
                    bad.append(("CLOCK_GAP","Stints are not contiguous."))
                    break
                if (left["TEAM_POINT_OUT"],left["OPP_POINT_OUT"]) != (right["TEAM_POINT_IN"],right["OPP_POINT_IN"]):
                    bad.append(("SCORE_DISCONTINUITY","Adjacent stint scores do not reconcile."))
                    break
            if rows and sum(x["REWARD"] for x in rows) != rows[-1]["TEAM_POINT_OUT"]-rows[-1]["OPP_POINT_OUT"]:
                bad.append(("REWARD_RECONCILIATION","Stint rewards do not equal final point differential."))
        if bad:
            issues.extend({"GAME_ID":game_id,"CODE":c,"DETAIL":d} for c,d in bad)
        else:
            output.extend(rows)
    stints = pd.DataFrame(output)
    issue_frame = pd.DataFrame(issues,columns=["GAME_ID","CODE","DETAIL"])
    return stints, issue_frame


def build_rl_transitions(stints):
    cols = ["GAME_ID","SEASON","SCORE_DIFF","SECONDS_REMAINING","PREVIOUS_LINEUP",
            "ACTION_LINEUP","REWARD","NEXT_SCORE_DIFF","NEXT_SECONDS_REMAINING",
            "NEXT_PREVIOUS_LINEUP","DONE","GAME_DATE"]
    rows = []
    if stints.empty:
        return pd.DataFrame(columns=cols)
    for game_id, game in stints.groupby("GAME_ID",sort=False):
        game = game.sort_values("TIME_IN",ascending=False).reset_index(drop=True)
        for i,row in game.iterrows():
            terminal = i == len(game)-1
            nxt = None if terminal else game.iloc[i+1]
            rows.append({"GAME_ID":game_id,"SEASON":str(row.SEASON),
                "SCORE_DIFF":int(row.TEAM_POINT_IN-row.OPP_POINT_IN),
                "SECONDS_REMAINING":int(row.TIME_IN),
                "PREVIOUS_LINEUP":tuple() if i == 0 else game.iloc[i-1].LINEUP,
                "ACTION_LINEUP":row.LINEUP,"REWARD":int(row.REWARD),
                "NEXT_SCORE_DIFF":int(row.TEAM_POINT_OUT-row.OPP_POINT_OUT),
                "NEXT_SECONDS_REMAINING":int(row.TIME_OUT),
                "NEXT_PREVIOUS_LINEUP":row.LINEUP,"DONE":terminal,"GAME_DATE":row.GAME_DATE})
    return pd.DataFrame(rows,columns=cols)


def build_dataset(minutes, game_end_sec=2160):
    stints, issues = build_stints(minutes,game_end_sec)
    return stints, build_rl_transitions(stints), issues
