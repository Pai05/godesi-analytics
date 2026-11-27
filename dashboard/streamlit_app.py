"""GoDesi Sales Dashboard v3 — Streamlit in Snowflake, GoDesi brand style.

Paste this whole file into the Streamlit app owned by role REPORTER in
GODESI_ANALYTICS.APPS. It only reads the dbt marts in GODESI_ANALYTICS.MARTS.

v3: GoDesi colours (logo orange #FF8700, black #111111, website teal #108474),
money in crore (₹ Cr) for totals and lakh (₹ L) for per-day / per-product-month
amounts, and one finding headline per tab, like the Power BI report.
"""
from datetime import date
from html import escape

import altair as alt
import pandas as pd
import streamlit as st
from snowflake.snowpark.context import get_active_session

st.set_page_config(page_title="GoDesi Sales Dashboard", layout="wide")
session = get_active_session()
DB = "GODESI_ANALYTICS.MARTS"
FIRST_DAY, LAST_DAY = date(2024, 1, 1), date(2025, 12, 31)

# --------------------------------------------------------------------------
# Brand colours (same as dashboard/godesi_theme.json for Power BI)
# --------------------------------------------------------------------------
ORANGE, ORANGE_D, PEACH, PEACH_L = "#FF8700", "#C25E00", "#FFB066", "#FFD3A3"
INK, TEAL, TEAL_L, CHARCOAL = "#111111", "#108474", "#6FB7AC", "#3D3935"
SAND, CREAM, BORDER, MUTED, GRID = "#CDBFAE", "#FFF7EE", "#EFE3D3", "#6B6257", "#F1E8DC"
RED, STONE = "#C0392B", "#8A7F72"

CHANNEL_TYPE_SCALE = alt.Scale(domain=["Offline", "Marketplace", "Quick Commerce", "D2C"],
                               range=[CHARCOAL, TEAL, ORANGE, SAND])
CHANNEL_NAME_SCALE = alt.Scale(
    domain=["Distributors and Stores", "Amazon", "Flipkart", "Blinkit", "Zepto", "Swiggy Instamart", "GoDesi Website"],
    range=[CHARCOAL, TEAL, TEAL_L, ORANGE, PEACH, PEACH_L, SAND])
CATEGORY_SCALE = alt.Scale(domain=["Candy", "Mithai", "Chikki", "Laddu", "Fruit Bar", "Namkeen", "Frozen"],
                           range=[ORANGE, TEAL, CHARCOAL, SAND, PEACH, TEAL_L, STONE])
STATUS_SCALE = alt.Scale(domain=["Stock-out", "Low", "Healthy", "Overstock"], range=[RED, ORANGE, TEAL, STONE])
YEAR_SCALE = alt.Scale(domain=["2024", "2025"], range=[SAND, ORANGE])
SEGMENT_SCALE = alt.Scale(domain=["One-time", "Repeat", "Loyal"], range=[SAND, PEACH, ORANGE])

# --------------------------------------------------------------------------
# Page style (CSS) — cream page, black header band, white rounded cards
# --------------------------------------------------------------------------
st.markdown("""
<style>
  .stApp { background: #FFF7EE; }
  [data-testid="stHeader"] { background: transparent; }
  .block-container { padding-top: 1.4rem; max-width: 1500px; }
  [data-testid="stSidebar"] { background: #FFFFFF; border-right: 1px solid #EFE3D3; }
  span[data-baseweb="tag"] { background: #FF8700 !important; color: #111111 !important; }

  .gd-band { background: #111111; border-radius: 12px; padding: 14px 20px; display: flex;
             align-items: center; gap: 16px; margin-bottom: 14px; }
  .gd-badge { background: #FF8700; color: #111111; font-weight: 800; letter-spacing: .5px;
              padding: 6px 12px; border-radius: 6px; font-size: 15px; white-space: nowrap; }
  .gd-band-title { color: #FFFFFF; font-size: 20px; font-weight: 600; line-height: 1.2; }
  .gd-band-sub { color: #CFC6BB; font-size: 12.5px; }

  .gd-finding { font-size: 22px; font-weight: 700; color: #111111; margin: 6px 0 0; line-height: 1.25; }
  .gd-finding-sub { font-size: 13px; color: #6B6257; margin: 2px 0 12px; }
  .gd-ptitle { font-size: 15px; font-weight: 600; color: #111111; margin-bottom: 2px; }

  [data-testid="stMetric"] { background: #FFFFFF; border: 1px solid #EFE3D3; border-radius: 10px;
                             padding: 14px 18px; }
  [data-testid="stMetricLabel"] p { color: #6B6257; font-size: 13px; }
  [data-testid="stMetricValue"] { color: #111111; font-weight: 700; }
  [data-testid="column"]:first-child [data-testid="stMetric"],
  [data-testid="stColumn"]:first-child [data-testid="stMetric"] { border-left: 5px solid #FF8700; }

  [data-testid="stVerticalBlockBorderWrapper"] { background: #FFFFFF; border-color: #EFE3D3 !important;
                                                 border-radius: 10px; }

  .stTabs [data-baseweb="tab-list"] { gap: 6px; background: #111111; padding: 6px; border-radius: 999px; }
  .stTabs [data-baseweb="tab"] { color: #D9D0C5; border-radius: 999px; padding: 6px 16px; height: auto; }
  .stTabs [aria-selected="true"] { background: #FF8700; color: #111111; font-weight: 700; }
  .stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { display: none; }
</style>
""", unsafe_allow_html=True)


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
@st.cache_data(ttl=3600, show_spinner=False)
def query(sql: str) -> pd.DataFrame:
    return session.sql(sql).to_pandas()


def lit(value) -> str:
    """SQL string literal with quotes escaped."""
    return "'" + str(value).replace("'", "''") + "'"


def crore(value) -> str:
    """₹ in crore (1 Cr = 1,00,00,000). Used for totals."""
    return f"₹{(value or 0) / 1e7:,.2f} Cr"


def lakh(value) -> str:
    """₹ in lakh (1 L = 1,00,000). Used for per-day and per-product-month amounts."""
    return f"₹{(value or 0) / 1e5:,.1f} L"


