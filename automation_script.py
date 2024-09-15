import pandas as pd
import requests
import json
import os
import sqlite3
import time
from datetime import datetime
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt
import seaborn as sns
from bs4 import BeautifulSoup
from selenium import webdriver
from dotenv import load_dotenv
load_dotenv()
API_URL = os.getenv('API_URL')
API_KEY = os.getenv('API_KEY')

def upload_product_data(file_path):
    df = pd.read_csv(file_path)
    headers = {'Authorization': f'Bearer {API_KEY}', 'Content-Type': 'application/json'}
    
    for _, row in df.iterrows():
        product_data = {
            'description': row['description'],
            'price': row['price'],
            'image_url': row['image_url']
        }
        print(f"Uploading product data: {product_data}") 
        try:
            response = requests.post(API_URL, headers=headers, data=json.dumps(product_data))
            
            print(f"Response status code: {response.status_code}")  # Debug print
            print(f"Response content: {response.text}")  # Debug print
            
            if response.status_code == 201:
                print(f"Product '{row['description']}' uploaded successfully.")
            else:
                print(f"Failed to upload product '{row['description']}': {response.text}")
        except requests.RequestException as e:
            print(f"Request failed: {e}")
conn = sqlite3.connect('prices.db')
cursor = conn.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS products
                  (product_id INTEGER PRIMARY KEY, 
                   product_name TEXT, 
                   current_price REAL, 
                   competitor_price REAL)''')

def fetch_competitor_prices():
    return pd.DataFrame({
        'product_id': [1, 2, 3],
        'competitor_price': [19.99, 29.99, 39.99]
    })
def adjust_prices():
    competitor_prices = fetch_competitor_prices()
    for index, row in competitor_prices.iterrows():
        cursor.execute('SELECT current_price FROM products WHERE product_id = ?', (row['product_id'],))
        result = cursor.fetchone()
        if result:
            current_price = result[0]
            if row['competitor_price'] < current_price:
                new_price = row['competitor_price'] + 1.00
                cursor.execute('UPDATE products SET current_price = ? WHERE product_id = ?', (new_price, row['product_id']))
                conn.commit()
                print(f"Price updated for product {row['product_id']} to {new_price}")
        else:
            print(f"Product ID {row['product_id']} not found in the database.")
def analyze_customer_data():
    customer_data = pd.read_csv('customer_data.csv')
    customer_data = customer_data.dropna()
    customer_data = customer_data.drop_duplicates()

    features = customer_data[['purchase_amount', 'browsing_time']]
    kmeans = KMeans(n_clusters=4, random_state=42).fit(features)
    customer_data['segment'] = kmeans.labels_

    sns.countplot(data=customer_data, x='segment')
    plt.title('Customer Segments by Value')
    plt.show()
def get_page_content(url):
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return BeautifulSoup(response.text, 'html.parser')
    else:
        print(f"Failed to retrieve page: {response.status_code}")
        return None


def get_dynamic_content(url):
    driver = webdriver.Chrome()
    driver.get(url)
    time.sleep(5)
    html_content = driver.page_source
    driver.quit()
    return BeautifulSoup(html_content, 'html.parser')

def extract_reviews(soup):
    if not soup:
        return []
    
    reviews_data = []
    reviews = soup.find_all('div', class_='review')
    for review in reviews:
        try:
            review_text = review.find('span', class_='review-text').text
            review_rating = review.find('span', class_='review-rating').text
            review_date = review.find('span', class_='review-date').text
            reviews_data.append({
                'Review Text': review_text,
                'Rating': review_rating,
                'Date': review_date
            })
        except AttributeError:
            continue
    return reviews_data


def scrape_reviews(url, dynamic=False):
    all_reviews = []
    while url:
        print(f"Scraping page: {url}")
        if dynamic:
            soup = get_dynamic_content(url)
        else:
            soup = get_page_content(url)

        if soup:
            reviews = extract_reviews(soup)
            all_reviews.extend(reviews)
            next_page = soup.find('a', class_='next-page')
            url = next_page['href'] if next_page else None
        else:
            print("Failed to retrieve or parse page.")
            break
    return all_reviews


def save_to_csv(data, filename='customer_reviews.csv'):
    df = pd.DataFrame(data)
    df.to_csv(filename, index=False)
    print(f"Saved {len(data)} reviews to {filename}")
def create_inventory_db():
    conn = sqlite3.connect('inventory.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS inventory
                      (p_id INTEGER PRIMARY KEY, 
                       name TEXT, 
                       stock_level INTEGER, 
                       reorder_level INTEGER, 
                       supplier TEXT)''')
    conn.commit()
    return conn, cursor

def update_stock(p_id, quantity, cursor, conn):
    cursor.execute('UPDATE inventory SET stock_level = stock_level + ? WHERE p_id = ?', (quantity, p_id))
    conn.commit()

def check_reorder(cursor):
    df = pd.read_sql_query('SELECT * FROM inventory', conn)
    df['reorder_needed'] = df['stock_level'] < df['reorder_level']
    
    for _, row in df[df['reorder_needed']].iterrows():
        print(f"Reorder needed for product {row['name']}")

if __name__ == '__main__':
    upload_product_data('products.csv')

    adjust_prices()

    analyze_customer_data()

    review_url = 'https://example.com/product-reviews'
    reviews = scrape_reviews(review_url, dynamic=False)
    if reviews:
        save_to_csv(reviews)

    conn, cursor = create_inventory_db()
    update_stock(1, 50, cursor, conn)
    check_reorder(cursor)
    conn.close()
