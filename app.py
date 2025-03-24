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
    
def get_tipps_from_db(db_path="kicktipp.db"):
    """Fetch tipps from database"""
    if not os.path.exists(db_path):
        print(f"Database file not found: {db_path}")
        return None

    try:
        conn = sqlite3.connect(db_path)
        query = """
        SELECT spieltag, member, points, expected, extra FROM pivot_tipps
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
@app.route('/matchday/<matchday>')
def show_matches(matchday=None):
    # Get matches from database
    df = get_matches_from_db()
    # round float to 2 decimal places
    df = df.round(2)
    df_tipps = get_tipps_from_db()
    # round float to 2 decimal places
    df_tipps = df_tipps.round(2)
    df_tipps['tendenz'] = df_tipps['points'] - df_tipps['extra']
    df_tipps['gluecksfaktor'] = df_tipps['tendenz'] / df_tipps['expected']
    # round float to 2 decimal places
    df_tipps = df_tipps.round(2)
    
    if df is None or df.empty:
        return render_template('matches.html', 
                            matches=[], 
                            matchdays=['gesamt'], 
                            current_matchday=None,
                            tipps=[],
                            is_total=False,
                            error="No matches found in database. Please ensure the database exists and contains data.")
    
    # Get unique matchdays for navigation
    matchdays = ['gesamt'] + [str(x) for x in sorted(df['spieltag'].unique())]
    
    # If no matchday specified, use 'gesamt'
    if matchday is None:
        matchday = 'gesamt'
    
    # Handle 'gesamt' view
    if matchday == 'gesamt':
        matches = []
        if df_tipps is not None and not df_tipps.empty:
            tipps = df_tipps.groupby('member').agg({
                'points': 'sum',
                'expected': 'sum',
                'extra': 'sum'
            }).round(2).reset_index()
            # Calculate tendenz and gluecksfaktor for aggregated data
            tipps['tendenz'] = tipps['points'] - tipps['extra']
            tipps['gluecksfaktor'] = tipps['tendenz'] / tipps['expected']
            tipps = tipps.round(2)
            tipps = tipps.sort_values('points', ascending=False).to_dict('records')
        else:
            tipps = []
        is_total = True
    # Handle regular matchday view
    else:
        try:
            matchday_int = int(matchday)
            matches = df[df['spieltag'] == matchday_int].to_dict('records')
            tipps = df_tipps[df_tipps['spieltag'] == matchday_int].to_dict('records') if df_tipps is not None else []
        except (ValueError, TypeError):
            matches = []
            tipps = []
        is_total = False
    
    return render_template('matches.html', 
                        matches=matches, 
                        matchdays=matchdays, 
                        current_matchday=matchday,
                        tipps=tipps,
                        is_total=is_total)

if __name__ == '__main__':
    app.run(debug=True) 