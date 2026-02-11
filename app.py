import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO

# ページ設定
st.set_page_config(
    page_title="Industry Buy Pressure Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🔥 Industry Buy Pressure Dashboard")
st.markdown("---")

# Buy Pressure のステータス判定関数
def get_buy_pressure_status(buy_pressure):
    """Buy Pressureに基づいてステータスと色を返す"""
    if buy_pressure > 0.667:
        return "🔥 EXTREME", "#FF0000"  # 赤
    elif buy_pressure > 0.60:
        return "🚀 STRONG", "#FF6B00"   # オレンジ赤
    elif buy_pressure > 0.55:
        return "📈 BUY", "#FFA500"      # オレンジ
    elif buy_pressure < 0.333:
        return "💀 WEAK", "#808080"     # グレー
    elif buy_pressure < 0.45:
        return "⚠️ CAUTION", "#FFD700"  # 黄色
    else:
        return "➖ NEUTRAL", "#87CEEB"  # 薄い青

# データ読み込み関数
@st.cache_data
def load_data():
    """エクセルファイルからデータを読み込む"""
    
    # File 1: Industry ETF Multi-Condition
    file1_path = 'data/industry_etf_multicondition_20260211_001951.xlsx'
    df_industry_raw = pd.read_excel(file1_path, sheet_name='Multi_Condition_Passed')
    
    # ヘッダー行を特定（'Industry'が含まれる行）
    header_row = df_industry_raw[df_industry_raw.iloc[:, 0] == 'Industry'].index[0]
    df_industry = pd.read_excel(file1_path, sheet_name='Multi_Condition_Passed', skiprows=header_row)
    df_industry.columns = df_industry.iloc[0]
    df_industry = df_industry[1:].reset_index(drop=True)
    
    # 必要な列を抽出・リネーム
    df_industry = df_industry[['Industry', 'RS_Rating', 'Buy_Pressure']].copy()
    df_industry['RS_Rating'] = pd.to_numeric(df_industry['RS_Rating'], errors='coerce')
    df_industry['Buy_Pressure'] = pd.to_numeric(df_industry['Buy_Pressure'], errors='coerce')
    df_industry = df_industry.dropna()
    
    # File 2: Integrated Screening
    file2_path = 'data/integrated_screening_20260211_114423.xlsx'
    df_screening = pd.read_excel(file2_path, sheet_name='Screening_Results')
    
    # Technical Score が10以上のみフィルタ
    df_screening_filtered = df_screening[df_screening['Technical_Score'] >= 10].copy()
    
    # 必要な列を抽出
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
    
    # Technical Score の最小値
    min_tech_score = st.slider(
        "テクニカルスコア最小値",
        min_value=10,
        max_value=int(df_screening['Technical_Score'].max()),
        value=10,
        step=1
    )
    
    # Industry フィルター
    selected_industries = st.multiselect(
        "業種選択（空白=全て）",
        options=sorted(df_industry['Industry'].unique()),
        default=None
    )
    
    st.markdown("---")
    st.markdown("### 🎨 カラーコード")
    st.markdown("- 🔥 **EXTREME** (>0.667)")
    st.markdown("- 🚀 **STRONG** (>0.60)")
    st.markdown("- 📈 **BUY** (>0.55)")
    st.markdown("- ➖ **NEUTRAL** (0.45-0.55)")
    st.markdown("- ⚠️ **CAUTION** (<0.45)")
    st.markdown("- 💀 **WEAK** (<0.333)")

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