def one_year_earlier(d: date) -> date:
    try:
        return d.replace(year=d.year - 1)
    except ValueError:           # 29 Feb
        return d.replace(year=d.year - 1, day=28)


def pct_change(now, before):
    if not before:
        return None
    return (now / before - 1) * 100


def styled(c):
    """Apply the GoDesi look to an Altair chart."""
    return (c.configure(font="Segoe UI", background="#FFFFFF")
             .configure_view(strokeWidth=0)
             .configure_axis(labelColor=MUTED, titleColor=MUTED, gridColor=GRID, gridDash=[3, 3],
                             domainColor=BORDER, tickColor=BORDER, labelFontSize=11, titleFontSize=11,
                             titleFontWeight="normal")
             .configure_legend(orient="top", labelColor=MUTED, titleColor=MUTED, labelFontSize=11,
                               titleFontSize=11, symbolType="square")
             .configure_range(category=[ORANGE, TEAL, CHARCOAL, SAND, PEACH, TEAL_L, PEACH_L, STONE]))


def chart(c, height=320):
    c = styled(c.properties(height=height))
    try:
        st.altair_chart(c, width="stretch", theme=None)
    except TypeError:            # older Streamlit without width="stretch"
        st.altair_chart(c, use_container_width=True)


def panel(title: str, note: str = None):
    """A white rounded card with a title, like a Power BI visual."""
    try:
        box = st.container(border=True)      # Streamlit >= 1.29
    except TypeError:
        box = st.container()
    box.markdown(f"<div class='gd-ptitle'>{escape(title)}</div>", unsafe_allow_html=True)
    if note:
        box.caption(note)
    return box


def finding(title: str, sub: str = ""):
    """Page headline that states the finding, not just the topic."""
    st.markdown(f"<div class='gd-finding'>{escape(title)}</div>"
                f"<div class='gd-finding-sub'>{escape(sub)}</div>", unsafe_allow_html=True)


# --------------------------------------------------------------------------
# Filters
# --------------------------------------------------------------------------
st.sidebar.header("Filters")
all_types = query(f"select distinct channel_type from {DB}.DIM_CHANNELS order by 1")["CHANNEL_TYPE"].tolist()
types = st.sidebar.multiselect("Channel type", all_types, default=all_types)
picked = st.sidebar.date_input("Order date", (date(2025, 1, 1), LAST_DAY), min_value=FIRST_DAY, max_value=LAST_DAY)
st.sidebar.caption("Year-on-year deltas need a date range that starts in 2025.")
st.sidebar.caption("Money: ₹ Cr = crore (1,00,00,000) · ₹ L = lakh (1,00,000).")

if not types:
    st.warning("Pick at least one channel type.")
    st.stop()
if not isinstance(picked, (tuple, list)) or len(picked) != 2:
    st.info("Pick an end date.")
    st.stop()
start, end = picked
types_sql = ", ".join(lit(t) for t in types)
filter_sql = f"order_date between '{start}' and '{end}' and channel_type in ({types_sql})"

st.markdown(f"""
<div class="gd-band">
  <span class="gd-badge">GO DESi</span>
  <div>
    <div class="gd-band-title">Sales dashboard</div>
    <div class="gd-band-sub">{start:%d %b %Y} – {end:%d %b %Y} · {escape(', '.join(types))} · source: dbt marts in Snowflake</div>
  </div>
</div>
""", unsafe_allow_html=True)


# --------------------------------------------------------------------------
# KPIs with year-on-year deltas
# --------------------------------------------------------------------------
def kpis(s: date, e: date) -> pd.Series:
    return query(f"""
        select count_if(not o.is_cancelled)                     as orders,
               coalesce(sum(o.net_revenue_inr), 0)              as revenue,
               coalesce(sum(o.gross_profit_inr), 0)             as profit,
               count(distinct iff(o.channel = 'website' and not o.is_cancelled, o.customer_id, null)) as d2c_customers
        from {DB}.FCT_ORDERS o
        join {DB}.DIM_CHANNELS c on o.channel = c.channel
        where o.order_date between '{s}' and '{e}' and c.channel_type in ({types_sql})
    """).iloc[0].astype(float)


now = kpis(start, end)
prev_start, prev_end = one_year_earlier(start), one_year_earlier(end)
prev = kpis(prev_start, prev_end) if prev_start >= FIRST_DAY else None


def delta(field: str, ratio: bool = False):
    if prev is None:
        return None
    if ratio:   # percentage-point change for margins
        a = now.PROFIT / now.REVENUE * 100 if now.REVENUE else 0
        b = prev.PROFIT / prev.REVENUE * 100 if prev.REVENUE else 0
        return f"{a - b:+.1f} pts vs LY"
    change = pct_change(now[field], prev[field])
    return None if change is None else f"{change:+.1f}% vs LY"


aov_now = now.REVENUE / now.ORDERS if now.ORDERS else 0
aov_prev = prev.REVENUE / prev.ORDERS if prev is not None and prev.ORDERS else None
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Net revenue", crore(now.REVENUE), delta("REVENUE"))
k2.metric("Orders", f"{now.ORDERS:,.0f}", delta("ORDERS"))
k3.metric("Avg order value", f"₹{aov_now:,.0f}",
          None if not aov_prev else f"{pct_change(aov_now, aov_prev):+.1f}% vs LY")
k4.metric("Gross margin", f"{now.PROFIT / now.REVENUE * 100:.1f}%" if now.REVENUE else "–", delta(None, ratio=True))
k5.metric("Website customers", f"{now.D2C_CUSTOMERS:,.0f}", delta("D2C_CUSTOMERS"))
st.write("")


