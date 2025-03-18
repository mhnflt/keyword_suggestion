# Google Suggestions Checker

A FastAPI-based web application that checks Google search suggestions for Persian words. The application allows users to input a word and check Google's suggestions by appending one or two Persian letters.

## Features

- Beautiful and responsive UI
- Real-time suggestion checking
- Support for Persian language
- Pause/Resume/Cancel functionality
- Progress tracking
- CSV download option
- Rate limiting protection

## Requirements

- Python 3.8+
- FastAPI
- Uvicorn
- Other dependencies listed in requirements.txt

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd google_suggestion_cursor
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Application

1. Start the server:
```bash
uvicorn main:app --reload
```

2. Open your browser and navigate to:
```
http://localhost:8000
```

## Usage

1. Enter a word in the text input field (e.g., "apple")
2. Select the number of letters to append (1 or 2)
3. Click "Start Search" to begin
4. Use the Pause/Resume/Cancel buttons to control the search
5. Results will appear in real-time
6. Download the results as CSV when complete

## Note

The application includes a 1-second delay between requests to avoid rate limiting from Google's API. 