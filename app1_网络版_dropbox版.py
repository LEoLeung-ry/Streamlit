import streamlit as st
import pandas as pd
import numpy as np
import locale
from datetime import datetime
import plotly.graph_objects as go
from io import BytesIO
import requests

# 页面基本设置
st.set_page_config(layout="wide", page_title="ASIN 日报数据分析面板")

# 处理 locale 异常（不在部署环境中设置 zh_CN.UTF-8）
try:
    locale.setlocale(locale.LC_TIME, 'zh_CN.UTF-8')
except locale.Error:
    pass

# ============ 数据加载函数 ============


@st.cache_data
def load_data():
    url = "https://www.dropbox.com/scl/fi/qzlknx8jkios4g6b5oz4q/ad_data.xlsx?rlkey=sx84p1ckfscu021hw3rfqck5d&st=7h850cfb&dl=1"
    response = requests.get(url)
    if response.status_code != 200:
        raise ValueError("无法下载数据文件，请检查 Dropbox 链接是否正确")
    data = BytesIO(response.content)
    df = pd.read_excel(data, sheet_name="源")
    df["日期"] = pd.to_datetime(df["日期"], errors='coerce')
    df = df.dropna(subset=["日期"])
    return df


df = load_data()

# ============ 页面标题 ============
st.title("ASIN 日报数据分析面板")

# ============ ASIN & 日期 选择 ============
asin_list = df["ASIN"].dropna().unique().tolist()
selected_asin = st.selectbox("请选择 ASIN", asin_list)

min_date = df["日期"].min().date()
max_date = df["日期"].max().date()
selected_date = st.date_input("选择日期范围", [min_date, max_date], format="YYYY/MM/DD")
start_date = pd.to_datetime(selected_date[0])
end_date = pd.to_datetime(selected_date[1])

# ============ 数据过滤 ============
filtered_df = df[
    (df["ASIN"] == selected_asin) &
    (df["日期"] >= start_date) &
    (df["日期"] <= end_date)
].copy()
if filtered_df.empty:
    st.warning("当前筛选条件下无数据。")
    st.stop()

# ============ 广告花费处理 ============
ad_cost_columns = ["花费-SP广告", "花费-SD广告", "花费-SB广告", "花费-SBV广告"]
existing_cost_columns = [col for col in ad_cost_columns if col in filtered_df.columns]
if existing_cost_columns:
    filtered_df["广告花费"] = filtered_df[existing_cost_columns].sum(axis=1)
else:
    filtered_df["广告花费"] = 0

# CPA & ACOS 处理
filtered_df["CPA"] = pd.to_numeric(filtered_df.get("CPA"), errors="coerce")
filtered_df["ACOS"] = (
    filtered_df["ACOS"]
    .replace("--", pd.NA)
    .astype(str)
    .str.replace("%", "", regex=False)
)
filtered_df["ACOS"] = pd.to_numeric(filtered_df["ACOS"], errors="coerce") / 100

# 转化率计算
filtered_df["访客转化率_num"] = np.where(
    filtered_df["Sessions-Total"] > 0,
    filtered_df["销量"] / filtered_df["Sessions-Total"],
    np.nan
)
filtered_df["CR_num"] = np.where(
    filtered_df["点击"] > 0,
    filtered_df["广告订单量"] / filtered_df["点击"],
    np.nan
)

# ============ 顶部指标 ============
col1, col2, col3, col4 = st.columns(4)
total_sales = pd.to_numeric(filtered_df["销售额"], errors='coerce').sum()
col1.metric("总销售额", f"{total_sales:,.0f} 円")

ad_cost_sum = pd.to_numeric(filtered_df["广告花费"], errors='coerce').sum()
col2.metric("广告花费（估）", f"{ad_cost_sum:,.0f} 円")

visitor_total = pd.to_numeric(filtered_df["Sessions-Total"], errors='coerce').sum()
col3.metric("访客数", f"{visitor_total:,.0f}")

acos_avg = filtered_df["ACOS"].mean()
col4.metric("ACOS (平均)", f"{acos_avg:.2%}" if pd.notnull(acos_avg) else "无效")

# ============ 显示格式 ============
filtered_df["访客转化率"] = filtered_df["访客转化率_num"].apply(
    lambda x: f"{x:.2%}" if pd.notnull(x) else "--"
)
filtered_df["CR"] = filtered_df["CR_num"].apply(
    lambda x: f"{x:.2%}" if pd.notnull(x) else "--"
)
filtered_df["ACOS"] = filtered_df["ACOS"].apply(
    lambda x: f"{x:.2%}" if pd.notnull(x) and not np.isnan(x) and x != float('inf') else "--"
)
filtered_df["CPA"] = filtered_df["CPA"].apply(
    lambda x: f"{x:,.0f}" if pd.notnull(x) else "--"
)

if "CPC" in filtered_df.columns:
    filtered_df["CPC"] = pd.to_numeric(filtered_df["CPC"], errors="coerce").apply(
        lambda x: f"{x:.1f}" if pd.notnull(x) else "--"
    )
