def get_players_sql():
    sql = """
    SELECT NUMBER,
           FIRST_NAME,
           LAST_NAME,
           YEAR
      FROM PLAYERS
    """
    return sql

def get_users():
    sql = """
    SELECT USER_NAME,
           PASSWORD,
           TYPE
      FROM USERS
    """
    return sql

def get_games_sql():
    sql = """
    SELECT GAME_ID,
           OPPONENT,
           LOCATION,
           DATE,
           SEASON
       FROM GAMES
    """
    return sql

def insert_game_summary_sql():
    sql = """
    INSERT INTO GAME_SUMMARY (PLAYER_ID,
                              GAME_ID,
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
                              FOULS)
    VALUES (?,? ,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """
    return sql
def get_shot_spots_sql():
    sql = """
    SELECT SPOT,
           XSPOT,
           YSPOT,
           OPP_EXPECTED,
           POINTS
      FROM SPOTS
    """
    return sql
# Add
def insert_minutes_sql():
    sql = """
    INSERT INTO MINUTES (GAME_ID,
                         PLAYER_ID,
                         TIME_IN,
                         TIME_OUT,
                         TEAM_POINT_IN,
                         TEAM_POINT_OUT,
                         OPP_POINT_IN,
                         OPP_POINT_OUT)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)

    """
    return sql

def update_game_summary_sql():
    sql = """
    UPDATE GAME_SUMMARY
       SET TWO_FGM = ?,
           TWO_FGA = ?,
           THREE_FGM = ?,
           THREE_FGA = ?,
           FTM = ?,
           FTA = ?,
           OFFENSIVE_REBOUNDS = ?,
           DEFENSIVE_REBOUNDS = ?,
           ASSISTS = ?,
           STEALS = ?,
           BLOCKS = ?,
           TURNOVER = ?,
           FOULS = ?
        WHERE PLAYER_ID = ?
            AND GAME_ID = ?
    """
    return sql

def get_player_game_sql():
    sql = """
    SELECT PLAYERS.NUMBER || ' - ' || PLAYERS.LAST_NAME AS PLAYER_LABEL,
                GAMES.OPPONENT || ' - ' || GAMES.DATE AS GAME_LABEL,
                PLAYERS.NUMBER,
                PLAYERS.FIRST_NAME,
                PLAYERS.LAST_NAME,
                PLAYERS.YEAR,
                GAMES.GAME_ID,
                GAMES.OPPONENT,
                GAMES.LOCATION,
                GAMES.DATE,
                GAMES.SEASON
  FROM PLAYERS
INNER JOIN GAMES
  ON GAMES.SEASON = PLAYERS.YEAR
    """
    return sql

def get_play_sql():
    sql = """
SELECT SPOTS.SPOT,
               PLAYS.SHOT_DEFENSE,
               PLAYS.MAKE_MISS,
               PLAYS.PLAY_NUM,
              COALESCE(PLAYS.SPOT_X, SPOTS.XSPOT) AS XSPOT,
              COALESCE(PLAYS.SPOT_Y, SPOTS.YSPOT) AS YSPOT,
              SPOTS.OPP_EXPECTED,
              SPOTS.POINTS,
              GAMES.GAME_ID,
              GAMES.OPPONENT,
              GAMES.LOCATION,
              GAMES.DATE,
              GAMES.SEASON,
              PLAYERS.NUMBER,
              PLAYERS.FIRST_NAME,
              PLAYERS.LAST_NAME,
              PLAYERS.YEAR,
              GAMES.OPPONENT || ' - ' || GAMES.DATE AS GAME_LABEL,
              PLAYERS.NUMBER || ' - ' || PLAYERS.FIRST_NAME AS PLAYER_LABEL
  FROM PLAYS
  INNER JOIN SPOTS
  ON SPOTS.SPOT = PLAYS.SHOT_SPOT
  INNER JOIN GAMES
  ON GAMES.GAME_ID = PLAYS.GAME_ID
  INNER JOIN PLAYERS
  ON PLAYERS.NUMBER = PLAYS.PLAYER_ID
  AND GAMES.SEASON = PLAYERS.YEAR
  WHERE GAMES.OPPONENT || ' - ' || GAMES.DATE = '?'
  """
    return sql


