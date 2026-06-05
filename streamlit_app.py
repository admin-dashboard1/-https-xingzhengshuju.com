#!/usr/bin/env python3
"""行政管理数据看板 — Streamlit 版"""

import json
import os
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# ============ 页面配置 ============
st.set_page_config(
    page_title="行政管理数据看板",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ============ 明亮清爽配色 ============
COLORS = {
    "primary": "#6366f1",
    "success": "#10b981",
    "warning": "#f59e0b",
    "danger": "#ef4444",
    "bg": "#f0f4f8",
    "text": "#1e293b",
    "text_secondary": "#475569",
    "text_muted": "#94a3b8",
    "purple": "#8b5cf6",
}

CAT_COLORS = [
    "#6366f1", "#059669", "#d97706", "#dc2626", "#8b5cf6",
    "#0891b2", "#ea580c", "#16a34a", "#2563eb", "#7c3aed",
    "#f43f5e", "#84cc16", "#14b8a6", "#a855f7", "#06b6d4",
]

RANK_COLORS = ["#d97706", "#6366f1", "#059669", "#64748b"]

DATA_DIR = os.path.join(os.path.dirname(__file__), "看板数据")

# ============ 辅助函数 ============
@st.cache_data(ttl=600)
def load_all_data():
    """加载所有 JSON 数据"""
    result = {}

    # 主数据
    try:
        with open(os.path.join(DATA_DIR, "dashboard_data.json"), encoding="utf-8") as f:
            result["main"] = json.load(f)
    except FileNotFoundError:
        result["main"] = None

    # 专项分析数据
    analysis_names = ["cleaning", "postal", "broadband", "rental", "express", "drinking_water", "asset"]
    for name in analysis_names:
        try:
            with open(os.path.join(DATA_DIR, f"{name}_analysis.json"), encoding="utf-8") as f:
                result[name] = json.load(f)
        except FileNotFoundError:
            result[name] = None

    return result


def fmt_w(num):
    """格式化为万元"""
    if num is None:
        return "-"
    if num >= 10000:
        return f"{num / 10000:.2f} 万"
    return f"{num:,.2f}"


def fmt_money(num):
    """格式化金额"""
    if num is None:
        return "-"
    return f"¥{num:,.2f}"


def fmt_int(num):
    """格式化整数"""
    if num is None:
        return "-"
    return f"{num:,}"


# ============ 加载数据 ============
all_data = load_all_data()
main_data = all_data.get("main")
analysis_data = {k: v for k, v in all_data.items() if k != "main"}

if main_data is None:
    st.error("❌ 无法加载主数据文件，请确保 data/dashboard_data.json 存在")
    st.stop()

expenses = main_data.get("expenses", {})
computers = main_data.get("computers", {})
deposits = main_data.get("deposits", {})
available_years = expenses.get("availableYears", [])
by_year = expenses.get("byYear", {})
monthly_trend = expenses.get("monthlyTrend", [])
last_updated = main_data.get("lastUpdated", "未知")


# ============ Header ============
st.markdown(
    f"""
<div style="display:flex;justify-content:space-between;align-items:center;padding-bottom:16px;border-bottom:1px solid rgba(148,163,184,0.2);margin-bottom:24px;flex-wrap:wrap;gap:12px">
    <h1 style="margin:0;font-size:24px;font-weight:800;color:{COLORS['primary']}">📊 行政管理数据看板
        <span style="font-size:10px;padding:2px 8px;border-radius:10px;background:rgba(16,185,129,0.15);color:#10b981;font-weight:700;margin-left:8px">LIVE</span>
    </h1>
    <span style="font-size:12px;color:{COLORS['text_muted']}">🕐 最后更新: {last_updated}</span>
</div>
""",
    unsafe_allow_html=True,
)


# ============ 年份筛选 ============
tab_names = [
    "💳 行政费用", "💻 资产管理", "🔒 押金台账",
    "🧹 保洁费", "📞 邮电通讯费", "📡 宽带费",
    "🏢 租赁费", "📦 快递费", "💧 饮用水",
]
tabs = st.tabs(tab_names)


# ================================================================
# Tab 1: 行政费用
# ================================================================
with tabs[0]:
    # --- 年度筛选 ---
    year_options = ["全部年份"] + [f"{y}年" for y in available_years]
    selected_year = st.selectbox("🔍 筛选年份", year_options, key="year_filter", label_visibility="collapsed")
    if selected_year == "全部年份":
        current_year = "all"
        active_expenses = expenses
    else:
        current_year = selected_year.replace("年", "")
        active_expenses = by_year.get(current_year, expenses)

    # --- 年度总览卡片 ---
    st.markdown("### 📅 年度出款总览")
    sorted_years = sorted(
        [(y, by_year.get(str(y), {})) for y in available_years],
        key=lambda x: x[1].get("totalAmount", 0) if x[1] else 0,
        reverse=True,
    )
    grand_total = expenses.get("totalAmount", 0)

    cols = st.columns(4)
    for idx, (yr, data) in enumerate(sorted_years):
        if not data:
            continue
        pct = (data.get("totalAmount", 0) / grand_total * 100) if grand_total > 0 else 0
        rank_label = ["🥇", "🥈", "🥉", "4️⃣"][idx] if idx < 4 else ""
        with cols[idx]:
            st.metric(
                label=f"{yr}年 {rank_label}",
                value=f"¥{data.get('totalAmount', 0) / 10000:.0f}万",
                delta=f"{data.get('totalCount', 0)} 笔 · 占比 {pct:.1f}%",
            )

    # --- 重复费用警告 ---
    dup = expenses.get("dupCheck", {}).get("summary")
    if dup and dup.get("totalGroups", 0) > 0:
        st.warning(
            f"⚠️ 疑似重复费用：共 **{dup['totalGroups']}** 组，涉及 **{dup['totalRecords']}** 条记录，"
            f"重复金额 **¥{dup.get('totalAmount', 0) / 10000:.1f}万**"
        )
    else:
        st.success("✅ 未发现疑似重复费用")

    # --- 年度对比 + 占比图 ---
    st.markdown("### 📊 各年度出款对比")
    col1, col2 = st.columns(2)

    with col1:
        sorted_all = sorted(
            [(y, by_year.get(str(y), {})) for y in available_years],
            key=lambda x: x[0],
        )
        year_labels = [f"{y}年" for y, _ in sorted_all]
        year_amounts = [d.get("totalAmount", 0) for _, d in sorted_all]

        fig = go.Figure(
            go.Bar(
                x=year_labels,
                y=year_amounts,
                marker_color=RANK_COLORS[: len(sorted_all)],
                text=[f"¥{a/10000:.0f}万" for a in year_amounts],
                textposition="outside",
            )
        )
        fig.update_layout(
            height=300,
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
            yaxis=dict(showgrid=True, gridcolor="rgba(148,163,184,0.15)", title=""),
            xaxis=dict(title=""),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = go.Figure(
            go.Pie(
                labels=year_labels,
                values=year_amounts,
                marker_colors=RANK_COLORS[: len(sorted_all)],
                hole=0.5,
                textinfo="label+percent",
            )
        )
        fig.update_layout(
            height=300,
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)

    # --- KPI 卡片 ---
    st.markdown("### 📈 关键指标")
    kpi_cols = st.columns(4)
    with kpi_cols[0]:
        st.metric("💰 费用总额", fmt_w(active_expenses.get("totalAmount", 0)))
    with kpi_cols[1]:
        st.metric("📊 月均费用", fmt_w(active_expenses.get("avgMonthly", 0)))
    with kpi_cols[2]:
        st.metric("📋 记录总数", fmt_int(active_expenses.get("totalCount", 0)))
    with kpi_cols[3]:
        st.metric("⚡ 今日出款", fmt_w(active_expenses.get("todayAmount", 0)))

    # --- 异常波动预警 ---
    if monthly_trend and len(monthly_trend) >= 6:
        amounts = [m["amount"] for m in monthly_trend]
        baseline = amounts[:-1]
        if len(baseline) >= 3:
            mean = sum(baseline) / len(baseline)
            variance = sum((v - mean) ** 2 for v in baseline) / len(baseline)
            std = variance ** 0.5
            last = monthly_trend[-1]
            if last["amount"] > mean + 2 * std:
                st.error(f"🚨 **{last['label']}** 异常 +{int((last['amount'] / mean - 1) * 100)}%（超出历史均值2倍标准差）")
            else:
                st.success("✅ 各项费用均在正常范围")

    # --- 月度趋势 ---
    st.markdown("### 📈 月度费用趋势")
    filtered_monthly = monthly_trend
    if current_year != "all":
        filtered_monthly = [m for m in monthly_trend if m["label"].startswith(current_year + "-")]
    else:
        filtered_monthly = [m for m in monthly_trend if int(m["label"].split("-")[0]) >= 2025]

    if filtered_monthly:
        fig = go.Figure(
            go.Scatter(
                x=[m["label"] for m in filtered_monthly],
                y=[m["amount"] for m in filtered_monthly],
                mode="lines+markers",
                line=dict(color=COLORS["primary"], width=2),
                fill="tozeroy",
                fillcolor="rgba(99,102,241,0.08)",
            )
        )
        fig.update_layout(
            height=300,
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
            yaxis=dict(showgrid=True, gridcolor="rgba(148,163,184,0.15)", tickformat=",.0f"),
            xaxis=dict(title=""),
        )
        st.plotly_chart(fig, use_container_width=True)

    # --- 费用分类 + 城市分布 ---
    st.markdown("### 📊 费用分类与城市分布")
    col1, col2 = st.columns(2)

    with col1:
        cats = active_expenses.get("categoryDistribution", [])[:10]
        if cats:
            fig = go.Figure(
                go.Pie(
                    labels=[c["name"] for c in cats],
                    values=[c["amount"] for c in cats],
                    marker_colors=CAT_COLORS[: len(cats)],
                    hole=0.5,
                )
            )
            fig.update_layout(
                height=340,
                margin=dict(l=10, r=10, t=10, b=10),
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        cities = active_expenses.get("cityDistribution", [])[:20]
        if cities:
            city_amounts = [c["amount"] for c in cities]
            city_avg = sum(city_amounts) / len(city_amounts) if city_amounts else 1
            bar_colors = []
            for amt in city_amounts:
                ratio = amt / city_avg if city_avg > 0 else 1
                if ratio > 1.5:
                    bar_colors.append(COLORS["danger"])
                elif ratio > 1.2:
                    bar_colors.append("#ea580c")
                elif ratio < 0.3:
                    bar_colors.append(COLORS["text_muted"])
                else:
                    bar_colors.append(COLORS["primary"])

            fig = go.Figure(
                go.Bar(
                    y=[c["name"] for c in cities],
                    x=city_amounts,
                    orientation="h",
                    marker_color=bar_colors,
                )
            )
            fig.update_layout(
                height=340,
                margin=dict(l=10, r=10, t=10, b=10),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                showlegend=False,
                xaxis=dict(showgrid=True, gridcolor="rgba(148,163,184,0.15)"),
                yaxis=dict(autorange="reversed"),
            )
            st.plotly_chart(fig, use_container_width=True)

    # --- 日支出热力 ---
    st.markdown("### 📅 近30天日支出")
    daily = active_expenses.get("dailyExpenses", []) or expenses.get("dailyExpenses", [])
    if daily:
        fig = go.Figure(
            go.Bar(
                x=[d["date"][5:] for d in daily[-30:]],
                y=[d["amount"] for d in daily[-30:]],
                marker_color=[
                    COLORS["danger"] if d["amount"] > 50000 else COLORS["primary"]
                    for d in daily[-30:]
                ],
            )
        )
        fig.update_layout(
            height=280,
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
            yaxis=dict(showgrid=True, gridcolor="rgba(148,163,184,0.15)", tickformat=",.0f"),
            xaxis=dict(title=""),
        )
        st.plotly_chart(fig, use_container_width=True)

    # --- 费用分类年度明细表 ---
    st.markdown("### 📋 费用分类年度明细表")
    if available_years:
        # 构建分类年度矩阵
        cat_map = {}
        for yr in available_years:
            yd = by_year.get(str(yr), {})
            for c in yd.get("categoryDistribution", []):
                cat_map.setdefault(c["name"], {})[str(yr)] = c["amount"]

        cats_sorted = sorted(
            [(name, yr_amts) for name, yr_amts in cat_map.items()],
            key=lambda x: sum(x[1].values()),
            reverse=True,
        )

        # 构建表格数据
        table_data = []
        for name, yr_amts in cats_sorted:
            row = {"费用分类": name}
            for yr in available_years:
                row[f"{yr}年"] = f"{yr_amts.get(str(yr), 0) / 10000:.1f}万"
            total = sum(yr_amts.values())
            row["合计"] = f"{total / 10000:.1f}万"
            grand = sum(sum(a.values()) for _, a in cats_sorted)
            row["占比"] = f"{total / grand * 100:.1f}%" if grand > 0 else "-"
            table_data.append(row)

        if table_data:
            st.dataframe(table_data, use_container_width=True, hide_index=True)

    # --- 最新记录 ---
    st.markdown("### 📝 最新费用记录")
    latest = active_expenses.get("latestExpenses", []) or expenses.get("latestExpenses", [])
    if latest:
        latest_rows = []
        for r in latest[:30]:
            latest_rows.append(
                {
                    "日期": r.get("date", ""),
                    "供应商": r.get("supplier", ""),
                    "城市": r.get("city", ""),
                    "分类": r.get("category", ""),
                    "金额": fmt_money(r.get("amount", 0)),
                    "用途": (r.get("purpose", "") or "")[:30],
                    "状态": r.get("status", ""),
                }
            )
        st.dataframe(latest_rows, use_container_width=True, hide_index=True)


# ================================================================
# Tab 2: 资产管理
# ================================================================
with tabs[1]:
    asset = analysis_data.get("asset")
    if asset:
        st.markdown("### 💻 电脑设备总览")
        asset_cols = st.columns(4)
        with asset_cols[0]:
            st.metric("📊 总数量", f"{asset.get('totalQty', 0)} 台")
        with asset_cols[1]:
            st.metric("🏠 自购", f"{asset.get('selfQty', 0)} 台", f"{asset.get('selfPct', 0)}%")
        with asset_cols[2]:
            st.metric("🏢 租赁", f"{asset.get('rentQty', 0)} 台", f"{asset.get('rentPct', 0)}%")
        with asset_cols[3]:
            st.metric("🌍 覆盖城市", f"{asset.get('cityCount', 0)} 城")

        col1, col2 = st.columns(2)

        # 类型分布饼图
        with col1:
            type_pie = asset.get("typePie", [])
            if type_pie:
                fig = go.Figure(
                    go.Pie(
                        labels=[t["name"] for t in type_pie],
                        values=[t["value"] for t in type_pie],
                        hole=0.5,
                        marker_colors=CAT_COLORS[: len(type_pie)],
                    )
                )
                fig.update_layout(
                    height=300,
                    margin=dict(l=10, r=10, t=10, b=10),
                    paper_bgcolor="rgba(0,0,0,0)",
                )
                st.plotly_chart(fig, use_container_width=True)

        # 城市分布
        with col2:
            city_table = asset.get("cityTable", [])[:15]
            if city_table:
                fig = go.Figure(
                    go.Bar(
                        y=[c["name"] for c in city_table],
                        x=[c["total"] for c in city_table],
                        orientation="h",
                        marker_color=COLORS["success"],
                    )
                )
                fig.update_layout(
                    height=300,
                    margin=dict(l=10, r=10, t=10, b=10),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    showlegend=False,
                    yaxis=dict(autorange="reversed"),
                )
                st.plotly_chart(fig, use_container_width=True)

        # 城市明细表
        st.markdown("### 📋 城市分布明细")
        if city_table:
            st.dataframe(
                [
                    {**c, "租赁占比": f"{c.get('rentPct', 0)}%"}
                    for c in city_table
                ],
                use_container_width=True,
                hide_index=True,
            )

        # 部门分布表
        dept_table = asset.get("deptTable", [])
        if dept_table:
            st.markdown("### 🏢 部门分布")
            st.dataframe(dept_table, use_container_width=True, hide_index=True)
    else:
        st.info("暂无资产管理数据，请先运行 asset_analysis.py 生成分析数据")


# ================================================================
# Tab 3: 押金台账
# ================================================================
with tabs[2]:
    if deposits and deposits.get("totalCount", 0) > 0:
        st.markdown("### 🔒 押金总览")
        dep_cols = st.columns(4)
        with dep_cols[0]:
            st.metric("💰 押金总额", f"¥{deposits.get('totalAmount', 0) / 10000:.1f}万")
        with dep_cols[1]:
            st.metric("✅ 已退回", f"¥{deposits.get('returnedAmount', 0) / 10000:.1f}万",
                     f"退回率 {deposits.get('returnRate', 0)}%")
        with dep_cols[2]:
            st.metric("⚠️ 未退回", f"¥{deposits.get('unreturnedAmount', 0) / 10000:.1f}万",
                     f"{deposits.get('unreturnedCount', 0)} 笔")
        with dep_cols[3]:
            st.metric("🔄 部分退回", f"¥{deposits.get('partialAmount', 0) / 10000:.1f}万",
                     f"{deposits.get('partialCount', 0)} 笔")

        col1, col2, col3 = st.columns(3)

        # 押金类型
        with col1:
            dep_types = deposits.get("byType", [])
            if dep_types:
                fig = go.Figure(
                    go.Pie(
                        labels=[t["name"] for t in dep_types],
                        values=[t["amount"] for t in dep_types],
                        hole=0.5,
                        marker_colors=CAT_COLORS[: len(dep_types)],
                    )
                )
                fig.update_layout(
                    title="押金类型分布",
                    height=300,
                    margin=dict(l=10, r=10, t=40, b=10),
                    paper_bgcolor="rgba(0,0,0,0)",
                )
                st.plotly_chart(fig, use_container_width=True)

        # 退回状态
        with col2:
            dep_status = deposits.get("byStatus", [])
            if dep_status:
                status_colors = {"已退回": COLORS["success"], "未退回": COLORS["danger"], "部分退回": COLORS["warning"]}
                fig = go.Figure(
                    go.Pie(
                        labels=[s["name"] for s in dep_status],
                        values=[s["count"] for s in dep_status],
                        hole=0.5,
                        marker_colors=[
                            status_colors.get(s["name"], "#94a3b8")
                            for s in dep_status
                        ],
                    )
                )
                fig.update_layout(
                    title="退回状态分布",
                    height=300,
                    margin=dict(l=10, r=10, t=40, b=10),
                    paper_bgcolor="rgba(0,0,0,0)",
                )
                st.plotly_chart(fig, use_container_width=True)

        # 城市分布
        with col3:
            dep_cities = deposits.get("byCity", [])[:15]
            if dep_cities:
                fig = go.Figure(
                    go.Bar(
                        y=[c["name"] for c in dep_cities],
                        x=[c["amount"] for c in dep_cities],
                        orientation="h",
                        marker_color=COLORS["warning"],
                    )
                )
                fig.update_layout(
                    title="城市分布",
                    height=300,
                    margin=dict(l=10, r=10, t=40, b=10),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    showlegend=False,
                    yaxis=dict(autorange="reversed"),
                    xaxis=dict(tickformat=",.0f"),
                )
                st.plotly_chart(fig, use_container_width=True)

        # 未退回明细
        st.markdown("### ⚠️ 未退回押金明细")
        unreturned = deposits.get("unreturnedList", [])
        if unreturned:
            st.dataframe(
                [
                    {
                        "类型": r.get("type", ""),
                        "城市": r.get("city", ""),
                        "收款方": r.get("payee", ""),
                        "金额": fmt_money(r.get("amount", 0)),
                        "付款日期": r.get("payDate", ""),
                        "负责人": r.get("person", ""),
                    }
                    for r in unreturned
                ],
                use_container_width=True,
                hide_index=True,
            )
    else:
        st.info("暂无押金台账数据")


# ================================================================
# Tab 4-9: 专项分析（保洁/邮电/宽带/租赁/快递/饮用水）
# ================================================================
def render_special_tab(tab, data, title, emoji):
    """渲染专项分析 Tab"""
    if data is None:
        st.info(f"暂无{title}分析数据，请先运行对应分析脚本")
        return

    st.markdown(f"### {emoji} {title}专项分析")

    cols = st.columns(4)
    total = data.get("totalAmount", 0)
    count = data.get("totalCount", 0)
    cities_cnt = data.get("cityCount", 0)
    avg = total / count if count > 0 else 0

    with cols[0]:
        st.metric("💰 总金额", fmt_w(total))
    with cols[1]:
        st.metric("📋 总笔数", f"{count} 笔")
    with cols[2]:
        st.metric("🌍 覆盖城市", f"{cities_cnt} 城")
    with cols[3]:
        st.metric("📊 单笔均价", fmt_w(avg))

    # 城市分布 + 年度趋势
    col1, col2 = st.columns(2)

    with col1:
        by_city = data.get("byCity", [])
        if by_city:
            fig = go.Figure(
                go.Pie(
                    labels=[c.get("name", c.get("city", "")) for c in by_city[:10]],
                    values=[c.get("amount", 0) for c in by_city[:10]],
                    hole=0.5,
                    marker_colors=CAT_COLORS[: len(by_city)],
                )
            )
            fig.update_layout(
                title="城市分布",
                height=300,
                margin=dict(l=10, r=10, t=40, b=10),
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        by_year = data.get("byYear", [])
        if by_year:
            fig = go.Figure(
                go.Bar(
                    x=[str(y.get("year", "")) for y in by_year],
                    y=[y.get("amount", 0) for y in by_year],
                    marker_color=COLORS["primary"],
                )
            )
            fig.update_layout(
                title="年度趋势",
                height=300,
                margin=dict(l=10, r=10, t=40, b=10),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                showlegend=False,
                yaxis=dict(showgrid=True, gridcolor="rgba(148,163,184,0.15)"),
            )
            st.plotly_chart(fig, use_container_width=True)

    # 重复检测
    dup_count = data.get("duplicateCount", 0)
    if dup_count > 0:
        st.warning(f"⚠️ 检测到 {dup_count} 组疑似重复记录")

    # 明细表
    details = data.get("details", [])
    if details:
        st.markdown("### 📋 明细记录")
        rows = []
        for r in details[:50]:
            rows.append(
                {
                    "日期": r.get("date", ""),
                    "城市": r.get("city", ""),
                    "用途": (r.get("purpose", "") or "")[:30],
                    "金额": f"{r.get('amount', 0):.2f}",
                    "收款方": r.get("receiver", ""),
                }
            )
        st.dataframe(rows, use_container_width=True, hide_index=True)


special_tabs = [
    (tabs[3], "cleaning", "保洁费", "🧹"),
    (tabs[4], "postal", "邮电通讯费", "📞"),
    (tabs[5], "broadband", "宽带费", "📡"),
    (tabs[6], "rental", "租赁费", "🏢"),
    (tabs[7], "express", "快递费", "📦"),
    (tabs[8], "drinking_water", "饮用水", "💧"),
]

for tab, key, title, emoji in special_tabs:
    with tab:
        render_special_tab(tab, analysis_data.get(key), title, emoji)


# ============ Footer ============
st.markdown("---")
st.markdown(
    f"<p style='text-align:center;color:{COLORS['text_muted']};font-size:11px'>"
    f"行政管理数据看板 · Streamlit 版 · 最后更新: {last_updated}"
    "</p>",
    unsafe_allow_html=True,
)
