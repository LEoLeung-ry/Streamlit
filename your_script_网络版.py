import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

# ============== 页面基础配置 ==============
st.set_page_config(layout="wide", page_title="产品月度 & 日度数据面板")

# ============== 数据读取函数 ==============
@st.cache_data
def load_data():
    df = pd.read_excel("https://drive.google.com/uc?export=download&id=1gz9qZdjeMZN_I-pc0u7XhD1kGAr6nZmx", sheet_name="源")
    df["日期"] = pd.to_datetime(df["日期"], errors="coerce")
    df = df.dropna(subset=["日期"])
    return df

df = load_data()

# ============== 日期筛选组件 ==============
min_date = df["日期"].min().date() if not df.empty else datetime.today().date()
max_date = df["日期"].max().date() if not df.empty else datetime.today().date()

st.title("产品历史销量数据看板")

selected_date = st.date_input("请选择日期范围", [min_date, max_date])
start_date = pd.to_datetime(selected_date[0])
end_date = pd.to_datetime(selected_date[1])

# ============== 筛选日期范围数据 ==============
filtered_df = df[(df["日期"] >= start_date) & (df["日期"] <= end_date)].copy()

# ============== 搜索框: SKU/品名/标题 ==============
search_keyword = st.text_input(
    "🔍 输入关键词（支持 SKU / 品名 / 标题 部分匹配）",
    value=""
)

if search_keyword.strip():
    keyword = search_keyword.strip().lower()
    filtered_df = filtered_df[
        filtered_df["SKU"].astype(str).str.lower().str.contains(keyword, na=False) |
        filtered_df["品名"].astype(str).str.lower().str.contains(keyword, na=False) |
        filtered_df["标题"].astype(str).str.lower().str.contains(keyword, na=False)
    ]

if filtered_df.empty:
    st.warning("当前筛选条件下无数据，请重新选择日期或输入关键词。")
    st.stop()

# ============== 1. 按品名 + 月份汇总 ==============
st.header("1. 每个产品的历史月销量（按品名 + 月份）")
filtered_df["year_month"] = filtered_df["日期"].dt.to_period("M")
monthly_summary = (
    filtered_df.groupby(["品名", "year_month"], dropna=True)
    .agg({"销量": "sum", "订单量": "sum", "销售额(折后)": "sum", "退款量": "sum"})
    .reset_index()
    .rename(columns={"销量": "月销量", "订单量": "月订单量", "销售额(折后)": "月销售额(折后)", "退款量": "月退款量"})
)
st.dataframe(monthly_summary, use_container_width=True)

# ============== 2. 按 品名 + ASIN + 月份汇总 ==============
st.header("2. 每个产品下各 ASIN 的历史月销量（品名 + ASIN + 月份）")
monthly_summary_asin = (
    filtered_df.groupby(["品名", "ASIN", "year_month"], dropna=True)
    .agg({"销量": "sum", "订单量": "sum", "销售额(折后)": "sum"})
    .reset_index()
    .rename(columns={"销量": "月销量", "订单量": "月订单量", "销售额(折后)": "月销售额(折后)"})
)
st.dataframe(monthly_summary_asin, use_container_width=True)

# ============== 3. 日级明细数据 ==============
st.header("3. 按日维度的数据明细")

# 数据预处理
daily_cols = [
    "日期", "Sessions-Total", "销量", "订单量", "CVR", "销售额", "平均客单价(折后)",
    "展示", "点击", "CTR", "CPC", "广告订单量", "广告销售额", "ACOS"
]
for col in daily_cols:
    filtered_df[col] = pd.to_numeric(filtered_df[col], errors="coerce").fillna(0)

filtered_df["\u8bbf\u5ba2\u8f6c\u5316\u7387"] = np.where(filtered_df["Sessions-Total"] > 0, filtered_df["\u9500\u91cf"] / filtered_df["Sessions-Total"], np.nan)
filtered_df["\u5e7f\u544aCR"] = np.where(filtered_df["\u70b9\u51fb"] > 0, filtered_df["\u5e7f\u544a\u8ba2\u5355\u91cf"] / filtered_df["\u70b9\u51fb"], np.nan)
filtered_df["\u5e7f\u544a\u82b1\u8d39"] = filtered_df["\u70b9\u51fb"] * filtered_df["\u5e7f\u544a\u8ba2\u5355\u91cf"]

# 最终显示表
final_df = filtered_df[[
    "日期", "Sessions-Total", "销量", "订单量", "访客转化率", "CVR", "销售额", "平均客单价(折后)",
    "展示", "点击", "CTR", "CPC", "广告订单量", "广告销售额", "广告CR", "广告花费", "ACOS"
]].copy()

final_df.rename(columns={
    "Sessions-Total": "访客", "订单量": "订单数", "平均客单价(折后)": "客单价(折后)",
    "展示": "Impressions", "点击": "Click", "CPC": "CPC-SP", "广告订单量": "广告订单",
    "广告销售额": "广告销售额", "广告CR": "CR"
}, inplace=True)

final_df["\u65e5\u671f"] = pd.to_datetime(final_df["\u65e5\u671f"]).dt.strftime("%Y-%m-%d")
final_df.sort_values("\u65e5\u671f", inplace=True)

st.dataframe(final_df, use_container_width=True)

# ============== 下载 ==============
csv = final_df.to_csv(index=False, encoding="utf-8-sig")
st.download_button("\u4e0b\u8f7d\u5f53\u524d\u65e5\u5ea6\u660e\u7ec6 (CSV)", csv, file_name="\u65e5\u5ea6\u660e\u7ec6.csv", mime="text/csv")
