# Project 189 — Weight Loss Dashboard

A personal weight tracking dashboard built with Flask and SQLite. A gamified Home screen (health bar HUD, weight-plate stat cards) links out to a dedicated Weigh-ins page for charting/logging weight and a Workouts page for logging exercise — all sharing one Jinja2 header/footer shell.

## Pages

- **Home** (`/`) — health bar HUD, four weight-plate cards (Starting / Current / Lost / Goal), and quick stats (7-day trend, weekly kcal burn, active streak).
- **Weigh-ins** (`/weights`) — daily and weekly weight charts, the data table, and weigh-in logging.
- **Workouts** (`/workouts`) — date-grouped workout log with staging/edit workflow.

All three share a fixed header (page nav + per-page stats) and footer (context-aware "+" quick-add button, profile menu button) defined once in `templates/base.html` and extended by each page template.

## Features

### Home
- **Health bar HUD** — fixed pixel-art health bar that fills as the user progresses from start weight toward goal weight. Fighter name (set in Fight Card) displays above it in Mortal Kombat–style gold text; hovering shows remaining weight to goal.
- **Weight plate cards** — Starting, Current, Lost, and Goal weight shown as styled plates; lost weight is calculated automatically. Click any plate to set or update its value with overwrite confirmation.
- **Quick Add** — footer "+" button opens a modal to jump straight to logging a weigh-in or a workout.
- **Header stats** — 7-day weight trend, weekly kcal burn, and active streak (union of weigh-in days and workout days).

### Weigh-ins
- **Interactive line chart** — powered by Chart.js with a floating HTML tooltip that follows the cursor. Interpolates estimated values between logged dates and marks them visually. Shows a warning icon when a selected date range exceeds available data history.
- **Weekly Summary chart** — second chart screen accessible via a `›` caret to the right of the daily chart; slides between views with a CSS transition. Groups entries into rolling 7-day windows, averages per window, and displays as a bar chart with optional goal and trend overlays. Default landing chart (Over Time or Weekly) is configurable in Settings.
- **Unified date range picker** — shared range control (7D, 30D, 90D, 1Y, All, or a custom range via a calendar picker) used consistently across the daily chart, weekly chart, and table.
- **Goal weight line** — optional teal dashed line on the chart with a y-axis GOAL label; toggled in Settings (default off).
- **7-day moving average line** — optional amber line on the chart with a y-axis 7D AVG label; toggled in Settings (default off).
- **Header stats** — rolling 7-day weight change (signed, e.g. `-2.4 lbs`, not a log count), 7-day average, and current day streak.
- **Data table** — scrollable log of entries for the selected range, showing weight in both lbs and kg. Inline editing with overwrite and delete confirmation modals. Dates with no entry display as empty rows; a "No Earlier Data Recorded" footer marks the bottom of available history. Each row has a note button to add, edit, or delete a text note; note-only rows (no weight logged) appear with a blank weight cell. The delete confirmation modal has independent checkboxes to remove the weight value, the note, or both. The note editor popover uses a themed custom scrollbar and locks table scrolling while open; its position is clamped within the viewport on window resize.
- **Responsive tables** — both the daily and weekly summary tables adapt cleanly across screen widths: the secondary column (kg) collapses at ≤ 800px, date labels switch from full to short at ≤ 560px, action buttons scale down at ≤ 720px, and column widths stay pinned across all sizes.
- **Unit toggle** — switch between lbs and kg; all plates, chart, and table update instantly.

### Workouts
- **Date-grouped log** — all logged workouts grouped by date in a scrollable table; each row shows a MET-based tier badge, duration, and kcal. Day headers show total duration/kcal for the day and collapse/expand via a pink chevron.
- **Staging workflow** — the Log Workout modal lets you add multiple activities before committing. The duration stepper and "+ Add Activity" button are grayed until a type is selected; the selected-activity chip swaps the search input in-place so the modal never resizes; the logged-activities area is a fixed-height scrollable region with a custom scrollbar.
- **Day-level notes** — one note per calendar day, displayed as an italic accent below each date group.
- **Delete confirmation** — removing an activity from the modal stages the deletion; on Save, a checkbox confirmation modal lists each pending deletion (uncheck to rescue it). Deleting a logged row directly from the table uses a simple confirm.
- **Discard-changes guard** — cancelling with unsaved staged activities, pending deletes, or an edited note triggers a warning.
- **Date range filter** — footer filter button opens a slide-up menu with preset ranges and a Custom option (two themed date pickers, From/To).
- **Header stats** — workouts logged this week, total kcal burned, and current day streak.

### Shared / site-wide
- **Menu modal** — footer profile button opens a menu with Insights, Profile, and Settings.
- **Settings** — collapsible accordion sections: Default Formats (weight/height/date display), Chart Landing (default chart + view), Daily Summary (range, moving avg, trend, goal line, legend), Weekly Summary (range, min/max range, trend, goal line, table expanded, week mode, legend), Workouts (range), and HUD (health bar, fighter name).
- **Fight Card modal** — record fighter profile info (name, sex, date of birth, height, activity level) with a themed date picker for DOB. Age is calculated automatically. Activity level is used for BMR calculations. Includes a **Goal Mode** toggle: **Lean Machine** (lose weight) or **Muscle Monster** (gain weight) — dynamically updates the lost/gained plate label, health bar fill direction, and goal weight validation.
- **Insights modal** — 10 stats computed from full weight history: Predicted Goal Date (Mifflin-St. Jeor BMR simulation), Total Weigh-ins, Longest Streak, Current Streak, Current Trend, Weekly Loss Rate, Monthly Loss Rate, Lowest Weight, Largest Weekly Loss, and Avg Daily Fluctuation.
- **Profile system** — four selectable profile pictures, each linked to its own custom cursor. Selection is persisted server-side and restored on every page load.
- **Custom cursor** — profile-linked pointer rendered as a DOM element positioned via `transform: translate3d()` (GPU-composited, never native `cursor: url()`, which Chromium/Edge silently suppress near viewport edges).
- **Site-wide tooltips** — hover help on buttons and icons, consistent styling across pages.
- **Persistent preferences & storage** — unit choice, date ranges, default views, chart line toggles, fight card data, and profile selection are stored server-side in SQLite and hydrated into every page on load.

