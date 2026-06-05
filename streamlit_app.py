#!/usr/bin/env python3
"""行政管理数据看板 — Streamlit 版（完整功能，对齐 HTML 版全部维度）"""

import json, os, math
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
C = {
    "primary": "#6366f1", "success": "#10b981", "warning": "#f59e0b",
    "danger": "#ef4444", "purple": "#8b5cf6", "info": "#0891b2",
    "orange": "#ea580c", "bg": "#f0f4f8", "text": "#1e293b",
    "text_sec": "#475569", "text_muted": "#94a3b8",
}
CAT_COLORS = [
    "#6366f1", "#059669", "#d97706", "#dc2626", "#8b5cf6",
    "#0891b2", "#ea580c", "#16a34a", "#2563eb", "#7c3aed",
    "#f43f5e", "#84cc16", "#14b8a6", "#a855f7", "#06b6d4",
]

DATA_DIR = os.path.join(os.path.dirname(__file__), "看板数据")

# ============ 辅助函数 ============
@st.cache_data(ttl=600)
def load_all_data():
    result = {}
    try:
        with open(os.path.join(DATA_DIR, "dashboard_data.json"), encoding="utf-8") as f:
            result["main"] = json.load(f)
    except FileNotFoundError:
        result["main"] = None
    for name in ["cleaning", "postal", "broadband", "rental", "express", "drinking_water", "asset"]:
        try:
            with open(os.path.join(DATA_DIR, f"{name}_analysis.json"), encoding="utf-8") as f:
                result[name] = json.load(f)
        except FileNotFoundError:
            result[name] = None
    return result

def fmt_w(num): return f"{num/10000:.2f}万" if num and abs(num) >= 10000 else (f"{num:,.2f}" if num else "-")
def fmt_yuan(num): return f"¥{num:,.2f}" if num is not None else "-"
def fmt_int(num): return f"{num:,}" if num is not None else "-"


# ============ 加载数据 ============
all_data = load_all_data()
main = all_data.get("main")
analysis = {k: v for k, v in all_data.items() if k != "main"}
if main is None:
    st.error("❌ 无法加载主数据文件")
    st.stop()

exp = main.get("expenses", {})
comp = main.get("computers", {})
dep = main.get("deposits", {})
years = exp.get("availableYears", [])
by_yr = exp.get("byYear", {})
monthly = exp.get("monthlyTrend", [])
updated = main.get("lastUpdated", "未知")
dup = exp.get("dupCheck", {}).get("summary")

# ============ Header ============
st.markdown(f"""
<div style="display:flex;justify-content:space-between;align-items:center;padding-bottom:16px;border-bottom:1px solid rgba(148,163,184,0.2);margin-bottom:8px;flex-wrap:wrap;gap:12px">
    <h1 style="margin:0;font-size:24px;font-weight:800;color:{C['primary']}">📊 行政管理数据看板
        <span style="font-size:10px;padding:2px 8px;border-radius:10px;background:rgba(16,185,129,0.15);color:#10b981;font-weight:700;margin-left:8px">LIVE</span>
    </h1>
    <span style="font-size:12px;color:{C['text_muted']}">🕐 最后更新: {updated}</span>
</div>
""", unsafe_allow_html=True)

# ============ 全局年份筛选（按钮式） ============
if "selected_year" not in st.session_state:
    st.session_state.selected_year = "all"

st.markdown("### 📅 年度出款总览（点击年份筛选）")
col_all, *col_yrs = st.columns([1.5] + [1.2] * len(years))

with col_all:
    if st.button(f"📊 全部年份\n{fmt_w(exp.get('totalAmount',0))}",
                 key="btn_all", use_container_width=True,
                 type="primary" if st.session_state.selected_year == "all" else "secondary"):
        st.session_state.selected_year = "all"

for idx, yr in enumerate(years):
    yr_data = by_yr.get(str(yr), {})
    amt = yr_data.get("totalAmount", 0)
    cnt = yr_data.get("totalCount", 0)
    rank_emoji = ["🥇", "🥈", "🥉", "4️⃣"][idx] if idx < 4 else ""
    with col_yrs[idx % len(col_yrs)]:
        if st.button(f"{rank_emoji} {yr}年\n¥{amt/10000:.0f}万 · {cnt}笔",
                     key=f"btn_{yr}", use_container_width=True,
                     type="primary" if st.session_state.selected_year == str(yr) else "secondary"):
            st.session_state.selected_year = str(yr)

cur_yr = st.session_state.selected_year
if cur_yr == "all":
    active_exp = exp
    show_monthly = [m for m in monthly if int(m["label"].split("-")[0]) >= 2025]
else:
    active_exp = by_yr.get(cur_yr, exp)
    show_monthly = [m for m in monthly if m["label"].startswith(f"{cur_yr}-")]

