# Football Match & Performance Analyser

An interactive web app for exploring football matches, comparing teams, building league tables and
visualising statistics. Built with **Python, Streamlit, Pandas and Plotly**.

> **Data notice:** `data/football_matches.csv` is a **synthetic sample dataset** (fictional teams, random
> scores, 168 matches). It is *not* real match data. Replace it with a verified dataset later (see
> "Using your own data").

## 1. The problem it solves
Match results sit in long tables that are hard to read. Fans, players and coaches want quick answers:
Who is top? How do two teams compare? Do teams score more at home? This app turns raw match rows into
tables, standings and charts without any spreadsheet work.

## 2. Objectives
- Show headline statistics and recent results on a dashboard.
- Let users search and filter matches (team, competition, date range, result).
- Compare any two teams using statistics calculated from the data.
- Build league standings automatically (win 3, draw 1, loss 0).
- Draw clear interactive charts and export results as CSV.
- Validate the data and fail with understandable messages instead of crashing.

## 3. Technologies and why
| Tool | Why it is used |
|---|---|
| Python | Simple, readable language for logic and data work |
| Streamlit | Builds a web interface from plain Python, no HTML/JavaScript needed |
| Pandas | Filtering, grouping and summing tables of data |
| Plotly | Interactive charts with hover tooltips |
| CSV | A plain-text file anyone can open and replace |
| GitHub + Streamlit Community Cloud | Free source hosting and a public link |

## 4. Project structure
```
football-performance-analyser/
├── app.py                      # Streamlit screens, sidebar and page navigation
├── requirements.txt            # Packages to install
├── README.md                   # This file
├── .gitignore                  # Files Git must ignore
├── .streamlit/config.toml      # Dark green theme
├── data/football_matches.csv   # Synthetic sample dataset (168 matches, 12 teams, 3 competitions)
├── src/
│   ├── __init__.py             # Makes src a Python package
│   ├── data_loader.py          # Read, validate and clean the CSV
│   ├── analytics.py            # Filters, team statistics, standings, summaries
│   └── charts.py               # Plotly chart builders
├── tests/
│   ├── test_analytics.py       # Hand-checked tests for the calculations
│   └── test_data_loader.py     # Tests for validation and error handling
├── scripts/generate_sample_data.py   # Recreates the sample CSV (seeded, so identical each time)
└── docs/
    ├── DEMO_AND_VIVA.md        # Demonstration script and viva questions
    └── SUBMISSION_CHECKLIST.md # Final checklist before you submit
```
(The file `src/__init__.py` is correct with double underscores. Writing `init.py` would not work as a package marker.)

## 5. How data flows
```
football_matches.csv
      │  data_loader.load_matches()   read CSV, check columns, remove bad rows, add "result"
      ▼
clean DataFrame (one row per match)   ── cached by Streamlit (st.cache_data)
      │  sidebar filters (competition, date range)  → analytics.filter_matches()
      ▼
filtered DataFrame
      │  analytics.* functions   team stats, standings, summaries
      ▼
charts.* functions → Plotly figures  ─┐
tables → st.dataframe                 ├─► shown by app.py and exportable with download buttons
metric cards → st.metric              ┘
```
`app.py` contains no football formulas, and `analytics.py` contains no Streamlit code. That separation
makes the calculations easy to test and easy to explain.

## 6. How each statistic is calculated
The CSV has one row per match. `analytics.build_team_rows()` creates **two rows per match** (one for the
home team, one for the away team) with `goals_for`, `goals_against` and an outcome. Then Pandas groups by team:

| Statistic | Calculation |
|---|---|
| Matches played | Number of rows for that team |
| Win / Draw / Loss | `goals_for` greater than / equal to / less than `goals_against` |
| Goals scored / conceded | Sum of `goals_for` / `goals_against` |
| Goal difference | Goals scored − goals conceded |
| Points | 3 × wins + 1 × draws (losses give 0) |
| Win percentage | wins ÷ matches played × 100 (0 if no matches) |
| Total teams | Unique names across home and away columns |
| Goals per match | Total goals ÷ number of matches (0 if no matches) |
| Most successful team | Team in position 1 of the standings (most points) |
| Monthly goals per match | Total goals in a month ÷ matches in that month |

**Standings order:** points, then goal difference, then goals scored (then team name only so ordering is stable).
Head-to-head and competition-specific tie-break rules are **not** implemented because the dataset does not
hold the data they need.

**Important:** if several competitions are selected, the table combines them. Choose one competition in the
sidebar (for example *Premier Division*) for a realistic league table.

