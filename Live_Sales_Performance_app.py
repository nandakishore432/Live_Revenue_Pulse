import random
import sqlite3
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title='Live Revenue Pulse - War Room', page_icon='🚨', layout='wide')

DB_FILE = 'sales_live.db'
REFRESH_MS = 5000
SALE_INTERVAL_SECONDS = 30
HEAT_THRESHOLD = 35
MAX_ROWS = 2500
IST = ZoneInfo('Asia/Kolkata')

BRAND_PRODUCT_MAP = {
    'Apple': ['Phone', 'Tablet', 'Smartwatch'],
    'Samsung': ['Phone', 'Tablet', 'Smartwatch'],
    'Dell': ['Laptop'],
    'Sony': ['Headphones'],
    'Boat': ['Headphones'],
    'Noise': ['Smartwatch']
}

PRODUCT_PRICE = {
    'Laptop': [45000, 65000, 85000],
    'Phone': [12000, 18000, 25000],
    'Tablet': [15000, 22000, 30000],
    'Headphones': [2000, 3500, 5000],
    'Smartwatch': [3000, 6000, 9000],
}

CITY_COORDS = {
    'Hyderabad': {'lat': 17.3850, 'lon': 78.4867},
    'Chennai': {'lat': 13.0827, 'lon': 80.2707},
    'Bengaluru': {'lat': 12.9716, 'lon': 77.5946},
    'Mumbai': {'lat': 19.0760, 'lon': 72.8777},
    'Pune': {'lat': 18.5204, 'lon': 73.8567},
}

BEHAVIOR_TAGS = ['Impulse', 'Planned', 'Weather-Driven', 'High Intent']
CUSTOMER_TYPES = ['New', 'Returning']
ORDER_STATUS = ['Normal', 'Delayed', 'Priority']

WEATHER_CODE_MAP = {
    0: 'Clear', 1: 'Mainly Clear', 2: 'Partly Cloudy', 3: 'Cloudy', 45: 'Fog', 48: 'Rime Fog',
    51: 'Light Drizzle', 53: 'Moderate Drizzle', 55: 'Dense Drizzle', 61: 'Slight Rain',
    63: 'Moderate Rain', 65: 'Heavy Rain', 71: 'Slight Snow', 80: 'Rain Showers',
    81: 'Rain Showers', 82: 'Violent Rain Showers', 95: 'Thunderstorm'
}
RAIN_CODES = {51, 53, 55, 61, 63, 65, 80, 81, 82, 95}


def now_ist():
    return datetime.now(IST)


