"""Generate labeled sample PDFs only. Never uploads or approves production documents."""

from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak

LIBRARY = [
    (
        "Corporate_Tax_Review_Checklist_DEMO.pdf",
        "Corporate Tax",
        "Corporate Tax review checklist",
        [
            (
                "1. REVIEW WORKFLOW",
                "For a fictional Corporate Tax review, obtain the trial balance, financial statements, fixed asset register and prior review notes. Reconcile accounting profit to the supporting ledgers. Record unresolved questions for professional review.",
            ),
            (
                "2. DOCUMENT REQUEST CHECKLIST",
                "Request entity registration records, ownership structure, contracts, related-party schedules, revenue analysis and expense support. This checklist does not prescribe statutory filing obligations or eligibility rules.",
            ),
            (
                "3. ILLUSTRATIVE FINANCIAL INFORMATION",
                "Fictional example: Demo Trading records AED 100,000 of revenue and AED 60,000 of supported operating expenses. These numbers illustrate a reconciliation workflow, not a tax calculation or legal conclusion.",
            ),
            (
                "4. FICTIONAL REVIEW OBSERVATIONS",
                "The reviewer noted missing supplier support and an unreconciled related-party balance. Request evidence, document the response and escalate unresolved matters. No actual client information is included.",
            ),
        ],
    ),
    (
        "VAT_Review_Checklist_DEMO.pdf",
        "VAT",
        "VAT review checklist",
        [
            (
                "1. VAT RETURN REVIEW WORKFLOW",
                "For a fictional VAT review, obtain the sales and purchase ledgers, invoice samples, credit notes and reconciliation workbook. Compare the proposed return totals to the underlying ledgers. Record unexplained differences.",
            ),
            (
                "2. INVOICE VALIDATION CHECKLIST",
                "Check that invoice samples identify the supplier, customer, transaction description, invoice date, reference and relevant supporting amounts. Obtain missing support. This is a demonstration checklist, not a statement of mandatory UAE invoice requirements.",
            ),
            (
                "3. INPUT AND OUTPUT RECONCILIATION",
                "Reconcile sales ledger totals to output tax working papers and purchase ledger totals to input tax working papers. Investigate duplicate entries, unmatched credit notes and timing differences. Do not infer recovery entitlement from this checklist.",
            ),
            (
                "4. FICTIONAL TRANSACTION EXAMPLES",
                "Fictional example: an invoice for AED 10,000 appears twice in a draft purchase reconciliation. The reviewer flags the duplicate and requests the original invoice and payment record. No statutory VAT rate or legal treatment is asserted.",
            ),
        ],
    ),
    (
        "Audit_TP_Evidence_Checklist_DEMO.pdf",
        "Transfer Pricing",
        "Audit and transfer pricing evidence checklist",
        [
            (
                "1. AUDIT EVIDENCE CHECKLIST",
                "For a fictional revenue review, inspect selected contracts, invoices, delivery records, credit notes and subsequent receipts. Reconcile the selected items to the ledger. Assess reliability and explain unresolved exceptions.",
            ),
            (
                "2. RELATED PARTY DOCUMENTATION",
                "Obtain a fictional group structure, related-party transaction schedule, intercompany agreements, management explanations and transaction reconciliations. Identify missing records and inconsistent descriptions.",
            ),
            (
                "3. TRANSFER PRICING EVIDENCE CHECKLIST",
                "Document the functions performed, assets used and risks described in the available records. Request support for the selection of a pricing approach and relevant comparisons. The checklist does not establish arm's length compliance or a statutory documentation threshold.",
            ),
            (
                "4. FICTIONAL SUPPORTING EXAMPLES",
                "Fictional example: Demo Services has an intercompany management service agreement but no supporting activity schedule. The reviewer requests evidence of services, allocation workings and the basis for charges. No actual client data or legal conclusion is included.",
            ),
        ],
    ),
]


def generate(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="DSBTitle",
            fontName="Helvetica-Bold",
            fontSize=25,
            leading=31,
            textColor=colors.HexColor("#171337"),
            spaceAfter=18,
        )
    )
    styles.add(
        ParagraphStyle(
            name="DSBSection",
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=17,
            textColor=colors.HexColor("#7132F5"),
            spaceBefore=18,
            spaceAfter=9,
        )
    )
    styles["BodyText"].leading = 18
    styles["BodyText"].fontSize = 11

    def page(canvas, doc):
        canvas.setFillColor(colors.HexColor("#171337"))
        canvas.rect(0, 798, 595, 44, fill=1, stroke=0)
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 10)
        canvas.drawCentredString(297, 815, "DEMONSTRATION ONLY — NOT UAE LAW")
        canvas.setFillColor(colors.HexColor("#827c90"))
        canvas.setFont("Helvetica", 9)
        canvas.drawString(48, 28, "DSBCA | Fictional professional learning material")
        canvas.drawRightString(547, 28, f"PDF page {doc.page}")

    paths = []
    for filename, subject, title, sections in LIBRARY:
        path = output / filename
        story = [
            Paragraph("DSBCA / DEMO LIBRARY", styles["DSBSection"]),
            Paragraph(title, styles["DSBTitle"]),
            Paragraph(
                "Fictional examples for testing evidence retrieval and citations. Not legal advice, legislation, official guidance or verified professional standards.",
                styles["BodyText"],
            ),
        ]
        for i, (heading, text) in enumerate(sections):
            if i == 2:
                story += [
                    PageBreak(),
                    Paragraph(title + " / continued", styles["DSBTitle"]),
                ]
            story += [
                Paragraph(heading, styles["DSBSection"]),
                Paragraph(text, styles["BodyText"]),
                Spacer(1, 12),
            ]
        SimpleDocTemplate(
            str(path),
            pagesize=(595, 842),
            rightMargin=48,
            leftMargin=48,
            topMargin=68,
            bottomMargin=52,
        ).build(story, onFirstPage=page, onLaterPages=page)
        paths.append(path)
    return paths


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[3]
    for path in generate(root / "output/pdf"):
        print(path.name)
