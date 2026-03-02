"""
Server-side chart generation from Genie query results.

Analyzes column types returned by the Genie API to decide whether a chart
is appropriate, then renders a PNG via matplotlib and returns it as a
base64 data URI suitable for embedding in an Adaptive Card Image element.
"""
import base64
import io
import logging
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Genie API type_name values that represent numeric data
NUMERIC_TYPES = {"INT", "LONG", "SHORT", "DOUBLE", "FLOAT", "DECIMAL", "BIGINT", "SMALLINT", "TINYINT"}

# Genie API type_name values that represent temporal data (line chart axis)
TEMPORAL_TYPES = {"DATE", "TIMESTAMP", "TIMESTAMP_NTZ"}

# Minimum rows needed to justify a chart
MIN_ROWS_FOR_CHART = 2


def should_chart(columns: List[Dict[str, str]], rows: List[list]) -> Optional[str]:
    """
    Decide if table data should produce a chart and which type.

    Args:
        columns: List of {"name": str, "type_name": str} from Genie API.
        rows: Data rows (list of lists).

    Returns:
        "line" for temporal label column, "bar" for categorical, or None.
    """
    if not columns or not rows or len(rows) < MIN_ROWS_FOR_CHART:
        return None

    label_col, numeric_cols = _classify_columns(columns)
    if label_col is None or not numeric_cols:
        return None

    label_type = columns[label_col]["type_name"].upper()
    if label_type in TEMPORAL_TYPES:
        return "line"
    return "bar"


def generate_chart(columns: List[Dict[str, str]], rows: List[list], chart_type: str) -> Optional[str]:
    """
    Render a chart as a base64 data URI (PNG).

    Args:
        columns: Column metadata from Genie.
        rows: Data rows.
        chart_type: "bar" or "line".

    Returns:
        "data:image/png;base64,..." string, or None on failure.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")  # non-interactive backend
        import matplotlib.pyplot as plt
        import matplotlib.ticker as ticker

        label_col, numeric_cols = _classify_columns(columns)
        if label_col is None or not numeric_cols:
            return None

        # Use first numeric column for the chart
        value_col = numeric_cols[0]

        labels = [str(row[label_col]) if row[label_col] is not None else "" for row in rows]
        values = []
        for row in rows:
            try:
                values.append(float(row[value_col]))
            except (ValueError, TypeError):
                values.append(0.0)

        label_name = columns[label_col]["name"]
        value_name = columns[value_col]["name"]

        fig, ax = plt.subplots(figsize=(6, 3.5), dpi=100)
        fig.patch.set_facecolor("white")
        ax.set_facecolor("white")

        color = "#0078D4"  # Microsoft blue

        if chart_type == "line":
            ax.plot(range(len(labels)), values, marker="o", color=color, linewidth=2, markersize=5)
            ax.set_xticks(range(len(labels)))
            ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
        else:
            bars = ax.bar(range(len(labels)), values, color=color, width=0.6)
            ax.set_xticks(range(len(labels)))
            ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
            # Add value labels on bars if few enough
            if len(labels) <= 10:
                for bar, val in zip(bars, values):
                    ax.text(
                        bar.get_x() + bar.get_width() / 2, bar.get_height(),
                        _format_number(val), ha="center", va="bottom", fontsize=7
                    )

        ax.set_ylabel(value_name, fontsize=9)
        ax.set_xlabel(label_name, fontsize=9)
        ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: _format_number(x)))
        ax.grid(axis="y", alpha=0.3)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

        plt.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight", facecolor="white")
        plt.close(fig)
        buf.seek(0)

        b64 = base64.b64encode(buf.read()).decode("utf-8")
        return f"data:image/png;base64,{b64}"

    except Exception as e:
        logger.error(f"Error generating chart: {e}", exc_info=True)
        return None


# ── Helpers ────────────────────────────────────────────────────

def _classify_columns(columns: List[Dict[str, str]]) -> Tuple[Optional[int], List[int]]:
    """
    Find the label column index and numeric column indices.

    Returns:
        (label_index, [numeric_indices])  — label_index may be None.
    """
    numeric_indices = []
    label_index = None

    for i, col in enumerate(columns):
        type_name = col.get("type_name", "STRING").upper()
        if type_name in NUMERIC_TYPES:
            numeric_indices.append(i)
        elif label_index is None:
            # First non-numeric column becomes the label
            label_index = i

    return label_index, numeric_indices


def _format_number(val: float) -> str:
    """Format large numbers with K/M suffixes for cleaner axis labels."""
    abs_val = abs(val)
    if abs_val >= 1_000_000:
        return f"{val / 1_000_000:.1f}M"
    if abs_val >= 1_000:
        return f"{val / 1_000:.1f}K"
    if val == int(val):
        return str(int(val))
    return f"{val:.1f}"