# --------------------------------------------------------------------------
# Data used by several sections
# --------------------------------------------------------------------------
daily = query(f"""
    select order_date, channel_type, region, category, is_festival_season, upcoming_festival,
           net_revenue_inr as revenue, gross_profit_inr as profit
    from {DB}.MART_SALES_DAILY
    where {filter_sql}
""")
products = query(f"""
    select sku_id, product_name, category, sum(units_sold) as units,
           sum(net_revenue_inr) as revenue, sum(gross_profit_inr) as profit
    from {DB}.MART_PRODUCT_PERFORMANCE
    where month_start between date_trunc('month', '{start}'::date) and '{end}'
    group by 1, 2, 3
""")
channel_years = query(f"""
    select channel_name, year(month_start) as yr, sum(net_revenue_inr) as revenue
    from {DB}.MART_CHANNEL_PERFORMANCE
    where channel_type in ({types_sql})
    group by 1, 2
""")
cohorts = query(f"""
    select cohort_month, to_char(cohort_month, 'YYYY-MM') as cohort, months_since_first_order as month_n,
           cohort_customers, retention_pct
    from {DB}.MART_CUSTOMER_COHORTS
    where months_since_first_order between 0 and 12
""")
inventory = query(f"""
    select snapshot_date, sku_id, product_name, category, on_hand_units, avg_daily_units_28d,
           days_of_cover, stock_status
    from {DB}.MART_INVENTORY_HEALTH
    where snapshot_date between '{start}' and '{end}'
""")

cy = channel_years.pivot_table(index="CHANNEL_NAME", columns="YR", values="REVENUE", aggfunc="sum")
if {2024, 2025} <= set(cy.columns):
    cy["GROWTH"] = cy[2025] / cy[2024] - 1

tabs = st.tabs(["Overview", "Products", "Channels & regions", "Customers", "Promotions", "Inventory",
                "Market (real data)"])

# --------------------------------------------------------------------------
# 1. Overview
# --------------------------------------------------------------------------
with tabs[0]:
    # festival vs normal day (per-day averages)
    per_day = daily.groupby(["ORDER_DATE", "IS_FESTIVAL_SEASON"], as_index=False)["REVENUE"].sum()
    per_day["SEASON"] = per_day.IS_FESTIVAL_SEASON.astype(str).str.lower().map(
        {"true": "Festival season", "false": "Normal days"})
    fest = per_day.groupby("SEASON", as_index=False)["REVENUE"].mean()
    fest_map = dict(zip(fest.SEASON, fest.REVENUE))
    mult = (fest_map["Festival season"] / fest_map["Normal days"]
            if fest_map.get("Normal days") and fest_map.get("Festival season") else None)

    growth = pct_change(now.REVENUE, prev.REVENUE) if prev is not None else None
    if growth is not None:
        head = f"Revenue {'grew' if growth >= 0 else 'fell'} {abs(growth):.0f}% vs last year to {crore(now.REVENUE)}"
    else:
        head = f"Net revenue of {crore(now.REVENUE)} in this period"
    if mult:
        head += f"; festival-season days sell about {mult:.1f}× a normal day"
    per_fest = daily.groupby(["ORDER_DATE", "UPCOMING_FESTIVAL"], dropna=False, as_index=False)["REVENUE"].sum()
    normal = per_fest[per_fest.UPCOMING_FESTIVAL.isna()]["REVENUE"].mean()
    diwali = per_fest[per_fest.UPCOMING_FESTIVAL == "Diwali"]["REVENUE"].mean()
    sub = (f"The two weeks before Diwali average {diwali / normal:.1f}× a normal day: stock and promos should be "
           "in place by early October." if normal and pd.notna(diwali) else
           "Net revenue after discounts and returns · cancelled orders excluded")
    finding(head, sub)

    monthly = daily.assign(MONTH=pd.to_datetime(daily.ORDER_DATE).dt.to_period("M").dt.to_timestamp()) \
                   .groupby(["MONTH", "CHANNEL_TYPE"], as_index=False)["REVENUE"].sum()
    monthly["REV_CR"] = monthly.REVENUE / 1e7
    festivals = query(f"""
        select date_day as day, festival_name as festival from {DB}.DIM_DATE
        where festival_name is not null and date_day between '{start}' and '{end}'
    """)
    left, right = st.columns([2, 1])
    with left:
        with panel("Net revenue by month and channel type"):
            bars = alt.Chart(monthly).mark_bar(cornerRadiusTopLeft=2, cornerRadiusTopRight=2).encode(
                x=alt.X("yearmonth(MONTH):T", title=None, axis=alt.Axis(format="%b %y")),
                y=alt.Y("REV_CR:Q", title="Net revenue (₹ Cr)", stack=True),
                color=alt.Color("CHANNEL_TYPE:N", title=None, scale=CHANNEL_TYPE_SCALE),
                tooltip=[alt.Tooltip("MONTH:T", format="%b %Y", title="Month"), alt.Tooltip("CHANNEL_TYPE", title="Type"),
                         alt.Tooltip("REV_CR:Q", format=",.2f", title="₹ Cr")],
            )
            rules = alt.Chart(festivals).mark_rule(strokeDash=[4, 4], color=MUTED).encode(x="DAY:T")
            labels = alt.Chart(festivals).mark_text(align="left", dx=3, color=MUTED, baseline="top", fontSize=10) \
                .encode(x="DAY:T", y=alt.value(2), text="FESTIVAL:N")
            chart(bars + rules + labels, 320)
    with right:
        with panel("2025 vs 2024, month by month", "Full calendar years; the date filter does not apply."):
            yoy = query(f"""
                select year(order_date) as yr, month(order_date) as mon, sum(net_revenue_inr) as revenue
                from {DB}.MART_SALES_DAILY where channel_type in ({types_sql}) group by 1, 2
            """)
            yoy["YEAR"] = yoy.YR.astype(str)
            yoy["REV_CR"] = yoy.REVENUE / 1e7
            chart(alt.Chart(yoy).mark_line(point=True, strokeWidth=3).encode(
                x=alt.X("MON:O", title="Month"),
                y=alt.Y("REV_CR:Q", title="Net revenue (₹ Cr)"),
                color=alt.Color("YEAR:N", title=None, scale=YEAR_SCALE),
                strokeDash=alt.StrokeDash("YEAR:N", scale=alt.Scale(domain=["2024", "2025"], range=[[6, 4], [1, 0]]),
                                          legend=None),
                tooltip=["YEAR", "MON", alt.Tooltip("REV_CR:Q", format=",.2f", title="₹ Cr")],
            ), 285)

    left, right = st.columns(2)
    with left:
        with panel("Average daily revenue: festival season vs normal days"):
            fest["REV_L"] = fest.REVENUE / 1e5
            fest["LABEL"] = fest.REV_L.map(lambda v: f"₹{v:,.1f} L / day")
            base = alt.Chart(fest).encode(y=alt.Y("SEASON:N", title=None, sort=["Festival season", "Normal days"]),
                                          x=alt.X("REV_L:Q", title="Average net revenue per day (₹ L)"))
            chart(base.mark_bar(cornerRadiusEnd=3).encode(
                      color=alt.Color("SEASON:N", legend=None, scale=alt.Scale(
                          domain=["Festival season", "Normal days"], range=[ORANGE, SAND])))
                  + base.mark_text(align="left", dx=6, color=INK, fontWeight="bold").encode(text="LABEL:N"), 200)
    with right:
        with panel("Average revenue by weekday"):
            wk = daily.groupby("ORDER_DATE", as_index=False)["REVENUE"].sum()
            wk["WEEKDAY"] = pd.to_datetime(wk.ORDER_DATE).dt.day_name().str[:3]
            wk = wk.groupby("WEEKDAY", as_index=False)["REVENUE"].mean()
            wk["REV_L"] = wk.REVENUE / 1e5
            chart(alt.Chart(wk).mark_bar(color=TEAL, cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
                x=alt.X("WEEKDAY:N", sort=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], title=None),
                y=alt.Y("REV_L:Q", title="Avg net revenue per day (₹ L)"),
                tooltip=["WEEKDAY", alt.Tooltip("REV_L:Q", format=",.1f", title="₹ L")],
            ), 200)

