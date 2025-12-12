# pyright: reportAny=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false
# pyright: reportAttributeAccessIssue=false, reportUnusedVariable=false
# pyright: reportUnusedParameter=false, reportArgumentType=false
# pyright: reportUnusedCallResult=false, reportImplicitStringConcatenation=false
# pyright: reportImportCycles=false
# ruff: noqa: ARG001, B007, E501, ICN001, N806, PLR0915, PLR2004, RUF059, TC003
"""Visualization generation for usage analysis.

This module provides:
- Static charts with matplotlib/seaborn (PNG/SVG)
- Interactive Bokeh dashboard (HTML)
"""

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._usage import UsageAnalysis

# Model display name mappings (duplicated here to avoid circular import)
MODEL_DISPLAY_NAMES: dict[str, str] = {
    "claude-opus-4-5-20251101": "Opus 4.5",
    "claude-sonnet-4-20250514": "Sonnet 4",
    "claude-haiku-4-5-20251001": "Haiku 4.5",
    "claude-3-5-sonnet-20241022": "Sonnet 3.5",
    "claude-3-5-haiku-20241022": "Haiku 3.5",
}


def generate_static_charts(
    analysis: UsageAnalysis,
    output_dir: Path,
    *,
    chart_format: str = "png",
) -> None:
    """Generate static charts using matplotlib/seaborn.

    Args:
        analysis: Usage analysis results.
        output_dir: Directory to write chart files.
        chart_format: Image format (png or svg).

    Raises:
        ImportError: If matplotlib or seaborn is not available.
    """
    import matplotlib

    matplotlib.use("Agg")  # Non-interactive backend
    import matplotlib.pyplot as plt
    import seaborn as sns

    # Set style
    sns.set_theme(style="whitegrid", palette="deep")
    plt.rcParams["figure.figsize"] = (10, 6)
    plt.rcParams["figure.dpi"] = 150

    # Generate each chart type
    _generate_daily_usage_chart(analysis, output_dir, chart_format, plt, sns)
    _generate_model_distribution_chart(analysis, output_dir, chart_format, plt)
    _generate_tool_usage_chart(analysis, output_dir, chart_format, plt, sns)
    _generate_cache_efficiency_chart(analysis, output_dir, chart_format, plt, sns)
    _generate_hourly_distribution_chart(analysis, output_dir, chart_format, plt, sns)
    _generate_weekly_trends_chart(analysis, output_dir, chart_format, plt, sns)


def _generate_daily_usage_chart(
    analysis: UsageAnalysis,
    output_dir: Path,
    chart_format: str,
    plt: object,
    sns: object,
) -> None:
    """Generate daily token usage line chart (stacked input/output)."""
    if not analysis.daily:
        return

    # Sort by date (oldest first for plotting)
    sorted_daily = sorted(analysis.daily, key=lambda d: d.date)

    dates = [d.date for d in sorted_daily]
    input_tokens = [d.input_tokens / 1000 for d in sorted_daily]  # Convert to K
    output_tokens = [d.output_tokens / 1000 for d in sorted_daily]

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.stackplot(
        dates,
        input_tokens,
        output_tokens,
        labels=["Input Tokens (K)", "Output Tokens (K)"],
        colors=["#3498db", "#e74c3c"],
        alpha=0.8,
    )

    ax.set_xlabel("Date")
    ax.set_ylabel("Tokens (thousands)")
    ax.set_title("Daily Token Usage")
    ax.legend(loc="upper left")

    # Rotate x-axis labels for readability
    plt.xticks(rotation=45, ha="right")

    # Show every Nth label if too many dates
    if len(dates) > 14:
        step = len(dates) // 10
        ax.set_xticks(dates[::step])

    plt.tight_layout()
    plt.savefig(output_dir / f"daily_usage.{chart_format}")
    plt.close()


