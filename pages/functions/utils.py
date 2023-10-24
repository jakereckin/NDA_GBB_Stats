import pandas as pd
import sqlite3 as sql
import os
import smtplib
import ssl 
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
import base64
from email.mime.base import MIMEBase
import mimetypes
from email import encoders

def create_db():
    if os.path.exists(r'C:\Users\Jake\Documents\GitHub\NDA_GBB_Stats'):
        conn = sql.connect(r'C:\Users\Jake\Documents\GitHub\NDA_GBB_Stats\NDA_BB.db', 
                           check_same_thread=False
        )
    else:
        conn = sql.connect('NDA_BB.db', 
                           check_same_thread=False
        )
    return conn

def close_db(conn):
    conn.close()
    return None

def create_game_summary(conn):
    cursor = conn.cursor()
    CREATE = """ CREATE TABLE IF NOT EXISTS GAME_SUMMARY_STATS (
    PLAYER_ID VARCHAR(255) NOT NULL,
    GAME_ID VARCHAR(255) NOT NULL,
    TWO_FGA INTEGER NOT NULL,
    TWO_FGM INTEGER NOT NULL,
    THREE_FGA INTEGER NOT NULL,
    THREE_FGM INTEGER NOT NULL,
    FTA INTEGER NOT NULL,
    FTM INTEGER NOT NULL,
    ASSITS INTEGER NOT NULL,
    TURNOVER INTEGER NOT NULL,
    OFFENSIVE_REBOUNDS INTEGER NOT NULL,
    DEFENSIVE_REBOUNDS INTEGER NOT NULL,
    BLOCKS INTEGER NOT NULL,
    STEALS INTEGER NOT NULL,
    PRIMARY KEY (PLAYER_ID, GAME_ID)
    )"""
    cursor.execute(CREATE)
    conn.commit()
    cursor.close()
    return None

def create_players(conn):
    cursor = conn.cursor()
    CREATE = """ CREATE TABLE IF NOT EXISTS PLAYERS (
        NUMBER VARCHAR(255) NOT NULL,
        FIRST_NAME VARCHAR(255) NOT NULL,
        LAST_NAME VARCHAR(255) NOT NULL,
        YEAR VARCHAR(255) NOT NULL
        )
    """
    cursor.execute(CREATE)
    conn.commit()
    cursor.close()
    return None

def create_games(conn):
    cursor = conn.cursor()
    CREATE = """ CREATE TABLE IF NOT EXISTS GAMES (
        GAME_ID VARCHAR(255) NOT NULL,
        OPPONENT VARCHAR(255) NOT NULL,
        LOCATION VARCHAR(255) NOT NULL,
        DATE VARCHAR(255) NOT NULL,
        SEASON VARCHAR(255) NOT NULL
    )
    """
    cursor.execute(CREATE)
    conn.commit()
    cursor.close()
    return None

def create_event(conn):
    cursor = conn.cursor()
    CREATE = """ CREATE TABLE IF NOT EXISTS PLAY_EVENT (
        GAME_ID VARCHAR(255) NOT NULL,
        PLAYER_ID VARCHAR(255) NOT NULL,
        TIME VARCHAR(255) NOT NULL,
        HALF VARCHAR(25) NOT NULL,
        EVENT_TYPE VARCHAR(255) NOT NULL,
        TEAM_SCORE VARCHAR(255) NOT NULL,
        OPPONENT_SCORE VARCHAR(255) NOT NULL,
        SHOT_SPOT VARCHAR(255),
        SHOT_DEFENSE VARCHAR(255),
        MAKE_MISS VARCHAR(25)
    )
    """
    cursor.execute(CREATE)
    conn.commit()
    cursor.close()
    return None