# タブ1: テクニカルスコア
with tab1:
    st.header("テクニカルスコア別 業種×銘柄マトリックス")
    
    # 業種ごとにソート（RS_Rating降順）
    df_industry_sorted = df_industry_display.sort_values('RS_Rating', ascending=False)
    
    # 各業種の銘柄を取得
    for _, industry_row in df_industry_sorted.iterrows():
        industry_name = industry_row['Industry']
        rs_rating = industry_row['RS_Rating']
        buy_pressure = industry_row['Buy_Pressure']
        
        # この業種の銘柄を取得
        stocks_in_industry = df_screening_display[
            df_screening_display['Industry'] == industry_name
        ].sort_values('Technical_Score', ascending=False)
        
        if len(stocks_in_industry) > 0:
            # 業種ヘッダー
            status, color = get_buy_pressure_status(buy_pressure)
            st.markdown(f"### {industry_name}")
            col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
            with col1:
                st.metric("業種", industry_name)
            with col2:
                st.metric("RS Rating", f"{rs_rating:.1f}")
            with col3:
                st.metric("Buy Pressure", f"{buy_pressure:.4f}")
            with col4:
                st.markdown(f"**{status}**")
            
            # 銘柄を横に並べる
            cols = st.columns(min(len(stocks_in_industry), 5))
            for idx, (_, stock) in enumerate(stocks_in_industry.iterrows()):
                if idx >= 20:  # 最大20銘柄まで表示
                    break
                    
                col_idx = idx % 5
                stock_status, stock_color = get_buy_pressure_status(stock['Buy_Pressure'])
                
                with cols[col_idx]:
                    st.markdown(
                        f"""
                        <div style="
                            border: 2px solid {stock_color};
                            border-radius: 8px;
                            padding: 10px;
                            margin: 5px 0;
                            background-color: {stock_color}20;
                        ">
                            <h4 style="margin: 0; color: {stock_color};">{stock['Symbol']}</h4>
                            <p style="margin: 5px 0; font-size: 12px;">{stock['Company Name'][:30]}</p>
                            <p style="margin: 5px 0;"><strong>Tech Score:</strong> {stock['Technical_Score']}</p>
                            <p style="margin: 5px 0;"><strong>Buy Pressure:</strong> {stock['Buy_Pressure']:.4f}</p>
                            <p style="margin: 0;">{stock_status}</p>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
            
            st.markdown("---")

# タブ2: スクリーニングスコア
with tab2:
    st.header("スクリーニングスコア (テクニカル+ファンダメンタル) 別 業種×銘柄マトリックス")
    
    # 業種ごとにソート（RS_Rating降順）
    df_industry_sorted = df_industry_display.sort_values('RS_Rating', ascending=False)
    
    # 各業種の銘柄を取得
    for _, industry_row in df_industry_sorted.iterrows():
        industry_name = industry_row['Industry']
        rs_rating = industry_row['RS_Rating']
        buy_pressure = industry_row['Buy_Pressure']
        
        # この業種の銘柄を取得
        stocks_in_industry = df_screening_display[
            df_screening_display['Industry'] == industry_name
        ].sort_values('Screening_Score', ascending=False)
        
        if len(stocks_in_industry) > 0:
            # 業種ヘッダー
            status, color = get_buy_pressure_status(buy_pressure)
            st.markdown(f"### {industry_name}")
            col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
            with col1:
                st.metric("業種", industry_name)
            with col2:
                st.metric("RS Rating", f"{rs_rating:.1f}")
            with col3:
                st.metric("Buy Pressure", f"{buy_pressure:.4f}")
            with col4:
                st.markdown(f"**{status}**")
            
            # 銘柄を横に並べる
            cols = st.columns(min(len(stocks_in_industry), 5))
            for idx, (_, stock) in enumerate(stocks_in_industry.iterrows()):
                if idx >= 20:  # 最大20銘柄まで表示
                    break
                    
                col_idx = idx % 5
                stock_status, stock_color = get_buy_pressure_status(stock['Buy_Pressure'])
                
                with cols[col_idx]:
                    st.markdown(
                        f"""
                        <div style="
                            border: 2px solid {stock_color};
                            border-radius: 8px;
                            padding: 10px;
                            margin: 5px 0;
                            background-color: {stock_color}20;
                        ">
                            <h4 style="margin: 0; color: {stock_color};">{stock['Symbol']}</h4>
                            <p style="margin: 5px 0; font-size: 12px;">{stock['Company Name'][:30]}</p>
                            <p style="margin: 5px 0;"><strong>Screening Score:</strong> {stock['Screening_Score']}</p>
                            <p style="margin: 5px 0;"><strong>Tech Score:</strong> {stock['Technical_Score']}</p>
                            <p style="margin: 5px 0;"><strong>Buy Pressure:</strong> {stock['Buy_Pressure']:.4f}</p>
                            <p style="margin: 0;">{stock_status}</p>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
            
            st.markdown("---")

# タブ3: 業種サマリー
with tab3:
    st.header("業種別サマリー統計")
    
    # 業種別の統計
    industry_summary = []
    for industry in df_industry_display['Industry']:
        stocks = df_screening_display[df_screening_display['Industry'] == industry]
        industry_data = df_industry_display[df_industry_display['Industry'] == industry].iloc[0]
        
        status, color = get_buy_pressure_status(industry_data['Buy_Pressure'])
        
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
    
    # サマリーテーブル表示
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