def _generate_model_distribution_chart(
    analysis: UsageAnalysis,
    output_dir: Path,
    chart_format: str,
    plt: object,
) -> None:
    """Generate model distribution pie/donut chart."""
    if not analysis.model_breakdown:
        return

    # Get top models (limit to 6 for readability)
    models = list(analysis.model_breakdown.items())[:6]
    if len(analysis.model_breakdown) > 6:
        other_tokens = sum(v for _, v in list(analysis.model_breakdown.items())[6:])
        models.append(("Other", other_tokens))

    labels = [MODEL_DISPLAY_NAMES.get(m, m) for m, _ in models]
    values = [v for _, v in models]

    # Colors
    colors = [
        "#3498db",
        "#e74c3c",
        "#2ecc71",
        "#f39c12",
        "#9b59b6",
        "#1abc9c",
        "#95a5a6",
    ]

    fig, ax = plt.subplots(figsize=(10, 8))

    # Create donut chart
    wedges, texts, autotexts = ax.pie(
        values,
        labels=labels,
        autopct="%1.1f%%",
        colors=colors[: len(values)],
        pctdistance=0.75,
        wedgeprops={"width": 0.5, "edgecolor": "white"},
    )

    # Style the percentage text
    for autotext in autotexts:
        autotext.set_fontsize(10)
        autotext.set_fontweight("bold")

    ax.set_title("Token Usage by Model")

    plt.tight_layout()
    plt.savefig(output_dir / f"model_distribution.{chart_format}")
    plt.close()


def _generate_tool_usage_chart(
    analysis: UsageAnalysis,
    output_dir: Path,
    chart_format: str,
    plt: object,
    sns: object,
) -> None:
    """Generate tool usage horizontal bar chart."""
    if not analysis.tool_breakdown:
        return

    # Get top 15 tools - use output_tokens for sorting (already sorted by tokens)
    tools = list(analysis.tool_breakdown.items())[:15]
    tool_names = [t for t, _ in tools]
    tokens = [stats.output_tokens for _, stats in tools]
    invocations = [stats.invocations for _, stats in tools]

    fig, ax = plt.subplots(figsize=(10, 8))

    # Create horizontal bar chart (reversed so highest is at top)
    colors = sns.color_palette("viridis", len(tool_names))
    ax.barh(
        tool_names[::-1],
        tokens[::-1],
        color=colors[::-1],
        edgecolor="white",
    )

    ax.set_xlabel("Output Tokens")
    ax.set_title("Tool Usage by Token Consumption (Top 15)")

    # Add value labels on bars showing both tokens and invocations
    max_tokens = max(tokens) if tokens else 1
    for i, (name, tok, inv) in enumerate(
        zip(tool_names[::-1], tokens[::-1], invocations[::-1], strict=True)
    ):
        label = f"{tok:,} ({inv:,} calls)"
        ax.text(tok + max_tokens * 0.01, i, label, va="center", fontsize=9)

    plt.tight_layout()
    plt.savefig(output_dir / f"tool_usage.{chart_format}")
    plt.close()