# --------------------------------------------------------------------------
# 2. Products
# --------------------------------------------------------------------------
with tabs[1]:
    products["MARGIN"] = products.PROFIT / products.REVENUE.where(products.REVENUE != 0)
    products["REV_CR"] = products.REVENUE / 1e7
    pareto = products.sort_values("REVENUE", ascending=False).reset_index(drop=True)
    pareto["RANK"] = pareto.index + 1
    pareto["CUM_SHARE"] = pareto.REVENUE.cumsum() / pareto.REVENUE.sum() if len(pareto) else 0
    n80 = int((pareto.CUM_SHARE < 0.8).sum()) + 1 if len(pareto) else 0
    pareto["GROUP"] = ["Top 80%" if r <= n80 else "Rest" for r in pareto.RANK]
    cats = products.groupby("CATEGORY", as_index=False)[["REVENUE", "PROFIT", "UNITS"]].sum()
    cats["MARGIN"] = cats.PROFIT / cats.REVENUE.where(cats.REVENUE != 0)
    cats["REV_CR"] = cats.REVENUE / 1e7
    if len(pareto):
        top_cat = cats.sort_values("REVENUE", ascending=False).iloc[0].CATEGORY
        finding(f"{n80} of {len(pareto)} products drive 80% of revenue; {top_cat} is the top-selling category",
                f"Top seller: {pareto.iloc[0].PRODUCT_NAME} ({pareto.iloc[0].REVENUE / pareto.REVENUE.sum():.0%} of revenue)"
                " · all channels (the product mart is not split by channel)")
    else:
        finding("No product sales in this period")

    left, right = st.columns(2)
    with left:
        with panel("Top 10 products by net revenue"):
            chart(alt.Chart(products.nlargest(10, "REVENUE")).mark_bar(cornerRadiusEnd=3).encode(
                x=alt.X("REV_CR:Q", title="Net revenue (₹ Cr)"),
                y=alt.Y("PRODUCT_NAME:N", sort="-x", title=None),
                color=alt.Color("CATEGORY:N", title=None, scale=CATEGORY_SCALE),
                tooltip=["PRODUCT_NAME", "CATEGORY", alt.Tooltip("REV_CR:Q", format=",.2f", title="₹ Cr"),
                         alt.Tooltip("MARGIN:Q", format=".1%"), alt.Tooltip("UNITS:Q", format=",.0f")],
            ))
    with right:
        with panel("Pareto: how concentrated is revenue?", f"Orange = the {n80} products that make up 80% of revenue"):
            base = alt.Chart(pareto).encode(x=alt.X("RANK:O", title="Products ranked by revenue",
                                                    axis=alt.Axis(labelAngle=0, values=list(range(0, 41, 5)))))
            line80 = alt.Chart(pd.DataFrame({"y": [0.8]})).mark_rule(color=TEAL, strokeDash=[5, 4], strokeWidth=1.5) \
                .encode(y=alt.Y("y:Q", axis=None, scale=alt.Scale(domain=[0, 1])))
            chart(alt.layer(
                base.mark_bar().encode(
                    y=alt.Y("REV_CR:Q", title="Net revenue (₹ Cr)"),
                    color=alt.Color("GROUP:N", legend=None, scale=alt.Scale(domain=["Top 80%", "Rest"], range=[ORANGE, SAND])),
                    tooltip=["PRODUCT_NAME", alt.Tooltip("REV_CR:Q", format=",.2f", title="₹ Cr")]),
                alt.layer(
                    base.mark_line(color=INK, point=alt.OverlayMarkDef(color=INK, size=18)).encode(
                        y=alt.Y("CUM_SHARE:Q", axis=alt.Axis(format="%"), title="Cumulative share",
                                scale=alt.Scale(domain=[0, 1])),
                        tooltip=["PRODUCT_NAME", alt.Tooltip("CUM_SHARE:Q", format=".0%")]),
                    line80),
            ).resolve_scale(y="independent"))

    left, right = st.columns(2)
    with left:
        with panel("Category revenue vs margin", "Bubble size = units sold"):
            chart(alt.Chart(cats).mark_circle(opacity=0.85, stroke="#FFFFFF", strokeWidth=1).encode(
                x=alt.X("REV_CR:Q", title="Net revenue (₹ Cr)"),
                y=alt.Y("MARGIN:Q", axis=alt.Axis(format="%"), title="Gross margin", scale=alt.Scale(zero=False)),
                size=alt.Size("UNITS:Q", legend=None, scale=alt.Scale(range=[150, 2200])),
                color=alt.Color("CATEGORY:N", legend=None, scale=CATEGORY_SCALE),
                tooltip=["CATEGORY", alt.Tooltip("REV_CR:Q", format=",.2f", title="₹ Cr"),
                         alt.Tooltip("MARGIN:Q", format=".1%")],
            ) + alt.Chart(cats).mark_text(dy=-22, color=INK, fontSize=11).encode(
                x="REV_CR:Q", y="MARGIN:Q", text="CATEGORY:N"), 300)
    with right:
        with panel("Category scorecard"):
            st.dataframe(
                cats.sort_values("REVENUE", ascending=False)[["CATEGORY", "REV_CR", "MARGIN", "UNITS"]]
                    .assign(MARGIN=lambda d: d.MARGIN * 100),
                hide_index=True, width="stretch", height=300,
                column_config={
                    "CATEGORY": "Category",
                    "REV_CR": st.column_config.ProgressColumn("Net revenue (₹ Cr)", format="₹%.2f Cr", min_value=0,
                                                              max_value=float(cats.REV_CR.max() or 1)),
                    "MARGIN": st.column_config.NumberColumn("Gross margin", format="%.1f%%"),
                    "UNITS": st.column_config.NumberColumn("Units sold", format="%d"),
                })

    names = pareto.PRODUCT_NAME.tolist()
    if names:
        with panel("Product drill-down", "Monthly amounts per product are small, so they are shown in lakh (₹ L)."):
            chosen = st.selectbox("Product", names)
            trend = query(f"""
                select month_start, units_sold, net_revenue_inr as revenue, gross_margin_pct, revenue_rank_in_month
                from {DB}.MART_PRODUCT_PERFORMANCE where product_name = {lit(chosen)} order by month_start
            """)
            trend["REV_L"] = trend.REVENUE / 1e5
            c1, c2 = st.columns([3, 1])
            with c1:
                chart(alt.Chart(trend).mark_area(opacity=0.25, color=ORANGE,
                                                 line=alt.OverlayMarkDef(color=ORANGE, strokeWidth=2.5)).encode(
                    x=alt.X("MONTH_START:T", title=None), y=alt.Y("REV_L:Q", title="Net revenue (₹ L)"),
                    tooltip=[alt.Tooltip("MONTH_START:T", format="%b %Y"), alt.Tooltip("REV_L:Q", format=",.1f", title="₹ L"),
                             "UNITS_SOLD", "GROSS_MARGIN_PCT", "REVENUE_RANK_IN_MONTH"],
                ), 240)
            with c2:
                row = products[products.PRODUCT_NAME == chosen].iloc[0]
                st.metric("Revenue (period)", crore(row.REVENUE))
                st.metric("Units", f"{row.UNITS:,.0f}")
                st.metric("Margin", f"{row.MARGIN:.1%}" if pd.notna(row.MARGIN) else "–")

