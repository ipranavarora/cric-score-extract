# Cricbuzz Live Score Extractor

A Python script that extracts live cricket match scores and details from Cricbuzz match URLs. The script can handle both live and finished matches, providing detailed information including scores, batsmen stats, bowler figures, and recent overs.

## Features

- Extract match title and status
- Get current and previous innings scores
- Show current batsmen at crease (for live matches)
- Display current bowler statistics (for live matches)
- View recent overs information (for live matches)
- Handles both live and completed matches

## Setup Instructions

1. Create a virtual environment:
```bash
python -m venv venv
```
2. Activate the virtual environment:
```bash
source venv/bin/activate
```
3. Install the required packages:
```bash
pip install -r requirements.txt
```
4. Run the script:
```bash
python app.py
```
5. Enter the Cricbuzz match URL when prompted.
