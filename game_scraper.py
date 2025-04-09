import requests
from bs4 import BeautifulSoup
import sqlite3
import time
import re

# Base URLs for each region (content frames)
BASE_URLS = {
    "NTSC-U": "https://psxdatacenter.com/ulist.html",
    "NTSC-J": "https://psxdatacenter.com/jlist.html",
    "PAL": "https://psxdatacenter.com/plist.html"
}

# Headers to mimic a browser
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://psxdatacenter.com/"
}

def create_database():
    """Create SQLite3 database and table with system and language columns."""
    conn = sqlite3.connect("games.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS games (
            game_id TEXT PRIMARY KEY,
            title TEXT,
            region TEXT,
            system TEXT,
            language TEXT,
            updated_from_redump INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

def scrape_region(region, url):
    """Scrape game data, excluding <span> and [ ] content from titles."""
    print(f"Scraping {region} games from {url}...")
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code != 200:
            print(f"Failed to access {url}: {response.status_code}")
            return []
        
        soup = BeautifulSoup(response.content, "html.parser")
        
        print(f"Page title: {soup.title.text if soup.title else 'No title found'}")
        
        tables = soup.find_all("table", class_="sectiontable")
        if not tables:
            print("No tables with class 'sectiontable' found.")
            return []
        
        print(f"Found {len(tables)} sectiontable elements")
        games = []
        
        for table in tables:
            rows = table.find_all("tr")[1:]  # Skip header
            for row in rows:
                cols = row.find_all("td")
                if len(cols) >= 4:  # Ensure col2 (ID), col3 (title), and col4 (language) exist
                    # Extract game IDs from col2, handling <br> tags
                    col2 = cols[1]
                    game_ids = []
                    contents = col2.contents
                    current_id = ""
                    for content in contents:
                        if isinstance(content, str) and content.strip():
                            current_id += content.strip()
                        elif content.name == "br" and current_id:
                            game_ids.append(current_id)
                            current_id = ""
                    if current_id:
                        game_ids.append(current_id)
                    if not game_ids:
                        game_ids = col2.text.strip().split()
                    
                    # Get title from col3, excluding <span> content
                    col3 = cols[2]
                    base_title = ""
                    for content in col3.contents:
                        if isinstance(content, str):
                            base_title += content.strip()
                        elif content.name in ["span", "br"]:
                            break
                    # Remove anything in [ ] including brackets
                    base_title = re.sub(r'\s*\[.*?\]', '', base_title).strip()
                    
                    # Get language from col4, remove brackets, join with commas
                    language_raw = cols[3].text.strip()
                    languages = [lang.strip("[]") for lang in language_raw.split("][")]
                    language = ", ".join(languages)
                    
                    # Handle single or multi-disc games
                    if len(game_ids) == 1:
                        games.append((game_ids[0], base_title, region, "PS1", language, 0))
                    else:
                        for i, game_id in enumerate(game_ids, 1):
                            disc_title = f"{base_title} (Disc {i})"
                            games.append((game_id, disc_title, region, "PS1", language, 0))
        
        print(f"Found {len(games)} game entries in {region}")
        return games
    
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return []

def populate_database():
    """Scrape all regions and populate the database."""
    create_database()
    conn = sqlite3.connect("games.db")
    cursor = conn.cursor()
    
    for region, url in BASE_URLS.items():
        games = scrape_region(region, url)
        cursor.executemany("""
            INSERT OR IGNORE INTO games (game_id, title, region, system, language, updated_from_redump)
            VALUES (?, ?, ?, ?, ?, ?)
        """, games)
        conn.commit()
        print(f"Added {len(games)} games for {region}")
        time.sleep(2)  # Be polite to the server
    
    conn.close()
    print("Database population complete.")

def main():
    print("Starting PS1 game data scrape for all regions...")
    populate_database()
    # Verify database contents
    conn = sqlite3.connect("games.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM games")
    count = cursor.fetchone()[0]
    print(f"Total games in database: {count}")
    # Test specific entries
    test_ids = ["SLUS-00518", "SLUS-01026", "SLUS-01183", "SLUS-00955", "SLUS-01224", "SLPS-01330"]  # Added AFRAID GEAR
    for test_id in test_ids:
        cursor.execute("SELECT title, region, system, language, updated_from_redump FROM games WHERE game_id = ?", (test_id,))
        result = cursor.fetchone()
        if result:
            print(f"Test: {test_id} = {result[0]} ({result[1]}, {result[2]}, Language: {result[3]}, Updated: {result[4]})")
    conn.close()

if __name__ == "__main__":
    main()