import httpx
import sqlite3
from datetime import datetime
from bs4 import BeautifulSoup
import pandas as pd

SEASON_ID = 3167671

# Team name mapping from kicktipp to odds data
TEAM_MAPPING = {
    'FC St. Pauli': 'St. Pauli',
    '1899 Hoffenheim': 'Hoffenheim',
    'FC Augsburg': 'Augsburg',
    'VfL Wolfsburg': 'Wolfsburg',
    'Werder Bremen': 'Werder Bremen',
    'Bor. Mönchengladbach': 'B. Monchengladbach',
    '1. FC Union Berlin': 'Union Berlin',
    'FC Bayern München': 'Bayern Munich',
    'FSV Mainz 05': 'Mainz',
    'SC Freiburg': 'Freiburg',
    'RB Leipzig': 'RB Leipzig',
    'Borussia Dortmund': 'Dortmund',
    'VfL Bochum': 'Bochum',
    'Eintracht Frankfurt': 'Eintracht Frankfurt',
    '1. FC Heidenheim 1846': 'Heidenheim',
    'Holstein Kiel': 'Holstein Kiel',
    'VfB Stuttgart': 'Stuttgart',
    'Bayer 04 Leverkusen': 'Bayer Leverkusen'
}

BASE_URL = "https://www.kicktipp.de/augustiner76/tippuebersicht"
def get_html_content(season_id: int, matchday: int):
    url = f"{BASE_URL}?tippsaisonId={season_id}&spieltagIndex={matchday}"
    response = httpx.get(url)
    return response.text


def extract_match_table(html_content, tippsaison_id: int, spieltag: int):
    # Parse HTML
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find the matches table
    table = soup.find('table', id='spielplanSpiele')
    
    # Initialize list to store matches
    matches = []
    
    # Get all rows from tbody
    rows = table.find('tbody').find_all('tr')
    
    # Process each row
    for row in rows:
        # Skip rows with class 'endOfBlock'
        if 'endOfBlock' in row.get('class', []):
            continue
            
        # Extract cells
        cells = row.find_all('td')
        if len(cells) >= 5:
            # Split punkteregel into home, draw, away
            punkteregel = cells[4].text.strip()
            home, draw, away = map(int, punkteregel.split('-'))
            
            match = {
                'tippsaisonId': tippsaison_id,
                'spieltag': spieltag,
                'termin': cells[0].text.strip(),
                'heim': cells[1].text.strip(),
                'gast': cells[2].text.strip(),
                'ergebnis': cells[3].text.strip(),
                'punkteregel': punkteregel,
                'home': home,
                'draw': draw,
                'away': away
            }
            matches.append(match)
    
    # Convert to DataFrame
    df = pd.DataFrame(matches)
    return df

def scrape_matchdays(season_id: int, start_matchday: int, end_matchday: int) -> pd.DataFrame:
    """
    Scrape match information for a range of matchdays.
    
    Args:
        season_id: The ID of the season to scrape
        start_matchday: First matchday to scrape (inclusive)
        end_matchday: Last matchday to scrape (inclusive)
    
    Returns:
        DataFrame containing all matches from the specified matchdays
    """
    all_matches = []
    
    for matchday in range(start_matchday, end_matchday + 1):
        try:
            html_content = get_html_content(season_id, matchday)
            df = extract_match_table(html_content, season_id, matchday)
            all_matches.append(df)
            print(f"Scraped matchday {matchday}")
        except Exception as e:
            print(f"Error scraping matchday {matchday}: {e}")
            continue
    
    # Combine all matchdays into one DataFrame
    if all_matches:
        combined_df = pd.concat(all_matches, ignore_index=True)
        return combined_df
    else:
        return pd.DataFrame()  # Return empty DataFrame if no matches were scraped

