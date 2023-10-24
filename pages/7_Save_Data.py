import streamlit as st
import datetime as dt
import sys
import time
import sys
import numpy as np
import os
import pandas as pd
sys.path.insert(1, os.path.dirname(os.path.abspath(__file__)))
from functions import utils as ut

with open("NDA_BB.db", "rb") as fp:
    btn = st.download_button(
        label="Download DB File",
        data=fp,
        file_name="NDA_BB.db",
        mime="application/octet-stream"
    )
    if btn:
        ut.my_email(st.secrets['email_password'])