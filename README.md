# Live Revenue Pulse

A real-time Streamlit sales command center that simulates one sale every 30 seconds, refreshes automatically, and overlays live city weather impact using Open-Meteo.

## Files

- `app.py` - Main Streamlit dashboard
- `sales_generator.py` - Fake live sales feed generator
- `requirements.txt` - Required Python packages
- `sales_data.csv` - Auto-created transaction log when generator starts

## Quick Start

1. Open Terminal 1
2. Install packages
   ```bash
   pip install -r requirements.txt
   ```
3. Start the generator
   ```bash
   python sales_generator.py
   ```
4. Open Terminal 2
5. Start the dashboard
   ```bash
   streamlit run app.py
   ```
6. Wait 30-60 seconds for new live records to appear

## Dashboard KPIs

- Total Revenue
- Current Order Volume
- Average Order Value
- Orders in Last 10 Minutes
- Revenue by City
- Revenue Trend
- Product Revenue Mix
- Weather Impact Alerts

## Weather Rule Logic

- `Rain` if current rain > 0 or rain-related weather code is returned
- `Heat` if temperature is 35°C or higher
- `Normal` otherwise

## Notes

- The app auto-refreshes every 5 seconds.
- Open-Meteo is used because it is free and does not require an API key.
- For demo stability, use a reliable internet connection for weather calls.
