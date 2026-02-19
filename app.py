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
from datetime import datetime, timedelta

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


# Buy Pressure のステータス判定関数（ソート用プレフィックス付き）
def get_buy_pressure_status(buy_pressure):
    """Buy Pressureに基づいてステータスを返す（先頭にソート順番号付き）"""
    if buy_pressure > 0.667:
        return "3 🔥 EXTREME"
    elif buy_pressure > 0.60:
        return "2 🚀 STRONG"
    elif buy_pressure > 0.55:
        return "1 📈 BUY"
    elif buy_pressure < 0.333:
        return "0a 💀 WEAK"
    elif buy_pressure < 0.45:
        return "0b ⚠️ CAUTION"
    else:
        return "0c ➖ NEUTRAL"


# チェックタブ等で番号なし表示用
def get_buy_pressure_status_display(buy_pressure):
    """Buy Pressureに基づいてステータスを返す（表示用・番号なし）"""
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


# RS Rating用カスタムカラースケール（0〜100）
CUSTOM_RS_COLORSCALE = [
    [0.0, "#ff0000"],
    [0.4, "#ff8c00"],
    [0.79, "#d4c860"],
    [0.80, "#9acd32"],
    [1.0, "#006400"],
]


# ============================================================
# 最新ファイル自動検出
# ============================================================
def find_latest_file(directory, prefix):
    pattern = os.path.join(directory, f"{prefix}*.xlsx")
    matched_files = glob.glob(pattern)

    if not matched_files:
        raise FileNotFoundError(
            f"'{directory}/' 内に '{prefix}*.xlsx' に一致するファイルが見つかりません。"
        )

    date_pattern = re.compile(r'(\d{8}_\d{6})\.xlsx$')

    files_with_dates = []
    for filepath in matched_files:
        filename = os.path.basename(filepath)
        match = date_pattern.search(filename)
        if match:
            files_with_dates.append((filepath, match.group(1)))

    if not files_with_dates:
        raise FileNotFoundError(
            f"'{directory}/' 内に日付パターン(YYYYMMDD_HHMMSS)を含むファイルが見つかりません。"
        )

    files_with_dates.sort(key=lambda x: x[1], reverse=True)
    return files_with_dates[0][0]


def get_data_date_from_filename(filename):
    match = re.search(r'(\d{8})_\d{6}', filename)
    if match:
        file_date = datetime.strptime(match.group(1), '%Y%m%d')
        data_date = file_date - timedelta(days=1)
        return data_date.strftime('%Y-%m-%d')
    return "不明"


# ============================================================
# データ読み込み関数
# ============================================================
@st.cache_data
def load_data():
    DATA_DIR = "data"

    file1_path = find_latest_file(DATA_DIR, "industry_etf_multicondition_")
    file2_path = find_latest_file(DATA_DIR, "integrated_screening_")

    file1_name = os.path.basename(file1_path)
    file2_name = os.path.basename(file2_path)

    data_date = get_data_date_from_filename(file1_name)

    xl = pd.ExcelFile(file1_path)
    sheet_names = xl.sheet_names

    df_industry = None

    if 'Multi_Condition_Passed' in sheet_names:
        df_raw = pd.read_excel(file1_path, sheet_name='Multi_Condition_Passed')

        if 'Industry' in df_raw.columns:
            df_industry = df_raw.copy()
        else:
            industry_matches = df_raw[df_raw.iloc[:, 0] == 'Industry']
            if len(industry_matches) > 0:
                header_row = industry_matches.index[0]
                df_industry = pd.read_excel(
                    file1_path,
                    sheet_name='Multi_Condition_Passed',
                    skiprows=header_row
                )
                df_industry.columns = df_industry.iloc[0]
                df_industry = df_industry[1:].reset_index(drop=True)
    else:
        df_raw = pd.read_excel(file1_path, sheet_name=0)
        if 'Industry' in df_raw.columns:
            df_industry = df_raw.copy()

    if df_industry is None:
        raise ValueError(
            f"'{file1_name}' から Industry データを読み取れませんでした。"
            f" シート名: {sheet_names}"
        )

    df_industry = df_industry[['Industry', 'RS_Rating', 'Buy_Pressure']].copy()
    df_industry['RS_Rating'] = pd.to_numeric(df_industry['RS_Rating'], errors='coerce')
    df_industry['Buy_Pressure'] = pd.to_numeric(df_industry['Buy_Pressure'], errors='coerce')
    df_industry = df_industry.dropna()

    df_all_industry = None
    if 'Full_Results' in sheet_names:
        df_full = pd.read_excel(file1_path, sheet_name='Full_Results')
        if 'Industry' in df_full.columns and 'Buy_Pressure' in df_full.columns:
            cols_to_use = ['Industry', 'Buy_Pressure']
            if 'RS_Rating' in df_full.columns:
                cols_to_use.append('RS_Rating')
            df_all_industry = df_full[cols_to_use].copy()
            df_all_industry['Buy_Pressure'] = pd.to_numeric(df_all_industry['Buy_Pressure'], errors='coerce')
            if 'RS_Rating' in df_all_industry.columns:
                df_all_industry['RS_Rating'] = pd.to_numeric(df_all_industry['RS_Rating'], errors='coerce')
            df_all_industry = df_all_industry.dropna(subset=['Buy_Pressure'])

    if df_all_industry is None:
        df_all_industry = df_industry.copy()

    df_screening = pd.read_excel(file2_path, sheet_name='Screening_Results')
    df_screening_filtered = df_screening[df_screening['Technical_Score'] >= 10].copy()
    df_screening_filtered = df_screening_filtered[[
        'Symbol', 'Industry', 'Technical_Score', 'Screening_Score',
        'Buy_Pressure', 'Company Name'
    ]].copy()

    industry_sector_map = {}
    if 'Sector' in df_screening.columns and 'Industry' in df_screening.columns:
        sector_df = df_screening[['Industry', 'Sector']].dropna().drop_duplicates()
        for industry in sector_df['Industry'].unique():
            sectors = sector_df[sector_df['Industry'] == industry]['Sector']
            industry_sector_map[industry] = sectors.mode().iloc[0] if len(sectors) > 0 else 'Unknown'

    return df_industry, df_all_industry, df_screening_filtered, industry_sector_map, data_date