## Stack

| Layer | Technology |
|---|---|
| Backend | Python 3, Flask 3.1 |
| Database | SQLite (via `sqlite3` stdlib) |
| Templates | Jinja2 template inheritance (`base.html` + per-page blocks) |
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
pip install -r requirements.txt
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
├── requirements.txt            # Runtime + test dependencies
├── weights.db                  # SQLite database (auto-created)
├── templates/
│   ├── base.html                # Shared header/footer shell, menu/settings/fight-card/insights modals, cursor + tooltip JS
│   ├── index.html                # Home dashboard (health bar, weight plates, Quick Add)
│   ├── weights.html              # Weigh-ins page (charts + table)
│   └── workouts.html             # Workout tracking page
├── static/
│   ├── style.css                # All styles
│   ├── pointer.png / pointer2-4.png       # Profile-linked custom cursors
│   ├── profilebutton.png / profile2-4button.png            # Profile avatars (default)
│   ├── profilebuttonsmile.png / profile2-4buttonsmile.png  # Profile avatars (hover)
│   ├── insightsbutton.png      # Home nav icon
│   ├── weightbutton.png        # Weigh-ins nav icon
│   ├── dumbbellbutton.png      # Workouts nav icon
│   ├── proteinshakebutton.png  # Nutrition nav icon (coming soon)
│   ├── healthbar.png           # Health bar HUD graphic
│   ├── weightplate.png         # Weight plate card graphic
│   ├── mainbackground.png      # Home page background
│   ├── miamibackground.png     # Parallax palm-tree frame overlay
│   └── workoutbackground4.png / workoutbackground7.png     # Weigh-ins / Workouts page backgrounds
└── tests/
    ├── conftest.py
    ├── test_home.py
    ├── test_weights_page.py
    ├── test_workouts_page.py
    ├── test_api_weight_post.py
    ├── test_api_weights_get.py
    ├── test_api_weights_edge.py
    ├── test_api_weight_delete.py
    ├── test_api_weight_notes.py
    ├── test_api_weight_stats.py
    ├── test_api_latest_weight.py
    ├── test_api_settings.py
    ├── test_api_preferences.py
    ├── test_api_workouts.py
    ├── test_business_logic.py
    └── test_db_init.py
```

A few other `static/` PNGs (`editpointer*.png`, `settingsbutton.png`, `homebutton.png`, `leanmachine.png`, `musclemonster.png`, various `workoutbackgroundtest*.png`) are earlier iterations no longer referenced by any template — left in place but not wired up.

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Home dashboard |
| `GET` | `/weights` | Weigh-ins page (charts + table) |
| `GET` | `/workouts` | Workout tracking page |
| `GET` | `/api/weights?range=7d` | Fetch weight entries for a range (`7d`, `30d`, `90d`, `1y`, `all`, or `custom&days=N`) |
| `POST` | `/api/weight` | Log or overwrite a weight entry |
| `DELETE` | `/api/weight/<date>` | Delete an entire entry (weight + note) by date |
| `DELETE` | `/api/weight/<date>/weight` | Null out only the weight for a date, keeping its note |
| `PATCH` | `/api/weight/<date>/note` | Save or create a note for a date (creates note-only row if no entry exists) |
| `GET` | `/api/weight/stats` | Rolling 7-day weight change, 7-day average, and current day streak (Weigh-ins header stats) |
| `GET` | `/api/latest-weight` | Get the most recent weight and oldest entry date |
| `GET` | `/api/settings` | Get saved settings (start weight, goal weight) |
| `POST` | `/api/setting` | Save or overwrite a setting |
| `GET` | `/api/preferences` | Get all persisted user preferences |
| `POST` | `/api/preference` | Save or update a single preference key/value |
| `GET` | `/api/home-stats` | Active streak, weekly kcal burn, and 7-day weight trend (Home header stats) |
| `GET` | `/api/workouts` | Get all logged workouts, ordered newest first (optional `?date=YYYY-MM-DD` filter) |
| `POST` | `/api/workout` | Log a workout (date, type, duration_min, kcal, note) |
| `DELETE` | `/api/workout/<id>` | Delete a workout by ID |
| `GET` | `/api/workout-day-note?date=YYYY-MM-DD` | Get the day note for a date (returns `{"note": ""}` if none) |
| `POST` | `/api/workout-day-note` | Upsert the day note for a date |
| `GET` | `/api/workout-day-notes` | Get all non-empty day notes as a `{date: note}` map |

## Running Tests

```bash
python -m pytest tests/ -v
```

367 tests covering all API endpoints, business logic, date range boundaries, and page structure across Home, Weigh-ins, and Workouts.
