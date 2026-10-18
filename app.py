"""Football Match & Performance Analyser - Streamlit interface.

Run with:  streamlit run app.py

This file only builds the screen. The data loading is in src/data_loader.py,
the calculations are in src/analytics.py and the charts are in src/charts.py.
"""

from pathlib import Path

import pandas as pd
import streamlit as st
import os
from datetime import date
from src import analytics, api_client, charts, data_loader

# ---------------------------------------------------------------------------
# Settings you may want to change
# ---------------------------------------------------------------------------
DATA_PATH = Path(__file__).parent / "data" / "football_matches.csv"
# Shown in the sidebar. Change this text when you replace the sample file with real data.
DATA_LABEL = "Real match results"

PAGE_NAMES = [
    "Dashboard",
    "Match Explorer",
    "Team Comparison",
    "League Standings",
    "Data and Downloads",
]

# Keys of the filter widgets (used by the "Clear all filters" button).
FILTER_KEYS = ["f_comp", "f_dates", "f_search", "f_teams", "f_result"]

st.set_page_config(page_title="Football Match & Performance Analyser", page_icon="⚽", layout="wide")


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def inject_css() -> None:
    """A little extra styling on top of the dark theme in .streamlit/config.toml."""
    st.markdown(
        """
        <style>
        [data-testid="stMetric"] {
            background: #14211A;
            border: 1px solid #1F3A2B;
            border-left: 4px solid #22C55E;
            border-radius: 10px;
            padding: 12px 16px;
        }
        [data-testid="stMetricValue"] > div {
            white-space: normal;
            overflow-wrap: anywhere;
        }
        h1, h2, h3 { letter-spacing: 0.2px; }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner=False)
def load_data(path_text: str, file_modified_time: float):
    """Load the CSV once and remember it. The modified time makes the cache refresh
    automatically when you replace the CSV file."""
    return data_loader.load_matches(path_text)


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def show_empty_state() -> None:
    st.info(
        "No matches fit the current filters. Widen the date range, select more "
        "competitions, or press **Clear all filters** in the sidebar."
    )


def clear_filters() -> None:
    """Callback for the 'Clear all filters' buttons: forget the saved widget values."""
    for key in FILTER_KEYS:
        st.session_state.pop(key, None)


def resolve_dates(selected, min_date, max_date):
    """st.date_input can return one date, or 1-2 dates in a tuple while the user is picking."""
    if isinstance(selected, (tuple, list)):
        if len(selected) == 2:
            return selected[0], selected[1]
        if len(selected) == 1:
            return selected[0], max_date
        return min_date, max_date
    return selected, selected


def download_button(label: str, df: pd.DataFrame, file_name: str, key: str) -> None:
    st.download_button(
        label,
        data=to_csv_bytes(df),
        file_name=file_name,
        mime="text/csv",
        disabled=df.empty,
        key=key,
    )


# ---------------------------------------------------------------------------
# Sidebar: navigation + filters shared by every page
# ---------------------------------------------------------------------------
def sidebar(df: pd.DataFrame):
    st.sidebar.title("⚽ Match Analyser")
    page = st.sidebar.radio("Go to", PAGE_NAMES, key="page")
    st.sidebar.divider()

    st.sidebar.subheader("Filters")
    competitions = sorted(df["competition"].unique())
    selected_competitions = st.sidebar.multiselect(
        "Competition", competitions, default=competitions, key="f_comp"
    )
    min_date = df["date"].min().date()
    max_date = df["date"].max().date()
    selected_dates = st.sidebar.date_input(
        "Date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        key="f_dates",
    )
    start_date, end_date = resolve_dates(selected_dates, min_date, max_date)
    st.sidebar.button("Clear all filters", on_click=clear_filters, key="clear_sidebar")

    st.sidebar.divider()
    st.sidebar.caption(DATA_LABEL)

    filtered = analytics.filter_matches(
        df,
        competitions=selected_competitions,
        start_date=start_date,
        end_date=end_date,
    )
    return page, filtered


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------
def page_dashboard(filtered: pd.DataFrame, **_) -> None:
    st.title("Dashboard")
    st.caption("A quick overview of the matches selected in the sidebar.")
    if filtered.empty:
        show_empty_state()
        return

    summary = analytics.summarise_matches(filtered)
    stats = analytics.calculate_team_stats(filtered)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total matches", summary["total_matches"])
    c2.metric("Total teams", summary["total_teams"])
    c3.metric("Goals scored", summary["total_goals"])
    c4.metric("Goals per match", f"{summary['avg_goals']:.2f}")
    c5.metric(
        "Most successful team",
        summary["top_team"],
        delta=f"{summary['top_team_points']} points",
        delta_color="off",
    )

    st.subheader("Recent results")
    st.dataframe(
        analytics.matches_for_display(analytics.recent_results(filtered, 10)),
        hide_index=True,
    )

    st.subheader("Charts")
    tab_goals, tab_results, tab_trend, tab_venue = st.tabs(
        ["Goals by team", "Wins, draws, losses", "Goals over time", "Home vs away"]
    )
    with tab_goals:
        st.plotly_chart(charts.goals_by_team_chart(stats), theme=None)
    with tab_results:
        st.plotly_chart(charts.results_by_team_chart(stats), theme=None)
    with tab_trend:
        monthly = analytics.goals_per_match_by_month(filtered)
        st.plotly_chart(charts.goals_over_time_chart(monthly), theme=None)
    with tab_venue:
        st.plotly_chart(
            charts.home_away_goals_chart(analytics.home_away_goals(filtered)), theme=None
        )


def page_match_explorer(filtered: pd.DataFrame, **_) -> None:
    st.title("Match Explorer")
    st.caption("Search and filter matches. Competition and date range come from the sidebar.")
    if filtered.empty:
        show_empty_state()
        return

    col_search, col_teams, col_result = st.columns([2, 2, 1])
    search_text = col_search.text_input("Search team or competition", key="f_search")
    teams = col_teams.multiselect(
        "Team (home or away)", sorted(set(filtered["home_team"]) | set(filtered["away_team"])), key="f_teams"
    )
    result_choice = col_result.selectbox(
        "Result", ["All"] + data_loader.RESULT_OPTIONS, key="f_result"
    )
    st.button("Clear all filters", on_click=clear_filters, key="clear_explorer")

    shown = analytics.filter_matches(
        filtered,
        teams=teams,
        results=None if result_choice == "All" else [result_choice],
        search_text=search_text,
    )
    st.write(f"Showing **{len(shown)}** of **{len(filtered)}** matches")
    if shown.empty:
        show_empty_state()
        return

    table = analytics.matches_for_display(shown)
    st.dataframe(table, hide_index=True)
    download_button("Download these matches (CSV)", table, "match_results_explorer.csv", "dl_explorer")


def team_cards(row: pd.Series, stats_row: dict) -> None:
    """Metric cards for one team on the comparison page."""
    st.subheader(row["team"])
    a, b, c = st.columns(3)
    a.metric("Played", stats_row["played"])
    b.metric("Wins", stats_row["wins"])
    c.metric("Draws", stats_row["draws"])
    d, e, f = st.columns(3)
    d.metric("Losses", stats_row["losses"])
    e.metric("Goals scored", stats_row["goals_for"])
    f.metric("Goals conceded", stats_row["goals_against"])
    g, h, i = st.columns(3)
    g.metric("Goal difference", f"{stats_row['goal_difference']:+d}")
    h.metric("Points", stats_row["points"])
    i.metric("Win %", f"{stats_row['win_pct']:.1f}%")


def page_team_comparison(filtered: pd.DataFrame, **_) -> None:
    st.title("Team Comparison")
    st.caption("Pick two teams and compare their record in the selected matches.")
    if filtered.empty:
        show_empty_state()
        return

    teams = sorted(set(filtered["home_team"]) | set(filtered["away_team"]))
    if len(teams) < 2:
        st.info("At least two teams are needed for a comparison. Widen the sidebar filters.")
        return

    left, right = st.columns(2)
    team_a = left.selectbox("Team A", teams, index=0, key="team_a")
    team_b = right.selectbox("Team B", teams, index=1, key="team_b")
    if team_a == team_b:
        st.warning("Please choose two different teams.")
        return

    comparison = analytics.compare_teams(filtered, team_a, team_b)
    card_left, card_right = st.columns(2)
    for column, (_, row) in zip((card_left, card_right), comparison.iterrows()):
        with column:
            stats_row = {
                "played": int(row["played"]),
                "wins": int(row["wins"]),
                "draws": int(row["draws"]),
                "losses": int(row["losses"]),
                "goals_for": int(row["goals_for"]),
                "goals_against": int(row["goals_against"]),
                "goal_difference": int(row["goal_difference"]),
                "points": int(row["points"]),
                "win_pct": float(row["win_pct"]),
            }
            team_cards(row, stats_row)

    st.subheader("Side by side")
    st.dataframe(analytics.comparison_table(comparison), hide_index=True)

    st.subheader("Charts")
    chart_left, chart_right = st.columns(2)
    chart_left.plotly_chart(
        charts.comparison_chart(comparison, ["wins", "draws", "losses"], "Results comparison"),
        theme=None,
    )
    chart_right.plotly_chart(
        charts.comparison_chart(
            comparison,
            ["goals_for", "goals_against", "goal_difference", "points"],
            "Goals and points comparison",
        ),
        theme=None,
    )

    st.subheader("Head-to-head matches")
    direct = analytics.head_to_head(filtered, team_a, team_b)
    if direct.empty:
        st.info("These two teams have not played each other in the selected matches.")
    else:
        st.dataframe(analytics.matches_for_display(direct), hide_index=True)

    download_button(
        "Download this comparison (CSV)",
        analytics.stats_for_display(comparison),
        "team_comparison.csv",
        "dl_comparison",
    )


def page_standings(filtered: pd.DataFrame, **_) -> None:
    st.title("League Standings")
    st.caption("Calculated from the matches selected in the sidebar: win = 3, draw = 1, loss = 0.")
    if filtered.empty:
        show_empty_state()
        return

    if filtered["competition"].nunique() > 1:
        st.warning(
            "Several competitions are selected, so this table combines all of them. "
            "Choose a single competition in the sidebar to see a real league table."
        )

    standings = analytics.calculate_standings(filtered)
    st.dataframe(analytics.stats_for_display(standings), hide_index=True)
    with st.expander("How is the table sorted?"):
        st.write(
            "Teams are sorted by **points**, then **goal difference**, then **goals scored**. "
            "Head-to-head results and competition-specific tie-break rules are **not** "
            "implemented, because the dataset does not contain the information they need "
            "(for example fair-play points or separate group stages). Teams still tied after "
            "these three rules are listed alphabetically."
        )
    st.plotly_chart(charts.points_chart(standings), theme=None)
    download_button(
        "Download standings (CSV)",
        analytics.stats_for_display(standings),
        "league_standings.csv",
        "dl_standings_page",
    )


def page_data_and_downloads(filtered: pd.DataFrame, df: pd.DataFrame, report, **_) -> None:
    st.title("Data and Downloads")
    st.caption(DATA_LABEL)

    st.subheader("Data quality check")
    c1, c2, c3 = st.columns(3)
    c1.metric("Rows read from CSV", report.rows_read)
    c2.metric("Rows used", report.rows_kept)
    c3.metric("Rows removed", report.rows_removed)
    if report.problems:
        st.warning("Some rows were removed because they were invalid:")
        st.table(
            pd.DataFrame(
                {"Problem": list(report.problems), "Rows": list(report.problems.values())}
            )
        )
    else:
        st.success("Every row passed the checks.")

    st.subheader("Downloads")
    st.write(
        f"These files use the sidebar filters ({len(filtered)} of {len(df)} matches selected)."
    )
    matches_table = analytics.matches_for_display(filtered)
    team_stats = analytics.stats_for_display(analytics.calculate_team_stats(filtered))
    standings = analytics.stats_for_display(analytics.calculate_standings(filtered))
    d1, d2, d3 = st.columns(3)
    with d1:
        download_button("Filtered match results", matches_table, "match_results.csv", "dl_matches")
    with d2:
        download_button("Team performance statistics", team_stats, "team_statistics.csv", "dl_stats")
    with d3:
        download_button("League standings", standings, "league_standings.csv", "dl_standings")
    if filtered.empty:
        st.info("The downloads are disabled because no matches fit the current filters.")

    st.subheader("Dataset preview")
    st.dataframe(analytics.matches_for_display(df).head(50), hide_index=True)

    with st.expander("How to use your own dataset"):
        st.markdown(
            "Replace `data/football_matches.csv` with a file that has these columns: "
            f"`{', '.join(data_loader.REQUIRED_COLUMNS)}`. Dates must look like `2025-01-31`, "
            "scores must be whole numbers, and every `match_id` must be unique. "
            "Then update `DATA_LABEL` at the top of `app.py`."
        )


PAGES = {
    "Dashboard": page_dashboard,
    "Match Explorer": page_match_explorer,
    "Team Comparison": page_team_comparison,
    "League Standings": page_standings,
    "Data and Downloads": page_data_and_downloads,
}

def get_api_key():
    try:
        return st.secrets["FOOTBALL_DATA_API_KEY"]
    except Exception:
        return os.environ.get("FOOTBALL_DATA_API_KEY")


@st.cache_data(ttl=3600, show_spinner="Fetching matches from the API...")
def load_api_data(api_key, codes, season):
    """Cache API data for one hour."""
    return api_client.load_from_api(
        api_key, list(codes), season
    )

# ---------------------------------------------------------------------------
# Main program
# ---------------------------------------------------------------------------

def main() -> None:
    global DATA_LABEL

    inject_css()
    st.markdown("### ⚽ Football Match & Performance Analyser")

    source = st.sidebar.radio(
        "Data source",
        ["Sample CSV", "Live API"],
        key="source",
        on_change=clear_filters,
    )

    try:
        if source == "Live API":
            competition_options = {
                "Premier League": "PL",
                "La Liga": "PD",
                "Bundesliga": "BL1",
                "Serie A": "SA",
                "Ligue 1": "FL1",
            }

            selected_competitions = st.sidebar.multiselect(
                "Select Competitions",
                list(competition_options.keys()),
                default=["Premier League"],
                key="api_competitions",
            )

            codes = tuple(
                competition_options[name]
                for name in selected_competitions
            )

            from datetime import date

            current_year = date.today().year

            season = st.sidebar.number_input(
                "Season (start year)",
                min_value=2015,
                max_value=current_year,
                value=current_year,
                key="api_season",
            )

            update_clicked = st.sidebar.button(
                "🔄 Update Data",
                key="update_api_data",
            )

            if not codes:
                st.info("Choose at least one competition in the sidebar.")
                st.stop()

            selection = (codes, int(season))

            if "api_data_loaded" not in st.session_state:
                st.session_state["api_data_loaded"] = False

            selection_changed = (
                st.session_state.get("api_last_selection") != selection
            )

            # Fetch initially, when the selection changes,
            # or when Update Data is clicked.
            if (
                not st.session_state["api_data_loaded"]
                or selection_changed
                or update_clicked
            ):
                with st.spinner("Fetching football data..."):
                    if update_clicked:
                        load_api_data.clear()

                    df, report = load_api_data(
                        get_api_key(), codes, int(season)
                    )

                st.session_state["api_data_loaded"] = True
                st.session_state["api_last_selection"] = selection

                st.sidebar.success("Football data updated!")

            else:
                df, report = load_api_data(
                    get_api_key(), codes, int(season)
                )

            DATA_LABEL = "Real data from football-data.org"

        else:
            modified = (
                DATA_PATH.stat().st_mtime
                if DATA_PATH.exists()
                else 0.0
            )
            df, report = load_data(str(DATA_PATH), modified)

    except (data_loader.DataValidationError, api_client.ApiError) as error:
        st.error(f"Could not load the data. {error}")
        st.stop()

    if df.empty:
        st.error(
            "The dataset has no usable matches. "
            f"{report.rows_read} row(s) were read and "
            f"{report.rows_removed} were removed. "
            "Check the dates, team names and scores in your data."
        )

        for reason, count in report.problems.items():
            st.write(f"- {reason}: {count} row(s)")

        st.stop()

    page, filtered = sidebar(df)
    PAGES[page](filtered=filtered, df=df, report=report)

main()
