def get_game_summary_sql():
    sql = """
SELECT PLAYER_ID,
               GAME_SUMMARY.GAME_ID,
               TWO_FGM,
              TWO_FGA,
              THREE_FGM,
              THREE_FGA,
              FTM,
              FTA,
              OFFENSIVE_REBOUNDS,
              DEFENSIVE_REBOUNDS,
              ASSISTS,
              STEALS,
              BLOCKS,
              TURNOVER,
              TWO_FGA  + THREE_FGA AS FGA,
              TWO_FGM + THREE_FGM AS FGM,
              ((2*TWO_FGM) + (3*THREE_FGM) + FTM) AS POINTS,
             (((2*TWO_FGM) + (3*THREE_FGM) + FTM)
              + (0.4*(TWO_FGA  + THREE_FGA))
              - (0.7*(TWO_FGA+THREE_FGA))
              -(0.4*(FTA-FTM))
              + (0.7*OFFENSIVE_REBOUNDS)
              +(0.3*(DEFENSIVE_REBOUNDS))
              +(STEALS)
              +(0.7*(ASSISTS))
             +(0.7*(BLOCKS))
              - (TURNOVER)) AS GAME_SCORE,
                OPPONENT,
                LOCATION,
                DATE,
                SEASON,
                OPPONENT || '  -  ' || DATE AS LABEL,
               NUMBER,
           FIRST_NAME,
           LAST_NAME,
           YEAR,
           FIRST_NAME || ' ' || LAST_NAME AS NAME
  FROM GAME_SUMMARY
  INNER JOIN GAMES
    ON GAMES.GAME_ID = GAME_SUMMARY.GAME_ID
  INNER JOIN PLAYERS
    ON PLAYERS.NUMBER = GAME_SUMMARY.PLAYER_ID
    AND PLAYERS.YEAR = GAMES.SEASON
  AND PLAYERS.NUMBER != '0'
    """
    return sql

def get_player_sql():
    sql = """
    SELECT NUMBER,
           FIRST_NAME,
           LAST_NAME,
           YEAR,
           FIRST_NAME || ' ' || LAST_NAME AS NAME
      FROM PLAYERS
    """
    return sql

def get_player_no_opp_sql():
    sql = """
    SELECT NUMBER,
           FIRST_NAME,
           LAST_NAME,
           YEAR,
           FIRST_NAME || ' ' || LAST_NAME AS NAME
      FROM PLAYERS
      WHERE NUMBER != 0
    """
    return sql

def get_games_sql():
    sql = """
    SELECT  GAME_ID,
                    OPPONENT,
                    LOCATION,
                    DATE,
                    SEASON,
                    OPPONENT || '  -  ' || DATE AS LABEL
    FROM GAMES
    """
    return sql
