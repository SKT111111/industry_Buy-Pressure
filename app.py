import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
import numpy as np
import html
import glob
import os
import re

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
        return "#808080"
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


# ============================================================
# ★ 最新ファイル自動検出ユーティリティ（ここが新規追加部分）
# ============================================================
def find_latest_file(directory: str, prefix: str) -> str:
    """
    指定ディレクトリから、指定プレフィックスに一致するファイルのうち
    ファイル名に埋め込まれた日付（YYYYMMDD_HHMMSS）が最も新しいものを返す。

    例:
        prefix="industry_etf_multicondition_"
        → industry_etf_multicondition_20260212_160443.xlsx が最新なら、そのパスを返す

    Parameters:
        directory: 検索対象ディレクトリ（例: "data"）
        prefix: ファイル名のプレフィックス（例: "industry_etf_multicondition_"）

    Returns:
        最新ファイルのフルパス

    Raises:
        FileNotFoundError: 該当ファイルが見つからない場合
    """
    # プレフィックスに一致する .xlsx ファイルを全て取得
    pattern = os.path.join(directory, f"{prefix}*.xlsx")
    matched_files = glob.glob(pattern)

    if not matched_files:
        raise FileNotFoundError(
            f"'{directory}/' 内に '{prefix}*.xlsx' に一致するファイルが見つかりません。"
        )

    # ファイル名から日時部分（YYYYMMDD_HHMMSS）を抽出してソート
    date_pattern = re.compile(r'(\d{8}_\d{6})\.xlsx$')
    
    files_with_dates = []
    for filepath in matched_files:
        filename = os.path.basename(filepath)
        match = date_pattern.search(filename)
        if match:
            date_str = match.group(1)  # "20260212_160443"
            files_with_dates.append((filepath, date_str))

    if not files_with_dates:
        raise FileNotFoundError(
            f"'{directory}/' 内に '{prefix}*.xlsx' で日付パターン(YYYYMMDD_HHMMSS)を含むファイルが見つかりません。"
        )

    # 日時文字列は YYYYMMDD_HHMMSS 形式なので、文字列の辞書順ソートでOK
    files_with_dates.sort(key=lambda x: x[1], reverse=True)
    
    latest_path = files_with_dates[0][0]
    return latest_path


# ============================================================
# ★ データ読み込み関数（自動検出版に改修）
# ============================================================
@st.cache_data
def load_data():
    """data/ フォルダから最新のファイルを自動検出して読み込む"""

    DATA_DIR = "data"

    # --- 最新ファイルを自動検出 ---
    file1_path = find_latest_file(DATA_DIR, "industry_etf_multicondition_")
    file2_path = find_latest_file(DATA_DIR, "integrated_screening_")

    # --- 読み込んだファイル名を表示用に保持 ---
    st.session_state['loaded_file1'] = os.path.basename(file1_path)
    st.session_state['loaded_file2'] = os.path.basename(file2_path)

    # --- industry_etf_multicondition 読み込み ---
    df_industry_raw = pd.read_excel(file1_path, sheet_name='Multi_Condition_Passed')
    header_row = df_industry_raw[df_industry_raw.iloc[:, 0] == 'Industry'].index[0]
    df_industry = pd.read_excel(file1_path, sheet_name='Multi_Condition_Passed', skiprows=header_row)
    df_industry.columns = df_industry.iloc[0]
    df_industry = df_industry[1:].reset_index(drop=True)
    df_industry = df_industry[['Industry', 'RS_Rating', 'Buy_Pressure']].copy()
    df_industry['RS_Rating'] = pd.to_numeric(df_industry['RS_Rating'], errors='coerce')
    df_industry['Buy_Pressure'] = pd.to_numeric(df_industry['Buy_Pressure'], errors='coerce')
    df_industry = df_industry.dropna()

    # --- integrated_screening 読み込み ---
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

    # どのファイルが読み込まれたかを表示
    loaded1 = st.session_state.get('loaded_file1', '不明')
    loaded2 = st.session_state.get('loaded_file2', '不明')
    st.success(f"✅ データ読み込み成功: {len(df_industry)} 業種, {len(df_screening)} 銘柄")
    st.caption(f"📂 読み込みファイル: `{loaded1}` / `{loaded2}`")

except Exception as e:
    st.error(f"❌ データ読み込みエラー: {str(e)}")
    st.stop()


# ============================================================
# 以下は変更なし（元のコードそのまま）
# ============================================================

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

# 業種別サマリーデータを作成（共通で使用）
def create_summary_data(df_screening_display, df_industry_display):
    """業種別サマリーデータを作成"""
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
    return df_summary

df_summary = create_summary_data(df_screening_display, df_industry_display)

# タブ作成
tab0, tab1, tab2, tab3 = st.tabs([
    "✅ チェック",
    "📈 テクニカルスコア別マトリックス",
    "🎯 スクリーニングスコア別マトリックス",
    "📊 業種サマリー"
])


def style_symbol(row):
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
        display_df = stocks_in_industry[['Symbol', 'Company Name', 'Technical_Score', 'Screening_Score', 'Buy_Pressure']].copy()
        display_df = display_df.reset_index(drop=True)
        display_df.index = display_df.index + 1
        display_df.index.name = 'No'
        display_df.columns = ['Symbol', 'Company Name', 'Technical Score', 'Screening Score', 'Buy Pressure']
        display_df['Company Name'] = display_df['Company Name'].apply(
            lambda x: str(x)[:40] if pd.notna(x) else ''
        )
        styled_df = display_df.style.apply(style_symbol, axis=1)
        st.dataframe(styled_df, use_container_width=True, height=min(len(display_df) * 40 + 50, 650))
        st.markdown("---")