def get_game_stats_sql():
    sql = """
    SELECT *
      FROM GAME_SUMMARY
    """
    return sql

def insert_plays_sql():
    sql = """
    INSERT INTO PLAYS (GAME_ID,
                       PLAYER_ID,
                       SHOT_SPOT,
                       SHOT_DEFENSE,
                       MAKE_MISS,
                       PLAY_NUM,
                       SPOT_X,
                       SPOT_Y,
                       PAINT_TOUCH)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    return sql

def get_formatted_game_sql():
    sql = """
    SELECT GAME_ID,
                    PLAYER_ID,
                    SUM(CASE WHEN STAT = 'TWO_FGM' THEN 1 ELSE 0 END) AS TWO_FGM,
      SUM(CASE WHEN STAT = 'TWO_FGA' THEN 1 ELSE 0 END) AS TWO_FGA,
      SUM(CASE WHEN STAT = 'THREE_FGM' THEN 1 ELSE 0 END) AS THREE_FGM,
      SUM(CASE WHEN STAT = 'THREE_FGA' THEN 1 ELSE 0 END) AS THREE_FGA,
    SUM(CASE WHEN STAT = 'FTM' THEN 1 ELSE 0 END) AS FTM,
      SUM(CASE WHEN STAT = 'FTA' THEN 1 ELSE 0 END) AS FTA,
      SUM(CASE WHEN STAT = 'OFFENSIVE_REBOUNDS' THEN 1 ELSE 0 END) AS OFFENSIVE_REBOUNDS,
      SUM(CASE WHEN STAT = 'DEFENSIVE_REBOUNDS' THEN 1 ELSE 0 END) AS DEFENSIVE_REBOUNDS,
      SUM(CASE WHEN STAT = 'ASSISTS' THEN 1 ELSE 0 END) AS ASSISTS,
      SUM(CASE WHEN STAT = 'STEALS' THEN 1 ELSE 0 END) AS STEALS,
      SUM(CASE WHEN STAT = 'BLOCKS' THEN 1 ELSE 0 END) AS BLOCKS,
      SUM(CASE WHEN STAT = 'TURNOVER' THEN 1 ELSE 0 END) AS TURNOVER,
      SUM(CASE WHEN STAT = 'FOULS' THEN 1 ELSE 0 END) AS FOULS
      FROM GAME_STATS_PLAYS
      WHERE GAME_ID = this_game_id
      AND PLAYER_ID = this_player_id
    GROUP BY GAME_ID, PLAYER_ID
    """
    return sql

def select_quick_game_info(game_id):
    sql = f"""
    SELECT *
      FROM TEAM_GAME_TOTALS
      WHERE GAME_ID = {game_id}
    """
    return sql

def view_minutes_sql():
    sql = """
    SELECT MINUTES.PLAYER_ID,
                    MINUTES.GAME_ID,
                    MINUTES.TIME_IN,
                    MINUTES.TIME_OUT,
                    MINUTES.TEAM_POINT_IN,
                    MINUTES.TEAM_POINT_OUT,
                    MINUTES.OPP_POINT_IN,
                    MINUTES.OPP_POINT_OUT,
                    GAMES.OPPONENT || ' - ' || GAMES.DATE AS GAME_DATE,
                    PLAYERS.FIRST_NAME || ' ' || PLAYERS.LAST_NAME AS PLAYER_NAME,
                    GAMES.SEASON
      FROM MINUTES
      INNER JOIN GAMES
         ON GAMES.GAME_ID = MINUTES.GAME_ID
      INNER JOIN PLAYERS
         ON PLAYERS.NUMBER = MINUTES.PLAYER_ID
         AND PLAYERS.YEAR = GAMES.SEASON
    """
    return sql

def insert_game_play():
    sql = """
    INSERT INTO GAME_STATS_PLAYS (GAME_ID, PLAYER_ID, STAT)
    VALUES (?, ?, ?)
    """
    return sql

def insert_game_sql():
    sql = """
    INSERT INTO GAMES (GAME_ID,
                       OPPONENT,
                       LOCATION,
                       DATE,
                       SEASON)
    VALUES (?, ?, ?, ?, ?)
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