## 7. Install and run
You need Python 3.10 or newer ([python.org](https://www.python.org/downloads/)).

**Windows (PowerShell):**
```
cd football-performance-analyser
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```
**macOS / Linux:**
```
cd football-performance-analyser
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```
Your browser opens at `http://localhost:8501`. Stop the app with `Ctrl + C`.

## 8. Testing
**Automated tests** (no extra packages needed):
```
python -m unittest discover -s tests -v
```
Expected result: `Ran 37 tests ... OK`. They cover win/draw/loss counts, goal difference, points, standings
order, team comparison, filters, monthly and home/away calculations, CSV table format, missing/invalid values,
empty datasets, a missing file and an empty file.

**Manual checklist** (run the app and tick each item):

| # | Test | Expected result |
|---|---|---|
| 1 | Fresh install: new venv, `pip install -r requirements.txt`, `streamlit run app.py` | App opens with no errors |
| 2 | Dashboard | 168 matches, 12 teams, 430 goals, 2.56 goals per match (for the sample data) |
| 3 | Sidebar: untick all competitions | Friendly "No matches" message, no crash |
| 4 | Sidebar: choose a narrow date range, then **Clear all filters** | Everything resets |
| 5 | Match Explorer: pick a team | Only matches with that team are listed |
| 6 | Match Explorer: Result = Draw | Every row shows equal scores |
| 7 | Team Comparison: choose two teams | Cards, table and charts update; same team twice shows a warning |
| 8 | League Standings (Premier Division only) | 12 teams, 22 matches each, sorted by points |
| 9 | Data and Downloads: download all three CSVs | Files open in Excel; rows match what is on screen after filtering |
| 10 | Rename the CSV temporarily | Red, readable "Could not find the data file" message |
| 11 | Delete a column header in the CSV | Message naming the missing column |
| 12 | Put `abc` as a score or a nonsense date | Data quality table shows the row was removed |
| 13 | Resize the browser to phone width | Layout stacks; charts remain readable |

**Honesty note:** the automated tests were run on the analytics and data-loading code. The Streamlit screens
(`app.py`, `charts.py`) must be checked by you with the manual checklist, and the online deployment must be
performed by you.

## 9. Deploy

### A. Upload to GitHub
1. Create a free account at <https://github.com>.
2. Click **New repository**. Name it `football-performance-analyser`, choose **Public**, do **not** add a README, click **Create repository**.
3. In a terminal inside the project folder:
```
git init
git add .
git commit -m "Football Match & Performance Analyser"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/football-performance-analyser.git
git push -u origin main
```
(Replace `YOUR-USERNAME`. GitHub may ask you to log in; use a browser sign-in or a personal access token as the password.)
4. Refresh the GitHub page and confirm you see `app.py`, `requirements.txt`, `data/`, `src/` and `.streamlit/`.

### B. Deploy on Streamlit Community Cloud
1. Go to <https://share.streamlit.io> and sign in with **Continue with GitHub**; authorise access.
2. Click **Create app** (or **New app**) → **Deploy a public app from GitHub**.
3. Repository: `YOUR-USERNAME/football-performance-analyser`. Branch: `main`. Main file path: `app.py`.
4. Optional: open **Advanced settings** and pick Python 3.11 or 3.12.
5. Click **Deploy**. The first build takes a few minutes while packages install.
6. Your **public URL** appears in the browser address bar and on your Streamlit dashboard. It looks like
   `https://your-app-name.streamlit.app`. Copy it, open it in a private window to confirm it works, and put it in your report.

Button names on the website may change slightly over time; follow the closest option.

### C. Troubleshooting
| Problem | Fix |
|---|---|
| `ModuleNotFoundError: plotly` (or pandas/streamlit) | The package is missing from `requirements.txt`. Add it, commit, push; the app rebuilds. Locally run `pip install -r requirements.txt` inside the activated venv |
| `ModuleNotFoundError: src` | `src/__init__.py` is missing or misnamed, or `src` was not pushed. Check the folder on GitHub |
| "Could not find the data file" | `data/football_matches.csv` is missing or in the wrong folder; the path is relative to `app.py` |
| `streamlit` is not recognised | The venv is not activated, or run `python -m streamlit run app.py` |
| Cloud app shows old code | Click **Reboot app** in the Streamlit Cloud menu, or push a new commit |
| Theme looks light on the cloud | `.streamlit/config.toml` was not pushed (check `.gitignore`) |
| Build fails on version errors | Open the build log (**Manage app**); loosen the version in `requirements.txt` (for example `pandas>=2.0`) |
| `git push` rejected | Run `git pull origin main --allow-unrelated-histories`, then push again |

## 10. Using your own data
Replace `data/football_matches.csv` with a file containing these columns:
`match_id, date, competition, home_team, away_team, home_score, away_score`.
Dates should look like `2025-01-31`, scores must be whole numbers, and `match_id` must be unique. Keep team names
spelled identically everywhere. Then change `DATA_LABEL` near the top of `app.py`. Rows that fail validation are
removed and listed on the **Data and Downloads** page. No other code changes are needed.

## 11. Limitations and future improvements
- Sample data is synthetic; real data must be supplied.
- Standings ignore head-to-head and competition-specific tie-breaks; cup matches are not modelled as knockout rounds.
- No live scores (they would need an API and, usually, a key).
- Ideas: upload your own CSV in the app, season selector, form guide (last five matches), team logos, goal-scorer data.

## 12. More documents
- Demonstration script and viva answers: `docs/DEMO_AND_VIVA.md`
- Final submission checklist: `docs/SUBMISSION_CHECKLIST.md`