# --------------------------------------------------------------------------
# 3. Channels & regions
# --------------------------------------------------------------------------
with tabs[2]:
    channels = query(f"""
        select month_start, channel_name, channel_type, net_revenue_inr, orders, aov_inr, discount_pct,
               return_rate_pct, gross_margin_pct, revenue_share_pct, commission_inr, gross_amount_inr
        from {DB}.MART_CHANNEL_PERFORMANCE
        where month_start between date_trunc('month', '{start}'::date) and '{end}' and channel_type in ({types_sql})
    """)
    sc = channels.groupby(["CHANNEL_NAME", "CHANNEL_TYPE"], as_index=False).agg(
        revenue=("NET_REVENUE_INR", "sum"), orders=("ORDERS", "sum"), gross=("GROSS_AMOUNT_INR", "sum"),
        commission=("COMMISSION_INR", "sum"), returns=("RETURN_RATE_PCT", "mean"), margin=("GROSS_MARGIN_PCT", "mean"))
    sc["revenue_cr"] = sc.revenue / 1e7
    sc["share"] = sc.revenue / sc.revenue.sum() * 100
    sc["aov"] = sc.revenue / sc.orders
    sc["commission_pct"] = sc.commission / sc.gross * 100
    if "GROWTH" in cy.columns:
        sc["growth_2025"] = sc.CHANNEL_NAME.map(cy["GROWTH"] * 100)

    if len(sc):
        leader = sc.sort_values("revenue", ascending=False).iloc[0].CHANNEL_NAME
        if "GROWTH" in cy.columns and cy["GROWTH"].notna().any():
            fastest = cy["GROWTH"].idxmax()
            finding(f"{leader} still lead, but {fastest} is growing fastest ({cy.loc[fastest, 'GROWTH']:+.0%})"
                    if fastest != leader else f"{leader} leads and is also growing fastest",
                    "Revenue, efficiency and growth by channel · growth compares full year 2025 with 2024")
        else:
            finding(f"{leader} is the largest channel in this period")

    left, right = st.columns([2, 1])
    with left:
        with panel("Share of net revenue by channel"):
            chart(alt.Chart(channels).mark_area(stroke="#FFFFFF", strokeWidth=0.8).encode(
                x=alt.X("MONTH_START:T", title=None, axis=alt.Axis(format="%b %y")),
                y=alt.Y("NET_REVENUE_INR:Q", stack="normalize", axis=alt.Axis(format="%"), title=None),
                color=alt.Color("CHANNEL_NAME:N", title=None, scale=CHANNEL_NAME_SCALE),
                order=alt.Order("CHANNEL_NAME:N"),
                tooltip=[alt.Tooltip("MONTH_START:T", format="%b %Y"), "CHANNEL_NAME", "REVENUE_SHARE_PCT"],
            ), 300)
    with right:
        with panel("Revenue growth by region, 2025 vs 2024"):
            reg = query(f"""
                select region, year(order_date) as yr, sum(net_revenue_inr) as revenue
                from {DB}.MART_SALES_DAILY where channel_type in ({types_sql}) group by 1, 2
            """).pivot_table(index="REGION", columns="YR", values="REVENUE", aggfunc="sum").reset_index()
            if {2024, 2025} <= set(reg.columns):
                reg["GROWTH"] = reg[2025] / reg[2024] - 1
                reg["LABEL"] = reg.GROWTH.map(lambda v: f"{v:+.0%}")
                reg = reg[["REGION", "GROWTH", "LABEL"]]       # Altair needs text column names, not 2024/2025
                base = alt.Chart(reg).encode(x=alt.X("GROWTH:Q", axis=alt.Axis(format="%"), title=None),
                                             y=alt.Y("REGION:N", sort="-x", title=None))
                chart(base.mark_bar(cornerRadiusEnd=3).encode(
                          color=alt.condition("datum.GROWTH > 0", alt.value(TEAL), alt.value(RED)),
                          tooltip=["REGION", alt.Tooltip("GROWTH:Q", format=".1%")])
                      + base.mark_text(align="left", dx=5, fontWeight="bold", color=INK).encode(text="LABEL:N"), 300)

    with panel("Channel scorecard", "Margin and return rate are monthly averages; growth compares full years."):
        st.dataframe(
            sc.sort_values("revenue", ascending=False)[
                [c for c in ["CHANNEL_NAME", "CHANNEL_TYPE", "revenue_cr", "share", "orders", "aov", "margin",
                             "commission_pct", "returns", "growth_2025"] if c in sc.columns]],
            hide_index=True, width="stretch",
            column_config={
                "CHANNEL_NAME": "Channel", "CHANNEL_TYPE": "Type",
                "revenue_cr": st.column_config.NumberColumn("Net revenue", format="₹%.2f Cr"),
                "share": st.column_config.ProgressColumn("Share", format="%.1f%%", min_value=0, max_value=100),
                "orders": st.column_config.NumberColumn("Orders", format="%d"),
                "aov": st.column_config.NumberColumn("AOV", format="₹%.0f"),
                "margin": st.column_config.NumberColumn("Margin", format="%.1f%%"),
                "commission_pct": st.column_config.NumberColumn("Commission", format="%.1f%%"),
                "returns": st.column_config.NumberColumn("Return rate", format="%.2f%%"),
                "growth_2025": st.column_config.NumberColumn("Growth 2025", format="%+.0f%%"),
            },
        )

    names = sorted(channels.CHANNEL_NAME.unique())
    if names:
        with panel("Channel drill-down: average order value"):
            ch = st.selectbox("Channel", names)
            one = channels[channels.CHANNEL_NAME == ch]
            chart(alt.Chart(one).mark_line(point=True, color=ORANGE, strokeWidth=2.5).encode(
                x=alt.X("MONTH_START:T", title=None), y=alt.Y("AOV_INR:Q", title="Average order value (₹)"),
                tooltip=[alt.Tooltip("MONTH_START:T", format="%b %Y"), "AOV_INR", "ORDERS", "DISCOUNT_PCT"],
            ), 240)

