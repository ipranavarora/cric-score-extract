import requests
from bs4 import BeautifulSoup
import re
from flask import Flask, request, render_template_string

app = Flask(__name__)

# --- HTML Template ---
# Using render_template_string for simplicity to keep it in one file.
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Cricbuzz Score Extractor</title>
    <style>
        body { font-family: sans-serif; line-height: 1.6; padding: 20px; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        input[type="text"] { width: 80%; max-width: 600px; padding: 8px; margin-bottom: 10px; }
        button { padding: 10px 15px; cursor: pointer; }
        .result { margin-top: 20px; padding: 15px; border: 1px solid #ccc; background-color: #f9f9f9; }
        .error { color: red; font-weight: bold; }
        .score-details { margin-top: 10px; }
        .score-details p { margin: 5px 0; }
    </style>
</head>
<body>
    <h1>Cricbuzz Live Score Extractor (Specific Match URL)</h1>
    <p>Enter the full URL of a live Cricbuzz match page (e.g., https://www.cricbuzz.com/live-cricket-scores/...)</p>

    <form method="post">
        <label for="url">Match URL:</label>
        <input type="text" id="url" name="url" size="70" value="{{ request.form.url if request.form.url else '' }}" required>
        <button type="submit">Get Score</button>
    </form>

    {% if error %}
        <div class="result error">
            Error: {{ error }}
        </div>
    {% endif %}

    {% if score_data %}
        <div class="result">
            <h2>Match Details:</h2>
            <p><strong>{{ score_data.title }}</strong></p>
            <hr>
            <div class="score-details">
                <p><strong>Score 1:</strong> {{ score_data.score1 if score_data.score1 else 'N/A' }}</p>
                <p><strong>Score 2:</strong> {{ score_data.score2 if score_data.score2 else 'N/A' }}</p>
                <p><strong>Status:</strong> {{ score_data.status if score_data.status else 'N/A' }}</p>
                <p><strong>Batsmen:</strong></p>
                <ul>
                    {% for batter in score_data.batsmen %}
                        <li>{{ batter }}</li>
                    {% else %}
                        <li>N/A</li>
                    {% endfor %}
                </ul>
                <p><strong>Bowlers:</strong></p>
                 <ul>
                    {% for bowler in score_data.bowlers %}
                        <li>{{ bowler }}</li>
                    {% else %}
                        <li>N/A</li>
                    {% endfor %}
                </ul>
                 <p><strong>Recent Overs:</strong> {{ score_data.recent_overs if score_data.recent_overs else 'N/A' }}</p>
            </div>
            <p><small><em>Note: Scraped data depends on Cricbuzz's current HTML structure and may break if they change it.</em></small></p>
        </div>
    {% endif %}

</body>
</html>
"""

def extract_score_from_url(url):
    """
    Fetches and extracts score details from a specific Cricbuzz match URL.

    Args:
        url (str): The URL of the Cricbuzz match page.

    Returns:
        dict: A dictionary containing score details if successful.
        str: An error message string if unsuccessful.
    """
    if not url or not url.startswith("http") or "cricbuzz.com/live-cricket-scores/" not in url:
        return "Invalid Cricbuzz match URL provided."

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'Connection': 'keep-alive'
    }
    extracted_data = {
        "title": "N/A",
        "score1": "N/A",
        "score2": "N/A",
        "status": "N/A",
        "batsmen": [],
        "bowlers": [],
        "recent_overs": "N/A"
    }

    try:
        print(f"Attempting to fetch: {url}")
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        print(f"Status Code: {response.status_code}")

        soup = BeautifulSoup(response.text, 'html.parser')
        print("Successfully parsed HTML.")

        # --- Extract Title ---
        title_tag = soup.find('h1', itemprop='name')
        extracted_data['title'] = title_tag.text.strip() if title_tag else "Title Not Found"
        print(f"Found Title: {extracted_data['title']}")

        # --- Locate the Miniscore Container (based on provided HTML structure) ---
        # This div often contains the core score elements we need
        miniscore_container = soup.find('div', class_='cb-col-100 cb-mini-col') # Trying a slightly broader class first

        if not miniscore_container:
             # Fallback using a different potential parent or structure if the first fails
             miniscore_container = soup.find('div', ng_include="'miniscore'")
             if miniscore_container:
                 # If found via ng-include, re-parse its content if needed (though BS4 usually handles this)
                 miniscore_container = BeautifulSoup(str(miniscore_container), 'html.parser') # Re-parse just this section maybe?

        if not miniscore_container:
             # Final attempt: Look for the score wrapper directly
             miniscore_container = soup.find('div', class_='cb-col-scores') # Find the direct parent of scores

        if not miniscore_container:
            print("Could not find the main miniscore container.")
            # Try finding elements globally if container is missed (less reliable)
            score1_tag = soup.find('h2', class_='cb-text-gray') # Often Innings 1 / opponent score
            score2_tag = soup.find('h2', class_=lambda x: x and 'cb-font-20' in x.split()) # Often Innings 2 / current score
            status_tag = soup.find('div', class_=re.compile(r'cb-text-(inprogress|live|complete|result|stumps|innings break)')) # Status line
        else:
            print("Found miniscore container (or alternative structure).")
            # Find elements within the container
            score1_tag = miniscore_container.find('h2', class_='cb-text-gray')
            score2_tag = miniscore_container.find('h2', class_=lambda x: x and 'cb-font-20' in x.split()) # Use split for robustness
            status_tag = miniscore_container.find('div', class_=re.compile(r'cb-text-(inprogress|live|complete|result|stumps|innings break)'))

        # Update the score container search
        miniscore_container = soup.find('div', class_='cb-col-100 cb-min-stts') or \
                            soup.find('div', class_='cb-col-100 cb-mini-col') or \
                            soup.find('div', class_='cb-col-scores')

        # First try to get match status to determine if match is finished
        status_tag = soup.find('div', class_=re.compile(r'cb-text-(complete|result|stumps|innings break|live|inprogress)'))
        extracted_data['status'] = status_tag.text.strip() if status_tag else "Status Not Found"
        
        # Try different score selectors based on match state
        score_tags = soup.select('.cb-col-100.cb-col.cb-scrs-lst')
        if score_tags:
            # Match might be finished, try to get both innings scores
            for i, score in enumerate(score_tags[:2], 1):
                score_text = score.get_text(strip=True)
                if i == 1:
                    extracted_data['score1'] = score_text
                else:
                    extracted_data['score2'] = score_text
        else:
            # Try live match score format
            score_parent = soup.find('div', class_='cb-min-bat-rw')
            if score_parent:
                current_score = score_parent.find('span', class_='cb-font-20')
                if current_score:
                    extracted_data['score1'] = current_score.text.strip()
                
                # Try to get previous innings score
                prev_score = soup.find('span', class_='cb-text-gray')
                if prev_score:
                    extracted_data['score2'] = prev_score.text.strip()

        # If still no scores found, try the original method
        if extracted_data['score1'] == "N/A" and extracted_data['score2'] == "N/A":
            score1_tag = soup.find('div', class_='cb-min-bat-rw')
            score2_tag = soup.find('span', class_='cb-text-gray')
            
            extracted_data['score1'] = score1_tag.text.strip() if score1_tag else "Score 1 Not Found"
            extracted_data['score2'] = score2_tag.text.strip() if score2_tag else "Score 2 Not Found"

        # --- Extract Batsmen and Bowler Info ---
        # Look for the tables within the container or globally if needed
        info_tables_container = miniscore_container if miniscore_container else soup

        batsman_rows = info_tables_container.select('div.cb-min-inf div.cb-col-100.cb-min-itm-rw') # Should select both batsman rows
        if len(batsman_rows) > 1: # Check if we have at least 2 rows likely belonging to batsmen table
             # Assume first section is batsmen
             for row in batsman_rows[:2]: # Take the first two relevant rows
                name_tag = row.find('a', class_='cb-text-link')
                runs_tag = row.find('div', class_='cb-col-10') # First cb-col-10 is Runs
                balls_tag = row.find_all('div', class_='cb-col-10') # Second cb-col-10 is Balls
                if name_tag and runs_tag and len(balls_tag) > 1:
                     name = name_tag.text.strip()
                     runs = runs_tag.text.strip()
                     balls = balls_tag[1].text.strip() # Get the second one for balls
                     extracted_data['batsmen'].append(f"{name}*: {runs} ({balls})") # Assuming first is striker

        bowler_rows = info_tables_container.select('div.cb-min-inf ~ div.cb-min-inf div.cb-col-100.cb-min-itm-rw') # Select rows in the *second* cb-min-inf block
        if not bowler_rows and len(batsman_rows) > 2: # If the specific selector failed, try using the remaining rows
             bowler_rows = batsman_rows[2:] # Assume rows after batsmen are bowlers (less reliable)

        for row in bowler_rows:
             name_tag = row.find('a', class_='cb-text-link')
             overs_tag = row.find('div', class_='cb-col-10') # First cb-col-10 is Overs
             runs_tag = row.find_all('div', class_='cb-col-10') # Third cb-col-10 is Runs
             wickets_tag = row.find_all('div', class_='cb-col-8') # Second cb-col-8 is Wickets
             if name_tag and overs_tag and len(runs_tag) > 1 and len(wickets_tag) > 1:
                 name = name_tag.text.strip()
                 overs = overs_tag.text.strip()
                 runs = runs_tag[1].text.strip() # Get the second cb-col-10 for runs
                 wickets = wickets_tag[1].text.strip() # Get the second cb-col-8 for wickets
                 extracted_data['bowlers'].append(f"{name}: {overs}-{runs}-{wickets}")

        # --- Extract Recent Overs ---
        recent_overs_tag = soup.find('div', class_='cb-min-rcnt')
        if recent_overs_tag:
            # Extract the text content directly after the 'Recent: ' span
            recent_text_node = recent_overs_tag.find('span', class_='text-bold').next_sibling
            if recent_text_node and isinstance(recent_text_node, str):
                 extracted_data['recent_overs'] = recent_text_node.strip()


        print(f"Batsmen: {extracted_data['batsmen']}")
        print(f"Bowlers: {extracted_data['bowlers']}")
        print(f"Recent Overs: {extracted_data['recent_overs']}")


        # Check if we actually got score data, not just "Not Found"
        if extracted_data['score1'] == "Score 1 Not Found" and extracted_data['score2'] == "Score 2 Not Found":
             return "Could not extract score information. Page structure might have changed or match is not live/valid."

        return extracted_data

    except requests.exceptions.Timeout:
        print("Error: Request timed out.")
        return "The request to Cricbuzz timed out. Please try again later."
    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL: {e}")
        return f"Error fetching URL: {e}"
    except Exception as e:
        print(f"An error occurred during parsing: {e}")
        import traceback
        traceback.print_exc() # Print detailed traceback for debugging
        return f"An error occurred while parsing the page: {e}"


@app.route('/', methods=['GET', 'POST'])
def index():
    score_data = None
    error = None
    if request.method == 'POST':
        url = request.form.get('url')
        result = extract_score_from_url(url)
        if isinstance(result, dict):
            score_data = result
        else:
            error = result
    return render_template_string(HTML_TEMPLATE, score_data=score_data, error=error, request=request)

if __name__ == '__main__':
    # Make it accessible on your local network (optional)
    # app.run(debug=True, host='0.0.0.0')
    app.run(debug=True) # Run only on localhost by default