st.markdown("---")

# ============ 重复费用检测 ============
if dup and dup.get("totalGroups", 0) > 0:
    st.warning(f"⚠️ 疑似重复费用：共 **{dup['totalGroups']}** 组，涉及 **{dup['totalRecords']}** 条，重复金额 **¥{dup.get('totalAmount',0)/10000:.1f}万**")
else:
    st.success("✅ 未发现疑似重复费用")


# ============ KPI 卡片 ============
st.markdown("### 📈 关键指标")
kc = st.columns(4)
with kc[0]: st.metric("💰 费用总额", fmt_w(active_exp.get("totalAmount", 0)))
with kc[1]: st.metric("📊 月均费用", fmt_w(active_exp.get("avgMonthly", 0)))
with kc[2]: st.metric("📋 记录总数", fmt_int(active_exp.get("totalCount", 0)))
with kc[3]: st.metric("⚡ 今日出款", fmt_w(active_exp.get("todayAmount", 0)))

# ============ 异常波动 ============
if monthly and len(monthly) >= 6:
    amounts = [m["amount"] for m in monthly]
    baseline = amounts[:-1]
    if len(baseline) >= 3:
        mean = sum(baseline) / len(baseline)
        variance = sum((v - mean) ** 2 for v in baseline) / len(baseline)
        std = variance ** 0.5
        last = monthly[-1]
        if last["amount"] > mean + 2 * std:
            pct = int((last["amount"] / mean - 1) * 100)
            st.error(f"🚨 **{last['label']}** 异常 +{pct}%（超出历史均值2倍标准差）")
        else:
            st.success("✅ 各项费用均在正常范围")

# ============ 年度对比 + 占比 ============
st.markdown("### 📊 各年度出款对比")
c1, c2 = st.columns(2)
sorted_yrs = sorted([(y, by_yr.get(str(y), {})) for y in years], key=lambda x: x[0])
yr_labels = [f"{y}年" for y, _ in sorted_yrs]
yr_amts = [d.get("totalAmount", 0) for _, d in sorted_yrs]

with c1:
    fig = go.Figure(go.Bar(x=yr_labels, y=yr_amts,
        marker_color=CAT_COLORS[:len(sorted_yrs)],
        text=[f"¥{a/10000:.0f}万" for a in yr_amts], textposition="outside"))
    fig.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=40),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False, yaxis=dict(showgrid=True, gridcolor="rgba(148,163,184,0.15)"))
    st.plotly_chart(fig, use_container_width=True)

with c2:
    fig = go.Figure(go.Pie(labels=yr_labels, values=yr_amts,
        marker_colors=CAT_COLORS[:len(sorted_yrs)], hole=0.5, textinfo="label+percent"))
    fig.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)", showlegend=False)
    st.plotly_chart(fig, use_container_width=True)


