import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
import numpy as np

# ページ設定
st.set_page_config(
    page_title="Industry Buy Pressure Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🔥 Industry Buy Pressure Dashboard")
st.markdown("---")

# Buy Pressure に応じた色を返す関数（緑→黄→赤のグラデーション）
def get_color_from_buy_pressure(buy_pressure):
    """Buy Pressureに基づいて色を返す（0=赤、0.5=黄、1=緑）"""
    if pd.isna(buy_pressure):
        return "#808080"  # グレー
    
    normalized = max(0.0, min(1.0, buy_pressure))
    
    if normalized >= 0.5:
        ratio = (normalized - 0.5) * 2
        r = int(255 * (1 - ratio))
        g = 255
        b = 0
    else:
        ratio = normalized * 2
        r = 255
        g = int(255 * ratio)
        b = 0
    
    return f"#{r:02x}{g:02x}{b:02x}"

# Buy Pressure のステータス判定関数
def get_buy_pressure_status(buy_pressure):
    """Buy Pressureに基づいてステータスを返す"""
    if buy_pressure > 0.667:
        return "🔥 EXTREME"
    elif buy_pressure > 0.60:
        return "🚀 STRONG"
    elif buy_pressure > 0.55:
        return "📈 BUY"
    elif buy_pressure < 0.333:
        return "💀 WEAK"
    elif buy_pressure < 0.45:
        return "⚠️ CAUTION"
    else:
        return "➖ NEUTRAL"

# データ読み込み関数
@st.cache_data
def load_data():
    """エクセルファイルからデータを読み込む"""
    
    file1_path = 'data/industry_etf_multicondition_20260211_001951.xlsx'
    df_industry_raw = pd.read_excel(file1_path, sheet_name='Multi_Condition_Passed')
    
    header_row = df_industry_raw[df_industry_raw.iloc[:, 0] == 'Industry'].index[0]
    df_industry = pd.read_excel(file1_path, sheet_name='Multi_Condition_Passed', skiprows=header_row)
    df_industry.columns = df_industry.iloc[0]
    df_industry = df_industry[1:].reset_index(drop=True)
    
    df_industry = df_industry[['Industry', 'RS_Rating', 'Buy_Pressure']].copy()
    df_industry['RS_Rating'] = pd.to_numeric(df_industry['RS_Rating'], errors='coerce')
    df_industry['Buy_Pressure'] = pd.to_numeric(df_industry['Buy_Pressure'], errors='coerce')
    df_industry = df_industry.dropna()
    
    file2_path = 'data/integrated_screening_20260211_114423.xlsx'
    df_screening = pd.read_excel(file2_path, sheet_name='Screening_Results')
    
    df_screening_filtered = df_screening[df_screening['Technical_Score'] >= 10].copy()
    
    df_screening_filtered = df_screening_filtered[[
        'Symbol', 'Industry', 'Technical_Score', 'Screening_Score', 
        'Buy_Pressure', 'Company Name'
    ]].copy()
    
    return df_industry, df_screening_filtered

# データ読み込み
try:
    df_industry, df_screening = load_data()
    st.success(f"✅ データ読み込み成功: {len(df_industry)} 業種, {len(df_screening)} 銘柄")
except Exception as e:
    st.error(f"❌ データ読み込みエラー: {str(e)}")
    st.stop()

# サイドバー
with st.sidebar:
    st.header("📊 フィルター設定")
    
    min_tech_score = st.slider(
        "テクニカルスコア最小値",
        min_value=10,
        max_value=int(df_screening['Technical_Score'].max()),
        value=10,
        step=1
    )
    
    max_stocks_per_industry = st.slider(
        "業種ごとの最大表示銘柄数",
        min_value=5,
        max_value=30,
        value=15,
        step=5
    )
    
    selected_industries = st.multiselect(
        "業種選択（空白=全て）",
        options=sorted(df_industry['Industry'].unique()),
        default=None
    )
    
    st.markdown("---")
    st.markdown("### 🎨 カラーコード")
    st.markdown("- 🟢 **緑**: Buy Pressure 高い")
    st.markdown("- 🟡 **黄**: Buy Pressure 中程度")
    st.markdown("- 🔴 **赤**: Buy Pressure 低い")

# フィルタ適用
df_screening_display = df_screening[df_screening['Technical_Score'] >= min_tech_score].copy()

if selected_industries:
    df_screening_display = df_screening_display[
        df_screening_display['Industry'].isin(selected_industries)
    ]
    df_industry_display = df_industry[df_industry['Industry'].isin(selected_industries)].copy()
else:
    df_industry_display = df_industry.copy()

# タブ作成
tab1, tab2, tab3 = st.tabs([
    "📈 テクニカルスコア別マトリックス", 
    "🎯 スクリーニングスコア別マトリックス",
    "📊 業種サマリー"
])


def style_symbol(row):
    """行全体に対して、Symbol列とBuy Pressure列に色を付けるスタイル関数"""
    styles = [''] * len(row)
    try:
        bp = float(row['Buy Pressure'])
        color = get_color_from_buy_pressure(bp)
        symbol_idx = row.index.get_loc('Symbol')
        styles[symbol_idx] = f'color: {color}; font-weight: bold; font-size: 16px;'
        bp_idx = row.index.get_loc('Buy Pressure')
        styles[bp_idx] = f'color: {color}; font-weight: bold;'
    except (ValueError, TypeError, KeyError):
        pass
    return styles


