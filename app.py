import requests
from bs4 import BeautifulSoup
import re  # Make sure re is imported
import traceback

def extract_score_from_url(url):
    """
    Fetches and extracts score details from a specific Cricbuzz match URL.
    Uses Regex within the finished match container for more robust score finding.

    Args:
        url (str): The URL of the Cricbuzz match page.

    Returns:
        dict: A dictionary containing score details if successful.
        str: An error message string if unsuccessful.
    """
    if not url or not url.startswith("http") or "cricbuzz.com/live-cricket-scores/" not in url:
        return "Invalid Cricbuzz match URL provided. Needs to be like 'https://www.cricbuzz.com/live-cricket-scores/...'"

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

    # Regex to find score patterns like "TEAM XXX/Y (ZZ.Z Ov)" or "TEAM XXX (ZZ Ov)"
    # Allows for 2-4 uppercase letters for team, optional /wickets, optional (Overs)
    score_pattern = re.compile(r"([A-Z]{2,4}\s+\d{1,3}(?:/\d{1,2})?(?:\s+\(\d{1,3}(?:\.\d)?\s*Ov\))?)")
    # Simpler pattern if the above is too complex or fails (finds TEAM SCORE/Wkts):
    # score_pattern_simple = re.compile(r"([A-Z]{2,4}\s+\d{1,3}(?:/\d{1,2})?)")


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

        # --- Locate the Main Score/Status Area ---
        live_container = soup.find('div', class_='cb-min-lv')
        finished_container = soup.find('div', class_='cb-min-comp')

        is_live = bool(live_container)
        is_finished = bool(finished_container)

        if is_finished:
            print("Detected finished match structure.")
            container_to_search = finished_container
            # --- Finished Match Logic ---
            status_tag = container_to_search.find('div', class_=re.compile(r'cb-text-(complete|result)'))
            extracted_data['status'] = status_tag.text.strip() if status_tag else "Status Not Found in Finished Container"

            # --- Extract scores using REGEX within the finished container ---
            container_text = container_to_search.get_text(separator=' ', strip=True)
            print(f"Text in finished container: '{container_text[:500]}...'") # Print start of text for debug
            score_matches = score_pattern.findall(container_text)

            print(f"Regex score matches found: {score_matches}")

            if len(score_matches) >= 1:
                extracted_data['score1'] = score_matches[0].strip()
                 # Try to remove the result text if it got included in the regex match accidentally
                if extracted_data['status'] != "Status Not Found in Finished Container" and extracted_data['status'] in extracted_data['score1']:
                     extracted_data['score1'] = extracted_data['score1'].replace(extracted_data['status'], '').strip()

            if len(score_matches) >= 2:
                extracted_data['score2'] = score_matches[1].strip()
                if extracted_data['status'] != "Status Not Found in Finished Container" and extracted_data['status'] in extracted_data['score2']:
                     extracted_data['score2'] = extracted_data['score2'].replace(extracted_data['status'], '').strip()

            # If regex failed, maybe try finding the h2 tags again as a last resort?
            if extracted_data['score1'] == 'N/A' or extracted_data['score2'] == 'N/A':
                 print("Regex failed to find scores, trying h2.cb-min-tm fallback...")
                 score_wrapper = container_to_search.find('div', class_='cb-scrs-wrp') or container_to_search
                 score_tags_h2 = score_wrapper.find_all('h2', class_='cb-min-tm')
                 if len(score_tags_h2) >= 1 and extracted_data['score1'] == 'N/A':
                     extracted_data['score1'] = score_tags_h2[0].text.strip()
                 if len(score_tags_h2) >= 2 and extracted_data['score2'] == 'N/A':
                     extracted_data['score2'] = score_tags_h2[1].text.strip()


            extracted_data['batsmen'] = ["N/A (Match Finished)"]
            extracted_data['bowlers'] = ["N/A (Match Finished)"]
            extracted_data['recent_overs'] = "N/A (Match Finished)"

        elif is_live:
            # Keep the existing live match logic (assuming it works reasonably well)
            print("Detected live match structure. Using previous live logic.")
            miniscore_container = live_container

            status_tag = miniscore_container.find('div', class_=re.compile(r'cb-text-(inprogress|live|innings break|stumps)'))
            extracted_data['status'] = status_tag.text.strip() if status_tag else "Status Not Found in Live Container"

            score1_tag = miniscore_container.find('h2', class_='cb-text-gray')
            score2_tag_container = miniscore_container.find('div', class_='cb-min-bat-rw')
            score2_tag = score2_tag_container.find('h2', class_=lambda x: x and 'cb-font-20' in x.split()) if score2_tag_container else None

            extracted_data['score1'] = score1_tag.text.strip() if score1_tag else "Score 1 Not Found"
            extracted_data['score2'] = score2_tag.text.strip() if score2_tag else "Score 2 Not Found"

            batsman_section = miniscore_container.find('div', class_='cb-min-inf')
            bowler_section = batsman_section.find_next_sibling('div', class_='cb-min-inf') if batsman_section else None

            if batsman_section:
                batsman_rows = batsman_section.select('.cb-col-100.cb-min-itm-rw')
                for row in batsman_rows:
                    name_tag = row.find('a', class_='cb-text-link')
                    runs_tag = row.find('div', class_='cb-col-10')
                    balls_tag_list = row.find_all('div', class_='cb-col-10')
                    if name_tag and runs_tag and len(balls_tag_list) > 1:
                         name = name_tag.text.strip()
                         runs = runs_tag.text.strip()
                         balls = balls_tag_list[1].text.strip()
                         is_striker = '*' in row.find('div', class_='cb-col-50').text
                         extracted_data['batsmen'].append(f"{name}{'*' if is_striker else ''}: {runs} ({balls})")

            if bowler_section:
                 bowler_rows = bowler_section.select('.cb-col-100.cb-min-itm-rw')
                 for row in bowler_rows:
                     name_tag = row.find('a', class_='cb-text-link')
                     overs_tag = row.find('div', class_='cb-col-10')
                     runs_tag_list = row.find_all('div', class_='cb-col-10')
                     wickets_tag_list = row.find_all('div', class_='cb-col-8')
                     if name_tag and overs_tag and len(runs_tag_list) > 1 and len(wickets_tag_list) > 1:
                         name = name_tag.text.strip()
                         overs = overs_tag.text.strip()
                         runs = runs_tag_list[1].text.strip()
                         wickets = wickets_tag_list[1].text.strip()
                         extracted_data['bowlers'].append(f"{name}: {overs}-{runs}-{wickets}")

            recent_overs_tag = miniscore_container.find('div', class_='cb-min-rcnt')
            if recent_overs_tag:
                recent_span = recent_overs_tag.find('span', string=re.compile(r'Recent:'))
                if recent_span:
                    recent_text = recent_span.next_sibling
                    if recent_text and isinstance(recent_text, str):
                        extracted_data['recent_overs'] = recent_text.strip()
                    elif recent_span.find_next_sibling('span'):
                         extracted_data['recent_overs'] = recent_span.find_next_sibling('span').text.strip()
        else:
            # --- Fallback if neither live nor finished structure detected clearly ---
            print("Could not detect standard live/finished structure. Attempting general extraction.")
            status_tag = soup.find('div', class_=re.compile(r'cb-text-(complete|result|stumps|innings break|live|inprogress)'))
            extracted_data['status'] = status_tag.text.strip() if status_tag else "Status Not Found (Fallback)"

            # Try regex on the whole body as a last resort? (Less reliable)
            body_text = soup.body.get_text(separator=' ', strip=True) if soup.body else ""
            score_matches = score_pattern.findall(body_text)
            if len(score_matches) >= 1:
                 extracted_data['score1'] = score_matches[0].strip()
            if len(score_matches) >= 2:
                 extracted_data['score2'] = score_matches[1].strip()
                 # Try to remove status if found
                 if extracted_data['status'] != "Status Not Found (Fallback)" and extracted_data['status'] in extracted_data['score2']:
                      extracted_data['score2'] = extracted_data['score2'].replace(extracted_data['status'], '').strip()

        print("-" * 20)
        print(f"Score 1 Extracted: {extracted_data['score1']}")
        print(f"Score 2 Extracted: {extracted_data['score2']}")
        print(f"Status Extracted: {extracted_data['status']}")
        print(f"Batsmen Extracted: {extracted_data['batsmen']}")
        print(f"Bowlers Extracted: {extracted_data['bowlers']}")
        print(f"Recent Overs Extracted: {extracted_data['recent_overs']}")
        print("-" * 20)

        # Final check if essential data is missing
        if extracted_data['status'].startswith("Status Not Found") and \
           (extracted_data['score1'] == 'N/A' or extracted_data['score1'].startswith("Score 1 Not Found")):
             return "Could not extract essential score/status information. Page structure might have changed, match not started, or URL is invalid."

        return extracted_data

    except requests.exceptions.Timeout:
        print("Error: Request timed out.")
        return "The request to Cricbuzz timed out. Please try again later."
    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL: {e}")
        return f"Error fetching URL: {e}"
    except Exception as e:
        print(f"An error occurred during parsing or processing: {e}")
        traceback.print_exc() # Print detailed traceback for debugging
        return f"An error occurred while parsing the page: {e}"