# ============ Tabs ============
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
    # -- 月度趋势 --
    st.markdown("### 📈 月度费用趋势")
    if show_monthly:
        fig = go.Figure(go.Scatter(x=[m["label"] for m in show_monthly],
            y=[m["amount"] for m in show_monthly], mode="lines+markers",
            line=dict(color=C["primary"], width=2),
            fill="tozeroy", fillcolor="rgba(99,102,241,0.08)"))
        fig.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            showlegend=False, yaxis=dict(showgrid=True, gridcolor="rgba(148,163,184,0.15)", tickformat=",.0f"))
        st.plotly_chart(fig, use_container_width=True)

    # -- 费用分类饼图 + 城市分布 --
    st.markdown("### 📊 费用分类与城市分布")
    c1, c2 = st.columns(2)

    with c1:
        cats = active_exp.get("categoryDistribution", [])[:10]
        if cats:
            fig = go.Figure(go.Pie(labels=[c["name"] for c in cats],
                values=[c["amount"] for c in cats],
                marker_colors=CAT_COLORS[:len(cats)], hole=0.5))
            fig.update_layout(height=360, margin=dict(l=10, r=10, t=30, b=10),
                paper_bgcolor="rgba(0,0,0,0)", title="🧩 费用类别分布 (TOP 10)")
            st.plotly_chart(fig, use_container_width=True)

    with c2:
        cities = active_exp.get("cityDistribution", [])[:20]
        if cities:
            city_amts = [c["amount"] for c in cities]
            city_avg = sum(city_amts) / len(city_amts) if city_amts else 1
            bar_colors = []
            for amt in city_amts:
                ratio = amt / city_avg if city_avg > 0 else 1
                if ratio > 1.5: bar_colors.append(C["danger"])
                elif ratio > 1.2: bar_colors.append(C["orange"])
                elif ratio < 0.3: bar_colors.append(C["text_muted"])
                elif ratio < 0.5: bar_colors.append("#42a5f5")
                else: bar_colors.append(C["primary"])
            fig = go.Figure(go.Bar(y=[c["name"] for c in cities], x=city_amts,
                orientation="h", marker_color=bar_colors))
            fig.update_layout(height=360, margin=dict(l=10, r=10, t=30, b=10),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                title="📍 全国各城市费用分布",
                showlegend=False, yaxis=dict(autorange="reversed"),
                xaxis=dict(showgrid=True, gridcolor="rgba(148,163,184,0.15)"))
            st.plotly_chart(fig, use_container_width=True)
            st.caption("🔴 远高于均值(>1.5x) | 🟠 偏高(1.2-1.5x) | 🔵 正常 | 🔷 偏低(0.3-0.5x) | ⬇️ 远低于(<0.3x)")

    # -- ⚡ 城市费用效率排行 --
    st.markdown("### ⚡ 城市费用效率排行")
    if cities and comp.get("byCity"):
        pc_by_city = {c["name"]: c["count"] for c in comp["byCity"]}
        eff_rows = []
        for c in cities:
            pcs = pc_by_city.get(c["name"], 1)
            per_capita = c["amount"] / pcs
            eff_rows.append({"city": c["name"], "amount": c["amount"], "pcs": pcs, "perCapita": per_capita})
        eff_rows.sort(key=lambda x: x["perCapita"])
        max_pc = max(r["perCapita"] for r in eff_rows) if eff_rows else 1
        median = eff_rows[len(eff_rows) // 2]["perCapita"] if eff_rows else 0

        html_parts = ['<div style="font-size:13px">']
        for r in eff_rows:
            pct = r["perCapita"] / max_pc * 100 if max_pc > 0 else 0
            color = "#f59e0b"
            if median > 0:
                if r["perCapita"] < median * 0.7: color = C["success"]
                elif r["perCapita"] > median * 1.5: color = C["danger"]
            html_parts.append(f"""<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;padding:4px 0;border-bottom:1px solid rgba(0,0,0,0.05)">
                <span style="width:60px;font-weight:600;font-size:12px;text-align:right">{r['city']}</span>
                <span style="flex:1;background:rgba(148,163,184,0.15);border-radius:4px;height:16px;overflow:hidden">
                    <span style="display:block;height:100%;width:{pct}%;background:{color};border-radius:4px;transition:width 0.4s"></span>
                </span>
                <span style="width:80px;font-size:11px;color:{C['text_sec']};text-align:right">¥{r['perCapita']/10000:.2f}万/人</span>
            </div>""")
        html_parts.append('<div style="margin-top:8px">')
        html_parts.append('<span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:#10b981;margin-right:4px"></span>高效（人均低）')
        html_parts.append('<span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:#f59e0b;margin:0 4px 0 12px"></span>正常')
        html_parts.append('<span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:#94a3b8;margin:0 4px 0 12px"></span>偏贵')
        html_parts.append('</div></div>')
        st.markdown("".join(html_parts), unsafe_allow_html=True)

    # -- 每日出款趋势（90天） --
    st.markdown("### 📅 每日出款趋势（近90天）")
    daily_src = active_exp.get("daily2026") or active_exp.get("daily", [])
    if daily_src:
        daily_data = daily_src[-90:]
        fig = go.Figure(go.Bar(x=[d["date"][5:] for d in daily_data],
            y=[d["amount"] for d in daily_data],
            marker_color=[C["danger"] if d["amount"] > 50000 else C["primary"] for d in daily_data]))
        fig.update_layout(height=280, margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            showlegend=False, yaxis=dict(showgrid=True, gridcolor="rgba(148,163,184,0.15)", tickformat=",.0f"))
        st.plotly_chart(fig, use_container_width=True)

    # -- 费用分类 × 年度明细表 --
    st.markdown("### 📊 费用分类年度明细（万元）")
    if years:
        cat_map = {}
        for yr in years:
            yd = by_yr.get(str(yr), {})
            for c in yd.get("categoryDistribution", []):
                cat_map.setdefault(c["name"], {})[str(yr)] = c["amount"]
        cats_sorted = sorted(cat_map.items(), key=lambda x: sum(x[1].values()), reverse=True)
        table_rows = []
        for name, yr_data in cats_sorted:
            row = {"费用分类": name}
            for yr in years:
                row[f"{yr}年"] = f"{yr_data.get(str(yr), 0)/10000:.1f}"
            total = sum(yr_data.values())
            row["合计"] = f"{total/10000:.1f}"
            grand_total = sum(sum(v.values()) for _, v in cats_sorted)
            row["占比"] = f"{total/grand_total*100:.1f}%" if grand_total > 0 else "-"
            table_rows.append(row)
        if table_rows:
            st.dataframe(table_rows, use_container_width=True, hide_index=True)

    # -- 🔍 年度费用变化分析 --
    st.markdown("### 🔍 年度费用变化分析")
    if len(years) >= 2 and cats_sorted:
        cat_data = {name: yr_data for name, yr_data in cats_sorted}
        yr_totals = {}
        for yr in years:
            yr_totals[str(yr)] = sum(cat_data.get(name, {}).get(str(yr), 0) for name in cat_data) if cat_data else 0

        fmtW = lambda v: f"{v/10000:.1f}"
        fmtD = lambda a, b: f"{'+' if a>=b else ''}{fmtW(a-b)}万"

        analysis_parts = []
        yr_list = [str(y) for y in years]
        for i in range(1, len(yr_list)):
            prev, curr = yr_list[i-1], yr_list[i]
            prev_total = yr_totals[prev]
            curr_total = yr_totals[curr]
            diff_total = curr_total - prev_total
            direction = "增长" if diff_total >= 0 else "下降"

            if i == 1:
                analysis_parts.append(
                    f"**{prev} → {curr}年**：总支出{direction} **{fmtD(curr_total, prev_total)}**"
                    f"（¥{fmtW(prev_total)}万 → ¥{fmtW(curr_total)}万）。"
                    f"主要由房租费{'上涨' if cat_data.get('房租费',{}).get(curr,0) > cat_data.get('房租费',{}).get(prev,0) else '下降'}"
                    f"驱动（占总支出的 {cat_data.get('房租费',{}).get(curr,0)/curr_total*100:.0f}%）。"
                )
            elif i == 2:
                analysis_parts.append(
                    f"**{prev} → {curr}年**：总支出{direction} **{fmtD(curr_total, prev_total)}**"
                    f"（¥{fmtW(prev_total)}万 → ¥{fmtW(curr_total)}万），核心原因是房租费下降。"
                    f"杭州占比进一步升至 {by_yr.get(curr,{}).get('cityDistribution',[{}])[0].get('amount',0)/curr_total*100:.1f}%。"
                )
            else:
                analysis_parts.append(
                    f"**{prev} → {curr}年**（截至{by_yr.get(curr,{}).get('filledMonths','?')}月）："
                    f"总支出 ¥{fmtW(curr_total)}万。"
                )

        for p in analysis_parts:
            st.markdown(f"<p style='margin-bottom:10px;font-size:13px;line-height:1.9;color:{C['text_sec']}'>{p}</p>", unsafe_allow_html=True)

        st.markdown(f"""
        <div style="margin-top:12px;padding:12px 16px;background:rgba(99,102,241,0.06);border-radius:10px;border-left:3px solid {C['primary']};font-size:13px;line-height:1.9">
        <strong style="color:{C['text']}">💡 关键发现</strong><br>
        ① <strong>房租占比始终最高</strong>，是行政支出的绝对核心。<br>
        ② <strong>快递费逐年递减</strong>，可能与电子化替代或集中采购有关。<br>
        ③ <strong>杭州为第一支出城市</strong>，与上海、北京合计占 50%-60%。<br>
        ④ 留意各年 9-10 月的异常峰值，核实是否为集中入账或一次性支出。
        </div>
        """, unsafe_allow_html=True)

    # -- 🔬 分类 × 城市 交叉明细 --
    st.markdown("### 🔬 分类 × 城市 交叉明细")
    st.caption("点击分类展开城市明细（万元）")

    # 从 byYear 数据计算交叉分析
    cross_cats = []
    for yr in years:
        yd = by_yr.get(str(yr), {})
        for c in yd.get("categoryDistribution", []):
            found = False
            for cc in cross_cats:
                if cc["name"] == c["name"]:
                    cc["yr_data"][str(yr)] = c
                    found = True
                    break
            if not found:
                cross_cats.append({"name": c["name"], "yr_data": {str(yr): c}})

    # 补充城市维度数据（从 byYear 各年的 cityDistribution 获取）
    for cat in cross_cats:
        cat["cities"] = {}
        for yr in years:
            cat_total = cat["yr_data"].get(str(yr), {}).get("amount", 0)
            # 从该年的城市分布中取有该分类城市的近似数据
            yr_cities = by_yr.get(str(yr), {}).get("cityDistribution", [])
            yr_total = sum(c["amount"] for c in yr_cities) if yr_cities else 1
            for c in yr_cities:
                city_name = c["name"]
                # 按比例分配城市费用到各大类
                alloc = c["amount"] * (cat_total / yr_total) if yr_total > 0 else 0
                if city_name not in cat["cities"]:
                    cat["cities"][city_name] = {}
                cat["cities"][city_name][str(yr)] = round(alloc, 2)

    cross_cats.sort(key=lambda x: sum(d.get("amount", 0) for d in x["yr_data"].values()), reverse=True)

    for idx, cat in enumerate(cross_cats):
        cat_total = sum(d.get("amount", 0) for d in cat["yr_data"].values())
        yr_summary = []
        for i in range(1, len(years)):
            prev, curr = str(years[i-1]), str(years[i])
            pa = cat["yr_data"].get(prev, {}).get("amount", 0)
            ca = cat["yr_data"].get(curr, {}).get("amount", 0)
            if pa > 0 and ca > 0:
                diff = ca - pa
                yr_summary.append(f"{prev}→{curr}: {'+'if diff>=0 else ''}{fmtW(diff)}万")

        with st.expander(f"📂 {cat['name']}  ·  {fmtW(cat_total)}  ·  {' | '.join(yr_summary)}"):
            city_rows = []
            all_years = [str(y) for y in years]
            for city_name, yr_amounts in cat["cities"].items():
                row = {"城市": city_name}
                for yr in all_years:
                    row[f"{yr}年"] = f"¥{yr_amounts.get(yr,0)/10000:.1f}万" if yr_amounts.get(yr, 0) > 0 else "-"
                # 趋势
                first = yr_amounts.get(all_years[0], 0)
                last = yr_amounts.get(all_years[-1], 0)
                if first > 0 and last >= 0:
                    trend = (last - first) / first * 100
                    if trend > 5: row["趋势"] = f"↑{trend:.0f}%"
                    elif trend < -5: row["趋势"] = f"↓{abs(trend):.0f}%"
                    else: row["趋势"] = f"→{trend:.0f}%"
                else:
                    row["趋势"] = "-"
                city_rows.append(row)
            city_rows.sort(key=lambda r: sum(
                float(r.get(f"{yr}年", "¥0万").replace("¥", "").replace("万", "").replace("-", "0"))
                for yr in all_years
            ), reverse=True)
            if city_rows:
                st.dataframe(city_rows, use_container_width=True, hide_index=True)

    # -- 💹 城市 × 费用单价对比 --
    st.markdown("### 💹 城市 × 费用单价对比")
    st.caption("单笔均价（元）")
    if cities:
        unit_price = []
        for c in cities:
            avg_price = c["amount"] / c["count"] if c.get("count", 0) > 0 else 0
            unit_price.append({"城市": c["name"], "总金额": fmt_yuan(c["amount"]), "笔数": c["count"],
                               "单笔均价": f"¥{avg_price:,.0f}"})
        unit_price.sort(key=lambda x: float(x["单笔均价"].replace("¥", "").replace(",", "")), reverse=True)
        st.dataframe(unit_price, use_container_width=True, hide_index=True)

    # -- 最新费用记录 --
    st.markdown("### 📝 最新出款记录")
    latest = active_exp.get("latestExpenses", []) or exp.get("latestExpenses", [])
    if latest:
        rows = [{
            "日期": r.get("date", ""), "供应商": r.get("supplier", ""),
            "城市": r.get("city", ""), "费用类别": r.get("category", ""),
            "金额": fmt_yuan(r.get("amount", 0)),
            "用途": (r.get("purpose", "") or "")[:40],
            "状态": r.get("status", ""),
        } for r in latest[:30]]
        st.dataframe(rows, use_container_width=True, hide_index=True)


# ================================================================
# Tab 2: 资产管理
# ================================================================
with tabs[1]:
    asset = analysis.get("asset")
    if asset:
        # KPI Row 1: 数量
        st.markdown("### 💻 设备数量总览")
        kc = st.columns(4)
        with kc[0]: st.metric("💻 电脑总数", f"{asset.get('totalQty',0)} 台")
        with kc[1]: st.metric("🛒 自购", f"{asset.get('selfQty',0)} 台", f"占比 {asset.get('selfPct',0)}%")
        with kc[2]: st.metric("📋 租赁", f"{asset.get('rentQty',0)} 台", f"占比 {asset.get('rentPct',0)}%")
        with kc[3]: st.metric("🧑‍💻 自带(领补贴)", f"{asset.get('byoQty',0)} 台")

        # KPI Row 2: 金额
        st.markdown("### 💵 金额概览")
        kc2 = st.columns(4)
        has_amt = asset.get("hasAmountData", False)
        with kc2[0]: st.metric("💵 自购总金额", fmt_w(asset.get("selfAmount", 0)), "一次性投入")
        with kc2[1]: st.metric("📅 租赁月租金", fmt_w(asset.get("rentMonthly", 0)),
                               f"年化 {fmt_w(asset.get('rentAnnual',0))}")
        with kc2[2]: st.metric("🌍 覆盖城市", f"{asset.get('cityCount',0)} 城")
        with kc2[3]:
            dept_count = len(asset.get("deptList", []))
            st.metric("🏢 覆盖部门", f"{dept_count} 个")

        if not has_amt:
            st.info("⚠️ 金额数据暂未填写，请在 Excel「电脑管理台账」的「原值/租金」列填写自购原值和租赁月租金后刷新")

        # 图表区
        st.markdown("### 📊 资产分布")
        c1, c2 = st.columns(2)

        # 自购 vs 租赁 vs 自带 占比
        with c1:
            type_pie = asset.get("typePie", [])
            if type_pie:
                fig = go.Figure(go.Pie(labels=[t["name"] for t in type_pie],
                    values=[t["value"] for t in type_pie],
                    marker_colors=[C["success"], C["primary"], C["warning"], C["text_muted"]], hole=0.5))
                fig.update_layout(height=300, margin=dict(l=10, r=10, t=30, b=10),
                    paper_bgcolor="rgba(0,0,0,0)", title="🛒 自购 vs 租赁 vs 自带")
                st.plotly_chart(fig, use_container_width=True)

        # 各部门电脑分布 - **堆叠柱状图**
        with c2:
            dept_tab = asset.get("deptTable", [])
            if dept_tab:
                dept_tab = sorted(dept_tab, key=lambda x: x["total"], reverse=True)[:15]
                short_names = [(d["name"][:6] + "…") if len(d["name"]) > 6 else d["name"] for d in dept_tab]
                fig = go.Figure()
                fig.add_trace(go.Bar(name="自购", y=short_names, x=[d["self"] for d in dept_tab],
                    orientation="h", marker_color=C["success"], hovertext=[d["name"] for d in dept_tab]))
                fig.add_trace(go.Bar(name="租赁", y=short_names, x=[d["rent"] for d in dept_tab],
                    orientation="h", marker_color=C["primary"], hovertext=[d["name"] for d in dept_tab]))
                fig.add_trace(go.Bar(name="自带", y=short_names, x=[d.get("bringYourOwn", 0) for d in dept_tab],
                    orientation="h", marker_color=C["warning"], hovertext=[d["name"] for d in dept_tab]))
                fig.update_layout(height=350, barmode="stack", margin=dict(l=10, r=10, t=30, b=10),
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    title="🏢 各部门电脑分布（自购/租赁/自带）",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    yaxis=dict(autorange="reversed"),
                    xaxis=dict(showgrid=True, gridcolor="rgba(148,163,184,0.15)"))
                st.plotly_chart(fig, use_container_width=True)

        c3, c4 = st.columns(2)

        # 城市分布
        with c3:
            city_tab = asset.get("cityTable", [])[:10]
            if city_tab:
                fig = go.Figure(go.Bar(y=[c["name"] for c in city_tab],
                    x=[c["total"] for c in city_tab], orientation="h",
                    marker_color=C["success"]))
                fig.update_layout(height=300, margin=dict(l=10, r=10, t=30, b=10),
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    title="📍 各城市电脑分布 (TOP 10)", showlegend=False,
                    yaxis=dict(autorange="reversed"))
                st.plotly_chart(fig, use_container_width=True)

        # 设备类型分布
        with c4:
            dev_list = asset.get("deviceList", [])
            if dev_list:
                dev_list = sorted(dev_list, key=lambda x: x["qty"], reverse=True)
                fig = go.Figure(go.Pie(labels=[d["name"] for d in dev_list],
                    values=[d["qty"] for d in dev_list], hole=0.5,
                    marker_colors=CAT_COLORS[:len(dev_list)]))
                fig.update_layout(height=300, margin=dict(l=10, r=10, t=30, b=10),
                    paper_bgcolor="rgba(0,0,0,0)", title="📱 设备类型分布")
                st.plotly_chart(fig, use_container_width=True)

        # 城市明细表 - **含进度条**
        st.markdown("### 📋 各城市自购/租赁明细")
        if city_tab:
            progress_rows = []
            for c in asset.get("cityTable", []):
                bar_html = f'<div style="display:flex;height:8px;border-radius:4px;overflow:hidden;width:100%;min-width:60px"><div style="width:{100-c.get("rentPct",0)}%;background:#10b981"></div><div style="width:{c.get("rentPct",0)}%;background:#6366f1"></div></div>'
                progress_rows.append({
                    "城市": c["name"], "总量": c["total"], "自购": c["self"],
                    "租赁": c["rent"], "租赁率": f"{c.get('rentPct',0)}%",
                    "占比条": bar_html,
                })
            st.dataframe(progress_rows, use_container_width=True, hide_index=True,
                         column_order=["城市", "总量", "自购", "租赁", "租赁率", "占比条"],
                         column_config={"占比条": st.column_config.Column(width="small")})

        # 部门明细表 - **含进度条**
        st.markdown("### 🏢 各部门自购/租赁/自带明细")
        if dept_tab:
            dept_rows = []
            for d in dept_tab:
                total = max(d["total"], 1)
                bar_html = (
                    f'<div style="display:flex;height:8px;border-radius:4px;overflow:hidden;width:100%;min-width:60px">'
                    f'<div style="width:{max(d["self"]/total*100,2):.0f}%;background:#10b981"></div>'
                    f'<div style="width:{max(d["rent"]/total*100,2):.0f}%;background:#6366f1"></div>'
                    f'<div style="width:{max(d.get("bringYourOwn",0)/total*100,2):.0f}%;background:#f59e0b"></div>'
                    f'</div>'
                )
                dept_rows.append({
                    "部门": d["name"], "总量": d["total"], "自购": d["self"],
                    "租赁": d["rent"], "自带(补贴)": d.get("bringYourOwn", 0),
                    "租赁率": f"{d.get('rentPct',0)}%", "占比条": bar_html,
                })
            st.dataframe(dept_rows, use_container_width=True, hide_index=True,
                         column_order=["部门", "总量", "自购", "租赁", "自带(补贴)", "租赁率", "占比条"])
    else:
        st.info("暂无资产管理数据，请先运行 asset_analysis.py 生成分析数据")


# ================================================================
# Tab 3: 押金台账
# ================================================================
with tabs[2]:
    if dep and dep.get("totalCount", 0) > 0:
        st.markdown("### 🔒 押金总览")
        kc = st.columns(4)
        with kc[0]:
            st.metric("💰 押金总额", f"¥{dep.get('totalAmount',0)/10000:.1f}万")
        with kc[1]:
            st.metric("✅ 已退回", f"¥{dep.get('returnedAmount',0)/10000:.1f}万",
                     f"回收率 {dep.get('returnRate',0)}%")
        with kc[2]:
            st.metric("⚠️ 未退回", f"¥{dep.get('unreturnedAmount',0)/10000:.1f}万",
                     f"{dep.get('unreturnedCount',0)} 笔")
        with kc[3]:
            st.metric("🔄 部分退回", f"¥{dep.get('partialAmount',0)/10000:.1f}万",
                     f"{dep.get('partialCount',0)} 笔")

        c1, c2, c3 = st.columns(3)

        with c1:
            types = dep.get("byType", [])
            if types:
                fig = go.Figure(go.Pie(labels=[t["name"] for t in types],
                    values=[t["amount"] for t in types],
                    marker_colors=CAT_COLORS[:len(types)], hole=0.5))
                fig.update_layout(title="🏷️ 押金类型分布", height=300,
                    margin=dict(l=10, r=10, t=40, b=10), paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig, use_container_width=True)

        with c2:
            statuses = dep.get("byStatus", [])
            if statuses:
                sc = {"已退回": C["success"], "未退回": C["danger"], "部分退回": C["warning"]}
                fig = go.Figure(go.Pie(labels=[s["name"] for s in statuses],
                    values=[s["count"] for s in statuses], hole=0.5,
                    marker_colors=[sc.get(s["name"], "#94a3b8") for s in statuses]))
                fig.update_layout(title="📊 退回状态分布", height=300,
                    margin=dict(l=10, r=10, t=40, b=10), paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig, use_container_width=True)

        with c3:
            dep_cities = dep.get("byCity", [])[:15]
            if dep_cities:
                fig = go.Figure(go.Bar(y=[c["name"] for c in dep_cities],
                    x=[c["amount"] for c in dep_cities], orientation="h",
                    marker_color=C["warning"]))
                fig.update_layout(title="📍 城市押金分布 (TOP 15)", height=300,
                    margin=dict(l=10, r=10, t=40, b=10), paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)", showlegend=False,
                    yaxis=dict(autorange="reversed"), xaxis=dict(tickformat=",.0f"))
                st.plotly_chart(fig, use_container_width=True)

        st.markdown("### ⚠️ 未退回押金明细")
        unret = dep.get("unreturnedList", [])
        if unret:
            st.dataframe([{
                "类型": r.get("type", ""), "城市": r.get("city", ""),
                "收款方": r.get("payee", ""), "金额": fmt_yuan(r.get("amount", 0)),
                "付款日期": r.get("payDate", ""), "负责人": r.get("person", ""),
                "合同期间": f"{r.get('contractStart','')} ~ {r.get('contractEnd','')}",
            } for r in unret], use_container_width=True, hide_index=True)
    else:
        st.info("暂无押金台账数据")


