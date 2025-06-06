def get_players_sql():
    sql = """
    SELECT NUMBER,
           FIRST_NAME,
           LAST_NAME,
           YEAR
      FROM PLAYERS
    """
    return sql

def insert_player_sql():
    sql = """
    INSERT INTO PLAYERS (NUMBER,
                         FIRST_NAME,
                         LAST_NAME,
                         YEAR)
    VALUES (?, ?, ?, ?)
    """
    return sql

def delete_player_sql():
    sql = """
    DELETE FROM PLAYERS
     WHERE NUMBER = ? AND YEAR = ?
    """
    return sql

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

def team_shot_chart_sql():
    sql = """
    WITH RAW_DATA AS (
    SELECT PLAYS.GAME_ID,
                PLAYS.PLAYER_ID,
                PLAYS.SHOT_SPOT,
                PLAYS.SHOT_DEFENSE,
                PLAYS.MAKE_MISS,
                PLAYS.PLAY_NUM,
                SPOTS.XSPOT,
                SPOTS.YSPOT,
                SPOTS.OPP_EXPECTED,
                SPOTS.POINTS,
                GAMES.OPPONENT,
                GAMES.LOCATION,
                GAMES.DATE,
                GAMES.SEASON,
                GAMES.OPPONENT || ' ' || GAMES.DATE AS GAME,
                GAMES.OPPONENT || ' -  ' || GAMES.DATE AS U_ID,
                CASE
                        WHEN PLAYS.MAKE_MISS = 'Y'
                            THEN 1
                        ELSE 0
                END AS MAKE,
                CASE
                        WHEN PLAYS.SHOT_DEFENSE = 'HEAVILY_GUARDED'
                            THEN 1
                        ELSE 0
                END AS HEAVILY_GUARDED,
                1 AS ATTEMPT
    FROM PLAYS
    INNER JOIN SPOTS
    ON PLAYS.SHOT_SPOT = SPOTS.SPOT
    INNER JOIN GAMES
        ON GAMES.GAME_ID = PLAYS.GAME_ID
    WHERE PLAYS.SHOT_SPOT != 'FREE_THROW1'
    AND PLAYS.PLAYER_ID != '0'),

    SUMMED_TABLE AS (
    SELECT U_ID,
                    XSPOT,
                    YSPOT,
                    SHOT_SPOT,
                    POINTS,
                    OPPONENT,
                    LOCATION,
                    DATE,
                    SEASON,
                    GAME_ID,
                    SUM(MAKE) AS MAKES,
                    SUM(HEAVILY_GUARDED) HEAVILY_GUARDED,
                    SUM(ATTEMPT) AS ATTEMPTS
        FROM RAW_DATA
        GROUP BY U_ID,
                    XSPOT,
                    YSPOT,
                    SHOT_SPOT,
                    POINTS,
                    OPPONENT,
                    LOCATION,
                    DATE,
                    SEASON,
                    GAME_ID)

    SELECT U_ID,
                    XSPOT,
                    YSPOT,
                    SHOT_SPOT,
                    POINTS,
                    OPPONENT,
                    GAME_ID,
                    LOCATION,
                    DATE,
                    SEASON,
                    MAKES,
                    HEAVILY_GUARDED,
                    ATTEMPTS,
                    CASE
                            WHEN ATTEMPTS = 0
                                THEN 0
                        ELSE CAST(MAKES AS FLOAT) / CAST(ATTEMPTS AS FLOAT)
                    END AS MAKE_PERCENT,
                    CASE
                            WHEN ATTEMPTS = 0
                                THEN 0
                        ELSE CAST(HEAVILY_GUARDED AS FLOAT) / CAST(ATTEMPTS AS FLOAT)
                    END  HG_PERCENT,
                    CASE
                            WHEN ATTEMPTS = 0
                                THEN 0
                        ELSE CAST(POINTS * MAKES AS FLOAT) / CAST(ATTEMPTS AS FLOAT)
                    END  AS POINTS_PER_ATTEMPT
    FROM SUMMED_TABLE
    """
    return sql

