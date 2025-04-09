import requests
from bs4 import BeautifulSoup
import csv

URL = "https://elephantflea.pw/2024/07/sega-saturn-game-ids"
CSV_FILE = "games.csv"

# Fetch existing IDs to avoid duplicates
existing_ids = set()
try:
    with open(CSV_FILE, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)  # Skip header
        for row in reader:
            if row:
                existing_ids.add(row[0])
except FileNotFoundError:
    with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["ID", "Title"])

# Scrape the website
response = requests.get(URL)
soup = BeautifulSoup(response.content, "html.parser")
table = soup.find("table")
rows = table.find_all("tr")[1:]  # Skip header

# Append new entries
with open(CSV_FILE, 'a', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    for row in rows:
        cols = row.find_all("td")
        if len(cols) >= 2:
            game_id = cols[0].text.strip()
            title = cols[1].text.strip()
            if game_id not in existing_ids:
                writer.writerow([game_id, title])
                print(f"Added: {title} ({game_id})")
            else:
                print(f"Skipped duplicate: {game_id}")

print("Scraping complete")