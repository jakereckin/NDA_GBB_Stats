import pandas as pd
import sqlite3 as sql
import os

def create_db():
    if os.path.exists(r'C:\Users\Jake\Documents\GitHub\NDA_GBB_Stats'):
        return r'C:\Users\Jake\Documents\GitHub\NDA_GBB_Stats\NDA_BB.db'
    else:
        return 'NDA_BB.db'