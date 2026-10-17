"""Plotly chart builders. Each function takes a table and returns a Plotly figure."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

GREEN = "#22C55E"
BLUE = "#38BDF8"
AMBER = "#F59E0B"
RED = "#EF4444"
TEXT = "#E8F1EA"
GRID = "#24382C"

METRIC_LABELS = {
    "wins": "Wins",
    "draws": "Draws",
    "losses": "Losses",
    "goals_for": "Goals scored",
    "goals_against": "Goals conceded",
    "goal_difference": "Goal difference",
    "points": "Points",
}


def _style(fig, title, x_title=None, y_title=None, height=420, show_legend=True):
    """Apply the shared dark football look to a figure."""
    fig.update_layout(
        title=dict(text=title, x=0),
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT),
        height=height,
        margin=dict(l=10, r=10, t=70, b=10),
        showlegend=show_legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_xaxes(title=x_title, gridcolor=GRID)
    fig.update_yaxes(title=y_title, gridcolor=GRID)
    return fig


def empty_figure(title: str, message: str = "No data to display") -> go.Figure:
    """A friendly blank chart used when there is nothing to plot."""
    fig = go.Figure()
    fig.add_annotation(text=message, showarrow=False, font=dict(size=16, color=TEXT))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return _style(fig, title, height=300, show_legend=False)


def _bar_height(rows: int) -> int:
    return max(320, 32 * rows + 130)


def goals_by_team_chart(stats: pd.DataFrame) -> go.Figure:
    title = "Goals scored by team"
    if stats.empty:
        return empty_figure(title)
    data = stats.sort_values("goals_for", ascending=True)
    fig = px.bar(
        data,
        x="goals_for",
        y="team",
        orientation="h",
        text="goals_for",
        color_discrete_sequence=[GREEN],
        hover_data={"played": True, "goals_against": True},
        labels={
            "goals_for": "Goals scored",
            "team": "Team",
            "played": "Matches played",
            "goals_against": "Goals conceded",
        },
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_yaxes(categoryorder="array", categoryarray=data["team"].tolist())
    return _style(fig, title, "Goals scored", "Team", _bar_height(len(data)), show_legend=False)


def results_by_team_chart(stats: pd.DataFrame) -> go.Figure:
    title = "Wins, draws and losses by team"
    if stats.empty:
        return empty_figure(title)
    data = stats.sort_values(["wins", "draws"], ascending=True)
    long = data.melt(
        id_vars="team",
        value_vars=["wins", "draws", "losses"],
        var_name="outcome",
        value_name="matches",
    )
    long["outcome"] = long["outcome"].map({"wins": "Wins", "draws": "Draws", "losses": "Losses"})
    fig = px.bar(
        long,
        x="matches",
        y="team",
        color="outcome",
        orientation="h",
        barmode="stack",
        color_discrete_map={"Wins": GREEN, "Draws": AMBER, "Losses": RED},
        category_orders={"outcome": ["Wins", "Draws", "Losses"], "team": data["team"].tolist()},
        labels={"matches": "Matches", "team": "Team", "outcome": "Result"},
    )
    return _style(fig, title, "Matches", "Team", _bar_height(len(data)))


def goals_over_time_chart(monthly: pd.DataFrame) -> go.Figure:
    title = "Average goals per match over time"
    if monthly.empty:
        return empty_figure(title)
    fig = px.line(
        monthly,
        x="month",
        y="goals_per_match",
        markers=True,
        color_discrete_sequence=[GREEN],
        hover_data={"matches": True, "total_goals": True},
        labels={
            "month": "Month",
            "goals_per_match": "Goals per match",
            "matches": "Matches",
            "total_goals": "Total goals",
        },
    )
    fig.update_yaxes(rangemode="tozero")
    return _style(fig, title, "Month", "Goals per match", 420, show_legend=False)


def points_chart(standings: pd.DataFrame) -> go.Figure:
    title = "League points by team"
    if standings.empty:
        return empty_figure(title)
    data = standings.sort_values("points", ascending=True)
    fig = px.bar(
        data,
        x="points",
        y="team",
        orientation="h",
        text="points",
        color_discrete_sequence=[GREEN],
        hover_data={"played": True, "goal_difference": True},
        labels={
            "points": "Points",
            "team": "Team",
            "played": "Matches played",
            "goal_difference": "Goal difference",
        },
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_yaxes(categoryorder="array", categoryarray=data["team"].tolist())
    return _style(fig, title, "Points", "Team", _bar_height(len(data)), show_legend=False)


def home_away_goals_chart(home_away: pd.DataFrame) -> go.Figure:
    title = "Home versus away goals by team"
    if home_away.empty:
        return empty_figure(title)
    data = home_away.copy()
    data["total"] = data["home_goals"] + data["away_goals"]
    data = data.sort_values("total", ascending=True)
    long = data.melt(
        id_vars="team",
        value_vars=["home_goals", "away_goals"],
        var_name="venue",
        value_name="goals",
    )
    long["venue"] = long["venue"].map({"home_goals": "Home goals", "away_goals": "Away goals"})
    fig = px.bar(
        long,
        x="goals",
        y="team",
        color="venue",
        orientation="h",
        barmode="group",
        color_discrete_map={"Home goals": GREEN, "Away goals": BLUE},
        category_orders={"team": data["team"].tolist()},
        labels={"goals": "Goals scored", "team": "Team", "venue": "Venue"},
    )
    return _style(fig, title, "Goals scored", "Team", max(360, 48 * len(data) + 130))


def comparison_chart(comparison: pd.DataFrame, metrics: list, title: str) -> go.Figure:
    """Grouped bars: one group per metric, one bar per team."""
    if comparison.empty:
        return empty_figure(title)
    long = comparison.melt(
        id_vars="team", value_vars=metrics, var_name="metric", value_name="value"
    )
    long["metric"] = long["metric"].map(METRIC_LABELS)
    fig = px.bar(
        long,
        x="metric",
        y="value",
        color="team",
        barmode="group",
        text="value",
        color_discrete_sequence=[GREEN, BLUE],
        labels={"metric": "Statistic", "value": "Value", "team": "Team"},
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    return _style(fig, title, "Statistic", "Value", 400)