# --------------------------------------------------------------------------
# 4. Customers (website only)
# --------------------------------------------------------------------------
with tabs[3]:
    seg = query(f"select customer_segment, count(*) as customers from {DB}.DIM_CUSTOMERS group by 1")
    buyers_seg = seg[seg.CUSTOMER_SEGMENT != "Prospect"]
    buyers = buyers_seg.CUSTOMERS.sum()
    one_time = seg[seg.CUSTOMER_SEGMENT == "One-time"].CUSTOMERS.sum()
    repeat = seg[seg.CUSTOMER_SEGMENT.isin(["Repeat", "Loyal"])].CUSTOMERS.sum()
    curve = cohorts[cohorts.MONTH_N > 0].groupby("MONTH_N", as_index=False)["RETENTION_PCT"].mean()
    if buyers:
        finding(f"{round(one_time / buyers * 10)} in 10 website buyers never order again; "
                "repeat buying is the biggest opportunity",
                (f"About {curve.RETENTION_PCT.mean():.0f}% of customers reorder in any given month after their first "
                 "purchase · " if len(curve) else "") + "website (D2C) customers only: marketplaces don't share buyer identities")

    left, right = st.columns([3, 2])
    with left:
        with panel("Monthly retention by first-order month (cohort)", "% of each cohort ordering again, by months since first order"):
            chart(alt.Chart(cohorts).mark_rect(cornerRadius=2, stroke="#FFFFFF", strokeWidth=1).encode(
                x=alt.X("MONTH_N:O", title="Months since first order", axis=alt.Axis(labelAngle=0)),
                y=alt.Y("COHORT:O", title=None),
                color=alt.Color("RETENTION_PCT:Q", title="% ordering",
                                scale=alt.Scale(domain=[0, 4, 10], range=[CREAM, ORANGE, ORANGE_D], clamp=True)),
                tooltip=["COHORT", "MONTH_N", "COHORT_CUSTOMERS", "RETENTION_PCT"],
            ), 520)
    with right:
        c1, c2 = st.columns(2)
        c1.metric("Repeat customer rate", f"{repeat / buyers:.1%}" if buyers else "–")
        c2.metric("Prospects (never ordered)", f"{seg[seg.CUSTOMER_SEGMENT == 'Prospect'].CUSTOMERS.sum():,}")
        with panel("Retention curve: average of all cohorts"):
            chart(alt.Chart(curve).mark_area(opacity=0.2, color=ORANGE,
                                             line=alt.OverlayMarkDef(color=ORANGE, strokeWidth=2.5),
                                             point=alt.OverlayMarkDef(color=ORANGE)).encode(
                x=alt.X("MONTH_N:O", title="Months since first order", axis=alt.Axis(labelAngle=0)),
                y=alt.Y("RETENTION_PCT:Q", title="% of cohort ordering"),
                tooltip=["MONTH_N", alt.Tooltip("RETENTION_PCT:Q", format=".1f")],
            ), 170)
        with panel("Customers by segment"):
            chart(alt.Chart(buyers_seg).mark_arc(innerRadius=55, stroke="#FFFFFF", strokeWidth=2).encode(
                theta=alt.Theta("CUSTOMERS:Q"),
                color=alt.Color("CUSTOMER_SEGMENT:N", title=None, scale=SEGMENT_SCALE,
                                sort=["One-time", "Repeat", "Loyal"]),
                tooltip=["CUSTOMER_SEGMENT", alt.Tooltip("CUSTOMERS:Q", format=",")],
            ), 190)

    with panel("New vs returning customer revenue (website)", "Monthly website revenue is small, so it is shown in lakh (₹ L)."):
        nvr = query(f"""
            select date_trunc('month', o.order_date)::date as month,
                   iff(date_trunc('month', o.order_date) = c.cohort_month, 'New', 'Returning') as customer_type,
                   sum(o.net_revenue_inr) as revenue
            from {DB}.FCT_ORDERS o
            join {DB}.DIM_CUSTOMERS c on o.customer_id = c.customer_id
            where o.channel = 'website' and not o.is_cancelled and o.order_date between '{start}' and '{end}'
            group by 1, 2
        """)
        nvr["REV_L"] = nvr.REVENUE / 1e5
        chart(alt.Chart(nvr).mark_bar(cornerRadiusTopLeft=2, cornerRadiusTopRight=2).encode(
            x=alt.X("yearmonth(MONTH):T", title=None, axis=alt.Axis(format="%b %y")),
            y=alt.Y("REV_L:Q", title="Net revenue (₹ L)"),
            color=alt.Color("CUSTOMER_TYPE:N", title=None, scale=alt.Scale(domain=["New", "Returning"],
                                                                         range=[SAND, ORANGE])),
            tooltip=[alt.Tooltip("MONTH:T", format="%b %Y"), "CUSTOMER_TYPE",
                     alt.Tooltip("REV_L:Q", format=",.1f", title="₹ L")],
        ), 240)

