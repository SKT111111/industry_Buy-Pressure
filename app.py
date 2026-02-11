import streamlit as st

import pandas as pd
 
st.title("Industry Buy Pressure Dashboard")
 
excel_url = "https://raw.githubusercontent.com/ユーザー名/industry_buy_pressure/main/data/integrated_screening_20260211.xlsx%22
 
df = pd.read_excel(excel_url)
 
st.write("データプレビュー")

st.dataframe(df.head(20))

 
