# Project 189 — Weight Loss Dashboard

A personal weight tracking dashboard built with Flask and SQLite. Logs daily weight entries, visualizes progress on an interactive line chart, and tracks start, current, and goal weight milestones.

## Features

- **Weight plate cards** — displays start, current, and goal weights as styled plates; lost weight is calculated automatically. Click any plate to set or update its value with overwrite confirmation. Adding a current weight immediately refreshes the chart and table.
- **Interactive line chart** — powered by Chart.js with a floating HTML tooltip that follows the cursor. Interpolates estimated values between logged dates and marks them visually. Shows a warning icon when a selected date range exceeds available data history.
- **Date range controls** — 7D (default), 30D, 90D, 1Y, All, or a custom day count (capped at 1,095 days / 3 years). Custom range highlights the Custom button on change.
- **Data table** — scrollable log of entries for the selected range, showing weight in both lbs and kg. Inline editing with overwrite and delete confirmation modals. Dates with no entry display as empty rows; a "No Earlier Data Recorded" footer marks the bottom of available history.
- **Unit toggle** — switch between lbs and kg; all plates, chart, and table update instantly.
- **Fight Card modal** — record fighter profile info (name, sex, date of birth, height, activity level) with a themed date picker for DOB. Age is calculated automatically. Activity level (Sedentary / Light / Moderate / Active) is used for BMR calculations.
- **Insights modal** — 10 stats computed from full weight history: Predicted Goal Date (Mifflin-St. Jeor BMR simulation), Total Weigh-ins, Longest Streak, Current Streak, Current Trend, Weekly Loss Rate, Monthly Loss Rate, Lowest Weight, Largest Weekly Loss, and Avg Daily Fluctuation. Predicted Goal Date uses week-by-week metabolic adaptation; falls back to a 500 kcal/day deficit estimate when no trend is available.
- **Profile system** — three selectable profile pictures, each linked to its own custom pointer and edit cursor set. Selection is persisted server-side and restored on every page load.
- **Custom cursors** — profile-linked pointer and edit cursors rendered via transparent PNGs; swap automatically when the active profile changes.
- **Site-wide tooltips** — hover help on buttons and icons matches the chart tooltip style.
- **Persistent preferences** — unit choice, date range, view mode, fight card data, and profile selection are stored server-side in SQLite and hydrated into the page on load.
- **Persistent storage** — all weight entries and goal/start weights are stored in a local SQLite database (`weights.db`).

## Stack

| Layer | Technology |
|---|---|
| Backend | Python 3, Flask |
| Database | SQLite (via `sqlite3` stdlib) |
| Frontend | Vanilla JS, Chart.js 4.4.0 |
| Styling | Custom CSS |

## Setup

**1. Clone the repo and create a virtual environment**

```bash
git clone <repo-url>
cd project-189
python -m venv .venv
```

**2. Activate the virtual environment**

Windows:
```bash
.venv\Scripts\activate
```

macOS/Linux:
```bash
source .venv/bin/activate
```

**3. Install dependencies**

```bash
pip install flask
```

**4. Run the app**

```bash
python app.py
```

Open `http://127.0.0.1:5000` in your browser.

The SQLite database (`weights.db`) is created automatically on first run in the project root.

## Project Structure

```
project-189/
├── app.py                      # Flask app and REST API routes
├── weights.db                  # SQLite database (auto-created)
├── templates/
│   └── index.html              # Single-page UI
├── static/
│   ├── style.css               # All styles
│   ├── pointer.png             # Profile 1 pointer cursor
│   ├── editpointer.png         # Profile 1 edit cursor
│   ├── pointer2.png            # Profile 2 pointer cursor
│   ├── editpointer2.png        # Profile 2 edit cursor
│   ├── pointer3.png            # Profile 3 pointer cursor
│   ├── editpointer3.png        # Profile 3 edit cursor
│   ├── profilebutton.png       # Profile 1 avatar (default)
│   ├── profilebuttonsmile.png  # Profile 1 avatar (hover)
│   ├── profile2button.png      # Profile 2 avatar (default)
│   ├── profile2buttonsmile.png # Profile 2 avatar (hover)
│   ├── profile3button.png      # Profile 3 avatar (default)
│   ├── profile3buttonsmile.png # Profile 3 avatar (hover)
│   ├── dumbbellbutton.png      # Workouts button icon
│   ├── proteinshakebutton.png  # Nutrition button icon
│   ├── settingsbutton.png      # Settings button icon
│   ├── insightsbutton.png      # Insights button icon
│   ├── weightplate.png         # Weight plate graphic
│   └── miamibackground.png     # Background image
└── tests/
    ├── conftest.py
    ├── test_home.py
    ├── test_api_weight_post.py
    ├── test_api_weights_get.py
    ├── test_api_weight_delete.py
    ├── test_api_latest_weight.py
    ├── test_api_settings.py
    ├── test_api_preferences.py
    ├── test_api_weights_edge.py
    ├── test_business_logic.py
    └── test_db_init.py
```

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/weights?range=7d` | Fetch weight entries for a range (`7d`, `30d`, `90d`, `1y`, `all`, or `custom&days=N`) |
| `POST` | `/api/weight` | Log or overwrite a weight entry |
| `DELETE` | `/api/weight/<date>` | Delete an entry by date (`YYYY-MM-DD`) |
| `GET` | `/api/latest-weight` | Get the most recent weight and oldest entry date |
| `GET` | `/api/settings` | Get saved settings (start weight, goal weight) |
| `POST` | `/api/setting` | Save or overwrite a setting |
| `GET` | `/api/preferences` | Get all persisted user preferences |
| `POST` | `/api/preference` | Save or update a single preference key/value |

## Running Tests

```bash
python -m pytest tests/ -v
```

180 tests covering all API endpoints, business logic, date range boundaries, and UI structure.