# --------------------------------------------------------------------------
# 5. Promotions
# --------------------------------------------------------------------------
with tabs[4]:
    promos = query(f"""
        select promo_code, promo_name, promo_channel, discount_pct, start_date, end_date,
               avg_daily_revenue_before, avg_daily_revenue_during, revenue_lift_pct
        from {DB}.MART_PROMO_IMPACT
        where start_date <= '{end}' and end_date >= '{start}'
        order by start_date
    """)
    if promos.empty:
        finding("No promotions in this date range")
    else:
        promos["KIND"] = promos.PROMO_NAME.str.extract(r"^(Holi|Raksha Bandhan|Diwali)", expand=False).fillna("Non-festival")
        promos["TYPE"] = promos.KIND.map(lambda k: "Other promotion" if k == "Non-festival" else "Festival promotion")
        avg_type = promos.groupby("TYPE")["REVENUE_LIFT_PCT"].mean()
        fest_lift, other_lift = avg_type.get("Festival promotion"), avg_type.get("Other promotion")
        if pd.notna(fest_lift) and pd.notna(other_lift) and fest_lift > other_lift:
            finding("Promo lift comes from festival timing, not discount size",
                    f"Festival promos average {fest_lift:+.0f}% lift vs {other_lift:+.0f}% for other promos · "
                    "discounts are only 10, 15 or 20%")
        else:
            finding("Promotion lift by campaign", "Average daily revenue during each promotion vs before it")

        left, right = st.columns([1, 1])
        with left:
            with panel("Revenue lift during promotion",
                       "Lift = average daily revenue during the promo vs the 28 days before, in the promo's channels."):
                lifted = promos.dropna(subset=["REVENUE_LIFT_PCT"]).copy()
                lifted["LABEL"] = lifted.REVENUE_LIFT_PCT.map(lambda v: f"{v:+.0f}%")
                base = alt.Chart(lifted).encode(x=alt.X("REVENUE_LIFT_PCT:Q", title="Revenue lift %"),
                                                y=alt.Y("PROMO_NAME:N", sort="-x", title=None))
                chart(base.mark_bar(cornerRadiusEnd=3).encode(
                          color=alt.Color("TYPE:N", title=None, scale=alt.Scale(
                              domain=["Festival promotion", "Other promotion"], range=[ORANGE, SAND])),
                          tooltip=["PROMO_CODE", "PROMO_CHANNEL", "DISCOUNT_PCT", "REVENUE_LIFT_PCT"])
                      + base.mark_text(align="left", dx=4, fontSize=10, color=INK).encode(text="LABEL:N"),
                      max(300, 22 * len(lifted)))
        with right:
            by_kind = promos.groupby("KIND", as_index=False)["REVENUE_LIFT_PCT"].mean()
            cols = st.columns(len(by_kind))
            for col, (_, r) in zip(cols, by_kind.iterrows()):
                col.metric(f"Avg lift: {r.KIND}", f"{r.REVENUE_LIFT_PCT:+.0f}%")
            with panel("Promotion details", "Daily revenue in lakh (₹ L)."):
                table = promos.assign(BEFORE_L=promos.AVG_DAILY_REVENUE_BEFORE / 1e5,
                                      DURING_L=promos.AVG_DAILY_REVENUE_DURING / 1e5) \
                              .sort_values("REVENUE_LIFT_PCT", ascending=False)
                st.dataframe(
                    table[["PROMO_CODE", "PROMO_CHANNEL", "DISCOUNT_PCT", "BEFORE_L", "DURING_L", "REVENUE_LIFT_PCT"]],
                    hide_index=True, width="stretch", height=min(640, 36 + 35 * len(table)),
                    column_config={
                        "PROMO_CODE": "Promo", "PROMO_CHANNEL": "Channel",
                        "DISCOUNT_PCT": st.column_config.NumberColumn("Discount", format="%d%%"),
                        "BEFORE_L": st.column_config.NumberColumn("Daily before", format="₹%.1f L"),
                        "DURING_L": st.column_config.NumberColumn("Daily during", format="₹%.1f L"),
                        "REVENUE_LIFT_PCT": st.column_config.NumberColumn("Lift", format="%+.0f%%"),
                    })