def create_shot_spots(conn):
    cursor = conn.cursor()
    CREATE = """ CREATE TABLE IF NOT EXISTS SPOT (
        SPOT VARCHAR(255) NOT NULL,
        XSPOT INTEGER NOT NULL,
        YSPOT INTEGER NOT NULL
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

def drop_event(conn):
    cursor = conn.cursor()
    DROP = """ 
    DROP TABLE PLAY_EVENT;
    """
    cursor.execute(DROP)
    conn.commit()
    cursor.close()
    return None

def insert_game_data (conn, data):
    cursor = conn.cursor()
    INSERT_DATA = """ INSERT OR REPLACE INTO GAME_SUMMARY_STATS VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
    cursor.executemany(INSERT_DATA, data)
    conn.commit()
    cursor.close()
    return None

def drop_game_summary(conn):
    cursor = conn.cursor()
    DROP = """ 
    DROP TABLE GAME_SUMMARY_STATS;
    """
    cursor.execute(DROP)
    conn.commit()
    cursor.close()
    return None

def insert_players(conn, data):
    cursor = conn.cursor()
    INSERT_PLAYER = """ INSERT INTO PLAYERS VALUES (?, ?, ?, ?)"""
    cursor.executemany(INSERT_PLAYER, data)
    conn.commit()
    cursor.close()
    return None

def insert_games(conn, data):
    cursor = conn.cursor()
    INSERT_GAMES = """ INSERT INTO GAMES VALUES(?, ?, ?, ?, ? ) """
    cursor.executemany(INSERT_GAMES, data)
    conn.commit()
    cursor.close()
    return None

def insert_spot(conn, data):
    cursor = conn.cursor()
    INSERT_SPOT = """ INSERT INTO SPOT VALUES(?, ?, ?) """
    cursor.executemany(INSERT_SPOT, data)
    conn.commit()
    cursor.close()
    return None

def insert_event(conn, data):
    cursor = conn.cursor()
    GAME_SHOT = """ INSERT INTO PLAY_EVENT VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?) """
    cursor.executemany(GAME_SHOT, data)
    conn.commit()
    cursor.close()
    return None

def select_game_summary(conn):
    SELECT = "SELECT * FROM GAME_SUMMARY_STATS"
    df = pd.read_sql_query(SELECT, conn)
    return df

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
    SELECT GAMES.OPPONENT + ' ' + GAMES.DATE AS GAME,
           GAMES.GAME_ID,
           PLAY_EVENT.GAME_ID AS T_ID,
           GAMES.OPPONENT,
           GAMES.DATE,
           PLAYER_ID,
           SHOT_SPOT,
           CASE
             WHEN MAKE_MISS = 'Y'
               THEN 1
             ELSE 0
           END AS MAKE,
           1 AS ATTEMPT,
           SPOT.XSPOT,
           SPOT.YSPOT
       FROM PLAY_EVENT
       INNER JOIN SPOT
         ON SPOT.SPOT = PLAY_EVENT.SHOT_SPOT
       INNER JOIN GAMES 
         ON GAMES.GAME_ID = PLAY_EVENT.GAME_ID
       WHERE PLAY_EVENT.EVENT_TYPE = 'SHOT_ATTEMPT'
    """
    df = pd.read_sql_query(SELECT, conn)
    return df

def my_email(password):
    ctype, encoding = mimetypes.guess_type('NDA_BB.db')
    maintype, subtype = ctype.split('/', 1)
    msg = MIMEMultipart()
    msg['From'] = 'jjrekn@gmail.com'
    msg['To'] = 'jjrekn@gmail.com'
    msg['Subject'] = 'Homework Submission'
    fp = open('NDA_BB.db', 'rb')
    part = MIMEBase(maintype, subtype)
    part.set_payload(fp.read())
    fp.close()
    # Encode the payload using Base64
    encoders.encode_base64(part)
    part.set_payload(part.get_payload().decode())
        
    part.add_header('Content-Disposition', 'attachment', filename='NDA_BB.db')
    msg.attach(part)

    with smtplib.SMTP('smtp.gmail.com', 587) as e:
        e.ehlo()
        e.starttls(context=ssl.create_default_context())
        e.login('jjrekn@gmail.com', password=password.strip())
        e.sendmail('jjrekn@gmail.com', 'jjrekn@gmail.com', msg.as_string())
    return None