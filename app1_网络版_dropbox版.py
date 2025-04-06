import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.graph_objects as go
from io import BytesIO
import requests

# ✅ Streamlit 配置（不使用 locale 设置，兼容云部署）
st.set_page_config(layout="wide", page_title="ASIN 日报数据分析面板")

# ✅ 数据加载函数（从 Dropbox 读取）
@st.cache_data
def load_data():
    url = "https://www.dropbox.com/scl/fi/qzlknx8jkios4g6b5oz4q/ad_data.xlsx?rlkey=sx84p1ckfscu021hw3rfqck5d&st=7h850cfb&dl=1"
    response = requests.get(url)
    if response.status_code != 200:
        raise ValueError("无法下载数据文件，请检查 Dropbox 链接是否正确")
    data = BytesIO(response.content)
    df = pd.read_excel(data, sheet_name="源")
    df["日期"] = pd.to_datetime(df["日期"], errors="coerce")
    df = df.dropna(subset=["日期"])
    return df

df = load_data()

# ✅ 页面标题
st.title("ASIN 日报数据分析面板")

# ✅ ASIN选择器 & 日期范围选择
asin_list = df["ASIN"].dropna().unique().tolist()
selected_asin = st.selectbox("请选择 ASIN", asin_list)

min_date = df["日期"].min().date()
max_date = df["日期"].max().date()
selected_date = st.date_input("选择日期范围", [min_date, max_date], format="YYYY/MM/DD")
start_date = pd.to_datetime(selected_date[0])
end_date = pd.to_datetime(selected_date[1])

# ✅ 数据过滤
filtered_df = df[
    (df["ASIN"] == selected_asin) & 
    (df["日期"] >= start_date) & 
    (df["日期"] <= end_date)
].copy()

if filtered_df.empty:
    st.warning("当前筛选条件下无数据。")
    st.stop()

# ✅ 广告花费列合并
ad_cost_columns = ["花费-SP广告", "花费-SD广告", "花费-SB广告", "花费-SBV广告"]
existing_cost_columns = [col for col in ad_cost_columns if col in filtered_df.columns]
filtered_df["广告花费"] = filtered_df[existing_cost_columns].sum(axis=1) if existing_cost_columns else 0

# ✅ 字段清洗
filtered_df["CPA"] = pd.to_numeric(filtered_df.get("CPA"), errors="coerce")
filtered_df["ACOS"] = (
    filtered_df["ACOS"]
    .replace("--", pd.NA)
    .astype(str)
    .str.replace("%", "", regex=False)
)
filtered_df["ACOS"] = pd.to_numeric(filtered_df["ACOS"], errors="coerce") / 100

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

# ✅ 指标卡片
col1, col2, col3, col4 = st.columns(4)
col1.metric("总销售额", f"{pd.to_numeric(filtered_df['销售额'], errors='coerce').sum():,.0f} 円")
col2.metric("广告花费（估）", f"{pd.to_numeric(filtered_df['广告花费'], errors='coerce').sum():,.0f} 円")
col3.metric("访客数", f"{pd.to_numeric(filtered_df['Sessions-Total'], errors='coerce').sum():,.0f}")
acos_avg = filtered_df["ACOS"].mean()
col4.metric("ACOS (平均)", f"{acos_avg:.2%}" if pd.notnull(acos_avg) else "无效")

# ✅ 字段格式化
filtered_df["访客转化率"] = filtered_df["访客转化率_num"].apply(lambda x: f"{x:.2%}" if pd.notnull(x) else "--")
filtered_df["CR"] = filtered_df["CR_num"].apply(lambda x: f"{x:.2%}" if pd.notnull(x) else "--")
filtered_df["ACOS"] = filtered_df["ACOS"].apply(lambda x: f"{x:.2%}" if pd.notnull(x) else "--")
filtered_df["CPA"] = filtered_df["CPA"].apply(lambda x: f"{x:,.0f}" if pd.notnull(x) else "--")

if "CPC" in filtered_df.columns:
    filtered_df["CPC"] = pd.to_numeric(filtered_df["CPC"], errors="coerce").apply(lambda x: f"{x:.1f}" if pd.notnull(x) else "--")

filtered_df["广告花费"] = pd.to_numeric(filtered_df["广告花费"], errors="coerce").apply(lambda x: f"{x:,.0f}" if pd.notnull(x) else "--")

if "平均客单价(折后)" in filtered_df.columns:
    filtered_df["平均客单价(折后)"] = pd.to_numeric(filtered_df["平均客单价(折后)"], errors="coerce").apply(lambda x: f"{x:,.0f}" if pd.notnull(x) else "--")

# ✅ 展示字段顺序
columns_to_show = [
    "日期", "店铺", "Sessions-Total", "销量", "订单量", "访客转化率", "CVR", "销售额", "平均客单价(折后)",
    "展示", "点击", "CTR", "CPC", "广告订单量", "广告销售额", "CR", "广告花费", "CPA", "ACOS"
]
for col in columns_to_show:
    if col not in filtered_df.columns:
        filtered_df[col] = "--"
display_df = filtered_df[columns_to_show].copy()

# ✅ 表头格式 & 日期格式
display_df["日期"] = pd.to_datetime(display_df["日期"]).dt.strftime('%Y-%m-%d')
display_df.columns = [
    "日期", "店铺", "访客数", "销量", "订单数", "访客转化率", "转化率", "销售额", "客单价(折后)",
    "Impressions", "Click", "CTR", "CPC-SP", "广告订单", "广告销售额", "CR", "广告花费", "CPA", "ACOS"
]
display_df.columns = pd.MultiIndex.from_arrays([
    ["整体数据"] * 9 + ["广告数据"] * 10,
    display_df.columns
])

# ✅ 条纹背景
def stripe_rows(df):
    n_rows, n_cols = df.shape
    return pd.DataFrame(
        [["background-color: #f9f9f9" if i % 2 == 0 else "background-color: white" for j in range(n_cols)] for i in range(n_rows)],
        columns=df.columns, index=df.index
    )

# ✅ 展示表格
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

# ✅ 下载按钮
csv_data = display_df.droplevel(0, axis=1).to_csv(index=False, encoding="utf-8-sig")
st.download_button("下载筛选数据 CSV", csv_data, file_name=f"ASIN日报_{selected_asin}.csv", mime="text/csv")

# ✅ 图表绘制
chart_df = df[(df["ASIN"] == selected_asin) & (df["日期"] >= start_date) & (df["日期"] <= end_date)].copy()
chart_df["访客转化率_num"] = np.where(chart_df["Sessions-Total"] > 0, chart_df["销量"] / chart_df["Sessions-Total"], np.nan)
chart_df["CR_num"] = np.where(chart_df["点击"] > 0, chart_df["广告订单量"] / chart_df["点击"], np.nan)
chart_df["Sessions-Total"] = pd.to_numeric(chart_df["Sessions-Total"], errors="coerce")
chart_df["点击"] = pd.to_numeric(chart_df["点击"], errors="coerce")
chart_df.dropna(subset=["Sessions-Total", "点击", "访客转化率_num", "CR_num"], inplace=True)
chart_df.sort_values("日期", inplace=True)

if not chart_df.empty:
    chart_df["访客转化率_MA30"] = chart_df["访客转化率_num"].rolling(30).mean()
    chart_df["CR_MA30"] = chart_df["CR_num"].rolling(30).mean()
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
        yaxis2=dict(title="转化率", overlaying="y", side="right", tickformat=".0%"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5)
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("暂无足够数据绘制图表。")