def create_industry_table(df_screening_display, df_industry_display, sort_by='Technical_Score'):
    """業種×銘柄の表を作成（st.dataframe + Pandas Styler使用）"""
    
    df_industry_sorted = df_industry_display.sort_values('RS_Rating', ascending=False)
    
    for _, industry_row in df_industry_sorted.iterrows():
        industry_name = industry_row['Industry']
        rs_rating = industry_row['RS_Rating']
        buy_pressure = industry_row['Buy_Pressure']
        
        stocks_in_industry = df_screening_display[
            df_screening_display['Industry'] == industry_name
        ].sort_values(sort_by, ascending=False).head(max_stocks_per_industry)
        
        if len(stocks_in_industry) == 0:
            continue
        
        # 業種ヘッダー表示
        st.markdown(f"### {industry_name}")
        col1, col2, col3, col4 = st.columns([3, 1, 1, 2])
        with col1:
            st.metric("業種", industry_name)
        with col2:
            st.metric("RS Rating", f"{rs_rating:.1f}")
        with col3:
            st.metric("Buy Pressure", f"{buy_pressure:.3f}")
        with col4:
            status = get_buy_pressure_status(buy_pressure)
            st.markdown(f"**{status}**")
        
        # 表示用DataFrameを作成
        display_df = stocks_in_industry[['Symbol', 'Company Name', 'Technical_Score', 'Screening_Score', 'Buy_Pressure']].copy()
        display_df = display_df.reset_index(drop=True)
        display_df.index = display_df.index + 1
        display_df.index.name = 'No'
        display_df.columns = ['Symbol', 'Company Name', 'Technical Score', 'Screening Score', 'Buy Pressure']
        
        display_df['Company Name'] = display_df['Company Name'].apply(
            lambda x: str(x)[:40] if pd.notna(x) else ''
        )
        
        styled_df = display_df.style.apply(style_symbol, axis=1)
        
        st.dataframe(
            styled_df,
            use_container_width=True,
            height=min(len(display_df) * 40 + 50, 650)
        )
        st.markdown("---")


# タブ1: テクニカルスコア別
with tab1:
    st.header("テクニカルスコア別 業種×銘柄マトリックス")
    create_industry_table(df_screening_display, df_industry_display, sort_by='Technical_Score')

# タブ2: スクリーニングスコア別
with tab2:
    st.header("スクリーニングスコア (テクニカル+ファンダメンタル) 別 業種×銘柄マトリックス")
    create_industry_table(df_screening_display, df_industry_display, sort_by='Screening_Score')

# タブ3: 業種サマリー
with tab3:
    st.header("業種別サマリー統計")
    
    industry_summary = []
    for industry in df_industry_display['Industry']:
        stocks = df_screening_display[df_screening_display['Industry'] == industry]
        industry_data = df_industry_display[df_industry_display['Industry'] == industry].iloc[0]
        
        status = get_buy_pressure_status(industry_data['Buy_Pressure'])
        
        industry_summary.append({
            '業種': industry,
            'RS Rating': industry_data['RS_Rating'],
            'Buy Pressure': industry_data['Buy_Pressure'],
            'ステータス': status,
            '銘柄数': len(stocks),
            '平均テクニカルスコア': stocks['Technical_Score'].mean() if len(stocks) > 0 else 0,
            '平均スクリーニングスコア': stocks['Screening_Score'].mean() if len(stocks) > 0 else 0,
        })
    
    df_summary = pd.DataFrame(industry_summary)
    df_summary = df_summary.sort_values('RS Rating', ascending=False)
    
    st.dataframe(
        df_summary,
        use_container_width=True,
        height=600
    )
    
    # グラフ：RS Rating vs Buy Pressure
    st.subheader("RS Rating vs Buy Pressure")
    fig = px.scatter(
        df_summary,
        x='RS Rating',
        y='Buy Pressure',
        size='銘柄数',
        color='ステータス',
        hover_data=['業種', '平均テクニカルスコア'],
        text='業種',
        title='業種別 RS Rating vs Buy Pressure'
    )
    fig.update_traces(textposition='top center')
    fig.update_layout(
        height=700,
        yaxis=dict(
            scaleanchor='x',
            scaleratio=1,
        )
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # グラフ：業種別銘柄数
    st.subheader("業種別銘柄数")
    fig2 = px.bar(
        df_summary.sort_values('銘柄数', ascending=True),
        x='銘柄数',
        y='業種',
        orientation='h',
        color='Buy Pressure',
        color_continuous_scale='RdYlGn',
        title='業種別銘柄数 (テクニカルスコア10以上)'
    )
    st.plotly_chart(fig2, use_container_width=True)

# フッター
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: gray; font-size: 12px;">
    Industry Buy Pressure Dashboard | Data updated: 2026-02-11
    </div>
    """,
    unsafe_allow_html=True
)
