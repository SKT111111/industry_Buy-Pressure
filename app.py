import streamlit as st

import pandas as pd
 
st.title("Industry Buy Pressure Dashboard")
 
excel_url = "https://raw.githubusercontent.com/SKT111111/industry_buy_pressure/main/data/integrated_screening_20260211.xlsx%22"
 
try:

    df = pd.read_excel(excel_url)

    st.success("Excel 読み込み成功")

    st.dataframe(df.head(20))

except Exception as e:

    st.error("Excel 読み込み失敗")

    st.code(str(e))

 