def delete_game_sql():
    sql = """
    DELETE FROM GAMES
     WHERE GAME_ID = ?
    """
    return sql

def get_this_game():
    sql = """
    SELECT *
      FROM TEAM_GAME_TOTALS
      WHERE GAME_ID = ?
    """
    return sql

def get_game_summary_sql():
    sql = """
          WITH AVG_MINUTES AS (
              SELECT MINUTES_PLAYED.PLAYER_ID,
                              AVG(MINUTES_PLAYED.MINUTES_PLAYED) AS AVG_MIN_PLAYED,
                              PLAYERS.YEAR
                    FROM MINUTES_PLAYED
                    INNER JOIN GAMES
                      ON GAMES.GAME_ID = MINUTES_PLAYED.GAME_ID
                    INNER JOIN PLAYERS
                      ON PLAYERS.NUMBER = MINUTES_PLAYED.PLAYER_ID
                      AND PLAYERS.YEAR = GAMES.SEASON
                  GROUP BY MINUTES_PLAYED.PLAYER_ID, PLAYERS.YEAR
          )

          SELECT GAME_SUMMARY.PLAYER_ID,
                 GAME_SUMMARY.GAME_ID,
                 GAME_SUMMARY.TWO_FGM,
                 GAME_SUMMARY.TWO_FGA,
                 GAME_SUMMARY.THREE_FGM,
                 GAME_SUMMARY.THREE_FGA,
                 GAME_SUMMARY.FTM,
                 GAME_SUMMARY.FTA,
                 GAME_SUMMARY.OFFENSIVE_REBOUNDS,
                 GAME_SUMMARY.DEFENSIVE_REBOUNDS,
                 GAME_SUMMARY.ASSISTS,
                 GAME_SUMMARY.STEALS,
                 GAME_SUMMARY.BLOCKS,
                 GAME_SUMMARY.TURNOVER,
                 COALESCE(GAME_SUMMARY.FOULS, 0) AS FOULS,
                 GAME_SUMMARY.TWO_FGA  
                 + GAME_SUMMARY.THREE_FGA AS FGA,
                 GAME_SUMMARY.TWO_FGM 
                 + GAME_SUMMARY.THREE_FGM AS FGM,
                 ((2*GAME_SUMMARY.TWO_FGM) 
                 + (3*GAME_SUMMARY.THREE_FGM) 
                 + GAME_SUMMARY.FTM) AS POINTS,
                 (((2*GAME_SUMMARY.TWO_FGM) + (3*GAME_SUMMARY.THREE_FGM) + FTM) -- Points
                  + (0.4*(GAME_SUMMARY.TWO_FGM  + GAME_SUMMARY.THREE_FGM)) --  + .4*FGM
                  - (0.7*(GAME_SUMMARY.TWO_FGA+GAME_SUMMARY.THREE_FGA)) -- -.7*FGA
                  - (0.4*(GAME_SUMMARY.FTA-FTM)) -- -.4*FTs missed
                  + (0.7*GAME_SUMMARY.OFFENSIVE_REBOUNDS) -- +.7*ORB
                  + (0.3*GAME_SUMMARY.DEFENSIVE_REBOUNDS) -- +.3*DRB
                  + GAME_SUMMARY.STEALS -- + Steals
                  + (0.7*GAME_SUMMARY.ASSISTS) -- + .7*Assists
                  + (0.7*GAME_SUMMARY.BLOCKS) -- + .7*Blocks
                  - (0.4*(COALESCE(GAME_SUMMARY.FOULS, 0))) -- -.4*Fouls
                   - GAME_SUMMARY.TURNOVER)  AS GAME_SCORE, -- -TOs
                   GAMES.OPPONENT,
                   GAMES.LOCATION,
                   GAMES.DATE,
                   GAMES.SEASON,
                   GAMES.OPPONENT || '  -  ' || GAMES.DATE AS LABEL,
                   PLAYERS.NUMBER,
                   PLAYERS.FIRST_NAME,
                   PLAYERS.LAST_NAME,
                   PLAYERS.YEAR,
                   PLAYERS.FIRST_NAME || ' ' || PLAYERS.LAST_NAME AS NAME,
                   COALESCE(MINUTES_PLAYED.MINUTES_PLAYED, AVG_MINUTES.AVG_MIN_PLAYED, 0) AS MINUTES_PLAYED
            FROM GAME_SUMMARY
            INNER JOIN GAMES
              ON GAMES.GAME_ID = GAME_SUMMARY.GAME_ID
            INNER JOIN PLAYERS
              ON PLAYERS.NUMBER = GAME_SUMMARY.PLAYER_ID
              AND PLAYERS.YEAR = GAMES.SEASON
            AND PLAYERS.NUMBER != '0'
          LEFT JOIN MINUTES_PLAYED
              ON GAMES.GAME_ID = MINUTES_PLAYED.GAME_ID
              AND PLAYERS.NUMBER = MINUTES_PLAYED.PLAYER_ID
          LEFT JOIN AVG_MINUTES
            ON AVG_MINUTES.PLAYER_ID = GAME_SUMMARY.PLAYER_ID
            AND AVG_MINUTES.YEAR = PLAYERS.YEAR
    """
    return sql