def store_matches_in_db(df: pd.DataFrame, db_path: str = "kicktipp.db"):
    """
    Store matches DataFrame in SQLite database.
    
    Args:
        df: DataFrame containing match information
        db_path: Path to SQLite database file
    """
    # Create connection to database
    conn = sqlite3.connect(db_path)
    
    # Create table if it doesn't exist
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS matches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tippsaisonId INTEGER,
        spieltag INTEGER,
        termin TEXT,
        heim TEXT,
        gast TEXT,
        ergebnis TEXT,
        punkteregel TEXT,
        home_points INTEGER,
        draw_points INTEGER,
        away_points INTEGER,
        xeid TEXT,
        odds_home FLOAT,
        odds_draw FLOAT,
        odds_away FLOAT,
        exp_home_points FLOAT,
        exp_draw_points FLOAT,
        exp_away_points FLOAT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    conn.execute(create_table_sql)
    
    # Insert data from DataFrame
    for _, row in df.iterrows():
        insert_sql = """
        INSERT INTO matches (
            tippsaisonId, spieltag, termin, heim, gast, ergebnis,
            punkteregel, home_points, draw_points, away_points, xeid,
            odds_home, odds_draw, odds_away,
            exp_home_points, exp_draw_points, exp_away_points
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        values = (
            row['tippsaisonId'],
            row['spieltag'],
            row['termin'],
            row['heim'],
            row['gast'],
            row['ergebnis'],
            row['punkteregel'],
            row['home_points'],
            row['draw_points'],
            row['away_points'],
            row['xeid'],
            row['odds_home'],
            row['odds_draw'],
            row['odds_away'],
            row['exp_home_points'],
            row['exp_draw_points'],
            row['exp_away_points']
        )
        conn.execute(insert_sql, values)
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    print(f"Stored {len(df)} matches in database {db_path}")

def enrich_matches_with_odds(matches_df: pd.DataFrame, odds_file: str = "buli_odds.csv") -> pd.DataFrame:
    """
    Enrich matches DataFrame with odds data from CSV file.
    Matches based on date (without time) and team names.
    Adds expected points columns based on odds and point rules.
    """
    # Read odds data
    odds_df = pd.read_csv(odds_file)
    
    # Convert team names in matches_df to match odds_df format
    matches_df['heim_odds'] = matches_df['heim'].map(TEAM_MAPPING)
    matches_df['gast_odds'] = matches_df['gast'].map(TEAM_MAPPING)
    
    # Convert dates and extract only the date part (no time)
    odds_df['date'] = pd.to_datetime(odds_df['date']).dt.date
    matches_df['match_date'] = pd.to_datetime(matches_df['termin'], format='%d.%m.%y %H:%M').dt.date
    
    # Merge DataFrames
    enriched_df = pd.merge(
        matches_df,
        odds_df,
        left_on=['match_date', 'heim_odds', 'gast_odds'],
        right_on=['date', 'home', 'away'],
        how='left'
    )
    
    # Rename point columns to avoid confusion
    enriched_df = enriched_df.rename(columns={
        'home_x': 'home_points',
        'draw': 'draw_points',
        'away_x': 'away_points',
        'home_1x2': 'odds_home',
        'draw_1x2': 'odds_draw',
        'away_1x2': 'odds_away'
    })
    
    # drop home_y, away_y
    enriched_df = enriched_df.drop(columns=['home_y', 'away_y'])
    
    # Calculate expected points using points * (1/odds)
    enriched_df['exp_home_points'] = enriched_df['home_points'] * (1 / enriched_df['odds_home'])
    enriched_df['exp_draw_points'] = enriched_df['draw_points'] * (1 / enriched_df['odds_draw'])
    enriched_df['exp_away_points'] = enriched_df['away_points'] * (1 / enriched_df['odds_away'])
    
    # Drop temporary columns
    columns_to_drop = ['heim_odds', 'gast_odds', 'date', 'match_date']
    existing_columns = [col for col in columns_to_drop if col in enriched_df.columns]
    enriched_df = enriched_df.drop(columns=existing_columns)
    
    return enriched_df

# Example usage:
# df = scrape_matchdays(SEASON_ID, 1, 34)  # Scrape all matchdays
# df_with_odds = enrich_matches_with_odds(df)  # Add odds data
# store_matches_in_db(df_with_odds)  # Store in database
