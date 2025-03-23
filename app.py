from flask import Flask, render_template
import sqlite3
import pandas as pd
import os

app = Flask(__name__)

def get_matches_from_db(db_path="kicktipp.db"):
    """Fetch matches from database and group by matchday"""
    if not os.path.exists(db_path):
        print(f"Database file not found: {db_path}")
        return None
        
    try:
        conn = sqlite3.connect(db_path)
        query = """
        SELECT spieltag, termin, heim, gast, ergebnis, punkteregel,
               odds_home, odds_draw, odds_away,
               exp_home_points, exp_draw_points, exp_away_points
        FROM matches
        ORDER BY spieltag, termin
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

@app.route('/')
@app.route('/matchday/<int:matchday>')
def show_matches(matchday=None):
    # Get matches from database
    df = get_matches_from_db()
    
    if df is None or df.empty:
        return render_template('matches.html', 
                            matches=[], 
                            matchdays=[], 
                            current_matchday=None,
                            error="No matches found in database. Please ensure the database exists and contains data.")
    
    # Get unique matchdays for navigation
    matchdays = sorted(df['spieltag'].unique())
    
    # If no matchday specified, use the latest one
    if matchday is None and len(matchdays) > 0:
        matchday = matchdays[-1]
    
    # Filter matches for selected matchday
    if matchday in matchdays:
        matches = df[df['spieltag'] == matchday].to_dict('records')
    else:
        matches = []
    
    return render_template('matches.html', 
                        matches=matches, 
                        matchdays=matchdays, 
                        current_matchday=matchday)

if __name__ == '__main__':
    app.run(debug=True) 