st.markdown('''
<style>
[data-testid="stAppViewContainer"]{background: radial-gradient(circle at top left, #17345d 0%, #0c1730 35%, #070f1e 100%);color:#eef6ff;}
[data-testid="stHeader"]{background: rgba(0,0,0,0);}
section[data-testid="stSidebar"]{background: linear-gradient(180deg, #091120 0%, #0f1b31 100%);}
.block-container{padding-top:0.8rem;padding-bottom:1rem;max-width:96%;}
.top-banner{background: linear-gradient(90deg, rgba(12,28,52,0.95), rgba(13,43,76,0.92));border:1px solid rgba(110,175,255,0.18);border-radius:20px;padding:18px 22px;margin-bottom:14px;box-shadow:0 16px 40px rgba(0,0,0,0.28);}
.banner-title{font-size:2.1rem;font-weight:800;color:#ffffff;margin-bottom:0.2rem;}
.banner-sub{color:#9dbbe0;font-size:0.98rem;}
.live-pill{display:inline-flex;align-items:center;gap:8px;padding:7px 14px;border-radius:999px;background:#10301f;color:#8df0b1;border:1px solid #1b6d3e;font-weight:700;font-size:0.84rem;}
.pulse-dot{width:10px;height:10px;border-radius:50%;background:#72f4a1;box-shadow:0 0 0 0 rgba(114,244,161,0.9);animation:pulse 1.8s infinite;display:inline-block;}
@keyframes pulse {0%{box-shadow:0 0 0 0 rgba(114,244,161,0.7)}70%{box-shadow:0 0 0 12px rgba(114,244,161,0)}100%{box-shadow:0 0 0 0 rgba(114,244,161,0)}}
.small-note{color:#8fa9c9;font-size:0.83rem;}
.metric-card{background:linear-gradient(180deg, rgba(18,31,54,0.96), rgba(11,22,39,0.92));border:1px solid rgba(98,162,255,0.24);border-radius:18px;padding:18px;min-height:132px;}
.metric-label{color:#8fa9c9;font-size:0.9rem;margin-bottom:8px;font-weight:600;}
.metric-value{color:#ffffff;font-size:1.95rem;font-weight:800;line-height:1.05;}
.metric-foot{color:#6fd0ff;font-size:0.84rem;margin-top:10px;}
.delta-strip{background:rgba(9,19,36,0.75);border:1px solid rgba(95,152,232,0.18);border-radius:16px;padding:12px 14px;margin:10px 0 16px 0;}
.delta-chip{display:inline-block;margin:4px 8px 4px 0;padding:8px 12px;border-radius:999px;background:rgba(17,39,70,0.95);border:1px solid rgba(109,168,255,0.18);color:#d7eaff;font-size:0.86rem;font-weight:600;}
.alert-wrap{background:rgba(10,22,40,0.75);border:1px solid rgba(123,180,255,0.16);border-radius:18px;padding:14px 16px;height:100%;}
.alert-box{padding:12px 14px;border-radius:14px;margin-bottom:10px;font-weight:700;border:1px solid rgba(255,255,255,0.1);}
.alert-rain{background:rgba(20,76,133,0.35);color:#a9d3ff;}
.alert-heat{background:rgba(138,62,8,0.35);color:#ffd18f;}
.alert-normal{background:rgba(23,74,45,0.35);color:#9bf0bf;}
.alert-anomaly{background:rgba(115,22,46,0.35);color:#ffb3c3;}
.section-title{font-size:1.08rem;font-weight:800;color:#f3f8ff;margin-bottom:8px;}
.kicker{color:#8db5d8;font-size:0.82rem;margin-bottom:6px;text-transform:uppercase;letter-spacing:0.08em;}
</style>
''', unsafe_allow_html=True)

st_autorefresh(interval=REFRESH_MS, key='live_refresh')