def player_shot_chart_sql():
    sql = """
    WITH RAW_DATA AS (
SELECT PLAYS.GAME_ID,
               PLAYS.PLAYER_ID,
              PLAYS.SHOT_SPOT,
              PLAYS.SHOT_DEFENSE,
              PLAYS.MAKE_MISS,
              PLAYS.PLAY_NUM,
              SPOTS.XSPOT,
              SPOTS.YSPOT,
              SPOTS.OPP_EXPECTED,
              SPOTS.POINTS,
              GAMES.OPPONENT,
              GAMES.LOCATION,
              GAMES.DATE,
              GAMES.SEASON,
              PLAYERS.FIRST_NAME || ' ' || PLAYERS.LAST_NAME AS NAME,
              CASE
                    WHEN PLAYS.MAKE_MISS = 'Y'
                           THEN 1
                    ELSE 0
              END AS MAKE,
              CASE
                    WHEN PLAYS.SHOT_DEFENSE = 'HEAVILY_GUARDED'
                           THEN 1
                    ELSE 0
              END AS HEAVILY_GUARDED,
              1 AS ATTEMPT
  FROM PLAYS
  INNER JOIN SPOTS
   ON PLAYS.SHOT_SPOT = SPOTS.SPOT
INNER JOIN GAMES
    ON GAMES.GAME_ID = PLAYS.GAME_ID
INNER JOIN PLAYERS
     ON PLAYERS.YEAR = GAMES.SEASON
  AND PLAYERS.NUMBER = PLAYS.PLAYER_ID
WHERE PLAYS.SHOT_SPOT != 'FREE_THROW1'
AND PLAYS.PLAYER_ID != '0'
AND PLAYERS.YEAR > 2023),

SUMMED_TABLE AS (
  SELECT NAME,
                  XSPOT,
                  YSPOT,
                  SHOT_SPOT,
                  POINTS,
                  SEASON,
                  SUM(MAKE) AS MAKES,
                  SUM(HEAVILY_GUARDED) HEAVILY_GUARDED,
                  SUM(ATTEMPT) AS ATTEMPTS
    FROM RAW_DATA
    GROUP BY NAME,
                  XSPOT,
                  YSPOT,
                  SHOT_SPOT,
                  POINTS,
                  SEASON)

SELECT NAME,
                  XSPOT,
                  YSPOT,
                  SHOT_SPOT,
                  POINTS,
                  SEASON,
                  MAKES,
                  HEAVILY_GUARDED,
                  ATTEMPTS,
                  CASE
                        WHEN ATTEMPTS = 0
                              THEN 0
                       ELSE CAST(MAKES AS FLOAT) / CAST(ATTEMPTS AS FLOAT)
                   END AS MAKE_PERCENT,
                  CASE
                        WHEN ATTEMPTS = 0
                              THEN 0
                       ELSE CAST(HEAVILY_GUARDED AS FLOAT) / CAST(ATTEMPTS AS FLOAT)
                   END  HG_PERCENT,
                  CASE
                        WHEN ATTEMPTS = 0
                              THEN 0
                       ELSE CAST(POINTS * MAKES AS FLOAT) / CAST(ATTEMPTS AS FLOAT)
                   END  AS POINTS_PER_ATTEMPT
  FROM SUMMED_TABLE
  
    """
    return sql

def get_play_by_play_sql():
    sql = """
SELECT PLAYS.GAME_ID,
                PLAYS.PLAYER_ID,
                PLAYS.SHOT_SPOT,
                PLAYS.SHOT_DEFENSE,
                PLAYS.MAKE_MISS,
                PLAYS.PLAY_NUM,
                SPOTS.XSPOT,
                SPOTS.YSPOT,
                SPOTS.OPP_EXPECTED,
                SPOTS.POINTS,
                SPOTS.SPOT,
                GAMES.OPPONENT,
                GAMES.LOCATION,
                GAMES.DATE,
                GAMES.SEASON,
                PLAYERS.YEAR,
                PLAYERS.NUMBER,
                GAMES.OPPONENT 
                || ' - '
                || GAMES.DATE AS LABEL,
                PLAYERS.FIRST_NAME
                || ' ' 
                || PLAYERS.LAST_NAME AS NAME,
                CASE
                  WHEN PLAYS.MAKE_MISS = 'Y'
                    THEN 1
                  ELSE 0
                END AS MAKE,
                1 AS ATTEMPT
FROM PLAYS
INNER JOIN SPOTS
  ON PLAYS.SHOT_SPOT = SPOTS.SPOT
INNER JOIN GAMES
  ON GAMES.GAME_ID = PLAYS.GAME_ID
INNER JOIN PLAYERS
  ON PLAYERS.NUMBER = PLAYS.PLAYER_ID
AND PLAYERS.YEAR = GAMES.SEASON
    """
    return sql