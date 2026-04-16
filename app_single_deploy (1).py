import random
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title='Live Revenue Pulse', page_icon='📈', layout='wide')

REFRESH_MS = 5000
SALE_INTERVAL_SECONDS = 30
HEAT_THRESHOLD = 35
MAX_ROWS = 500

PRODUCTS = {
    'Laptop': [45000, 65000, 85000],
    'Phone': [12000, 18000, 25000],
    'Tablet': [15000, 22000, 30000],
    'Headphones': [2000, 3500, 5000],
    'Smartwatch': [3000, 6000, 9000],
    'Speakers': [4500, 6000, 7500],
    'DSLR Camperas': [34500, 39500, 43500],
}

CITY_COORDS = {
    'Hyderabad': {'lat': 17.3850, 'lon': 78.4867},
    'Chennai': {'lat': 13.0827, 'lon': 80.2707},
    'Bengaluru': {'lat': 12.9716, 'lon': 77.5946},
    'Mumbai': {'lat': 19.0760, 'lon': 72.8777},
    'Pune': {'lat': 18.5204, 'lon': 73.8567},
    'Kolkata': {'lat': 22.5726, 'lon': 88.3639},
    'New Delhi': {'lat': 28.6139, 'lon': 77.2088},
}

WEATHER_CODE_MAP = {
    0: 'Clear', 1: 'Mainly Clear', 2: 'Partly Cloudy', 3: 'Cloudy', 45: 'Fog', 48: 'Rime Fog',
    51: 'Light Drizzle', 53: 'Moderate Drizzle', 55: 'Dense Drizzle', 61: 'Slight Rain',
    63: 'Moderate Rain', 65: 'Heavy Rain', 71: 'Slight Snow', 80: 'Rain Showers',
    81: 'Rain Showers', 82: 'Violent Rain Showers', 95: 'Thunderstorm'
}
RAIN_CODES = {51, 53, 55, 61, 63, 65, 80, 81, 82, 95}

st.markdown('''
<style>
[data-testid="stAppViewContainer"]{
    background: linear-gradient(135deg, #08111f 0%, #0f1e36 55%, #132743 100%);
    color: #eef6ff;
}
[data-testid="stHeader"]{background: rgba(0,0,0,0);}
.block-container{padding-top:1rem;padding-bottom:1rem;max-width:95%;}
.war-room{background: rgba(8,18,34,0.78);border:1px solid rgba(120,180,255,0.18);border-radius:18px;padding:18px 20px;box-shadow:0 12px 32px rgba(0,0,0,0.22);}
.hero-title{font-size:2rem;font-weight:800;color:#f8fbff;margin-bottom:0.25rem;}
.hero-sub{color:#9fb9d8;font-size:0.98rem;}
.live-pill{display:inline-block;padding:6px 12px;border-radius:999px;background:#10301f;color:#8df0b1;border:1px solid #1b6d3e;font-weight:700;font-size:0.82rem;}
.metric-card{background:linear-gradient(180deg, rgba(18,31,54,0.96), rgba(11,22,39,0.92));border:1px solid rgba(98,162,255,0.22);border-radius:18px;padding:18px;min-height:130px;}
.metric-label{color:#8fa9c9;font-size:0.9rem;margin-bottom:8px;font-weight:600;}
.metric-value{color:#ffffff;font-size:2rem;font-weight:800;line-height:1.1;}
.metric-foot{color:#6fd0ff;font-size:0.85rem;margin-top:10px;}
.alert-box{padding:12px 14px;border-radius:14px;margin-bottom:10px;font-weight:600;border:1px solid rgba(255,255,255,0.12);}
.alert-rain{background:rgba(20,76,133,0.35);color:#a9d3ff;}
.alert-heat{background:rgba(138,62,8,0.35);color:#ffd18f;}
.alert-normal{background:rgba(23,74,45,0.35);color:#9bf0bf;}
.small-note{color:#8fa9c9;font-size:0.85rem;}
</style>
''', unsafe_allow_html=True)

