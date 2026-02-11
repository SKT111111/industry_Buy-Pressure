import streamlit as st
import pandas as pd
import requests
from io import BytesIO
 
st.title("Industry Buy Pressure Dashboard")
 
excel_url = "https://raw.githubusercontent.com/SKT111111/industry_Buy-Pressure/main/data/industry_etf_multicondition_20260211_001951.xlsx"
 
try:
    r = requests.get(excel_url)
    r.raise_for_status()
    file = BytesIO(r.content)
    df = pd.read_excel(file)
 
    st.success("Excel 読み込み成功")
    st.dataframe(df.head(20))
 
except Exception as e:
    st.error("Excel 読み込み失敗")
    st.code(str(e))
 