def get_conn():
    return sqlite3.connect(DB_FILE, check_same_thread=False)


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS sales (
            order_id INTEGER PRIMARY KEY,
            timestamp TEXT,
            brand TEXT,
            product TEXT,
            price REAL,
            units INTEGER,
            city TEXT,
            customer_type TEXT,
            behavior_tag TEXT,
            demand_score INTEGER,
            order_status TEXT
        )
    ''')
    conn.commit()
    conn.close()


def get_max_order_id():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT COALESCE(MAX(order_id), 0) FROM sales')
    value = cur.fetchone()[0]
    conn.close()
    return value


def get_last_timestamp():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT timestamp FROM sales ORDER BY order_id DESC LIMIT 1')
    row = cur.fetchone()
    conn.close()
    if row and row[0]:
        ts = datetime.fromisoformat(row[0])
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=IST)
        else:
            ts = ts.astimezone(IST)
        return ts
    return None


def generate_fake_sale(next_order_id):
    brand = random.choice(list(BRAND_PRODUCT_MAP.keys()))
    product = random.choice(BRAND_PRODUCT_MAP[brand])
    base_price = random.choice(PRODUCT_PRICE[product])
    city = random.choice(list(CITY_COORDS.keys()))
    return {
        'order_id': next_order_id,
        'timestamp': now_ist().isoformat(),
        'brand': brand,
        'product': product,
        'price': max(base_price + random.randint(-500, 1200), 500),
        'units': random.randint(1, 3),
        'city': city,
        'customer_type': random.choice(CUSTOMER_TYPES),
        'behavior_tag': random.choice(BEHAVIOR_TAGS),
        'demand_score': random.randint(55, 98),
        'order_status': random.choice(ORDER_STATUS),
    }


def append_sale_if_due():
    last_ts = get_last_timestamp()
    now = now_ist()
    if last_ts is None or (now - last_ts).total_seconds() >= SALE_INTERVAL_SECONDS:
        sale = generate_fake_sale(get_max_order_id() + 1)
        conn = get_conn()
        pd.DataFrame([sale]).to_sql('sales', conn, if_exists='append', index=False)
        conn.close()


def trim_rows():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM sales')
    total = cur.fetchone()[0]
    if total > MAX_ROWS:
        delete_count = total - MAX_ROWS
        cur.execute(f'DELETE FROM sales WHERE order_id IN (SELECT order_id FROM sales ORDER BY order_id ASC LIMIT {delete_count})')
        conn.commit()
    conn.close()


def load_data():
    conn = get_conn()
    df = pd.read_sql_query('SELECT * FROM sales ORDER BY order_id ASC', conn)
    conn.close()
    if not df.empty:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['price'] = pd.to_numeric(df['price'])
        df['units'] = pd.to_numeric(df['units'])
        df['demand_score'] = pd.to_numeric(df['demand_score'])
    return df


@st.cache_data(ttl=300, show_spinner=False)
def fetch_weather(city):
    coords = CITY_COORDS[city]
    url = 'https://api.open-meteo.com/v1/forecast'
    params = {'latitude': coords['lat'], 'longitude': coords['lon'], 'current': 'temperature_2m,weather_code,rain', 'forecast_days': 1}
    response = requests.get(url, params=params, timeout=15)
    response.raise_for_status()
    current = response.json().get('current', {})
    temp = current.get('temperature_2m', 0)
    rain = current.get('rain', 0) or 0
    code = current.get('weather_code', -1)
    condition = WEATHER_CODE_MAP.get(code, 'Unknown')
    if rain > 0 or code in RAIN_CODES:
        impact = 'Rain'
        sales_signal = 'Possible slowdown in walk-in or local delivery demand'
    elif temp >= HEAT_THRESHOLD:
        impact = 'Heat'
        sales_signal = 'High heat may influence customer movement and purchase timing'
    else:
        impact = 'Normal'
        sales_signal = 'No strong weather disruption signal currently'
    return {'city': city, 'temperature': temp, 'rain': rain, 'condition': condition, 'impact': impact, 'sales_signal': sales_signal}


def build_weather_table(cities):
    rows = []
    for city in cities:
        try:
            rows.append(fetch_weather(city))
        except Exception:
            rows.append({'city': city, 'temperature': None, 'rain': None, 'condition': 'Unavailable', 'impact': 'Unknown', 'sales_signal': 'Weather API unavailable for this city'})
    return pd.DataFrame(rows)


def fmt_inr(x):
    return f'₹{x:,.0f}'


init_db()
append_sale_if_due()
trim_rows()
df = load_data()

if df.empty:
    st.warning('No live orders are available yet.')
    st.stop()

st.sidebar.header('🎛️ War Room Filters')
brand_options = sorted(df['brand'].dropna().unique().tolist())
product_options = sorted(df['product'].dropna().unique().tolist())
city_options = sorted(df['city'].dropna().unique().tolist())
brand_filter = st.sidebar.multiselect('Select Brand', options=brand_options, default=brand_options)
product_filter = st.sidebar.multiselect('Select Product', options=product_options, default=product_options)
city_filter = st.sidebar.multiselect('Select City', options=city_options, default=city_options)

filtered_df = df[df['brand'].isin(brand_filter) & df['product'].isin(product_filter) & df['city'].isin(city_filter)].copy()
if filtered_df.empty:
    st.warning('No records match the selected slicers. Please broaden the filters.')
    st.stop()

now = filtered_df['timestamp'].max()
last_10m = filtered_df[filtered_df['timestamp'] >= now - timedelta(minutes=10)]
prev_10m = filtered_df[(filtered_df['timestamp'] < now - timedelta(minutes=10)) & (filtered_df['timestamp'] >= now - timedelta(minutes=20))]
last_city = filtered_df.sort_values('timestamp').iloc[-1]['city']
last_order_id = int(filtered_df.sort_values('timestamp').iloc[-1]['order_id'])
active_cities = sorted(filtered_df['city'].dropna().unique().tolist())
weather = build_weather_table(active_cities)
rain_count = int((weather['impact'] == 'Rain').sum()) if not weather.empty else 0
heat_count = int((weather['impact'] == 'Heat').sum()) if not weather.empty else 0
critical_alerts = rain_count + heat_count
recent_revenue = last_10m['price'].sum()
previous_revenue = prev_10m['price'].sum()
revenue_delta_pct = ((recent_revenue - previous_revenue) / previous_revenue * 100) if previous_revenue > 0 else 0
recent_orders = len(last_10m)
previous_orders = len(prev_10m)
order_delta = recent_orders - previous_orders

st.markdown('<div class="top-banner">', unsafe_allow_html=True)
col_a, col_b = st.columns([4, 1.1])
with col_a:
    st.markdown('<div class="banner-title">🚨 Live Revenue Pulse War Room</div>', unsafe_allow_html=True)
    st.markdown('<div class="banner-sub">Command-center dashboard for live revenue monitoring, anomaly response, and weather-linked city action</div>', unsafe_allow_html=True)
with col_b:
    st.markdown('<div style="text-align:right;"><span class="live-pill"><span class="pulse-dot"></span>LIVE AUTO REFRESH 5s</span></div>', unsafe_allow_html=True)
    updated_time_ist = now_ist().strftime('%d-%m-%Y %H:%M:%S IST')
    st.markdown(
        f'<div class="small-note" style="text-align:right;margin-top:8px;">Updated: {updated_time_ist}</div>',
        unsafe_allow_html=True
    )
    st.markdown(f'<div class="small-note" style="text-align:right;margin-top:4px;">Next sale cycle: ~{SALE_INTERVAL_SECONDS}s cadence</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="delta-strip">', unsafe_allow_html=True)
st.markdown(
    f'<span class="delta-chip">📍 Last City: {last_city}</span>'
    f'<span class="delta-chip">🆔 Last Order ID: {last_order_id}</span>'
    f'<span class="delta-chip">⚠️ Critical Weather Alerts: {critical_alerts}</span>'
    f'<span class="delta-chip">💸 Revenue Last 10 Min: {fmt_inr(recent_revenue)}</span>'
    f'<span class="delta-chip">📦 Orders Last 10 Min: {recent_orders}</span>'
    f'<span class="delta-chip">📈 Revenue Delta vs Prev 10 Min: {revenue_delta_pct:+.1f}%</span>'
    f'<span class="delta-chip">🧾 Order Delta vs Prev 10 Min: {order_delta:+d}</span>',
    unsafe_allow_html=True
)
st.markdown('</div>', unsafe_allow_html=True)

metric1, metric2, metric3, metric4 = st.columns(4)
with metric1:
    st.markdown(f'<div class="metric-card"><div class="metric-label">💰 Total Revenue</div><div class="metric-value">{fmt_inr(filtered_df["price"].sum())}</div><div class="metric-foot">Filtered live revenue</div></div>', unsafe_allow_html=True)
with metric2:
    st.markdown(f'<div class="metric-card"><div class="metric-label">🧾 Current Order Volume</div><div class="metric-value">{len(filtered_df)}</div><div class="metric-foot">Persistent order count</div></div>', unsafe_allow_html=True)
with metric3:
    st.markdown(f'<div class="metric-card"><div class="metric-label">📦 Avg Order Value</div><div class="metric-value">{fmt_inr(filtered_df["price"].mean())}</div><div class="metric-foot">Average filtered ticket size</div></div>', unsafe_allow_html=True)
with metric4:
    st.markdown(f'<div class="metric-card"><div class="metric-label">🌡️ Impact Cities</div><div class="metric-value">{critical_alerts}</div><div class="metric-foot">Cities under Rain or Heat</div></div>', unsafe_allow_html=True)

alert_col, city_col, demand_col = st.columns([1.05, 1.35, 1.2])
with alert_col:
    st.markdown('<div class="kicker">Priority Zone</div><div class="section-title">🚨 Weather & Risk Alerts</div>', unsafe_allow_html=True)
    st.markdown('<div class="alert-wrap">', unsafe_allow_html=True)
    for _, row in weather.iterrows():
        cls = 'alert-normal'
        if row['impact'] == 'Rain':
            cls = 'alert-rain'
        elif row['impact'] == 'Heat':
            cls = 'alert-heat'
        msg = f"{row['city']}: {row['impact']} | {row['condition']} | Temp: {row['temperature']}°C"
        st.markdown(f'<div class="alert-box {cls}">{msg}</div>', unsafe_allow_html=True)
    st.caption('Operational rule: Rain if rain > 0 or rain-coded weather; Heat if temperature ≥ 35°C; otherwise Normal.')
    st.markdown('</div>', unsafe_allow_html=True)

with city_col:
    st.markdown('<div class="kicker">Intelligence Layer</div><div class="section-title">🏙️ City Revenue Command View</div>', unsafe_allow_html=True)
    city_revenue = filtered_df.groupby('city', as_index=False)['price'].sum().sort_values('price', ascending=False)
    fig_city = px.bar(city_revenue, x='city', y='price', text='price', title='Revenue by City', color='price', color_continuous_scale='Blues')
    fig_city.update_traces(texttemplate='₹%{text:,.0f}', textposition='outside')
    fig_city.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', coloraxis_showscale=False, height=355, font=dict(color='white'))
    st.plotly_chart(fig_city, use_container_width=True)

with demand_col:
    st.markdown('<div class="kicker">Demand Layer</div><div class="section-title">📊 Brand Demand Intelligence</div>', unsafe_allow_html=True)
    demand_by_brand = filtered_df.groupby('brand', as_index=False)['demand_score'].mean().sort_values('demand_score', ascending=False)
    fig_demand = px.bar(demand_by_brand, x='brand', y='demand_score', text='demand_score', title='Average Demand Score by Brand', color='demand_score', color_continuous_scale='Tealgrn')
    fig_demand.update_traces(texttemplate='%{text:.0f}', textposition='outside')
    fig_demand.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', coloraxis_showscale=False, height=355, font=dict(color='white'))
    st.plotly_chart(fig_demand, use_container_width=True)

row2_left, row2_mid, row2_right = st.columns([1.15, 1.1, 1])
with row2_left:
    st.markdown('<div class="kicker">Behavior Feed</div><div class="section-title">🧠 Human Behavior Simulation Feed</div>', unsafe_allow_html=True)
    behavior_view = filtered_df.sort_values('timestamp', ascending=False)[['order_id', 'timestamp', 'city', 'brand', 'product', 'customer_type', 'behavior_tag', 'order_status']].head(10).copy()
    behavior_view['timestamp'] = behavior_view['timestamp'].dt.strftime('%d-%m-%Y %H:%M:%S')
    st.dataframe(behavior_view, use_container_width=True, hide_index=True)

with row2_mid:
    st.markdown('<div class="kicker">Product Layer</div><div class="section-title">🛍️ Product Intelligence</div>', unsafe_allow_html=True)
    brand_product_rev = filtered_df.groupby(['brand', 'product'], as_index=False)['price'].sum().sort_values('price', ascending=False)
    st.dataframe(brand_product_rev, use_container_width=True, hide_index=True)

with row2_right:
    st.markdown('<div class="kicker">Anomaly Zone</div><div class="section-title">⚡ AI Anomaly Detector</div>', unsafe_allow_html=True)
    threshold = filtered_df['price'].mean() + 1.5 * filtered_df['price'].std() if len(filtered_df) > 1 else 0
    anomalies = filtered_df[filtered_df['price'] > threshold].sort_values('timestamp', ascending=False)
    if not anomalies.empty:
        st.markdown(f'<div class="alert-box alert-anomaly">{len(anomalies)} high-value orders detected above anomaly threshold.</div>', unsafe_allow_html=True)
        anom_view = anomalies[['order_id', 'timestamp', 'brand', 'product', 'city', 'price']].head(5).copy()
        anom_view['timestamp'] = anom_view['timestamp'].dt.strftime('%d-%m-%Y %H:%M:%S')
        anom_view['price'] = anom_view['price'].map(lambda x: f'₹{x:,.0f}')
        st.dataframe(anom_view, use_container_width=True, hide_index=True)
    else:
        st.success('No unusual order spikes detected in the current filtered view.')

row3_left, row3_right = st.columns([1.3, 1])
with row3_left:
    st.markdown('<div class="kicker">Trend Layer</div><div class="section-title">⏱️ Revenue Trend Monitor</div>', unsafe_allow_html=True)
    timeline = filtered_df.set_index('timestamp').resample('5min')['price'].sum().reset_index()
    fig_line = go.Figure()
    fig_line.add_trace(go.Scatter(x=timeline['timestamp'], y=timeline['price'], mode='lines+markers', line=dict(color='#5cc8ff', width=3), marker=dict(size=7), fill='tozeroy'))
    fig_line.update_layout(title='Revenue Trend (5-Min Buckets)', template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=350, margin=dict(l=20, r=20, t=50, b=20), yaxis_title='Revenue', xaxis_title='Time', font=dict(color='white'))
    st.plotly_chart(fig_line, use_container_width=True)

with row3_right:
    st.markdown('<div class="kicker">Mix Layer</div><div class="section-title">🧩 Product Revenue Mix</div>', unsafe_allow_html=True)
    product_mix = filtered_df.groupby('product', as_index=False)['price'].sum()
    fig_pie = px.pie(product_mix, names='product', values='price', title='Product Revenue Mix', hole=0.55)
    fig_pie.update_traces(textinfo='label+percent', textfont=dict(color='white', size=14), insidetextorientation='horizontal')
    fig_pie.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=350, font=dict(color='white'), legend=dict(font=dict(color='white')))
    st.plotly_chart(fig_pie, use_container_width=True)

st.markdown('<div class="kicker">Recommendation Layer</div><div class="section-title">🧠 AI Recommendation Engine</div>', unsafe_allow_html=True)
recommendations = []
if not weather.empty and (weather['impact'] == 'Rain').any():
    recommendations.append('Increase delivery-focused promotions in rain-affected cities.')
if not weather.empty and (weather['impact'] == 'Heat').any():
    recommendations.append('Push mobile-first offers during heat spikes when customer footfall may reduce.')
if not filtered_df.empty:
    top_brand = filtered_df.groupby('brand')['price'].sum().idxmax()
    top_product = filtered_df.groupby('product')['price'].sum().idxmax()
    recommendations.append(f'Prioritize {top_brand} because it leads filtered revenue performance.')
    recommendations.append(f'Feature {top_product} more prominently because it is the top filtered product by revenue.')
for rec in recommendations:
    st.info(rec)

st.markdown('<div class="kicker">Operations Feed</div><div class="section-title">🛰️ Live Sales Feed</div>', unsafe_allow_html=True)
show_df = filtered_df.sort_values('timestamp', ascending=False).head(15).copy()
show_df['timestamp'] = show_df['timestamp'].dt.strftime('%d-%m-%Y %H:%M:%S')
show_df['price'] = show_df['price'].map(lambda x: f'₹{x:,.0f}')
st.dataframe(show_df[['order_id', 'timestamp', 'brand', 'product', 'price', 'units', 'city', 'customer_type', 'behavior_tag', 'demand_score', 'order_status']], use_container_width=True, hide_index=True)

st.markdown('<div class="kicker">Weather Layer</div><div class="section-title">🌦️ City Weather Status</div>', unsafe_allow_html=True)
if not weather.empty:
    weather_display = weather.copy()
    weather_display['temperature'] = weather_display['temperature'].apply(lambda x: f'{x}°C' if pd.notnull(x) else 'N/A')
    weather_display['rain'] = weather_display['rain'].apply(lambda x: f'{x} mm' if pd.notnull(x) else 'N/A')
    st.dataframe(weather_display[['city', 'condition', 'temperature', 'rain', 'impact', 'sales_signal']], use_container_width=True, hide_index=True)

st.success('War Room Deliverable Status: Auto-refresh is active, decision-first command layout is enabled, alert-first monitoring is visible, and Day 3 weather impact is integrated for active cities.')
