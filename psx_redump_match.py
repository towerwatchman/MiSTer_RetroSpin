import xml.etree.ElementTree as ET
import sqlite3
from fuzzywuzzy import fuzz
import re

# Path to the Redump XML file (adjust as needed)
REDUMP_FILE = "Sony - PlayStation - Discs (10850) (2025-04-08 08-03-06).xml"
MATCH_THRESHOLD = 85  # Minimum similarity score for a match (0-100)

# Region mappings from Redump to games.db
REGION_MAP = {
    "(USA)": "NTSC-U",
    "(Europe)": "PAL",  # Covers (Europe) and variants like (Europe, Australia)
    "(Japan)": "NTSC-J"
}

# Language mappings from Redump to games.db
LANGUAGE_MAP = {
    "En": "E",  # English
    "De": "G",  # Germany
    "Fr": "F",  # France
    "Ja": "J",  # Japan
    "Es": "Es", # Spanish
    "It": "I"   # Italy
}

def connect_to_database():
    """Connect to games.db and return connection and cursor."""
    conn = sqlite3.connect("games.db")
    cursor = conn.cursor()
    return conn, cursor

def update_table_schema(cursor):
    """Add updated_from_redump column if it doesn’t exist."""
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
    cursor.execute("PRAGMA table_info(games)")
    columns = [col[1] for col in cursor.fetchall()]
    if "updated_from_redump" not in columns:
        cursor.execute("ALTER TABLE games ADD COLUMN updated_from_redump INTEGER DEFAULT 0")

def extract_region_and_language(redump_title):
    """Extract region, language, and clean title from Redump title, defaulting to PAL if no USA/Japan."""
    region = "PAL"  # Default to PAL unless USA or Japan is specified
    language = "Unknown"
    
    # Check for explicit region in parentheses
    for redump_region, db_region in REGION_MAP.items():
        if redump_region in redump_title:
            region = db_region
            if redump_region == "(USA)" and not re.search(r'\((En?,(?:[A-Z][a-z]?,)*[A-Z][a-z]?)\)', redump_title):
                language = "E"
            break
    
    # Extract languages if present (e.g., (En,Fr,De))
    lang_match = re.search(r'\((En?,(?:[A-Z][a-z]?,)*[A-Z][a-z]?)\)', redump_title)
    if lang_match:
        redump_langs = lang_match.group(1).split(",")
        db_langs = [LANGUAGE_MAP.get(lang.strip(), lang.strip()) for lang in redump_langs]
        language = ", ".join(db_langs)
    
    # Clean title: remove all parentheses except (Disc X)
    title = re.sub(r'\s*\((?!Disc\s*\d+\b)[^)]+\)', '', redump_title).strip()
    return title, region, language, redump_title

def parse_redump_xml(file_path):
    """Parse the Redump XML file and return a list of (title, region, language, full_title) tuples."""
    redump_data = []
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        for game in root.findall("game"):
            full_title = game.get("name")
            title, region, language, redump_full_title = extract_region_and_language(full_title)
            redump_data.append((title, region, language, redump_full_title))
        
        return redump_data
    
    except Exception as e:
        print(f"Error parsing Redump XML: {e}")
        return []

def fuzzy_match_titles(redump_title, redump_region, redump_language, db_titles):
    """Find the best match for a Redump title, prioritizing title then language."""
    best_match = None
    best_score = 0
    for db_id, (db_title, db_region, db_language) in db_titles.items():
        if db_region == redump_region:  # Match region first
            # Clean database title similarly, preserving (Disc X)
            db_clean_title = re.sub(r'\s*\((?!Disc\s*\d+\b)[^)]+\)', '', db_title).strip()
            score = fuzz.token_sort_ratio(redump_title, db_clean_title)
            if score >= MATCH_THRESHOLD:
                # Check language compatibility (partial match allowed)
                redump_langs = set(redump_language.split(", "))
                db_langs = set(db_language.split(", "))
                lang_overlap = redump_langs.intersection(db_langs)
                lang_score = len(lang_overlap) / max(len(redump_langs), len(db_langs)) * 100 if redump_langs and db_langs else 0
                combined_score = score + (lang_score * 0.2)  # Weight language lightly
                if combined_score > best_score:
                    best_score = combined_score
                    best_match = (db_id, db_title, db_language)
    
    return best_match, best_score if best_match else 0

def update_database_with_redump(redump_file):
    """Update games.db with Redump names using title-first fuzzy matching."""
    # Parse Redump data
    redump_data = parse_redump_xml(redump_file)
    if not redump_data:
        print("No titles parsed from Redump file. Exiting.")
        return
    
    # Connect to database
    conn, cursor = connect_to_database()
    update_table_schema(cursor)
    
    # Fetch existing games from database
    cursor.execute("SELECT game_id, title, region, language FROM games")
    db_titles = {row[0]: (row[1], row[2], row[3]) for row in cursor.fetchall()}
    
    updated_count = 0
    added_count = 0
    
    for redump_title, redump_region, redump_language, redump_full_title in redump_data:
        match, score = fuzzy_match_titles(redump_title, redump_region, redump_language, db_titles)
        
        if match:
            # Update existing game with Redump full title
            game_id, old_title, db_language = match
            if old_title != redump_full_title:
                cursor.execute("""
                    UPDATE games 
                    SET title = ?, updated_from_redump = 1 
                    WHERE game_id = ?
                """, (redump_full_title, game_id))
                updated_count += 1
                print(f"Updated {game_id}: '{old_title}' -> '{redump_full_title}' (Region: {redump_region}, Language Match: {redump_language} vs {db_language}, Score: {score:.1f})")
        else:
            # Add new game with inferred data
            cursor.execute("""
                INSERT OR IGNORE INTO games (game_id, title, region, system, language, updated_from_redump)
                VALUES (NULL, ?, ?, ?, ?, 1)
            """, (redump_full_title, redump_region, "PS1", redump_language))
            added_count += 1
            print(f"Added '{redump_full_title}' (Region: {redump_region}, Language: {redump_language}, No ID match, Score: {score})")
    
    # Commit changes
    conn.commit()
    print(f"\nUpdated {updated_count} games.")
    print(f"Added {added_count} new games without IDs.")
    
    # Verify specific examples
    test_ids = ["SLUS-00518", "SLUS-01026", "SLUS-01183", "SLUS-00955"]
    for test_id in test_ids:
        cursor.execute("SELECT title, region, system, language, updated_from_redump FROM games WHERE game_id = ?", (test_id,))
        result = cursor.fetchone()
        if result:
            print(f"Test: {test_id} = {result[0]} ({result[1]}, {result[2]}, Language: {result[3]}, Updated: {result[4]})")
    
    conn.close()

def main():
    print("Updating games.db with Redump names using title-first fuzzy matching, region, and language comparison...")
    update_database_with_redump(REDUMP_FILE)

if __name__ == "__main__":
    main()