def team_shot_chart_sql():
    sql = """
    WITH RAW_DATA AS (
    SELECT PLAYS.GAME_ID,
                PLAYS.PLAYER_ID,
                PLAYS.SHOT_SPOT,
                CASE
                  WHEN PLAYS.SHOT_DEFENSE = 'Open'
                    THEN 'OPEN'
                  WHEN PLAYS.SHOT_DEFENSE = 'Guarded'
                    THEN 'GUARDED'
                  WHEN PLAYS.SHOT_DEFENSE = 'Heavily Guarded'
                    THEN 'HEAVILY_GUARDED'
                  ELSE PLAYS.SHOT_DEFENSE
                END AS SHOT_DEFENSE,
                PLAYS.MAKE_MISS,
                PLAYS.PLAY_NUM,
                COALESCE(PLAYS.PAINT_TOUCH, 'N') AS PAINT_TOUCH,
                COALESCE(PLAYS.SPOT_X, SPOTS.XSPOT) AS XSPOT,
                COALESCE(PLAYS.SPOT_Y, SPOTS.YSPOT) AS YSPOT,
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
    WHERE PLAYS.PLAYER_ID != '0'),

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
                    PAINT_TOUCH,
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
                    GAME_ID,
                    PAINT_TOUCH)

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
                    PAINT_TOUCH,
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

def opp_shot_chart_sql():
    sql = """
    WITH RAW_DATA AS (
    SELECT PLAYS.GAME_ID,
                PLAYS.PLAYER_ID,
                PLAYS.SHOT_SPOT,
                CASE
                  WHEN PLAYS.SHOT_DEFENSE = 'Open'
                    THEN 'OPEN'
                  WHEN PLAYS.SHOT_DEFENSE = 'Guarded'
                    THEN 'GUARDED'
                  WHEN PLAYS.SHOT_DEFENSE = 'Heavily Guarded'
                    THEN 'HEAVILY_GUARDED'
                  ELSE PLAYS.SHOT_DEFENSE
                END AS SHOT_DEFENSE,
                PLAYS.MAKE_MISS,
                PLAYS.PLAY_NUM,
                COALESCE(PLAYS.PAINT_TOUCH, 'N') AS PAINT_TOUCH,
                COALESCE(PLAYS.SPOT_X, SPOTS.XSPOT) AS XSPOT,
                COALESCE(PLAYS.SPOT_Y, SPOTS.YSPOT) AS YSPOT,
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
    WHERE PLAYS.PLAYER_ID = '0'),

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
                    PAINT_TOUCH,
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
                    GAME_ID,
                    PAINT_TOUCH)

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
                    PAINT_TOUCH,
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
                CASE
                  WHEN PLAYS.SHOT_DEFENSE = 'Open'
                    THEN 'OPEN'
                  WHEN PLAYS.SHOT_DEFENSE = 'Guarded'
                    THEN 'GUARDED'
                  WHEN PLAYS.SHOT_DEFENSE = 'Heavily Guarded'
                    THEN 'HEAVILY_GUARDED'
                  ELSE PLAYS.SHOT_DEFENSE
                END AS SHOT_DEFENSE,
              PLAYS.MAKE_MISS,
              PLAYS.PLAY_NUM,
              COALESCE(PLAYS.SPOT_X, SPOTS.XSPOT) AS XSPOT,
              COALESCE(PLAYS.SPOT_Y, SPOTS.YSPOT) AS YSPOT,
              SPOTS.OPP_EXPECTED,
              SPOTS.POINTS,
              GAMES.OPPONENT,
              GAMES.LOCATION,
              GAMES.OPPONENT || ' ' || GAMES.DATE AS GAME,
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
--AND PLAYS.PLAYER_ID != '0'
AND PLAYERS.YEAR > 2023),