def get_colored_symbols_html(industry, score, df_screening_display):
    stocks = df_screening_display[
        (df_screening_display['Industry'] == industry) &
        (df_screening_display['Technical_Score'] == score)
    ].sort_values('Buy_Pressure', ascending=False)
    if len(stocks) == 0:
        return '', ''
    colored_spans = []
    plain_symbols = []
    for _, stock in stocks.iterrows():
        symbol = html.escape(str(stock['Symbol']))
        bp = stock['Buy_Pressure']
        color = get_color_from_buy_pressure(bp)
        colored_spans.append(f'<span style="color:{color}; font-weight:bold;">{symbol}</span>')
        plain_symbols.append(symbol)
    display_html = ', '.join(colored_spans)
    copy_text = ', '.join(plain_symbols)
    return display_html, copy_text


# タブ0: チェック
with tab0:
    st.header("Buy Pressure")
    df_check = df_summary[['業種', 'RS Rating', 'Buy Pressure', 'ステータス']].copy()
    max_symbols_per_row = []
    for _, row in df_check.iterrows():
        row_max = 0
        for score in [14, 13, 12, 11, 10]:
            count = len(df_screening_display[
                (df_screening_display['Industry'] == row['業種']) &
                (df_screening_display['Technical_Score'] == score)
            ])
            row_max = max(row_max, count)
        max_symbols_per_row.append(row_max)

    table_html = """
    <style>
    #check-table { width: 100%; border-collapse: collapse; font-size: 13px; }
    #check-table th { background-color: #262730; color: #fafafa; padding: 8px 10px; text-align: left; border: 1px solid #444; }
    #check-table td { padding: 6px 10px; border: 1px solid #444; background-color: #0e1117; color: #fafafa; }
    #check-table tr:hover td { background-color: #1a1d24; }
    .copyable { cursor: pointer; position: relative; }
    .copyable:hover { background-color: #2a2d34 !important; }
    .copy-toast { position: fixed; top: 20px; right: 20px; background-color: #00c853; color: white; padding: 10px 20px; border-radius: 8px; font-size: 14px; font-weight: bold; z-index: 9999; opacity: 0; transition: opacity 0.3s; pointer-events: none; }
    .copy-toast.show { opacity: 1; }
    </style>
    <div id="copy-toast" class="copy-toast">📋 Copied!</div>
    <div style="overflow-x: auto;">
    <table id="check-table">
    <thead><tr>
        <th>業種</th><th>RS Rating</th><th>Buy Pressure</th><th>ステータス</th>
        <th>TS 14</th><th>TS 13</th><th>TS 12</th><th>TS 11</th><th>TS 10</th>
    </tr></thead><tbody>
    """
    for idx, row in df_check.iterrows():
        bp = row['Buy Pressure']
        bp_color = get_color_from_buy_pressure(bp)
        industry = html.escape(str(row['業種']))
        rs = f"{row['RS Rating']:.1f}"
        bp_val = f"{bp:.3f}"
        status = html.escape(str(row['ステータス']))
        table_html += f'<tr><td>{industry}</td><td>{rs}</td><td style="color: {bp_color}; font-weight: bold;">{bp_val}</td><td>{status}</td>'
        for score in [14, 13, 12, 11, 10]:
            display_html, copy_text = get_colored_symbols_html(row['業種'], score, df_screening_display)
            if display_html:
                escaped_copy = html.escape(copy_text).replace("'", "\\'")
                table_html += f"<td class=\"copyable\" onclick=\"copySymbols(this, '{escaped_copy}')\" title=\"クリックでコピー\">{display_html}</td>"
            else:
                table_html += '<td></td>'
        table_html += "</tr>"

    table_html += """
    </tbody></table></div>
    <script>
    function copySymbols(el, text) {
        navigator.clipboard.writeText(text).then(function() {
            var toast = document.getElementById('copy-toast');
            toast.classList.add('show');
            el.style.backgroundColor = '#1b5e20';
            setTimeout(function() { toast.classList.remove('show'); el.style.backgroundColor = ''; }, 1500);
        });
    }
    </script>
    """
    total_height = 80
    for sym_count in max_symbols_per_row:
        if sym_count <= 3: total_height += 40
        elif sym_count <= 6: total_height += 55
        elif sym_count <= 10: total_height += 75
        else: total_height += 95
    st.components.v1.html(table_html, height=total_height, scrolling=False)

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
    st.dataframe(df_summary, use_container_width=True, height=600)
    st.subheader("RS Rating vs Buy Pressure")
    fig = px.scatter(df_summary, x='RS Rating', y='Buy Pressure', size='銘柄数', color='ステータス',
                     hover_data=['業種', '平均テクニカルスコア'], text='業種', title='業種別 RS Rating vs Buy Pressure')
    fig.update_traces(textposition='top center')
    fig.update_layout(height=700, yaxis=dict(range=[0.5, 1]))
    st.plotly_chart(fig, use_container_width=True)
    st.subheader("業種別銘柄数")
    fig2 = px.bar(df_summary.sort_values('銘柄数', ascending=True), x='銘柄数', y='業種', orientation='h',
                  color='Buy Pressure', color_continuous_scale='RdYlGn', title='業種別銘柄数 (テクニカルスコア10以上)')
    st.plotly_chart(fig2, use_container_width=True)

# フッター（日付も自動化）
footer_date = "不明"
try:
    fname = st.session_state.get('loaded_file1', '')
    match = re.search(r'(\d{4})(\d{2})(\d{2})_', fname)
    if match:
        footer_date = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
except:
    pass

st.markdown("---")
st.markdown(
    f"""
    <div style="text-align: center; color: gray; font-size: 12px;">
    Industry Buy Pressure Dashboard | Data updated: {footer_date}
    </div>
    """,
    unsafe_allow_html=True
)