def _generate_cache_efficiency_chart(
    analysis: UsageAnalysis,
    output_dir: Path,
    chart_format: str,
    plt: object,
    sns: object,
) -> None:
    """Generate cache efficiency bar chart by week."""
    if not analysis.weekly:
        return

    # Sort by week (oldest first)
    sorted_weekly = sorted(analysis.weekly, key=lambda w: w.week_start)[
        -8:
    ]  # Last 8 weeks

    weeks = [f"{w.week_start}" for w in sorted_weekly]
    efficiencies = [w.cache_efficiency * 100 for w in sorted_weekly]

    fig, ax = plt.subplots(figsize=(10, 6))

    # Color bars by efficiency level
    colors = [
        "#e74c3c" if e < 25 else "#f39c12" if e < 50 else "#2ecc71"
        for e in efficiencies
    ]

    bars = ax.bar(weeks, efficiencies, color=colors, edgecolor="white")

    ax.set_xlabel("Week Starting")
    ax.set_ylabel("Cache Efficiency (%)")
    ax.set_title("Weekly Cache Efficiency")
    ax.set_ylim(0, 100)

    # Add threshold lines
    ax.axhline(y=50, color="#2ecc71", linestyle="--", alpha=0.5, label="Good (50%)")
    ax.axhline(y=25, color="#f39c12", linestyle="--", alpha=0.5, label="Fair (25%)")

    # Rotate x-axis labels
    plt.xticks(rotation=45, ha="right")

    # Add value labels on bars
    for bar, eff in zip(bars, efficiencies, strict=True):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 1,
            f"{eff:.1f}%",
            ha="center",
            va="bottom",
            fontsize=9,
        )

    ax.legend(loc="upper right")

    plt.tight_layout()
    plt.savefig(output_dir / f"cache_efficiency.{chart_format}")
    plt.close()


def _generate_hourly_distribution_chart(
    analysis: UsageAnalysis,
    output_dir: Path,
    chart_format: str,
    plt: object,
    sns: object,
) -> None:
    """Generate time of day heatmap/bar chart."""
    if not analysis.hourly_distribution:
        return

    # Ensure all hours are present (0-23)
    hours = list(range(24))
    tokens = [
        analysis.hourly_distribution.get(h, 0) / 1000 for h in hours
    ]  # Convert to K

    fig, ax = plt.subplots(figsize=(12, 5))

    # Create bar chart with color gradient
    colors = sns.color_palette("YlOrRd", len(hours))
    max_tokens = max(tokens) if tokens else 1
    color_indices = [
        int((t / max_tokens) * (len(colors) - 1)) if max_tokens > 0 else 0
        for t in tokens
    ]
    bar_colors = [colors[i] for i in color_indices]

    ax.bar(hours, tokens, color=bar_colors, edgecolor="white", width=0.8)

    ax.set_xlabel("Hour of Day (UTC)")
    ax.set_ylabel("Tokens (thousands)")
    ax.set_title("Token Usage by Hour of Day")
    ax.set_xticks(hours)
    ax.set_xticklabels([f"{h:02d}" for h in hours])

    plt.tight_layout()
    plt.savefig(output_dir / f"hourly_distribution.{chart_format}")
    plt.close()


def _generate_weekly_trends_chart(
    analysis: UsageAnalysis,
    output_dir: Path,
    chart_format: str,
    plt: object,
    sns: object,
) -> None:
    """Generate weekly trend comparison chart."""
    if not analysis.weekly:
        return

    # Sort by week (oldest first)
    sorted_weekly = sorted(analysis.weekly, key=lambda w: w.week_start)

    weeks = [w.week_start for w in sorted_weekly]
    total_tokens = [w.total_tokens / 1000 for w in sorted_weekly]  # Convert to K
    sessions = [w.session_count for w in sorted_weekly]

    fig, ax1 = plt.subplots(figsize=(12, 6))

    # Primary axis: tokens
    color1 = "#3498db"
    ax1.set_xlabel("Week Starting")
    ax1.set_ylabel("Tokens (thousands)", color=color1)
    line1 = ax1.plot(
        weeks, total_tokens, color=color1, marker="o", linewidth=2, label="Total Tokens"
    )
    ax1.tick_params(axis="y", labelcolor=color1)
    ax1.fill_between(weeks, total_tokens, alpha=0.2, color=color1)

    # Secondary axis: sessions
    ax2 = ax1.twinx()
    color2 = "#e74c3c"
    ax2.set_ylabel("Sessions", color=color2)
    line2 = ax2.plot(
        weeks,
        sessions,
        color=color2,
        marker="s",
        linewidth=2,
        linestyle="--",
        label="Sessions",
    )
    ax2.tick_params(axis="y", labelcolor=color2)

    # Combine legends
    lines = line1 + line2
    labels = [line.get_label() for line in lines]
    ax1.legend(lines, labels, loc="upper left")

    ax1.set_title("Weekly Usage Trends")

    # Rotate x-axis labels
    plt.xticks(rotation=45, ha="right")

    plt.tight_layout()
    plt.savefig(output_dir / f"weekly_trends.{chart_format}")
    plt.close()


