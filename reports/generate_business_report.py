"""Generates Anveshak_Business_Market_Report.pdf — a 12-page-style business/
market report matching the AankhoDekha reference report's structure and the
Anveshak brand palette (navy / slate / tan / cream).

Run:  python reports/generate_business_report.py
Output: reports/Anveshak_Business_Market_Report.pdf
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer,
                                 Table, TableStyle, Image, NextPageTemplate, PageBreak,
                                 HRFlowable)

HERE = Path(__file__).parent
ASSETS = HERE.parent / "assets"
OUT_PDF = HERE / "Anveshak_Business_Market_Report.pdf"
CHART_PATH = HERE / "_chart_market.png"

# ---------------------------------------------------------------------------
# Brand palette (matches ui_common.py)
# ---------------------------------------------------------------------------
NAVY = HexColor("#071739")
SLATE = HexColor("#4B6382")
BLUEGRAY = HexColor("#A4B5C4")
PALE = HexColor("#CDD5DB")
TAN = HexColor("#A68868")
CREAM = HexColor("#E3C39D")
BG = HexColor("#F7F2EA")
WHITE = colors.white
INK = HexColor("#12213D")
RED = HexColor("#C4324D")
GREEN = HexColor("#2E9E6B")

PAGE_SIZE = landscape(letter)
PW, PH = PAGE_SIZE
MARGIN = 0.6 * inch

# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------
styles = {
    "cover_title": ParagraphStyle("cover_title", fontName="Helvetica-Bold", fontSize=44,
                                   textColor=WHITE, leading=48),
    "cover_sub": ParagraphStyle("cover_sub", fontName="Helvetica-Bold", fontSize=16,
                                 textColor=CREAM, leading=20, spaceBefore=6),
    "cover_body": ParagraphStyle("cover_body", fontName="Helvetica", fontSize=11,
                                  textColor=PALE, leading=16, spaceBefore=14),
    "cover_kicker": ParagraphStyle("cover_kicker", fontName="Helvetica-Bold", fontSize=10,
                                    textColor=TAN, leading=12, tracking=2),
    "cover_box_label": ParagraphStyle("cover_box_label", fontName="Helvetica-Bold", fontSize=9,
                                       textColor=TAN, leading=11),
    "cover_box_text": ParagraphStyle("cover_box_text", fontName="Helvetica", fontSize=12,
                                      textColor=WHITE, leading=16),
    "cover_footer": ParagraphStyle("cover_footer", fontName="Helvetica", fontSize=8.5,
                                    textColor=BLUEGRAY, leading=11),
    "sec_num": ParagraphStyle("sec_num", fontName="Helvetica-Bold", fontSize=30,
                               textColor=TAN, leading=32),
    "sec_title": ParagraphStyle("sec_title", fontName="Helvetica-Bold", fontSize=20,
                                 textColor=NAVY, leading=24),
    "body": ParagraphStyle("body", fontName="Helvetica", fontSize=9.7, textColor=INK,
                            leading=14.5, spaceAfter=6),
    "body_bold_lead": ParagraphStyle("body_bold_lead", fontName="Helvetica", fontSize=9.7,
                                      textColor=INK, leading=14.5, spaceAfter=6),
    "bullet": ParagraphStyle("bullet", fontName="Helvetica", fontSize=9.5, textColor=INK,
                              leading=13.5, spaceAfter=5, leftIndent=12, bulletIndent=0),
    "small": ParagraphStyle("small", fontName="Helvetica", fontSize=8, textColor=SLATE,
                             leading=11),
    "stat_value": ParagraphStyle("stat_value", fontName="Helvetica-Bold", fontSize=20,
                                  textColor=NAVY, leading=22),
    "stat_caption": ParagraphStyle("stat_caption", fontName="Helvetica", fontSize=8,
                                    textColor=SLATE, leading=10.5),
    "box_label": ParagraphStyle("box_label", fontName="Helvetica-Bold", fontSize=8,
                                 textColor=SLATE, leading=10, spaceAfter=3),
    "box_text": ParagraphStyle("box_text", fontName="Helvetica", fontSize=9.3, textColor=INK,
                                leading=13),
    "table_header": ParagraphStyle("table_header", fontName="Helvetica-Bold", fontSize=8.5,
                                    textColor=WHITE, leading=11),
    "table_cell": ParagraphStyle("table_cell", fontName="Helvetica", fontSize=8.7,
                                  textColor=INK, leading=12),
    "table_cell_bold": ParagraphStyle("table_cell_bold", fontName="Helvetica-Bold", fontSize=8.7,
                                       textColor=NAVY, leading=12),
    "chain_title": ParagraphStyle("chain_title", fontName="Helvetica-Bold", fontSize=9.5,
                                   textColor=WHITE, leading=12, alignment=TA_CENTER),
    "chain_text": ParagraphStyle("chain_text", fontName="Helvetica", fontSize=8,
                                  textColor=WHITE, leading=10.5, alignment=TA_CENTER),
    "toc_num": ParagraphStyle("toc_num", fontName="Helvetica-Bold", fontSize=11, textColor=TAN),
    "toc_title": ParagraphStyle("toc_title", fontName="Helvetica", fontSize=11, textColor=INK),
    "toc_cat": ParagraphStyle("toc_cat", fontName="Helvetica", fontSize=8.5, textColor=SLATE,
                               alignment=TA_LEFT),
    "vision": ParagraphStyle("vision", fontName="Helvetica-Bold", fontSize=15, textColor=WHITE,
                              leading=21),
}


def P(text, style="body"):
    return Paragraph(text, styles[style])


def section_header(num, title, category):
    t = Table(
        [[P(num, "sec_num"), P(title, "sec_title")],
         ["", P(category.upper(), "small")]],
        colWidths=[0.7 * inch, 8 * inch],
    )
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 2),
        ("LEFTPADDING", (0, 0), (0, -1), 0),
    ]))
    rule = HRFlowable(width="100%", thickness=1.2, color=PALE, spaceBefore=6, spaceAfter=12)
    return [t, rule]


def stat_row(stats, bg=CREAM):
    """stats: list of (value, caption) tuples."""
    n = len(stats)
    w = 9.4 * inch / n
    cells = []
    for value, caption in stats:
        cell = Table([[P(value, "stat_value")], [P(caption, "stat_caption")]], colWidths=[w - 0.15 * inch])
        cell.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), bg),
            ("BOX", (0, 0), (-1, -1), 0, bg),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, 0), 10),
            ("BOTTOMPADDING", (0, -1), (-1, -1), 10),
            ("LINEBEFORE", (0, 0), (0, -1), 3, TAN),
        ]))
        cells.append(cell)
    row = Table([cells], colWidths=[w] * n)
    row.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0),
                              ("RIGHTPADDING", (0, 0), (-1, -1), 6)]))
    return row


def info_box(label, text, border=SLATE, bg=HexColor("#EFF2F5"), label_style="box_label",
             text_style="box_text", width=4.6):
    t = Table([[P(label, label_style)], [P(text, text_style)]], colWidths=[width * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("BOX", (0, 0), (-1, -1), 1, border),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    return t


def two_col(left, right, gap=0.3):
    t = Table([[left, right]], colWidths=[(9.4 - gap) / 2 * inch, (9.4 - gap) / 2 * inch])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (0, -1), gap * inch),
        ("RIGHTPADDING", (1, 0), (1, -1), 0),
    ]))
    return t


def data_table(header, rows, col_widths=None):
    data = [[P(h, "table_header") for h in header]]
    for r in rows:
        data.append([P(str(c), "table_cell") if i > 0 else P(str(c), "table_cell_bold")
                     for i, c in enumerate(r)])
    t = Table(data, colWidths=col_widths, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, PALE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]
    for i in range(1, len(data)):
        if i % 2 == 0:
            style.append(("BACKGROUND", (0, i), (-1, i), HexColor("#F2EFE7")))
    t.setStyle(TableStyle(style))
    return t


def bullets(items):
    return [P(f"•  {i}", "bullet") for i in items]


def chain_boxes(steps, colors_list=None):
    n = len(steps)
    w = 9.4 * inch / n
    colors_list = colors_list or [NAVY] * n
    cells = []
    for (title, desc), c in zip(steps, colors_list):
        cell = Table([[P(title, "chain_title")], [P(desc, "chain_text")]], colWidths=[w - 0.1 * inch])
        cell.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), c),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        cells.append(cell)
    row = Table([cells], colWidths=[w] * n)
    row.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                              ("TOPPADDING", (0, 0), (-1, -1), 0)]))
    return row


# ---------------------------------------------------------------------------
# Chart: India GRC platform market growth 2025 -> 2034
# ---------------------------------------------------------------------------
def make_market_chart():
    fig, ax = plt.subplots(figsize=(5.0, 2.4), dpi=200)
    years = ["2025", "2034"]
    values = [1788.3, 4442.8]
    bars = ax.bar(years, values, color=["#4B6382", "#071739"], width=0.5)
    for b, v in zip(bars, values):
        ax.text(b.get_x() + b.get_width() / 2, v + 60, f"${v:,.0f}M", ha="center",
                fontsize=11, fontweight="bold", color="#12213D")
    ax.set_ylim(0, 5200)
    ax.set_ylabel("USD million", fontsize=9, color="#4B6382")
    ax.set_title("India GRC Platform Market", fontsize=10.5, color="#12213D",
                  fontweight="bold", loc="left", pad=10)
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color("#CDD5DB")
    ax.tick_params(colors="#4B6382", labelsize=9)
    ax.set_facecolor("white")
    fig.patch.set_facecolor("white")
    plt.tight_layout()
    plt.savefig(CHART_PATH, facecolor="white", bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Page decoration callbacks
# ---------------------------------------------------------------------------
def draw_cover_bg(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(NAVY)
    canvas.rect(0, 0, PW, PH, fill=1, stroke=0)
    canvas.setFillColor(TAN)
    canvas.rect(0, PH - 0.12 * inch, PW, 0.12 * inch, fill=1, stroke=0)
    # faint circle decoration
    canvas.setStrokeColor(HexColor("#13294F"))
    canvas.setLineWidth(1)
    canvas.circle(PW - 1.6 * inch, PH - 2.3 * inch, 1.6 * inch, stroke=1, fill=0)
    canvas.circle(PW - 1.6 * inch, PH - 2.3 * inch, 1.15 * inch, stroke=1, fill=0)
    logo_path = ASSETS / "logo_icon.png"
    if logo_path.exists():
        canvas.drawImage(str(logo_path), PW - 2.35 * inch, PH - 3.05 * inch,
                          width=1.5 * inch, height=1.5 * inch, mask="auto")
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(BLUEGRAY)
    canvas.drawString(MARGIN, 0.35 * inch,
                       "ANVESHAK  ·  Business & Market Report")
    canvas.drawRightString(PW - MARGIN, 0.35 * inch, "Page 1")
    canvas.restoreState()


def draw_body_bg(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(BG)
    canvas.rect(0, 0, PW, PH, fill=1, stroke=0)
    canvas.setFillColor(NAVY)
    canvas.rect(0, PH - 0.09 * inch, PW, 0.09 * inch, fill=1, stroke=0)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(SLATE)
    canvas.drawString(MARGIN, 0.35 * inch, "ANVESHAK  ·  Business & Market Report")
    canvas.drawRightString(PW - MARGIN, 0.35 * inch, f"Page {doc.page}")
    canvas.restoreState()


def draw_toc_bg(canvas, doc):
    draw_body_bg(canvas, doc)


# ---------------------------------------------------------------------------
# Build document
# ---------------------------------------------------------------------------
def build():
    make_market_chart()

    doc = BaseDocTemplate(str(OUT_PDF), pagesize=PAGE_SIZE,
                           leftMargin=MARGIN, rightMargin=MARGIN,
                           topMargin=0.55 * inch, bottomMargin=0.55 * inch)

    cover_frame = Frame(0.9 * inch, 0.9 * inch, PW - 1.8 * inch, PH - 1.8 * inch,
                         id="cover", showBoundary=0)
    body_frame = Frame(MARGIN, 0.6 * inch, PW - 2 * MARGIN, PH - 1.3 * inch,
                        id="body", showBoundary=0)

    doc.addPageTemplates([
        PageTemplate(id="Cover", frames=[cover_frame], onPage=draw_cover_bg),
        PageTemplate(id="Body", frames=[body_frame], onPage=draw_body_bg),
    ])

    story = []

    # ---- COVER ----
    story.append(Spacer(1, 1.6 * inch))
    story.append(P("BUSINESS MODEL &nbsp;&middot;&nbsp; MARKET &nbsp;&middot;&nbsp; "
                    "COMPETITIVE SCALING", "cover_kicker"))
    story.append(Spacer(1, 10))
    story.append(P("Anveshak", "cover_title"))
    story.append(P("Business Model, Market &amp; Competitive Scaling Report", "cover_sub"))
    story.append(P("A business-pitch analysis of the Indian GRC, critical-infrastructure "
                    "audit, and regulatory supervision software market.", "cover_body"))
    story.append(Spacer(1, 26))
    story.append(info_box(
        "CORE PROPOSITION",
        "Anveshak converts existing SOC alert, case, and audit-log data into searchable, "
        "benchmarked, and explainable supervisory risk intelligence.",
        border=TAN, bg=HexColor("#0D2148"),
        label_style="cover_box_label", text_style="cover_box_text", width=6.6,
    ))
    story.append(Spacer(1, 16))
    story.append(P("Prepared for business strategy, pitch-deck development, and B2G "
                    "commercialisation planning.", "cover_footer"))
    story.append(NextPageTemplate("Body"))
    story.append(PageBreak())

    # ---- TOC ----
    toc_items = [
        ("01", "Executive Summary", "THESIS"),
        ("02", "Market Opportunity", "MARKET"),
        ("03", "Existing Solution Landscape", "MARKET"),
        ("04", "Competitor Case Study — MetricStream", "COMPETITION"),
        ("05", "Competitor Case Study — Safe Security", "COMPETITION"),
        ("06", "What the Existing Players Prove", "COMPETITION"),
        ("07", "Anveshak Business Model", "MODEL"),
        ("08", "The Revenue Engine", "MODEL"),
        ("09", "Illustrative Contract Economics", "MODEL"),
        ("10", "Scaling Strategy", "GROWTH"),
        ("11", "Anveshak's Differentiation", "GROWTH"),
        ("12", "Go-to-Market Strategy", "GROWTH"),
        ("13", "Key Business Risks & Mitigation", "RISK"),
        ("14", "Future Revenue Expansion", "GROWTH"),
        ("15", "Competitive Financial Snapshot", "FINANCIALS"),
        ("16", "Business Pitch Conclusion", "CLOSE"),
        ("17", "Sources & References", "APPENDIX"),
    ]
    story.append(P("INSIDE THIS REPORT", "small"))
    story.append(P("Contents", "sec_title"))
    story.append(Spacer(1, 10))
    toc_rows = []
    for num, title, cat in toc_items:
        toc_rows.append([P(num, "toc_num"), P(title, "toc_title"), P(cat, "toc_cat")])
    toc_table = Table(toc_rows, colWidths=[0.5 * inch, 6.6 * inch, 2.3 * inch])
    toc_table.setStyle(TableStyle([
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, PALE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(toc_table)
    story.append(PageBreak())

    # ---- 01 Executive Summary ----
    story += section_header("01", "Executive Summary", "Thesis")
    story.append(P(
        "India is moving from point-in-time compliance audits toward continuous, "
        "evidence-based regulatory supervision. Regulators &mdash; CERT-In, RBI, SEBI, "
        "IRDAI, and NCIIPC &mdash; each mandate recurring cybersecurity audits and oversight "
        "of regulated entities, creating a market for software that turns raw SOC data into "
        "structured, defensible supervisory findings.", "body"))
    story.append(P(
        "Anveshak should be positioned not as another SIEM or alert-correlation tool, but as "
        "a <b>supervisory evidence layer</b> that sits above existing SOC infrastructure and "
        "serves the regulator's side of the relationship, not just the entity being regulated.",
        "body"))
    story.append(Spacer(1, 8))
    story.append(two_col(
        info_box("BUSINESS THESIS",
                  "Acquire a regulator or NCIIPC pilot deployment, expand the number of "
                  "covered entities and detector modules, and generate recurring revenue "
                  "through licensing, managed deployment, integrations, custom rule packs, "
                  "and annual maintenance."),
        info_box("MARKET VALIDATION",
                  "Public company data shows that GRC and cyber-risk-quantification "
                  "platforms &mdash; MetricStream and Safe Security among them &mdash; have "
                  "already built substantial businesses around exactly this supervisory / "
                  "compliance analytics category.", border=TAN, bg=HexColor("#F6EEE3")),
    ))
    story.append(PageBreak())

    # ---- 02 Market Opportunity ----
    story += section_header("02", "Market Opportunity", "Market")
    story.append(P(
        "The core market problem: regulators can mandate that entities log and report SOC "
        "activity, but they cannot manually review every alert, case, and audit record across "
        "every regulated entity. The commercial value shifts from the SOC tooling itself to "
        "the <b>supervisory intelligence layer</b> that reviews it on the regulator's behalf.",
        "body"))
    story.append(Spacer(1, 6))
    story.append(stat_row([
        ("USD 1.79B", "India's GRC platform market size in 2025 [1]"),
        ("6 Sectors", "Critical sectors designated by NCIIPC [2]"),
        ("4 Regulators", "CERT-In, RBI, SEBI, IRDAI each mandate cyber audits [3]"),
    ]))
    story.append(Spacer(1, 10))
    story.append(Image(str(CHART_PATH), width=5.0 * inch, height=2.4 * inch))
    story.append(Spacer(1, 6))
    story.append(P("<b>Typical regulator requirements include:</b>", "body"))
    story.append(two_col(
        Table([[b] for b in bullets([
            "Periodic third-party cybersecurity audits of regulated entities",
            "Continuous SOC/alert-handling oversight, not just point-in-time audits",
            "Cross-entity peer benchmarking within a sector",
            "Escalation and incident-handling accountability tracking",
        ])], colWidths=[4.5 * inch]),
        Table([[b] for b in bullets([
            "Audit-log completeness verification",
            "Evidence-backed findings usable for regulatory action",
            "Integration with each entity's existing SOC/SIEM/case-management tools",
        ])], colWidths=[4.5 * inch]),
    ))
    story.append(PageBreak())

    # ---- 03 Existing Solution Landscape ----
    story += section_header("03", "Existing Solution Landscape", "Market")
    story.append(P(
        "The competitive market can be divided into four broad layers &mdash; with Anveshak "
        "positioned as a focused supervisory-evidence layer.", "body"))
    story.append(Spacer(1, 8))
    story.append(data_table(
        ["Layer", "Examples", "Role"],
        [
            ["SIEM / SOC tooling", "Splunk, QRadar, Securonix",
             "Real-time alert correlation — operational, not supervisory"],
            ["GRC platforms", "MetricStream, Resolver, Archer",
             "Enterprise-wide risk/compliance workflow — broad, not SOC-evidence-specific"],
            ["Compliance audit firms", "SISA, Big 4 cyber-audit arms",
             "Manual, periodic third-party audits — point-in-time, not continuous"],
            ["Anveshak", "Supervisory evidence layer",
             "Batch detection + peer benchmarking + explainable evidence, continuous and "
             "regulator-facing"],
        ],
        col_widths=[1.9 * inch, 2.3 * inch, 5 * inch],
    ))
    story.append(PageBreak())

    # ---- 04 Competitor — MetricStream ----
    story += section_header("04", "Competitor Case Study — MetricStream", "Competition")
    story.append(P(
        "MetricStream is an AI-powered GRC platform with an R&amp;D center in Bangalore "
        "(HQ in San Jose), offering cybersecurity, compliance, and internal-audit modules to "
        "large enterprises globally. [4]", "body"))
    story.append(Spacer(1, 6))
    story.append(stat_row([
        ("$252.1M", "Reported annual revenue (global) [4]"),
        ("$213M–$375M", "Total funding raised across sources [4][5]"),
    ], bg=HexColor("#EAEFF4")))
    story.append(Spacer(1, 8))
    story.append(two_col(
        info_box("FINANCIAL CAVEAT",
                  "Public third-party sources disagree on MetricStream's exact funding "
                  "total. For a pitch deck, revenue is the safer headline metric unless the "
                  "statutory filing is independently reconciled.",
                  border=RED, bg=HexColor("#FBEAEE")),
        info_box("LESSON FOR ANVESHAK",
                  "The scalable product is not a single detector — it's the platform around "
                  "it: peer benchmarking, evidence drill-down, integrations, and long-term "
                  "regulator contracts.", border=TAN, bg=HexColor("#F6EEE3")),
    ))
    story.append(PageBreak())

    # ---- 05 Competitor — Safe Security ----
    story += section_header("05", "Competitor Case Study — Safe Security (formerly Lucideus)", "Competition")
    story.append(P(
        "Safe Security is an Indian-founded (2012, by Saket Modi) cyber-risk-quantification "
        "platform offering Cyber Risk Quantification (CRQ), Third-Party Risk Management, and "
        "Continuous Threat Exposure Management modules. [6][7]", "body"))
    story.append(Spacer(1, 6))
    story.append(stat_row([
        ("$170M", "Total funding raised across 13 rounds [7][8]"),
        ("₹86 Lakh", "FY22 revenue, India filing entity [6]"),
        ("−68.7%", "YoY change vs. ₹2.8 Cr in FY21 [6]"),
    ], bg=HexColor("#F6EEE3")))
    story.append(Spacer(1, 8))
    story.append(two_col(
        info_box("FINANCIAL CAVEAT",
                  "The India-entity revenue figure likely understates the company's actual "
                  "global scale after its 2021 rebrand and shift of primary revenue to the "
                  "US parent entity — the same caution the AankhoDekha report applied to "
                  "Videonetics.", border=RED, bg=HexColor("#FBEAEE")),
        info_box("LESSON FOR ANVESHAK",
                  "A founder-led, India-origin risk platform can scale to real global funding "
                  "rounds without needing to be a full GRC suite — a focused, sharp "
                  "proposition is enough to build a fundable business.",
                  border=TAN, bg=HexColor("#F6EEE3")),
    ))
    story.append(PageBreak())

    # ---- 06 What Players Prove ----
    story += section_header("06", "What the Existing Players Prove", "Competition")
    story.append(P("The public examples support four commercial conclusions:", "body"))
    story.append(Spacer(1, 6))
    conclusions = [
        ("Regulators are real, funded buyers",
         "RBI, SEBI, and CERT-In already mandate periodic audits and GRC tooling adoption."),
        ("Recurring relationships matter",
         "Audits and licenses renew annually by regulatory mandate, not customer choice."),
        ("Scale comes from integration",
         "Platforms become more valuable connected to each entity's SOC/SIEM/case tools."),
        ("Expansion is easier after proof",
         "A successful NCIIPC pilot becomes the reference for expansion across sectors."),
    ]
    rows = []
    for i in range(0, 4, 2):
        rows.append(two_col(
            info_box(conclusions[i][0], conclusions[i][1]),
            info_box(conclusions[i + 1][0], conclusions[i + 1][1]),
        ))
        rows.append(Spacer(1, 8))
    story += rows
    story.append(PageBreak())

    # ---- 07 Business Model ----
    story += section_header("07", "Anveshak Business Model", "Model")
    story.append(P(
        "<b>Positioning:</b> Anveshak should be sold as a supervisory evidence platform for "
        "regulators, not a one-time detection script.", "body"))
    story.append(Spacer(1, 6))
    story.append(data_table(
        ["Revenue Stream", "What the Customer Pays For", "Revenue Character"],
        [
            ["Platform licensing", "Annual licence based on entities, sectors, and users", "Recurring"],
            ["Managed on-prem deployment", "Hosting support, updates, monitoring within own infra", "Recurring"],
            ["Integration", "Connectors into each CSE's SOC/SIEM/case-management tools", "Project + expansion"],
            ["Custom detector modules", "Sector- or regulator-specific rule packs", "High-margin add-on"],
            ["AMC / support", "Maintenance, updates, technical support", "Annual recurring"],
            ["Training", "Supervisor onboarding, rule-tuning workshops", "Service revenue"],
            ["System-integrator partnerships", "Participation in larger govt cybersecurity programmes", "Scale channel"],
        ],
        col_widths=[2.4 * inch, 4.8 * inch, 2 * inch],
    ))
    story.append(PageBreak())

    # ---- 08 Revenue Engine ----
    story += section_header("08", "The Revenue Engine", "Model")
    story.append(P(
        "Anveshak should be designed around an expansion model, not a one-off project model.",
        "body"))
    story.append(Spacer(1, 10))
    engine_colors = [NAVY, SLATE, TAN, SLATE, NAVY, TAN]
    story.append(chain_boxes([
        ("01 Acquire", "Pilot deployment with one regulator or sector"),
        ("02 Prove", "Detection accuracy, explainability, audit-coverage gain"),
        ("03 Expand", "More entities and sectors onboarded"),
        ("04 Integrate", "Connect to each CSE's SOC/SIEM/case tools"),
        ("05 Renew", "Annual licence / AMC"),
        ("06 Replicate", "Additional regulators adopt the same platform"),
    ], engine_colors))
    story.append(Spacer(1, 10))
    story.append(P(
        "This creates a customer lifecycle in which the initial deployment is the entry point "
        "and recurring services become the long-term revenue base.", "body"))
    story.append(PageBreak())

    # ---- 09 Contract Economics ----
    story += section_header("09", "Illustrative Contract Economics", "Model")
    story.append(P("<i>Strategic planning example — not a quoted market price or forecast.</i>", "small"))
    story.append(Spacer(1, 8))
    story.append(data_table(
        ["Pilot Component", "Illustrative Value", "Share"],
        [
            ["Platform licence", "₹10 lakh", "42%"],
            ["Integration (SOC/SIEM connectors)", "₹6 lakh", "25%"],
            ["Customisation (sector rule tuning)", "₹4 lakh", "17%"],
            ["Training", "₹2 lakh", "8%"],
            ["Year-1 AMC", "₹2 lakh", "8%"],
            ["Illustrative Year-1 contract", "₹24 lakh", "100%"],
        ],
        col_widths=[4.4 * inch, 2.8 * inch, 2 * inch],
    ))
    story.append(Spacer(1, 8))
    story.append(P(
        "As deployment expands from one sector to multiple regulators, additional entity "
        "licences, rule packs, and integrations increase contract value. Actual pricing "
        "depends on procurement structure and scope.", "body"))
    story.append(PageBreak())

    # ---- 10 Scaling Strategy ----
    story += section_header("10", "Scaling Strategy", "Growth")
    story.append(data_table(
        ["Phase", "Scope", "Focus"],
        [
            ["Phase 1 — Pilot", "1 sector, 3–5 entities", "Establish detection accuracy and explainability benchmarks"],
            ["Phase 2 — Sector-wide", "One full sector (e.g., all Power CSEs)", "Peer benchmarking becomes statistically meaningful"],
            ["Phase 3 — Multi-sector", "Power + Banking + Telecom", "Cross-sector reference deployment"],
            ["Phase 4 — Multi-regulator", "RBI / SEBI / IRDAI adopt alongside NCIIPC", "Regulator-level licensing"],
            ["Phase 5 — National", "All CII sectors", "Reusable platform across India's full CII mandate"],
        ],
        col_widths=[2 * inch, 3.2 * inch, 4 * inch],
    ))
    story.append(Spacer(1, 10))
    story.append(P("<b>Scaling flywheel</b>", "body"))
    story.append(P(
        "Pilot &rarr; Measurable accuracy &rarr; Case study &rarr; Regulatory mandate/tender "
        "&rarr; Larger deployment &rarr; Recurring revenue &rarr; More references &rarr; "
        "More sectors &#8635;", "body"))
    story.append(PageBreak())

    # ---- 11 Differentiation ----
    story += section_header("11", "Anveshak's Differentiation", "Growth")
    story.append(P(
        "Anveshak should avoid unsupported claims that competitors lack explainability or "
        "auditability &mdash; MetricStream and Safe Security both offer real risk-scoring and "
        "audit features. The stronger positioning is <b>evidence transparency</b>: every score "
        "connects to the exact record that produced it.", "body"))
    story.append(Spacer(1, 10))
    story.append(chain_boxes([
        ("01 Finding", "Which rule fired?"),
        ("02 Evidence", "Which alert/case/audit record supports it?"),
        ("03 Threshold", "What statistical bar was crossed?"),
        ("04 Peer Context", "How does this compare to sector peers?"),
        ("05 Review", "Can a supervisor act on a prioritized worklist?"),
    ], [NAVY, SLATE, TAN, SLATE, NAVY]))
    story.append(Spacer(1, 16))
    vision_box = Table([[P("&ldquo;From flag to evidence.&rdquo;", "vision")]], colWidths=[9.4 * inch])
    vision_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("TOPPADDING", (0, 0), (-1, -1), 18),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 18),
        ("LEFTPADDING", (0, 0), (-1, -1), 20),
    ]))
    story.append(vision_box)
    story.append(PageBreak())

    # ---- 12 GTM ----
    story += section_header("12", "Go-to-Market Strategy", "Growth")
    gtm = [
        ("01  Direct pilot", "With NCIIPC or one sector regulator"),
        ("02  Regulatory mandate conversion", "Pilot becomes a mandated tool across that sector's regulated entities"),
        ("03  System-integrator partnerships", "With established govt cybersecurity consulting firms"),
        ("04  Existing infrastructure", "Targets CSEs that already run SOC/SIEM, reducing new-sensor burden"),
        ("05  Expansion sales", "More sectors, more detectors, more regulators on the same core engine"),
    ]
    for i in range(0, 4, 2):
        story.append(two_col(
            info_box(gtm[i][0], gtm[i][1]),
            info_box(gtm[i + 1][0], gtm[i + 1][1]),
        ))
        story.append(Spacer(1, 8))
    story.append(info_box(gtm[4][0], gtm[4][1]))
    story.append(PageBreak())

    # ---- 13 Risks ----
    story += section_header("13", "Key Business Risks & Mitigation", "Risk")
    story.append(data_table(
        ["Risk", "Mitigation"],
        [
            ["Long government sales cycles", "Use pilots, SI partnerships, and reference deployments"],
            ["Large incumbents (MetricStream, Safe Security, SIEM vendors)", "Focus on the narrow supervisory-evidence niche, not broad GRC"],
            ["Detector false positives / threshold tuning", "Validate against known ground truth; publish precision/recall once real data is available"],
            ["CSE reluctance to share SOC data", "Offline/on-prem architecture, zero external calls, CSE-controlled deployment"],
            ["Regulatory fragmentation (RBI vs. SEBI vs. CERT-In formats)", "Modular schema adapters per regulator's data format"],
            ["Procurement complexity", "Clear licence, integration, and AMC packages that fit government procurement"],
        ],
        col_widths=[4.2 * inch, 5.2 * inch],
    ))
    story.append(PageBreak())

    # ---- 14 Future Revenue ----
    story += section_header("14", "Future Revenue Expansion", "Growth")
    future_items = [
        "Local embedding-based similarity detection (smarter duplicate/template-note detection)",
        "Predictive risk-trend modeling (early warning before a score crosses Severe)",
        "Additional regulator-specific rule packs (RBI / SEBI / IRDAI formats)",
        "Configurable data retention and privacy controls",
        "Natural-language finding summaries for non-technical reviewers",
        "RBAC and in-app supervisor action logging",
        "New modules for additional CII sectors (Transport, Government, Strategic Enterprises)",
        "State/regulator-level deployments through consulting partnerships",
    ]
    left = Table([[b] for b in bullets(future_items[:4])], colWidths=[4.5 * inch])
    right = Table([[b] for b in bullets(future_items[4:])], colWidths=[4.5 * inch])
    story.append(two_col(left, right))
    story.append(PageBreak())

    # ---- 15 Financial Snapshot ----
    story += section_header("15", "Competitive Financial Snapshot", "Financials")
    story.append(data_table(
        ["Company", "Reported Revenue", "Funding", "Note"],
        [
            ["MetricStream", "~$252.1M (global)", "$213M–$375M (sources vary)", "India R&D center only; revenue is global"],
            ["Safe Security", "₹86 lakh (India entity, FY22)", "$170M across 13 rounds", "India-entity revenue understates global scale post-rebrand"],
        ],
        col_widths=[1.8 * inch, 2.4 * inch, 2.4 * inch, 3 * inch],
    ))
    story.append(Spacer(1, 10))
    story.append(P(
        "<i>These figures are drawn from third-party company-data platforms and press "
        "coverage, and should be treated as secondary-source figures — useful for market "
        "context, not audited financial claims. [4][5][6][7][8]</i>", "small"))
    story.append(PageBreak())

    # ---- 16 Conclusion ----
    story += section_header("16", "Business Pitch Conclusion", "Close")
    story.append(P(
        "The opportunity for Anveshak is not to out-build MetricStream's full GRC suite or "
        "Safe Security's risk-quantification platform. It's to own a narrower, sharper "
        "category: <b>continuous, evidence-linked supervisory analytics</b> for the "
        "regulators that already mandate SOC oversight across India's critical sectors.",
        "body"))
    story.append(P(
        "The commercial model follows a simple progression: enter through a pilot with one "
        "regulator, prove detection accuracy against real evidence, expand across sectors, "
        "and convert into a recurring licence/AMC relationship &mdash; the same path that took "
        "MetricStream and Safe Security from pilot deployments to funded, scaled businesses.",
        "body"))
    story.append(Spacer(1, 14))
    vision_box2 = Table([[P(
        "Anveshak aims to become the evidence layer that turns India's existing SOC and "
        "audit data into traceable, benchmarked, and actionable supervisory intelligence.",
        "vision")]], colWidths=[9.4 * inch])
    vision_box2.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("TOPPADDING", (0, 0), (-1, -1), 20),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 20),
        ("LEFTPADDING", (0, 0), (-1, -1), 22),
        ("RIGHTPADDING", (0, 0), (-1, -1), 22),
    ]))
    story.append(vision_box2)
    story.append(PageBreak())

    # ---- 17 Sources ----
    story += section_header("17", "Sources & References", "Appendix")
    refs = [
        ("[1]", "IMARC Group — India Governance, Risk & Compliance Platform Market 2034.",
         "imarcgroup.com/india-governance-risk-compliance-platform-market"),
        ("[2]", "Testbook / NCIIPC guidelines — Critical Sectors identified by NCIIPC.",
         "testbook.com/question-answer/which-of-the-following-sectors-have-been-identifie--66af40b10a284c581afb8c90"),
        ("[3]", "Veritect — India's Cyber Compliance Stack 2026: RBI, SEBI, IRDAI, CERT-In.",
         "veritect.ai/digital-data-ai-law/india-cyber-compliance-stack-rbi-sebi-irdai-cert-in-2026"),
        ("[4]", "MetricStream — Strategic Financing press release.",
         "metricstream.com/pressNews/strategic-financing-to-accelerate-profitable-growth-innovation.html"),
        ("[5]", "Tracxn — MetricStream Company Profile.", "tracxn.com/d/companies/metricstream/"),
        ("[6]", "Inc42 — Safe Security Funding, Revenue & Investors.",
         "inc42.com/company/safe-security/financials/"),
        ("[7]", "BankInfoSecurity — Safe Raises $70M Series C.",
         "bankinfosecurity.com/safe-raises-70m-series-c-to-scale-cyber-risk-management-a-29109"),
        ("[8]", "YourStory — John Chambers-backed Lucideus/Safe Security.",
         "yourstory.com/2021/01/john-chambers-cybersecurity-startup-lucideus-safe-security"),
        ("[9]", "SEBI — Cybersecurity and Cyber Resilience Framework (CSCRF) circular.",
         "sebi.gov.in/legal/circulars/aug-2024/cybersecurity-and-cyber-resilience-framework-cscrf-for-sebi-regulated-entities-res-_85964.html"),
    ]
    for num, desc, url in refs:
        story.append(P(f"<b>{num}</b> &nbsp; {desc}", "body"))
        story.append(P(url, "small"))
        story.append(Spacer(1, 4))
    story.append(Spacer(1, 10))
    story.append(info_box(
        "USE NOTE",
        "Financial figures are time-sensitive and drawn from secondary sources. Verify "
        "against the latest statutory filings and current company disclosures before final "
        "submission.", border=TAN, bg=HexColor("#F6EEE3")))

    doc.build(story)
    print(f"Written: {OUT_PDF}")


if __name__ == "__main__":
    build()
