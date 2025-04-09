import requests
from bs4 import BeautifulSoup
import csv
import os

URL = "https://elephantflea.pw/2024/07/sega-saturn-game-ids"
CSV_FILE = "games.csv"

# Initialize CSV file with header if it doesn't exist
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["ID", "Title", "Region", "System"])

# Scrape the website
response = requests.get(URL)
soup = BeautifulSoup(response.content, "html.parser")
table = soup.find("table")
rows = table.find_all("tr")[1:]  # Skip header

# Append all entries, including duplicate IDs
with open(CSV_FILE, 'a', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    for row in rows:
        cols = row.find_all("td")
        if len(cols) >= 2:
            title = cols[0].text.strip()    # e.g., "Tokimeki Memorial Drama Series Vol. 1 - Nijiiro no Seishun (Japan) (Demo)"
            full_id = cols[1].text.strip()  # e.g., "6106663   V1.000"
            game_id = full_id.split()[0]    # Take first part, e.g., "6106663"
            system = "SATURN"
            
            # Determine region from title
            if "(Japan)" in title:
                region = "NTSC-J"
            elif "(USA)" in title:
                region = "NTSC-U"
            elif "(Europe)" in title:
                region = "PAL"
            else:
                region = "Unknown"
            
            # Write every entry, even if ID duplicates
            writer.writerow([game_id, title, region, system])
            print(f"Added: {game_id}, {title}, {region}, {system}")

print("Scraping complete")