st_autorefresh(interval=REFRESH_MS, key='live_refresh')

if 'sales_df' not in st.session_state:
    st.session_state.sales_df = pd.DataFrame(columns=['timestamp', 'product', 'price', 'city'])
if 'last_generated_at' not in st.session_state:
    st.session_state.last_generated_at = None


def generate_fake_sale():
    product = random.choice(list(PRODUCTS.keys()))
    base_price = random.choice(PRODUCTS[product])
    city = random.choice(list(CITY_COORDS.keys()))
    price = max(base_price + random.randint(-500, 1200), 500)
    return {
        'timestamp': datetime.now(),
        'product': product,
        'price': price,
        'city': city,
    }


def append_sale_if_due():
    now = datetime.now()
    if st.session_state.last_generated_at is None:
        new_row = pd.DataFrame([generate_fake_sale()])
        st.session_state.sales_df = pd.concat([st.session_state.sales_df, new_row], ignore_index=True)
        st.session_state.last_generated_at = now
    else:
        elapsed = (now - st.session_state.last_generated_at).total_seconds()
        if elapsed >= SALE_INTERVAL_SECONDS:
            new_row = pd.DataFrame([generate_fake_sale()])
            st.session_state.sales_df = pd.concat([st.session_state.sales_df, new_row], ignore_index=True)
            st.session_state.last_generated_at = now

    if len(st.session_state.sales_df) > MAX_ROWS:
        st.session_state.sales_df = st.session_state.sales_df.tail(MAX_ROWS).reset_index(drop=True)


@st.cache_data(ttl=300, show_spinner=False)
def fetch_weather(city):
    coords = CITY_COORDS[city]
    url = 'https://api.open-meteo.com/v1/forecast'
    params = {
        'latitude': coords['lat'],
        'longitude': coords['lon'],
        'current': 'temperature_2m,weather_code,rain',
        'forecast_days': 1,
    }
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

    return {
        'city': city,
        'temperature': temp,
        'rain': rain,
        'weather_code': code,
        'condition': condition,
        'impact': impact,
        'sales_signal': sales_signal,
    }


def build_weather_table(cities):
    rows = []
    for city in cities:
        try:
            rows.append(fetch_weather(city))
        except Exception:
            rows.append({
                'city': city,
                'temperature': None,
                'rain': None,
                'weather_code': None,
                'condition': 'Unavailable',
                'impact': 'Unknown',
                'sales_signal': 'Weather API unavailable for this city',
            })
    return pd.DataFrame(rows)


def fmt_inr(x):
    return f'₹{x:,.0f}'


append_sale_if_due()
df = st.session_state.sales_df.copy()
df['timestamp'] = pd.to_datetime(df['timestamp'])
df['price'] = pd.to_numeric(df['price'])
now = df['timestamp'].max()
last_10m = df[df['timestamp'] >= now - timedelta(minutes=10)]

st.markdown('<div class="war-room">', unsafe_allow_html=True)
col_a, col_b = st.columns([4, 1])
with col_a:
    st.markdown('<div class="hero-title">📈 Automated Live Revenue Pulse </div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-sub">Real-time sales command center with weather-linked city monitoring</div>', unsafe_allow_html=True)