# データ読み込み
try:
    df_industry, df_all_industry, df_screening, industry_sector_map, data_date = load_data()
    st.success(f"✅ データ読み込み成功: {len(df_industry)} 業種 (条件通過), {len(df_all_industry)} 業種 (全体), {len(df_screening)} 銘柄")
    st.caption(f"📅 データ日付: **{data_date}**")
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

# ファンダメンタルスコア列を追加
df_screening_display['Fundamental_Score'] = (
    df_screening_display['Screening_Score'] - df_screening_display['Technical_Score']
)

if selected_industries:
    df_screening_display = df_screening_display[
        df_screening_display['Industry'].isin(selected_industries)
    ]
    df_industry_display = df_industry[df_industry['Industry'].isin(selected_industries)].copy()
else:
    df_industry_display = df_industry.copy()


# 業種別サマリーデータを作成
def create_summary_data(df_screening_disp, df_industry_disp):
    industry_summary = []
    for industry in df_industry_disp['Industry']:
        stocks = df_screening_disp[df_screening_disp['Industry'] == industry]
        industry_data = df_industry_disp[df_industry_disp['Industry'] == industry].iloc[0]
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
tab0, tab0b, tab1, tab2, tab3 = st.tabs([
    "✅ チェック",
    "✅ チェック②",
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


def create_industry_table(df_screening_disp, df_industry_disp, sort_by='Technical_Score'):
    df_industry_sorted = df_industry_disp.sort_values('RS_Rating', ascending=False)

    for _, industry_row in df_industry_sorted.iterrows():
        industry_name = industry_row['Industry']
        rs_rating = industry_row['RS_Rating']
        buy_pressure = industry_row['Buy_Pressure']

        stocks_in_industry = df_screening_disp[
            df_screening_disp['Industry'] == industry_name
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
            status = get_buy_pressure_status_display(buy_pressure)
            st.markdown(f"**{status}**")

        display_df = stocks_in_industry[
            ['Symbol', 'Company Name', 'Technical_Score', 'Screening_Score', 'Buy_Pressure']
        ].copy()
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


def get_colored_symbols_html(industry, score, df_screening_disp):
    stocks = df_screening_disp[
        (df_screening_disp['Industry'] == industry) &
        (df_screening_disp['Technical_Score'] == score)
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


def get_colored_symbols_html_with_fs(industry, ts, fs, df_screening_disp):
    """業種・TS・FSに該当する銘柄を色付きHTMLで返す"""
    stocks = df_screening_disp[
        (df_screening_disp['Industry'] == industry) &
        (df_screening_disp['Technical_Score'] == ts) &
        (df_screening_disp['Fundamental_Score'] == fs)
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


# ============================================================
# チェックタブ用 HTML 生成関数（タブ0 用：従来版）
# ============================================================
def render_check_tab(df_check, df_screening_disp, table_id_suffix=""):
    st.header("Buy Pressure")

    max_symbols_per_row = []
    for _, row in df_check.iterrows():
        row_max = 0
        for score in [14, 13, 12, 11, 10]:
            count = len(df_screening_disp[
                (df_screening_disp['Industry'] == row['業種']) &
                (df_screening_disp['Technical_Score'] == score)
            ])
            row_max = max(row_max, count)
        max_symbols_per_row.append(row_max)

    tid = f"check-table{table_id_suffix}"
    toast_id = f"copy-toast{table_id_suffix}"
    func_name = f"copySymbols{table_id_suffix.replace('-', '_')}"

    table_html = f"""
    <style>
    #{tid} {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    #{tid} th {{ background-color: #262730; color: #fafafa; padding: 8px 10px; text-align: left; border: 1px solid #444; }}
    #{tid} td {{ padding: 6px 10px; border: 1px solid #444; background-color: #0e1117; color: #fafafa; }}
    #{tid} tr:hover td {{ background-color: #1a1d24; }}
    .copyable{table_id_suffix} {{ cursor: pointer; position: relative; }}
    .copyable{table_id_suffix}:hover {{ background-color: #2a2d34 !important; }}
    #{toast_id} {{ position: fixed; top: 20px; right: 20px; background-color: #00c853; color: white; padding: 10px 20px; border-radius: 8px; font-size: 14px; font-weight: bold; z-index: 9999; opacity: 0; transition: opacity 0.3s; pointer-events: none; }}
    #{toast_id}.show {{ opacity: 1; }}
    </style>
    <div id="{toast_id}" class="copy-toast">📋 Copied!</div>
    <div style="overflow-x: auto;">
    <table id="{tid}">
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
        status_raw = str(row['ステータス'])
        status_display = re.sub(r'^\d+[a-z]?\s+', '', status_raw)
        status = html.escape(status_display)

        table_html += f'<tr><td>{industry}</td><td>{rs}</td>'
        table_html += f'<td style="color: {bp_color}; font-weight: bold;">{bp_val}</td>'
        table_html += f'<td>{status}</td>'

        for score in [14, 13, 12, 11, 10]:
            display_html, copy_text = get_colored_symbols_html(
                row['業種'], score, df_screening_disp
            )
            if display_html:
                escaped_copy = html.escape(copy_text).replace("'", "\\'")
                table_html += (
                    f'<td class="copyable{table_id_suffix}" '
                    f'onclick="{func_name}(this, \'{escaped_copy}\')" '
                    f'title="クリックでコピー">{display_html}</td>'
                )
            else:
                table_html += '<td></td>'

        table_html += "</tr>"

    table_html += f"""
    </tbody></table></div>
    <script>
    function {func_name}(el, text) {{
        navigator.clipboard.writeText(text).then(function() {{
            var toast = document.getElementById('{toast_id}');
            toast.classList.add('show');
            el.style.backgroundColor = '#1b5e20';
            setTimeout(function() {{ toast.classList.remove('show'); el.style.backgroundColor = ''; }}, 1500);
        }});
    }}
    </script>
    """

    total_height = 80
    for sym_count in max_symbols_per_row:
        if sym_count <= 3:
            total_height += 40
        elif sym_count <= 6:
            total_height += 55
        elif sym_count <= 10:
            total_height += 75
        else:
            total_height += 95

    st.components.v1.html(table_html, height=total_height, scrolling=False)


# ============================================================
# チェック②タブ用 HTML 生成関数（TS × FS 細分化版）
# ============================================================
def render_check_tab_with_fs(df_check, df_screening_disp):
    """チェック②: TS 列の中をさらに FS（Fundamental Score）で細分化して表示"""
    st.header("Buy Pressure（TS × FS 細分化）")

    # TS ごとに存在する FS 値を降順で取得
    ts_values = sorted(df_screening_disp['Technical_Score'].unique(), reverse=True)
    ts_fs_map = {}  # {ts: [fs_desc, ...]}
    for ts in ts_values:
        fs_vals = sorted(
            df_screening_disp[df_screening_disp['Technical_Score'] == ts]['Fundamental_Score'].unique(),
            reverse=True
        )
        ts_fs_map[ts] = [int(f) for f in fs_vals]

    # 全サブカラム数（TS×FS の組み合わせ数）
    all_sub_cols = []  # [(ts, fs), ...]
    for ts in ts_values:
        for fs in ts_fs_map[ts]:
            all_sub_cols.append((ts, fs))

    # 行ごとの最大シンボル数（高さ計算用）
    max_symbols_per_row = []
    for _, row in df_check.iterrows():
        row_max = 0
        for ts, fs in all_sub_cols:
            count = len(df_screening_disp[
                (df_screening_disp['Industry'] == row['業種']) &
                (df_screening_disp['Technical_Score'] == ts) &
                (df_screening_disp['Fundamental_Score'] == fs)
            ])
            row_max = max(row_max, count)
        max_symbols_per_row.append(row_max)

    tid = "check-table-fs"
    toast_id = "copy-toast-fs"
    func_name = "copySymbolsFS"

    # --- ヘッダー色: TS 値で背景色を変える ---
    ts_header_colors = {
        14: "#1b3a1b",
        13: "#2a4a1b",
        12: "#3a3a1b",
        11: "#4a3a1b",
        10: "#3a2a1b",
    }

    table_html = f"""
    <style>
    #{tid} {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    #{tid} th {{ background-color: #262730; color: #fafafa; padding: 6px 8px;
                 text-align: center; border: 1px solid #444; white-space: nowrap; }}
    #{tid} td {{ padding: 6px 8px; border: 1px solid #444;
                 background-color: #0e1117; color: #fafafa; }}
    #{tid} tr:hover td {{ background-color: #1a1d24; }}
    .copyable-fs {{ cursor: pointer; position: relative; }}
    .copyable-fs:hover {{ background-color: #2a2d34 !important; }}
    #{toast_id} {{ position: fixed; top: 20px; right: 20px; background-color: #00c853;
                   color: white; padding: 10px 20px; border-radius: 8px; font-size: 14px;
                   font-weight: bold; z-index: 9999; opacity: 0; transition: opacity 0.3s;
                   pointer-events: none; }}
    #{toast_id}.show {{ opacity: 1; }}
    </style>
    <div id="{toast_id}" class="copy-toast">📋 Copied!</div>
    <div style="overflow-x: auto;">
    <table id="{tid}">
    <thead>
    """

    # --- 上段ヘッダー: 固定列 + TS グループ（colspan） ---
    fixed_cols = 4  # 業種, RS Rating, BP, ステータス
    table_html += "<tr>"
    table_html += f'<th rowspan="2">業種</th>'
    table_html += f'<th rowspan="2">RS Rating</th>'
    table_html += f'<th rowspan="2">Buy Pressure</th>'
    table_html += f'<th rowspan="2">ステータス</th>'
    for ts in ts_values:
        colspan = len(ts_fs_map[ts])
        bg = ts_header_colors.get(ts, "#262730")
        table_html += f'<th colspan="{colspan}" style="background-color:{bg};">TS {ts}</th>'
    table_html += "</tr>"

    # --- 下段ヘッダー: FS 値 ---
    table_html += "<tr>"
    for ts in ts_values:
        bg = ts_header_colors.get(ts, "#262730")
        for fs in ts_fs_map[ts]:
            table_html += f'<th style="background-color:{bg}; font-size:11px;">FS {fs}</th>'
    table_html += "</tr>"
    table_html += "</thead><tbody>"

    # --- データ行 ---
    for idx, row in df_check.iterrows():
        bp = row['Buy Pressure']
        bp_color = get_color_from_buy_pressure(bp)
        industry_name = str(row['業種'])
        industry_esc = html.escape(industry_name)
        rs = f"{row['RS Rating']:.1f}"
        bp_val = f"{bp:.3f}"
        status_raw = str(row['ステータス'])
        status_display = re.sub(r'^\d+[a-z]?\s+', '', status_raw)
        status = html.escape(status_display)

        table_html += "<tr>"
        table_html += f"<td>{industry_esc}</td>"
        table_html += f"<td>{rs}</td>"
        table_html += f'<td style="color: {bp_color}; font-weight: bold;">{bp_val}</td>'
        table_html += f"<td>{status}</td>"

        for ts, fs in all_sub_cols:
            display_html, copy_text = get_colored_symbols_html_with_fs(
                industry_name, ts, fs, df_screening_disp
            )
            if display_html:
                escaped_copy = html.escape(copy_text).replace("'", "\\'")
                table_html += (
                    f'<td class="copyable-fs" '
                    f'onclick="{func_name}(this, \'{escaped_copy}\')" '
                    f'title="クリックでコピー">{display_html}</td>'
                )
            else:
                table_html += "<td></td>"

        table_html += "</tr>"

    table_html += f"""
    </tbody></table></div>
    <script>
    function {func_name}(el, text) {{
        navigator.clipboard.writeText(text).then(function() {{
            var toast = document.getElementById('{toast_id}');
            toast.classList.add('show');
            el.style.backgroundColor = '#1b5e20';
            setTimeout(function() {{ toast.classList.remove('show'); el.style.backgroundColor = ''; }}, 1500);
        }});
    }}
    </script>
    """

    total_height = 100  # ヘッダー 2 段分
    for sym_count in max_symbols_per_row:
        if sym_count <= 3:
            total_height += 40
        elif sym_count <= 6:
            total_height += 55
        elif sym_count <= 10:
            total_height += 75
        else:
            total_height += 95

    st.components.v1.html(table_html, height=total_height, scrolling=False)


# ============================================================
# タブ0: チェック（従来版）
# ============================================================
with tab0:
    df_check = df_summary[['業種', 'RS Rating', 'Buy Pressure', 'ステータス']].copy()
    render_check_tab(df_check, df_screening_display, table_id_suffix="")

# ============================================================
# タブ0b: チェック②（TS × FS 細分化版）
# ============================================================
with tab0b:
    df_check2 = df_summary[['業種', 'RS Rating', 'Buy Pressure', 'ステータス']].copy()
    render_check_tab_with_fs(df_check2, df_screening_display)


# ============================================================
# タブ1: テクニカルスコア別
# ============================================================
with tab1:
    st.header("テクニカルスコア別 業種×銘柄マトリックス")
    create_industry_table(df_screening_display, df_industry_display, sort_by='Technical_Score')


# ============================================================
# タブ2: スクリーニングスコア別
# ============================================================
with tab2:
    st.header("スクリーニングスコア (テクニカル+ファンダメンタル) 別 業種×銘柄マトリックス")
    create_industry_table(df_screening_display, df_industry_display, sort_by='Screening_Score')


# ============================================================
# タブ3: 業種サマリー
# ============================================================
with tab3:
    st.header("業種別サマリー統計")

    st.dataframe(
        df_summary,
        use_container_width=True,
        height=600,
        column_config={
            'ステータス': st.column_config.TextColumn(
                'ステータス',
                help='クリックでソート: BUY → STRONG → EXTREME',
                width='medium',
            ),
        },
    )

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
    fig.update_layout(height=700, yaxis=dict(range=[0.5, 1]))
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("業種別BPランキング")

    df_bp_ranking = df_all_industry.copy()
    df_bp_ranking['Sector'] = df_bp_ranking['Industry'].map(industry_sector_map).fillna('Unknown')

    sector_avg_bp = df_bp_ranking.groupby('Sector')['Buy_Pressure'].mean().sort_values(ascending=False)
    sorted_sectors = sector_avg_bp.index.tolist()

    for sector in sorted_sectors:
        df_sector = df_bp_ranking[df_bp_ranking['Sector'] == sector].copy()
        df_sector = df_sector.sort_values('RS_Rating', ascending=True)

        if len(df_sector) == 0:
            continue

        sector_avg = df_sector['Buy_Pressure'].mean()
        rs80_count = len(df_sector[df_sector['RS_Rating'] >= 80])
        total_count = len(df_sector)
        st.markdown(f"#### 📂 {sector}（平均BP: {sector_avg:.3f}　RS≧80: {rs80_count}/{total_count}）")

        fig_sector = px.bar(
            df_sector,
            x='Buy_Pressure',
            y='Industry',
            orientation='h',
            color='RS_Rating',
            color_continuous_scale=CUSTOM_RS_COLORSCALE,
            range_color=[0, 100],
            labels={
                'Buy_Pressure': 'Buy Pressure',
                'Industry': '業種',
                'RS_Rating': 'RS Rating',
            },
        )

        fig_sector.add_vline(
            x=0.550,
            line_dash="dot",
            line_color="black",
            line_width=2,
            annotation_text="BUY (0.550)",
            annotation_position="top",
            annotation_font_size=11,
            annotation_font_color="black",
        )

        fig_sector.update_layout(
            height=max(len(df_sector) * 30 + 80, 150),
            yaxis=dict(dtick=1),
            coloraxis_colorbar=dict(title='RS Rating'),
            margin=dict(t=40, b=20),
            showlegend=False,
        )
        st.plotly_chart(fig_sector, use_container_width=True)


# ============================================================
# フッター
# ============================================================
st.markdown("---")
st.markdown(
    f"""
    <div style="text-align: center; color: gray; font-size: 12px;">
    Industry Buy Pressure Dashboard | Data: {data_date}
    </div>
    """,
    unsafe_allow_html=True
)
