import os
import time
import random
import pandas as pd
from datetime import datetime

DATA_FILE = 'sales_data.csv'
INTERVAL_SECONDS = 30

PRODUCTS = {
    'Laptop': [45000, 65000, 85000],
    'Phone': [12000, 18000, 25000],
    'Tablet': [15000, 22000, 30000],
    'Headphones': [2000, 3500, 5000],
    'Smartwatch': [3000, 6000, 9000],
}

CITIES = ['Hyderabad', 'Chennai', 'Bengaluru', 'Mumbai', 'Pune']


def init_file():
    if not os.path.exists(DATA_FILE):
        df = pd.DataFrame(columns=['timestamp', 'product', 'price', 'city'])
        df.to_csv(DATA_FILE, index=False)


def fake_sale():
    product = random.choice(list(PRODUCTS.keys()))
    price = random.choice(PRODUCTS[product]) + random.randint(-500, 1200)
    city = random.choice(CITIES)
    return {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'product': product,
        'price': max(price, 500),
        'city': city,
    }


def append_sale(row):
    pd.DataFrame([row]).to_csv(DATA_FILE, mode='a', header=False, index=False)


if __name__ == '__main__':
    init_file()
    print('Live sales generator started. Press Ctrl+C to stop.')
    while True:
        row = fake_sale()
        append_sale(row)
        print(f"New sale -> {row}")
        time.sleep(INTERVAL_SECONDS)