with col_b:
    st.markdown('<div style="text-align:right;"><span class="live-pill">● AUTO REFRESH 5s</span></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="small-note" style="text-align:right;margin-top:8px;">Updated: {datetime.now().strftime("%d-%m-%Y %H:%M:%S")}</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

metric1, metric2, metric3, metric4 = st.columns(4)
with metric1:
    st.markdown(f'<div class="metric-card"><div class="metric-label">💰 Total Revenue</div><div class="metric-value">{fmt_inr(df["price"].sum())}</div><div class="metric-foot">All processed sales</div></div>', unsafe_allow_html=True)
with metric2:
    st.markdown(f'<div class="metric-card"><div class="metric-label">🧾 Current Order Volume</div><div class="metric-value">{len(df)}</div><div class="metric-foot">Total live orders captured</div></div>', unsafe_allow_html=True)
with metric3:
    st.markdown(f'<div class="metric-card"><div class="metric-label">📦 Avg Order Value</div><div class="metric-value">{fmt_inr(df["price"].mean())}</div><div class="metric-foot">Average ticket size</div></div>', unsafe_allow_html=True)
with metric4:
    st.markdown(f'<div class="metric-card"><div class="metric-label">⚡ Orders in Last 10 Min</div><div class="metric-value">{len(last_10m)}</div><div class="metric-foot">Recent order velocity</div></div>', unsafe_allow_html=True)

active_cities = sorted(df['city'].dropna().unique().tolist())
weather = build_weather_table(active_cities)

left, right = st.columns([2, 1])
with left:
    revenue_by_city = df.groupby('city', as_index=False)['price'].sum().sort_values('price', ascending=False)
    fig_city = px.bar(revenue_by_city, x='city', y='price', text='price', title='🏙️ Revenue by City', color='price', color_continuous_scale='Blues')
    fig_city.update_traces(texttemplate='₹%{text:,.0f}', textposition='outside')
    fig_city.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', coloraxis_showscale=False, height=360)
    st.plotly_chart(fig_city, use_container_width=True)

with right:
    st.markdown('### 🚨 Weather Impact Alerts')
    for _, row in weather.iterrows():
        cls = 'alert-normal'
        if row['impact'] == 'Rain':
            cls = 'alert-rain'
        elif row['impact'] == 'Heat':
            cls = 'alert-heat'
        msg = f"{row['city']}: {row['impact']} | {row['condition']} | Temp: {row['temperature']}°C"
        st.markdown(f'<div class="alert-box {cls}">{msg}</div>', unsafe_allow_html=True)
    st.caption('Rule logic: Rain if rain > 0 or rain-related weather code exists; Heat if temperature ≥ 35°C; otherwise Normal.')

bottom_left, bottom_right = st.columns([1.25, 1])
with bottom_left:
    timeline = df.set_index('timestamp').resample('5min')['price'].sum().reset_index()
    fig_line = go.Figure()
    fig_line.add_trace(go.Scatter(x=timeline['timestamp'], y=timeline['price'], mode='lines+markers', line=dict(color='#5cc8ff', width=3), marker=dict(size=7), fill='tozeroy'))
    fig_line.update_layout(title='⏱️ Revenue Trend (5-Min Buckets)', template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=340, margin=dict(l=20, r=20, t=50, b=20), yaxis_title='Revenue', xaxis_title='Time')
    st.plotly_chart(fig_line, use_container_width=True)

with bottom_right:
    product_mix = df.groupby('product', as_index=False)['price'].sum()
    fig_pie = px.pie(product_mix, names='product', values='price', title='🛍️ Product Revenue Mix', hole=0.55)
    fig_pie.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', color:#ffffff, height=340)
    st.plotly_chart(fig_pie, use_container_width=True)

st.markdown('### 🛰️ Live Sales Feed')
show_df = df.sort_values('timestamp', ascending=False).head(15).copy()
show_df['timestamp'] = show_df['timestamp'].dt.strftime('%d-%m-%Y %H:%M:%S')
show_df['price'] = show_df['price'].map(lambda x: f'₹{x:,.0f}')
st.dataframe(show_df, use_container_width=True, hide_index=True)

st.markdown('### 🌦️ City Weather Status')
if not weather.empty:
    weather_display = weather.copy()
    weather_display['temperature'] = weather_display['temperature'].apply(lambda x: f'{x}°C' if pd.notnull(x) else 'N/A')
    weather_display['rain'] = weather_display['rain'].apply(lambda x: f'{x} mm' if pd.notnull(x) else 'N/A')
    st.dataframe(weather_display[['city', 'condition', 'temperature', 'rain', 'impact', 'sales_signal']], use_container_width=True, hide_index=True)

st.markdown('### ✅ Day 3 Weather Impact View')
st.info('This dashboard flags whether Rain or Heat is currently affecting sales in active cities by combining live city-level weather conditions with operational sales monitoring.')
