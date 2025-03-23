import httpx
import sqlite3
# from datetime import datetime
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

def _get_tendency_from_tipp(tipp: str) -> str:
    """Helper function to determine tendency (1, X, 2) from a tipp string."""
    if not tipp or not isinstance(tipp, str):
        return None
    
    try:
        home, away = map(int, tipp.split(':'))
        if home > away:
            return '1'
        elif home < away:
            return '2'
        else:
            return 'X'
    except (ValueError, AttributeError):
        return None

def extract_tipps(html_content, tippsaison_id: int, spieltag: int) -> pd.DataFrame:
    """
    Extract tipps from HTML content and return as DataFrame with matches as rows and members as columns.
    
    Args:
        html_content: Raw HTML content
        tippsaison_id: ID of the season
        spieltag: Matchday number
    
    Returns:
        DataFrame with matches as rows and members as columns containing their tipps
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find the ranking table which contains the tipps
    table = soup.find('table', id='ranking')
    if not table:
        return pd.DataFrame()
    
    # Extract member names from table rows
    members = []
    tipps_by_member = []
    points_by_member = []
    
    # Process each row (member)
    for row in table.find('tbody').find_all('tr', class_='teilnehmer'):
        # Get member name
        member_name = row.find('div', class_='mg_name').text.strip()
        members.append(member_name)
        
        # Get all tipps for this member
        tipp_cells = row.find_all('td', class_='ereignis')
        
        # Extract tipps and points, handling empty cells
        member_tipps = []
        member_points = []
        
        for cell in tipp_cells:
            tipp = None
            points = None
            
            # Get the tipp (main text content before any sub tag)
            if cell.strings:
                tipp_text = next(cell.strings, '').strip()
                if tipp_text:
                    tipp = tipp_text
            
            # Get points (content of sub tag if it exists)
            sub_tag = cell.find('sub')
            if sub_tag and sub_tag.text.strip():
                try:
                    points = int(sub_tag.text.strip())
                except ValueError:
                    points = None
            
            member_tipps.append(tipp if tipp else None)
            member_points.append(points)
                
        tipps_by_member.append(member_tipps)
        points_by_member.append(member_points)
    
    # Create two DataFrames - one for tipps and one for points
    tipps_df = pd.DataFrame(tipps_by_member, index=members).T
    points_df = pd.DataFrame(points_by_member, index=members).T
    
    # Create tendency DataFrame
    tendency_df = tipps_df.apply(lambda x: x.map(_get_tendency_from_tipp))
    
    # Add suffixes to distinguish between tipps, points, and tendencies
    tipps_df = tipps_df.add_suffix('_tipp')
    points_df = points_df.add_suffix('_points')
    tendency_df = tendency_df.add_suffix('_tendenz')
    
    # Combine the DataFrames
    result_df = pd.concat([tipps_df, points_df, tendency_df], axis=1)
    
    return result_df

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

def combine_match_table_and_tipps(match_table: pd.DataFrame, tipps: pd.DataFrame) -> pd.DataFrame:
    """
    Combine match table and tipps DataFrames.
    
    Args:
        match_table: DataFrame containing match information
        tipps: DataFrame containing tipps and points for each member
    
    Returns:
        DataFrame with match information and corresponding tipps/points
    """
    # Create a copy of match_table to avoid modifying the original
    result_df = match_table.copy()
    
    # Reset index to ensure we can concatenate properly
    result_df = result_df.reset_index(drop=True)
    tipps = tipps.reset_index(drop=True)
    
    # Add all tipp columns to the match table
    for column in tipps.columns:
        result_df[column] = tipps[column]
    
    return result_df

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
            df_tipps = extract_tipps(html_content, season_id, matchday)
            df_ = combine_match_table_and_tipps(df, df_tipps)
            all_matches.append(df_)
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
    
def expected_points_member(enriched_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate expected points for each member based on their tendency prediction
    and the corresponding expected points from odds.
    
    Args:
        enriched_df: DataFrame containing matches, tipps, tendencies, and expected points from odds
    
    Returns:
        DataFrame with additional columns for expected points per member
    """
    result_df = enriched_df.copy()
    
    # Get all member columns by finding columns ending with '_tendenz'
    member_cols = [col for col in result_df.columns if col.endswith('_tendenz')]
    
    for col in member_cols:
        # Get member name (remove '_tendenz' suffix)
        member_name = col[:-8]
        
        # Create expected points column for member
        expected_col = f"{member_name}_expected"
        
        # Initialize with zeros
        result_df[expected_col] = 0.0
        
        # Set expected points based on tendency
        mask_1 = result_df[col] == '1'
        mask_x = result_df[col] == 'X'
        mask_2 = result_df[col] == '2'
        
        result_df.loc[mask_1, expected_col] = result_df.loc[mask_1, 'exp_home_points']
        result_df.loc[mask_x, expected_col] = result_df.loc[mask_x, 'exp_draw_points']
        result_df.loc[mask_2, expected_col] = result_df.loc[mask_2, 'exp_away_points']
    
    return result_df

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

def get_members(df: pd.DataFrame) -> list:
    """
    Get all member names from DataFrame columns.
    
    Args:
        df: DataFrame containing matches, tipps, points, and expected points
    
    Returns:
        List of member names
    """
    # Get unique member names by finding columns ending with '_points'
    # Filter out home/draw/away points columns
    member_cols = [col[:-7] for col in df.columns 
                  if col.endswith('_points') 
                  and not any(s in col for s in ('home_', 'draw_', 'away_'))]
    return member_cols

def pivot_tipps(df: pd.DataFrame) -> pd.DataFrame:
    """
    Pivot the DataFrame to show total points and expected points per member per matchday.
    
    Args:
        df: DataFrame containing matches, tipps, points, and expected points
    
    Returns:
        DataFrame with columns: spieltag, member, points, expected
    """
    # Get unique member names by finding columns ending with '_points'
    members = get_members(df)
    print(members)
    
    # Initialize list to store rows
    pivot_data = []
    
    # Group by spieltag
    for spieltag, group in df.groupby('spieltag'):
        for member in members:
            points_col = f"{member}_points"
            expected_col = f"{member}_expected"
            
            # Sum points and expected points for this member in this matchday
            total_points = group[points_col].sum()
            total_expected = group[expected_col].sum()
            
            pivot_data.append({
                'spieltag': spieltag,
                'member': member,
                'points': total_points,
                'expected': total_expected
            })
    
    # Create DataFrame from pivot data and sort by spieltag and member
    result_df = pd.DataFrame(pivot_data)
    result_df = result_df.sort_values(['spieltag', 'member']).reset_index(drop=True)
    
    return result_df
    

def store_pivot_tipps(df: pd.DataFrame, db_path: str = "kicktipp.db"):
    """
    Store pivot DataFrame in SQLite database.
    """
    # Create connection to database
    conn = sqlite3.connect(db_path)
    
    # Create table if it doesn't exist
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS pivot_tipps (
        spieltag INTEGER,
        member TEXT,
        points INTEGER,
        expected FLOAT
    )
    """
    conn.execute(create_table_sql)
    
    # Insert data from DataFrame
    for _, row in df.iterrows():
        insert_sql = """
        INSERT INTO pivot_tipps (spieltag, member, points, expected)
        VALUES (?, ?, ?, ?)
        """
        values = (
            row['spieltag'],
            row['member'],
            row['points'],
            row['expected']
        )
        conn.execute(insert_sql, values)
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    print(f"Stored {len(df)} pivot tipps in database {db_path}")
    