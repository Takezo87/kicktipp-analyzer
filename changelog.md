Added Tendency Information to Tipps
Added tendency (1, X, 2) calculation for each member's tipps to enable tendency-based analysis.

- Added _get_tendency_from_tipp helper function to convert score predictions to tendencies
- Modified extract_tipps to include tendency columns for each member 

Added Expected Points Calculation per Member
Added functionality to calculate expected points for each member based on their tendency prediction and odds-based expected points.

- Implemented expected_points_member function to calculate expected points per member
- Maps member tendencies (1, X, 2) to corresponding expected points from odds 

Display Tipps on Matchday Page
Added functionality to display tipps for each matchday below the matches, providing better visibility of predictions and results.

- Updated show_matches route to process and pass tipps data to template
- Added tipps display section in matches.html template
- Added error handling for cases when tipps data is unavailable 

Add Total Points Overview Page
Added a new route '/gesamt' that displays the total points and expected points for each member across all matchdays, with values rounded to 2 decimal places.

- Added new route 'show_total' to display overall points
- Created new template 'total.html' for showing total points
- Added navigation link to the total points overview
- Implemented rounding to 2 decimal places for point values 

Integrate Total Points View into Matchday Route
Modified the matchday route to include a 'gesamt' view as the default landing page, showing total points across all matchdays.

- Updated matchday route to handle 'gesamt' as a special matchday
- Modified template to display different headers and labels for total view
- Changed default landing page to show total points view
- Removed separate gesamt route in favor of integrated approach 

Fix Matchday and Total View Integration
Fixed issues with template rendering and matchday display after integrating the total points view.

- Fixed matchday navigation by converting numbers to strings
- Added proper error handling for matchday conversion
- Updated template to correctly handle both total and matchday views
- Fixed conditional display of matches section
- Ensured consistent passing of is_total flag 

Fix Navigation Link for Total View
Fixed the navigation link in base template to use the integrated matchday route for the total view.

- Updated base.html template to use correct route for total view
- Removed obsolete show_total endpoint reference 

Enhanced Match Display Information
Added display of point rules and expected points columns to provide more detailed match information.

- Added punkteregel column to match table
- Added expected points columns (home/draw/away) to match table 

# Bonus Points Calculation

Implemented the extra_punkte function to calculate bonus points based on match predictions:
- 2 points for exact match result
- 1 point for correct goal difference
- 0 points for draws or incorrect predictions 

# Extra Points Integration

Added extra points calculation to match table combination:
- Added extra points columns for each member
- Calculates bonus points based on match results and predictions
- Uses the extra_punkte function to determine points (2 for exact match, 1 for correct difference) 

# Table Styling Improvements
Improved the visual appearance of tables and navigation with modern styling, better spacing, and subtle visual effects.

- Enhanced table styling with better borders and spacing
- Added alternating row colors and hover effects
- Improved section headers and container styling
- Updated navigation buttons with modern design
- Added subtle shadows and rounded corners for depth 

# Add Tendenz and Glücksfaktor to Tables
Added Tendenz and Glücksfaktor columns to the tipps tables with visual indicators for positive and negative values.

- Added Tendenz and Glücksfaktor columns to tipps table
- Added color coding for positive (green) and negative (red) values
- Improved table column alignment and spacing
- Right-aligned numeric columns for better readability 

# Fix Total View Tendenz and Glücksfaktor
Fixed calculation of Tendenz and Glücksfaktor in the total view to properly show aggregated values.

- Added Tendenz and Glücksfaktor calculation for aggregated data in total view
- Ensured consistent rounding of values
- Fixed missing calculations in groupby aggregation 