# --------------------------------------------------------------------------
# 6. Inventory
# --------------------------------------------------------------------------
with tabs[5]:
    if inventory.empty:
        finding("No stock data in this date range")
    else:
        inv = inventory.assign(MONTH=pd.to_datetime(inventory.SNAPSHOT_DATE).dt.to_period("M").dt.to_timestamp())
        latest_day = inv.SNAPSHOT_DATE.max()
        latest = inv[inv.SNAPSHOT_DATE == latest_day]
        outs_by_month = inv[inv.STOCK_STATUS == "Stock-out"].groupby("MONTH").size()
        n_out = int((latest.STOCK_STATUS == "Stock-out").sum())
        n_over = int((latest.STOCK_STATUS == "Overstock").sum())
        sub = (f"On {pd.to_datetime(latest_day):%d %b %Y}: {n_out} product{'s' if n_out != 1 else ''} out of stock, "
               f"{n_over} overstocked")
        if len(outs_by_month):
            peak = pd.to_datetime(outs_by_month.idxmax())
            if peak.month in (9, 10, 11):
                finding(f"Stock-outs spike every {peak:%B} before Diwali; restocking can't keep up with festival demand", sub)
            else:
                finding(f"Stock-outs peaked in {peak:%B %Y}", sub)
        else:
            finding("No stock-outs in this period", sub)

        left, right = st.columns([3, 1])
        with left:
            with panel("Products by stock status, monthly (share of product-days)"):
                chart(alt.Chart(inv.groupby(["MONTH", "STOCK_STATUS"], as_index=False).size()).mark_area(
                    stroke="#FFFFFF", strokeWidth=0.8).encode(
                    x=alt.X("yearmonth(MONTH):T", title=None, axis=alt.Axis(format="%b %y")),
                    y=alt.Y("size:Q", stack="normalize", axis=alt.Axis(format="%"), title=None),
                    color=alt.Color("STOCK_STATUS:N", scale=STATUS_SCALE, title=None,
                                    sort=["Stock-out", "Low", "Healthy", "Overstock"]),
                    order=alt.Order("STATUS_ORDER:Q"),
                    tooltip=[alt.Tooltip("MONTH:T", format="%b %Y"), "STOCK_STATUS",
                             alt.Tooltip("size:Q", title="product-days")],
                ).transform_calculate(
                    STATUS_ORDER="indexof(['Stock-out','Low','Healthy','Overstock'], datum.STOCK_STATUS)"), 300)
        with right:
            for status in ["Stock-out", "Low", "Healthy", "Overstock"]:
                st.metric(f"{status} (latest day)", int((latest.STOCK_STATUS == status).sum()))

        with panel(f"Products needing action on {pd.to_datetime(latest_day):%d %b %Y}"):
            action = latest[latest.STOCK_STATUS != "Healthy"].sort_values("DAYS_OF_COVER")
            st.dataframe(action[["PRODUCT_NAME", "CATEGORY", "STOCK_STATUS", "ON_HAND_UNITS", "AVG_DAILY_UNITS_28D",
                                 "DAYS_OF_COVER"]], hide_index=True, width="stretch",
                         column_config={
                             "PRODUCT_NAME": "Product", "CATEGORY": "Category", "STOCK_STATUS": "Status",
                             "ON_HAND_UNITS": st.column_config.NumberColumn("Units in stock", format="%d"),
                             "AVG_DAILY_UNITS_28D": st.column_config.NumberColumn("Avg daily sales", format="%.1f"),
                             "DAYS_OF_COVER": st.column_config.NumberColumn("Days of stock left", format="%.1f"),
                         })

        with panel("Days of cover drill-down", "Dashed lines: below 7 days = Low, above 60 days = Overstock"):
            names = sorted(inv.PRODUCT_NAME.dropna().unique())
            sku = st.selectbox("Product ", names)
            one = inv[inv.PRODUCT_NAME == sku]
            line = alt.Chart(one).mark_line(color=ORANGE, strokeWidth=2).encode(
                x=alt.X("SNAPSHOT_DATE:T", title=None), y=alt.Y("DAYS_OF_COVER:Q", title="Days of cover"),
                tooltip=["SNAPSHOT_DATE:T", "ON_HAND_UNITS", "AVG_DAILY_UNITS_28D", "DAYS_OF_COVER", "STOCK_STATUS"])
            bands = alt.Chart(pd.DataFrame({"y": [7, 60], "label": ["Low (7 days)", "Overstock (60 days)"],
                                            "c": [RED, STONE]})) \
                .mark_rule(strokeDash=[4, 4]).encode(y="y:Q", color=alt.Color("c:N", scale=None), tooltip=["label"])
            chart(line + bands, 260)

# --------------------------------------------------------------------------
# 7. Market landscape (real Open Food Facts data)
# --------------------------------------------------------------------------
with tabs[6]:
    market = query(f"""
        select brand_name, is_godesi, products, median_sugars_100g, median_energy_kcal_100g,
               pct_nutriscore_d_or_e, most_common_category
        from {DB}.MART_MARKET_LANDSCAPE
        where median_sugars_100g is not null
    """)
    market["BRAND"] = market.IS_GODESI.map({True: "GoDesi", False: "Other brands"})
    finding("Where GoDesi sits among Indian packaged-food brands",
            "Real data: Open Food Facts, products sold in India (ODbL licence) · bubble size = products listed")
    left, right = st.columns([3, 2])
    with left:
        with panel("Sugar vs Nutri-Score by brand",
                   "GoDesi's candies are sugar-heavy by nature; compare it with confectionery brands rather than all foods."):
            pts = alt.Chart(market).mark_circle(opacity=0.75, stroke="#FFFFFF", strokeWidth=0.5).encode(
                x=alt.X("MEDIAN_SUGARS_100G:Q", title="Median sugar, g per 100 g"),
                y=alt.Y("PCT_NUTRISCORE_D_OR_E:Q", title="% of graded products scoring D or E"),
                size=alt.Size("PRODUCTS:Q", title="Products"),
                color=alt.Color("BRAND:N", scale=alt.Scale(domain=["GoDesi", "Other brands"], range=[ORANGE, SAND]),
                                title=None),
                tooltip=["BRAND_NAME", "PRODUCTS", "MEDIAN_SUGARS_100G", "PCT_NUTRISCORE_D_OR_E", "MOST_COMMON_CATEGORY"])
            tag = alt.Chart(market[market.IS_GODESI]).mark_text(dx=12, align="left", fontWeight="bold", color=ORANGE_D) \
                .encode(x="MEDIAN_SUGARS_100G:Q", y="PCT_NUTRISCORE_D_OR_E:Q", text="BRAND_NAME:N")
            chart(pts + tag, 400)
    with right:
        with panel("Biggest brands"):
            st.dataframe(market.nlargest(15, "PRODUCTS")[["BRAND_NAME", "PRODUCTS", "MEDIAN_SUGARS_100G",
                                                          "PCT_NUTRISCORE_D_OR_E"]],
                         hide_index=True, width="stretch", height=420,
                         column_config={
                             "BRAND_NAME": "Brand", "PRODUCTS": "Products",
                             "MEDIAN_SUGARS_100G": st.column_config.NumberColumn("Sugar g/100g", format="%.1f"),
                             "PCT_NUTRISCORE_D_OR_E": st.column_config.NumberColumn("Nutri-Score D/E", format="%.0f%%"),
                         })