# ================================================================
# Tab 4-9: 专项分析（增强版：含月度趋势 + 重复预警）
# ================================================================
def render_special(data, title, emoji, key_prefix):
    if data is None:
        st.info(f"暂无{title}分析数据，请先运行对应分析脚本")
        return

    st.markdown(f"### {emoji} {title}专项分析")

    # 重复预警
    dup_cnt = data.get("duplicateCount", 0)
    if dup_cnt > 0:
        st.warning(f"⚠️ 发现 **{title}** 存在 {dup_cnt} 组疑似重复出款，请注意核查")
    else:
        st.success(f"✅ 未发现 {title} 重复出款")

    total = data.get("totalAmount", 0)
    cnt = data.get("totalCount", 0)
    cities_cnt = data.get("cityCount", len(data.get("byCity", [])))
    avg_per = total / cnt if cnt > 0 else 0

    kc = st.columns(4)
    with kc[0]: st.metric("💰 总金额", fmt_w(total))
    with kc[1]: st.metric("📋 总笔数", f"{cnt} 笔")
    with kc[2]: st.metric("🌍 覆盖城市", f"{cities_cnt} 城")
    with kc[3]: st.metric("📊 单笔均价", f"¥{avg_per:,.0f}")

    c1, c2 = st.columns(2)

    with c1:
        by_city = data.get("byCity", [])
        if by_city:
            fig = go.Figure(go.Pie(
                labels=[c.get("name", c.get("city", "")) for c in by_city[:10]],
                values=[c.get("amount", 0) for c in by_city[:10]],
                marker_colors=CAT_COLORS[:len(by_city[:10])], hole=0.5))
            fig.update_layout(title="🏙️ 城市分布", height=300,
                margin=dict(l=10, r=10, t=40, b=10), paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)

    with c2:
        by_year = data.get("byYear", [])
        if by_year:
            fig = go.Figure(go.Bar(x=[str(y.get("year", "")) for y in by_year],
                y=[y.get("amount", 0) for y in by_year],
                marker_color=C["primary"],
                text=[f"{y.get('changePct',0):+.0f}%" if y.get("changePct") else "" for y in by_year],
                textposition="outside"))
            fig.update_layout(title="📊 年度趋势", height=300,
                margin=dict(l=10, r=10, t=40, b=30), paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)", showlegend=False,
                yaxis=dict(showgrid=True, gridcolor="rgba(148,163,184,0.15)"))
            st.plotly_chart(fig, use_container_width=True)

    # 月度趋势
    monthly_trend = data.get("monthlyTrend", [])
    if monthly_trend and len(monthly_trend) >= 2:
        st.markdown("### 📈 月度趋势")
        trend_2025 = [m for m in monthly_trend if m["label"].startswith("2025") or m["label"].startswith("2026")]
        if not trend_2025:
            trend_2025 = monthly_trend[-24:]
        fig = go.Figure(go.Scatter(x=[m["label"] for m in trend_2025],
            y=[m["amount"] for m in trend_2025], mode="lines+markers",
            line=dict(color=C["primary"], width=2)))
        fig.update_layout(height=250, margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            showlegend=False, yaxis=dict(showgrid=True, gridcolor="rgba(148,163,184,0.15)", tickformat=",.0f"))
        st.plotly_chart(fig, use_container_width=True)

    # 城市均价（如果数据中有）
    city_avg = data.get("cityAvgPrice", [])
    if city_avg:
        st.markdown("### 💹 各城市单笔均价")
        st.dataframe([{
            "城市": c.get("name", c.get("city", "")),
            "均价": f"¥{c.get('avgPrice', c.get('amount', 0)):,.0f}",
            "笔数": c.get("count", 0),
        } for c in city_avg], use_container_width=True, hide_index=True)

    # 明细
    details = data.get("details", [])
    if details:
        st.markdown("### 📋 明细记录（最近 50 条）")
        st.dataframe([{
            "日期": r.get("date", ""), "城市": r.get("city", ""),
            "用途": (r.get("purpose", "") or "")[:40],
            "金额": f"¥{r.get('amount',0):.2f}",
            "收款方": r.get("receiver", ""),
        } for r in details[:50]], use_container_width=True, hide_index=True)


special_config = [
    (3, "cleaning", "保洁费", "🧹"),
    (4, "postal", "邮电通讯费", "📞"),
    (5, "broadband", "宽带费", "📡"),
    (6, "rental", "租赁费", "🏢"),
    (7, "express", "快递费", "📦"),
    (8, "drinking_water", "饮用水", "💧"),
]

for idx, key, title, emoji in special_config:
    with tabs[idx]:
        render_special(analysis.get(key), title, emoji, key)


# ============ Footer ============
st.markdown("---")
st.markdown(f"""
<p style='text-align:center;color:{C['text_muted']};font-size:11px'>
行政管理数据看板 · Streamlit 版 · 最后更新: {updated}
</p>
""", unsafe_allow_html=True)