def _format_tokens_display(tokens: int) -> str:
    """Format token count for display in dashboard."""
    if tokens >= 1_000_000:
        return f"{tokens / 1_000_000:.1f}M"
    if tokens >= 1_000:
        return f"{tokens / 1_000:.1f}K"
    return str(tokens)


def generate_bokeh_dashboard(
    analysis: UsageAnalysis,
    output_path: Path,
) -> None:
    """Generate interactive Bokeh dashboard.

    Args:
        analysis: Usage analysis results.
        output_path: Path to write the HTML file.

    Raises:
        ImportError: If bokeh is not available.
    """
    from bokeh.embed import file_html
    from bokeh.layouts import column, row
    from bokeh.models import (
        ColumnDataSource,
        Div,
        HoverTool,
        NumeralTickFormatter,
        Spacer,
    )
    from bokeh.palettes import Category10, Viridis256
    from bokeh.plotting import figure
    from bokeh.resources import CDN

    # Styles for consistent appearance
    HEADER_STYLE = """
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        color: #1a1a2e;
    """
    SECTION_STYLE = """
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        color: #333;
        margin-top: 20px;
        margin-bottom: 10px;
        padding-bottom: 10px;
        border-bottom: 2px solid #e0e0e0;
    """
    DESCRIPTION_STYLE = """
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        color: #666;
        font-size: 13px;
        margin-bottom: 10px;
        line-height: 1.4;
    """
    STAT_CARD_STYLE = """
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        min-width: 150px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    """
    STAT_CARD_SECONDARY_STYLE = """
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        color: white;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        min-width: 150px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    """
    STAT_CARD_TERTIARY_STYLE = """
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        min-width: 150px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    """

    # Build layout components
    layout_items = []

    # Header section
    header_html = f"""
    <div style="{HEADER_STYLE}">
        <h1 style="margin: 0 0 10px 0; font-size: 28px; font-weight: 600;">
            Claude Code Usage Dashboard
        </h1>
        <p style="margin: 0; color: #666; font-size: 14px;">
            Interactive analysis of your Claude Code token usage and patterns
        </p>
    </div>
    """
    layout_items.append(Div(text=header_html, sizing_mode="stretch_width"))
    layout_items.append(Spacer(height=20))

    # Time period
    time_period = ""
    if analysis.time_range_start and analysis.time_range_end:
        start_date = analysis.time_range_start[:10]
        end_date = analysis.time_range_end[:10]
        time_period = f"{start_date} to {end_date}"

    # Summary statistics cards
    total_tokens_display = _format_tokens_display(analysis.total_tokens)
    input_tokens_display = _format_tokens_display(analysis.total_input_tokens)
    output_tokens_display = _format_tokens_display(analysis.total_output_tokens)
    cache_efficiency_pct = analysis.overall_cache_efficiency * 100
    session_count = len(analysis.sessions)

    stats_html = f"""
    <div style="display: flex; gap: 15px; flex-wrap: wrap; margin-bottom: 10px;">
        <div style="{STAT_CARD_STYLE}">
            <div style="font-size: 28px; font-weight: bold;">{total_tokens_display}</div>
            <div style="font-size: 12px; opacity: 0.9; margin-top: 5px;">Total Tokens</div>
            <div style="font-size: 11px; opacity: 0.7; margin-top: 3px;">
                In: {input_tokens_display} / Out: {output_tokens_display}
            </div>
        </div>
        <div style="{STAT_CARD_SECONDARY_STYLE}">
            <div style="font-size: 28px; font-weight: bold;">{session_count}</div>
            <div style="font-size: 12px; opacity: 0.9; margin-top: 5px;">Sessions</div>
            <div style="font-size: 11px; opacity: 0.7; margin-top: 3px;">
                {len(analysis.daily)} days active
            </div>
        </div>
        <div style="{STAT_CARD_TERTIARY_STYLE}">
            <div style="font-size: 28px; font-weight: bold;">{cache_efficiency_pct:.1f}%</div>
            <div style="font-size: 12px; opacity: 0.9; margin-top: 5px;">Cache Efficiency</div>
            <div style="font-size: 11px; opacity: 0.7; margin-top: 3px;">
                {"Excellent" if cache_efficiency_pct >= 50 else "Good" if cache_efficiency_pct >= 25 else "Low"}
            </div>
        </div>
    </div>
    """
    if time_period:
        stats_html += f"""
        <div style="font-size: 13px; color: #888; margin-top: 5px;">
            Analysis period: {time_period}
        </div>
        """
    layout_items.append(Div(text=stats_html, sizing_mode="stretch_width"))
    layout_items.append(Spacer(height=30))

    # Section: Token Usage Over Time
    section_usage_html = f"""
    <div style="{SECTION_STYLE}">
        <h2 style="margin: 0; font-size: 18px; font-weight: 600;">Token Usage Over Time</h2>
    </div>
    """
    layout_items.append(Div(text=section_usage_html, sizing_mode="stretch_width"))

    # 1. Daily token usage timeline
    if analysis.daily:
        daily_desc_html = f"""
        <div style="{DESCRIPTION_STYLE}">
            Daily breakdown of input and output tokens. Hover over bars to see detailed
            counts. Spikes indicate heavy usage days; gaps show periods of inactivity.
        </div>
        """
        layout_items.append(Div(text=daily_desc_html, sizing_mode="stretch_width"))

        sorted_daily = sorted(analysis.daily, key=lambda d: d.date)
        daily_source = ColumnDataSource(
            data={
                "date": [d.date for d in sorted_daily],
                "input_tokens": [d.input_tokens for d in sorted_daily],
                "output_tokens": [d.output_tokens for d in sorted_daily],
                "total_tokens": [d.total_tokens for d in sorted_daily],
                "sessions": [d.session_count for d in sorted_daily],
            }
        )

        daily_fig = figure(
            title="Daily Token Usage",
            x_range=[d.date for d in sorted_daily],
            height=300,
            sizing_mode="stretch_width",
            tools="pan,wheel_zoom,box_zoom,reset,save",
        )

        daily_fig.vbar_stack(
            ["input_tokens", "output_tokens"],
            x="date",
            width=0.8,
            color=[Category10[3][0], Category10[3][1]],
            source=daily_source,
            legend_label=["Input", "Output"],
        )

        daily_fig.add_tools(
            HoverTool(
                tooltips=[
                    ("Date", "@date"),
                    ("Input", "@input_tokens{0,0}"),
                    ("Output", "@output_tokens{0,0}"),
                    ("Total", "@total_tokens{0,0}"),
                    ("Sessions", "@sessions"),
                ]
            )
        )

        daily_fig.xaxis.major_label_orientation = 0.7
        daily_fig.yaxis.formatter = NumeralTickFormatter(format="0,0")
        daily_fig.legend.location = "top_left"
        layout_items.append(daily_fig)
        layout_items.append(Spacer(height=20))

    # 5. Weekly trends (moved up to be with time-based charts)
    if analysis.weekly:
        weekly_desc_html = f"""
        <div style="{DESCRIPTION_STYLE}">
            Week-over-week token consumption trends. Useful for identifying usage
            growth patterns and planning capacity.
        </div>
        """
        layout_items.append(Div(text=weekly_desc_html, sizing_mode="stretch_width"))

        sorted_weekly = sorted(analysis.weekly, key=lambda w: w.week_start)
        weekly_source = ColumnDataSource(
            data={
                "week": [w.week_start for w in sorted_weekly],
                "tokens": [w.total_tokens for w in sorted_weekly],
                "sessions": [w.session_count for w in sorted_weekly],
                "cache_eff": [w.cache_efficiency * 100 for w in sorted_weekly],
            }
        )

        weekly_fig = figure(
            title="Weekly Trends",
            x_range=[w.week_start for w in sorted_weekly],
            height=280,
            sizing_mode="stretch_width",
            tools="pan,wheel_zoom,box_zoom,reset,save",
        )

        weekly_fig.line(
            x="week",
            y="tokens",
            line_width=2,
            color=Category10[3][0],
            legend_label="Tokens",
            source=weekly_source,
        )
        weekly_fig.scatter(
            x="week",
            y="tokens",
            size=8,
            color=Category10[3][0],
            source=weekly_source,
        )

        weekly_fig.add_tools(
            HoverTool(
                tooltips=[
                    ("Week", "@week"),
                    ("Tokens", "@tokens{0,0}"),
                    ("Sessions", "@sessions"),
                    ("Cache Efficiency", "@cache_eff{0.1}%"),
                ]
            )
        )

        weekly_fig.xaxis.major_label_orientation = 0.7
        weekly_fig.yaxis.formatter = NumeralTickFormatter(format="0,0")
        weekly_fig.legend.location = "top_left"
        layout_items.append(weekly_fig)
        layout_items.append(Spacer(height=30))

    # Section: Usage Breakdown
    section_breakdown_html = f"""
    <div style="{SECTION_STYLE}">
        <h2 style="margin: 0; font-size: 18px; font-weight: 600;">Usage Breakdown</h2>
    </div>
    """
    layout_items.append(Div(text=section_breakdown_html, sizing_mode="stretch_width"))

    # Create row for model and hourly distribution
    breakdown_row_items = []

    # 2. Model breakdown
    if analysis.model_breakdown:
        model_col_items = []
        model_desc_html = f"""
        <div style="{DESCRIPTION_STYLE}">
            Token distribution across Claude models. Higher-capability models
            (Opus) consume more tokens but may require fewer iterations.
        </div>
        """
        model_col_items.append(Div(text=model_desc_html, sizing_mode="stretch_width"))

        models = list(analysis.model_breakdown.items())[:8]
        model_names = [MODEL_DISPLAY_NAMES.get(m, m) for m, _ in models]
        model_tokens = [t for _, t in models]

        model_source = ColumnDataSource(
            data={
                "model": model_names,
                "tokens": model_tokens,
                "color": Viridis256[:: 256 // len(model_names)][: len(model_names)],
            }
        )

        model_fig = figure(
            title="Token Usage by Model",
            y_range=model_names[::-1],
            height=280,
            sizing_mode="stretch_width",
            tools="hover,save",
            tooltips=[("Model", "@model"), ("Tokens", "@tokens{0,0}")],
        )

        model_fig.hbar(
            y="model",
            right="tokens",
            height=0.7,
            color="color",
            source=model_source,
        )

        model_fig.xaxis.formatter = NumeralTickFormatter(format="0,0")
        model_col_items.append(model_fig)
        breakdown_row_items.append(
            column(*model_col_items, sizing_mode="stretch_width")
        )

    # 3. Hourly distribution
    if analysis.hourly_distribution:
        hourly_col_items = []
        hourly_desc_html = f"""
        <div style="{DESCRIPTION_STYLE}">
            Token usage by hour of day (UTC). Identifies your peak productivity
            hours and helps plan heavy usage to avoid rate limits.
        </div>
        """
        hourly_col_items.append(Div(text=hourly_desc_html, sizing_mode="stretch_width"))

        hours = list(range(24))
        tokens = [analysis.hourly_distribution.get(h, 0) for h in hours]

        hourly_source = ColumnDataSource(
            data={
                "hour": [f"{h:02d}:00" for h in hours],
                "tokens": tokens,
            }
        )

        hourly_fig = figure(
            title="Token Usage by Hour (UTC)",
            x_range=[f"{h:02d}:00" for h in hours],
            height=280,
            sizing_mode="stretch_width",
            tools="hover,save",
            tooltips=[("Hour", "@hour"), ("Tokens", "@tokens{0,0}")],
        )

        hourly_fig.vbar(
            x="hour",
            top="tokens",
            width=0.8,
            color=Category10[3][2],
            source=hourly_source,
        )

        hourly_fig.xaxis.major_label_orientation = 0.7
        hourly_fig.yaxis.formatter = NumeralTickFormatter(format="0,0")
        hourly_col_items.append(hourly_fig)
        breakdown_row_items.append(
            column(*hourly_col_items, sizing_mode="stretch_width")
        )

    if breakdown_row_items:
        if len(breakdown_row_items) == 2:
            layout_items.append(row(*breakdown_row_items, sizing_mode="stretch_width"))
        else:
            layout_items.extend(breakdown_row_items)
        layout_items.append(Spacer(height=30))

    # Section: Tool Usage
    if analysis.tool_breakdown:
        section_tools_html = f"""
        <div style="{SECTION_STYLE}">
            <h2 style="margin: 0; font-size: 18px; font-weight: 600;">Tool Usage</h2>
        </div>
        """
        layout_items.append(Div(text=section_tools_html, sizing_mode="stretch_width"))

        tool_desc_html = f"""
        <div style="{DESCRIPTION_STYLE}">
            Most frequently used tools ranked by invocation count. High Read counts
            suggest exploration-heavy work; high Edit/Write counts indicate active
            development. Tool invocations contribute to both input and output tokens.
        </div>
        """
        layout_items.append(Div(text=tool_desc_html, sizing_mode="stretch_width"))

        tools = list(analysis.tool_breakdown.items())[:10]
        tool_names = [t for t, _ in tools]
        tool_invocations = [stats.invocations for _, stats in tools]
        tool_tokens = [stats.output_tokens for _, stats in tools]

        tool_source = ColumnDataSource(
            data={
                "tool": tool_names,
                "invocations": tool_invocations,
                "tokens": tool_tokens,
            }
        )

        tool_fig = figure(
            title="Tool Usage (Top 10)",
            y_range=tool_names[::-1],
            height=320,
            sizing_mode="stretch_width",
            tools="hover,save",
            tooltips=[
                ("Tool", "@tool"),
                ("Invocations", "@invocations{0,0}"),
                ("Output Tokens", "@tokens{0,0}"),
            ],
        )

        tool_fig.hbar(
            y="tool",
            right="tokens",
            height=0.7,
            color=Category10[3][0],
            source=tool_source,
        )

        tool_fig.xaxis.formatter = NumeralTickFormatter(format="0,0")
        tool_fig.xaxis.axis_label = "Output Tokens"
        layout_items.append(tool_fig)
        layout_items.append(Spacer(height=20))

    # Footer
    footer_html = """
    <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e0e0e0;
                font-size: 12px; color: #888; text-align: center;">
        Generated by OAPS (Overengineered Agentic Project System)
    </div>
    """
    layout_items.append(Div(text=footer_html, sizing_mode="stretch_width"))

    # Create final layout
    if layout_items:
        final_layout = column(*layout_items, sizing_mode="stretch_width")
    else:
        # Create an empty figure if no data
        no_data_html = """
        <div style="text-align: center; padding: 50px; color: #666;">
            <h2>No Data Available</h2>
            <p>No usage data was found to display.</p>
        </div>
        """
        final_layout = Div(text=no_data_html, sizing_mode="stretch_width")

    # Generate HTML
    html = file_html(final_layout, CDN, "Claude Code Usage Dashboard")
    output_path.write_text(html)
