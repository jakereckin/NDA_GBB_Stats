import pandas as pd
import sqlite3 as sql
import os


def create_db():
    conn = sql.connect(r'C:\Users\Jake\Documents\GitHub\NDA_GBB_Stats\NDA_BB.db', 
                       check_same_thread=False
    )
    #conn = sql.connect(r'C:\Users\Jake\Documents\GitHub\Katelyn_School_DP\kmo13.db',
    #                    check_same_thread=False)
    return conn

def close_db(conn):
    conn.close()
    return None

def create_players(conn):
    cursor = conn.cursor()
    CREATE = """ CREATE TABLE IF NOT EXISTS PLAYERS (
        NUMBER VARCHAR(255) NOT NULL,
        FIRST_NAME VARCHAR(255) NOT NULL,
        LAST_NAME VARCHAR(255) NOT NULL)
    """
    cursor.execute(CREATE)
    conn.commit()
    cursor.close()
    return None

def create_games(conn):
    cursor = conn.cursor()
    CREATE = """ CREATE TABLE IF NOT EXISTS GAMES (
        GAME_ID VARCHAR(255) NOT NULL,
        OPPONENT VARCHAR(25) NOT NULL
    )
    """
    cursor.execute(CREATE)
    conn.commit()
    cursor.close()
    return None

def create_player_shot(conn):
    cursor = conn.cursor()
    CREATE = """ CREATE TABLE IF NOT EXISTS GAME_SHOT (
        GAME_ID VARCHAR(255) NOT NULL,
        PLAYER_ID VARCHAR(255) NOT NULL,
        SHOT_SPOT VARCHAR(255) NOT NULL,
        MAKE_MISS VARCHAR(25) NOT NULL
    )
    """
    cursor.execute(CREATE)
    conn.commit()
    cursor.close()
    return None

def create_shot_spots(conn):
    cursor = conn.cursor()
    CREATE = """ CREATE TABLE IF NOT EXISTS SPOT (
        SPOT VARCHAR(255) NOT NULL
    )
    """
    cursor.execute(CREATE)
    conn.commit()
    cursor.close()
    return None

def drop_players(conn):
    cursor = conn.cursor()
    DROP = """ 
    DROP TABLE PLAYERS;
    """
    cursor.execute(DROP)
    conn.commit()
    cursor.close()
    return None

def drop_games(conn):
    cursor = conn.cursor()
    DROP = """ 
    DROP TABLE GAMES;
    """
    cursor.execute(DROP)
    conn.commit()
    cursor.close()
    return None

def drop_spots(conn):
    cursor = conn.cursor()
    DROP = """ 
    DROP TABLE SPOT;
    """
    cursor.execute(DROP)
    conn.commit()
    cursor.close()
    return None

def drop_shot_game(conn):
    cursor = conn.cursor()
    DROP = """ 
    DROP TABLE GAME_SHOT;
    """
    cursor.execute(DROP)
    conn.commit()
    cursor.close()
    return None

def insert_players(conn, data):
    cursor = conn.cursor()
    INSERT_PLAYER = """ INSERT INTO PLAYERS VALUES (?, ?, ?)"""
    cursor.executemany(INSERT_PLAYER, data)
    conn.commit()
    cursor.close()
    return None

def insert_games(conn, data):
    cursor = conn.cursor()
    INSERT_GAMES = """ INSERT INTO GAMES VALUES(?, ?) """
    cursor.executemany(INSERT_GAMES, data)
    conn.commit()
    cursor.close()
    return None

def insert_games(conn, data):
    cursor = conn.cursor()
    GAME_SHOT = """ INSERT INTO GAME_SHOT VALUES(?, ?, ?, ?) """
    cursor.executemany(GAME_SHOT, data)
    conn.commit()
    cursor.close()
    return None

def insert_spot(conn, data):
    cursor = conn.cursor()
    INSERT_SPOT = """ INSERT INTO SPOT VALUES(?) """
    cursor.executemany(INSERT_SPOT, data)
    conn.commit()
    cursor.close()
    return None

def select_players(conn):
    SELECT = "SELECT * FROM PLAYERS"
    df = pd.read_sql_query(SELECT, conn)
    return df

def select_games(conn):
    SELECT = """ 
    SELECT *
       FROM GAMES
    """
    df = pd.read_sql_query(SELECT, conn)
    return df

def select_spot(conn):
    SELECT = """ 
    SELECT *
       FROM SPOT
    """
    df = pd.read_sql_query(SELECT, conn)
    return df

def select_game_shot(conn):
    SELECT = """ 
    SELECT *
       FROM GAME_SHOT
    """
    df = pd.read_sql_query(SELECT, conn)
    return df