filtered_df["广告花费"] = pd.to_numeric(filtered_df["广告花费"], errors="coerce").apply(
    lambda x: f"{x:,.0f}" if pd.notnull(x) else "--"
)
if "平均客单价(折后)" in filtered_df.columns:
    filtered_df["平均客单价(折后)"] = pd.to_numeric(filtered_df["平均客单价(折后)"], errors="coerce").apply(
        lambda x: f"{x:,.0f}" if pd.notnull(x) else "--"
    )

# ============ 表格列 & 多级表头 ============
columns_to_show = [
    "日期", "店铺", "Sessions-Total", "销量", "订单量", "访客转化率", "CVR", "销售额", "平均客单价(折后)",
    "展示", "点击", "CTR", "CPC", "广告订单量", "广告销售额", "CR", "广告花费", "CPA", "ACOS"
]
for col in columns_to_show:
    if col not in filtered_df.columns:
        filtered_df[col] = "--"
display_df = filtered_df[columns_to_show].copy()

display_df["日期"] = pd.to_datetime(display_df["日期"]).dt.strftime('%Y-%m-%d')
display_df.columns = [
    "日期", "店铺", "访客数", "销量", "订单数", "访客转化率", "转化率", "销售额", "客单价(折后)",
    "Impressions", "Click", "CTR", "CPC-SP", "广告订单", "广告销售额", "CR", "广告花费", "CPA", "ACOS"
]
header_level_0 = ["整体数据"] * 9 + ["广告数据"] * 10
header_level_1 = list(display_df.columns)
multi_header = pd.MultiIndex.from_arrays([header_level_0, header_level_1])
display_df.columns = multi_header

def stripe_rows(df):
    n_rows, n_cols = df.shape
    styles = []
    for i in range(n_rows):
        row_style = []
        for j in range(n_cols):
            row_style.append("background-color: #f9f9f9" if i % 2 == 0 else "background-color: white")
        styles.append(row_style)
    return pd.DataFrame(styles, columns=df.columns, index=df.index)

# ============ 表格展示 ============
st.subheader("每日维度数据明细")
styled_df = (
    display_df.style
    .set_table_styles([
        {"selector": "thead th", "props": [("font-weight", "bold"), ("background-color", "#f0f2f6"), ("color", "#000")]},
        {"selector": "thead tr", "props": [("border-bottom", "1px solid #bbb")]}
    ])
    .apply(stripe_rows, axis=None)
)
st.dataframe(styled_df, use_container_width=True)

# ============ 下载 ============
csv_data = display_df.droplevel(0, axis=1).to_csv(index=False, encoding="utf-8-sig")
st.download_button(
    "下载筛选数据 CSV",
    csv_data,
    file_name=f"ASIN日报_{selected_asin}.csv",
    mime='text/csv'
)

# ============ 图表绘制 ============
chart_df = df[
    (df["ASIN"] == selected_asin) &
    (df["日期"] >= start_date) &
    (df["日期"] <= end_date)
].copy()
chart_df["访客转化率_num"] = np.where(
    chart_df["Sessions-Total"] > 0,
    chart_df["销量"] / chart_df["Sessions-Total"],
    np.nan
)
chart_df["CR_num"] = np.where(
    chart_df["点击"] > 0,
    chart_df["广告订单量"] / chart_df["点击"],
    np.nan
)
chart_df["Sessions-Total"] = pd.to_numeric(chart_df["Sessions-Total"], errors="coerce")
chart_df["点击"] = pd.to_numeric(chart_df["点击"], errors="coerce")
chart_df.dropna(subset=["Sessions-Total", "点击", "访客转化率_num", "CR_num"], inplace=True)
chart_df.sort_values(by="日期", inplace=True)

if not chart_df.empty:
    chart_df["访客转化率_MA30"] = chart_df["访客转化率_num"].rolling(window=30).mean()
    chart_df["CR_MA30"] = chart_df["CR_num"].rolling(window=30).mean()
    chart_df["日期字符串"] = chart_df["日期"].dt.strftime("%Y-%m-%d")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=chart_df["日期字符串"], y=chart_df["Sessions-Total"], mode='lines+markers', name='访客'))
    fig.add_trace(go.Scatter(x=chart_df["日期字符串"], y=chart_df["点击"], mode='lines+markers', name='点击'))
    fig.add_trace(go.Bar(x=chart_df["日期字符串"], y=chart_df["访客转化率_num"], name='访客转化率', yaxis='y2'))
    fig.add_trace(go.Bar(x=chart_df["日期字符串"], y=chart_df["CR_num"], name='广告转化率', yaxis='y2'))
    fig.add_trace(go.Scatter(x=chart_df["日期字符串"], y=chart_df["访客转化率_MA30"], name='访客转化率-30MA', yaxis='y2', line=dict(dash='dot')))
    fig.add_trace(go.Scatter(x=chart_df["日期字符串"], y=chart_df["CR_MA30"], name='广告转化率-30MA', yaxis='y2', line=dict(dash='dot')))
    fig.update_layout(
        title="访客 & 点击 vs 转化率",
        height=600,
        xaxis=dict(title="日期"),
        yaxis=dict(title="流量"),
        yaxis2=dict(title="转化率", overlaying='y', side='right', tickformat='.0%'),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5)
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("暂无足够数据绘制图表。")