SUMMED_TABLE AS (
  SELECT NAME,
                  XSPOT,
                  YSPOT,
                  SHOT_SPOT,
                  POINTS,
                  SEASON,
                  GAME,
                  SUM(MAKE) AS MAKES,
                  SUM(HEAVILY_GUARDED) HEAVILY_GUARDED,
                  SUM(ATTEMPT) AS ATTEMPTS
    FROM RAW_DATA
    GROUP BY NAME,
                  XSPOT,
                  YSPOT,
                  SHOT_SPOT,
                  POINTS,
                  GAME,
                  SEASON)

SELECT NAME,
                  XSPOT,
                  YSPOT,
                  SHOT_SPOT,
                  POINTS,
                  SEASON,
                  GAME,
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

def player_grouped_shot_chart_sql():
    sql = """
    WITH RAW_DATA AS (
SELECT PLAYS.GAME_ID,
               PLAYS.PLAYER_ID,
              PLAYS.SHOT_SPOT,
                CASE
                  WHEN PLAYS.SHOT_DEFENSE = 'Open'
                    THEN 'OPEN'
                  WHEN PLAYS.SHOT_DEFENSE = 'Guarded'
                    THEN 'GUARDED'
                  WHEN PLAYS.SHOT_DEFENSE = 'Heavily Guarded'
                    THEN 'HEAVILY_GUARDED'
                  ELSE PLAYS.SHOT_DEFENSE
                END AS SHOT_DEFENSE,
              PLAYS.MAKE_MISS,
              PLAYS.PLAY_NUM,
              SPOTS.OPP_EXPECTED,
              SPOTS.POINTS,
              GAMES.OPPONENT,
              GAMES.LOCATION,
              GAMES.DATE,
              GAMES.SEASON,
              PLAYERS.FIRST_NAME || ' ' || PLAYERS.LAST_NAME AS NAME,
              GAMES.OPPONENT || ' ' || GAMES.DATE AS GAME,
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
--AND PLAYS.PLAYER_ID != '0'
AND PLAYERS.YEAR > 2023),

SUMMED_TABLE AS (
  SELECT NAME,
                
                  SHOT_SPOT,
                  POINTS,
                  SEASON,
                  GAME,
                  SUM(MAKE) AS MAKES,
                  SUM(HEAVILY_GUARDED) HEAVILY_GUARDED,
                  SUM(ATTEMPT) AS ATTEMPTS
    FROM RAW_DATA
    GROUP BY NAME,
                  SHOT_SPOT,
                  POINTS,
                  SEASON,
                  GAME)

SELECT NAME,
                
                  SHOT_SPOT,
                  POINTS,
                  SEASON,
                  MAKES,
                  HEAVILY_GUARDED,
                  ATTEMPTS,
                  GAME,
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
                CASE
                  WHEN PLAYS.SHOT_DEFENSE = 'Open'
                    THEN 'OPEN'
                  WHEN PLAYS.SHOT_DEFENSE = 'Guarded'
                    THEN 'GUARDED'
                  WHEN PLAYS.SHOT_DEFENSE = 'Heavily Guarded'
                    THEN 'HEAVILY_GUARDED'
                  ELSE PLAYS.SHOT_DEFENSE
                END AS SHOT_DEFENSE,
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


def delete_shot():
    sql = """
    DELETE FROM PLAYS
     WHERE GAME_ID = ? AND PLAY_NUM = ? AND PLAYER_ID = ?
    """
    return sql