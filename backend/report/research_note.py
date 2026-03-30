"""Generate 4-page A4 PDF research note using reportlab."""

from __future__ import annotations

import io
import json
import logging
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from config import config

logger = logging.getLogger(__name__)

# Design system colours
BG_COLOR = colors.HexColor("#080C14")
CARD_COLOR = colors.HexColor("#0D1320")
GOLD = colors.HexColor("#C9A84C")
TEXT_PRIMARY = colors.HexColor("#E8ECF0")
TEXT_SECONDARY = colors.HexColor("#8B9CB6")
WHITE = colors.white
BLACK = colors.black


def generate_research_note(
    params: dict,
    comparison: dict,
    strategy: str = "all",
    X: float = 10000,
    T: float = 30,
) -> bytes:
    """Generate a 4-page PDF research note.

    Args:
        params: Calibrated parameters.
        comparison: Results from compare_strategies.
        strategy: Which strategy or "all".
        X: Shares.
        T: Time horizon.

    Returns:
        PDF as bytes.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "Title",
        parent=styles["Title"],
        fontSize=24,
        textColor=colors.HexColor("#1a1a2e"),
        spaceAfter=12,
        alignment=TA_CENTER,
    )

    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        fontSize=11,
        textColor=colors.HexColor("#4a4a6a"),
        spaceAfter=20,
        alignment=TA_CENTER,
    )

    heading_style = ParagraphStyle(
        "Heading",
        parent=styles["Heading2"],
        fontSize=14,
        textColor=colors.HexColor("#1a1a2e"),
        spaceBefore=16,
        spaceAfter=8,
    )

    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#333333"),
        spaceAfter=8,
        alignment=TA_JUSTIFY,
        leading=14,
    )

    mono_style = ParagraphStyle(
        "Mono",
        parent=styles["Code"],
        fontSize=8,
        textColor=colors.HexColor("#2d2d2d"),
        backColor=colors.HexColor("#f5f5f5"),
        spaceAfter=8,
        leading=11,
    )

    elements = []

    # PAGE 1: Title + Summary
    elements.append(Paragraph("Optimal Execution Research Note", title_style))
    elements.append(
        Paragraph(
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | "
            f"X={X:,.0f} shares | T={T:.0f} min",
            subtitle_style,
        )
    )
    elements.append(Spacer(1, 12))

    # Execution summary table
    elements.append(Paragraph("Executive Summary", heading_style))

    strats = comparison.get("strategies", {})
    summary_data = [["Strategy", "E[IS] (bps)", "Std[IS] (bps)", "Sharpe-of-IS", "VWAP Slip (bps)"]]
    for name in ["ac", "ow", "ppo", "twap", "vwap"]:
        if name in strats:
            s = strats[name]
            summary_data.append([
                name.upper(),
                f"{s['mean_IS']:.2f}",
                f"{s['std_IS']:.2f}",
                f"{s['sharpe_IS']:.3f}",
                f"{s['VWAP_slippage_bps']:.2f}",
            ])

    if len(summary_data) > 1:
        t = Table(summary_data, colWidths=[80, 80, 80, 80, 80])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#ffffff"), colors.HexColor("#f9f9f9")]),
        ]))
        elements.append(t)

    elements.append(Spacer(1, 12))

    # Calibration parameters
    elements.append(Paragraph("Calibration Parameters", heading_style))
    param_text = (
        f"eta={params.get('eta', 0):.4f}, "
        f"gamma={params.get('gamma', 0):.4f}, "
        f"rho={params.get('rho', 0):.1f}, "
        f"sigma={params.get('sigma', 0):.4f}, "
        f"spread_mean={params.get('spread_mean', 0):.4f}"
    )
    elements.append(Paragraph(param_text, body_style))

    # PAGE 2: Model Descriptions
    elements.append(PageBreak())
    elements.append(Paragraph("Model Descriptions", heading_style))

    elements.append(Paragraph("<b>Almgren-Chriss (2001)</b>", body_style))
    elements.append(Paragraph(
        "Closed-form optimal execution minimising E[IS] + lambda * Var[IS]. "
        "Assumes linear temporary and permanent impact. The optimal trajectory "
        "is determined by kappa = sqrt(lambda * sigma^2 / eta_tilde), producing "
        "a sinh-shaped inventory path.",
        body_style,
    ))
    elements.append(Paragraph(
        "x(t) = X * sinh(kappa * (T-t)) / sinh(kappa * T)",
        mono_style,
    ))

    elements.append(Paragraph("<b>Obizhaeva-Wang (2013)</b>", body_style))
    elements.append(Paragraph(
        "Resilient order book model with block-shaped depth D and exponential "
        "recovery at rate rho. The optimal strategy front-loads a discrete block "
        "v0 = X*rho/(rho + 2/T), then trades continuously at constant rate.",
        body_style,
    ))

    elements.append(Paragraph("<b>PPO Deep RL Agent</b>", body_style))
    elements.append(Paragraph(
        "A Proximal Policy Optimisation agent trained on the calibrated simulation "
        "environment. 5-dimensional state space (inventory fraction, time fraction, "
        "normalised spread, OFI, last impact). Continuous action in [0,1] representing "
        "fraction of remaining inventory to trade.",
        body_style,
    ))

    # Key equations
    elements.append(Paragraph("Key Equations", heading_style))
    elements.append(Paragraph(
        "IS = SUM_k( v_k * (S_exec_k - S_arrival) )", mono_style
    ))
    elements.append(Paragraph(
        "IS_bps = IS / (X * S_arrival) * 10000", mono_style
    ))
    elements.append(Paragraph(
        "Sharpe_IS = -E[IS_bps] / Std[IS_bps]", mono_style
    ))

    # PAGE 3: Results
    elements.append(PageBreak())
    elements.append(Paragraph("Detailed Results", heading_style))

    # Full comparison table
    detail_data = [["Strategy", "E[IS]", "Std[IS]", "Sharpe", "VWAP Slip", "Perm Impact", "Temp Impact", "Remaining %"]]
    for name in ["ac", "ow", "ppo", "twap", "vwap"]:
        if name in strats:
            s = strats[name]
            detail_data.append([
                name.upper(),
                f"{s['mean_IS']:.2f}",
                f"{s['std_IS']:.2f}",
                f"{s['sharpe_IS']:.3f}",
                f"{s['VWAP_slippage_bps']:.2f}",
                f"{s['perm_impact_bps']:.2f}",
                f"{s['temp_impact_bps']:.2f}",
                f"{s['x_remaining_pct']:.1f}",
            ])

    if len(detail_data) > 1:
        t = Table(detail_data, colWidths=[55, 50, 50, 50, 55, 60, 60, 60])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#ffffff"), colors.HexColor("#f9f9f9")]),
        ]))
        elements.append(t)

    elements.append(Spacer(1, 16))
    elements.append(Paragraph(
        "[Chart placeholders: Inventory trajectories, Cost breakdown, IS distribution histograms]",
        body_style,
    ))

    # PAGE 4: Analysis
    elements.append(PageBreak())
    elements.append(Paragraph("Analysis & Conclusions", heading_style))

    # Auto-generated narrative
    if strats:
        best_strategy = min(strats.items(), key=lambda x: x[1]["mean_IS"])
        worst_strategy = max(strats.items(), key=lambda x: x[1]["mean_IS"])

        elements.append(Paragraph(
            f"Across {comparison.get('n_episodes', 500)} simulated episodes, "
            f"<b>{best_strategy[0].upper()}</b> achieved the lowest mean implementation "
            f"shortfall at {best_strategy[1]['mean_IS']:.2f} bps, while "
            f"<b>{worst_strategy[0].upper()}</b> had the highest at "
            f"{worst_strategy[1]['mean_IS']:.2f} bps.",
            body_style,
        ))

        if "ppo" in strats and "ac" in strats:
            ppo_is = strats["ppo"]["mean_IS"]
            ac_is = strats["ac"]["mean_IS"]
            improvement = (ac_is - ppo_is) / abs(ac_is) * 100 if ac_is != 0 else 0
            elements.append(Paragraph(
                f"The PPO agent achieved {ppo_is:.2f} bps IS vs AC's {ac_is:.2f} bps, "
                f"a {'improvement' if improvement > 0 else 'degradation'} of "
                f"{abs(improvement):.1f}%. This {'supports' if improvement > 0 else 'contradicts'} "
                f"the hypothesis that RL can adapt to microstructure violations.",
                body_style,
            ))

    elements.append(Paragraph("Limitations", heading_style))
    elements.append(Paragraph(
        "1. Simulation calibrated to a single day of AAPL data (or synthetic fallback). "
        "2. No latency modelling or queue position effects. "
        "3. PPO training uses simplified reward shaping. "
        "4. Linear impact assumptions may not hold for very large orders.",
        body_style,
    ))

    doc.build(elements)
    return buffer.getvalue()