# --- Command-Line Interface Execution ---
if __name__ == '__main__':
    try:
        url_input = input("Enter Cricbuzz match URL: ")
        score_result = extract_score_from_url(url_input)

        print("\n" + "="*30)
        if isinstance(score_result, dict):
            print("      Match Score Details")
            print("="*30)
            print(f" Title:         {score_result.get('title', 'N/A')}")
            print(f" Score 1:       {score_result.get('score1', 'N/A')}")
            print(f" Score 2:       {score_result.get('score2', 'N/A')}")
            print(f" Status:        {score_result.get('status', 'N/A')}")
            print("-"*30)

            batsmen = score_result.get('batsmen', [])
            if batsmen and batsmen[0] != "N/A (Match Finished)":
                print(" Batsmen:")
                for batter in batsmen:
                    print(f"   - {batter}")
            else:
                 print(" Batsmen:       N/A")

            bowlers = score_result.get('bowlers', [])
            if bowlers and bowlers[0] != "N/A (Match Finished)":
                print("\n Bowlers:")
                for bowler in bowlers:
                    print(f"   - {bowler}")
            else:
                 print("\n Bowlers:       N/A")

            recent = score_result.get('recent_overs', 'N/A')
            if recent != "N/A (Match Finished)":
                 print(f"\n Recent Overs:  {recent}")
            else:
                 print(f"\n Recent Overs:  N/A")

            print("="*30)
            print("\nNote: Accuracy depends on Cricbuzz's current HTML structure and score text format.")

        else:
            # It's an error message string
            print(f" Error: {score_result}")
            print("="*30)

    except Exception as main_e:
         print(f"\nAn unexpected error occurred in the main execution block: {main_e}")
         traceback.print_exc()