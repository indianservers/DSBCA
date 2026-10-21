"""Explicit, repeatable demonstration content. Never creates accounts or schemas."""

import argparse
from datetime import timedelta
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.database import engine
from app.models import (
    SubjectCategory,
    Video,
    Publication,
    PublicationChapter,
    Article,
    RegulatoryUpdate,
    Webinar,
    Notification,
    NotificationRecipient,
    User,
    Company,
    CompanyDocument,
    CompanyPerson,
    CompanyReminder,
    now,
)


def seed(db, user_email=None):
    categories = {}
    for name in ["Corporate Tax", "VAT", "Transfer Pricing", "IFRS", "Pillar Two"]:
        row = db.scalar(select(SubjectCategory).where(SubjectCategory.name == name))
        if not row:
            row = SubjectCategory(name=name)
            db.add(row)
            db.flush()
        categories[name] = row.id
    titles = [
        "QFZP: the conditions, end to end",
        "From accounting profit to taxable income",
        "Filing the CT return on EmaraTax",
        "Small Business Relief: who can elect",
        "Transfer pricing fundamentals",
    ]
    body = "Demonstration content for interface evaluation. No legislative reference is asserted as verified. Replace with professionally reviewed content before publication to clients."
    for i, title in enumerate(titles):
        if not db.scalar(
            select(Video.id).where(Video.title == title, Video.demo.is_(True))
        ):
            db.add(
                Video(
                    title=title,
                    body=body,
                    demo=True,
                    status="published",
                    category_id=categories["Corporate Tax"],
                    duration_seconds=[1330, 1120, 1505, 570, 960][i],
                )
            )
    for model, entries in [
        (
            Publication,
            [
                ("UAE Corporate Tax, chapter by chapter", "Corporate Tax"),
                ("IFRS professional reference", "IFRS"),
            ],
        ),
        (
            Article,
            [
                ("Small Business Relief after 2026: what comes next", "Corporate Tax"),
                ("When a free zone company loses QFZP status", "Corporate Tax"),
            ],
        ),
        (
            RegulatoryUpdate,
            [
                ("E-invoicing preparation checklist", "VAT"),
                ("Transfer pricing documentation review", "Transfer Pricing"),
            ],
        ),
        (
            Webinar,
            [
                ("UAE DMTT: an introductory workshop", "Pillar Two"),
                ("IFRS reporting clinic", "IFRS"),
            ],
        ),
    ]:
        for title, category in entries:
            if not db.scalar(
                select(model.id).where(model.title == title, model.demo.is_(True))
            ):
                db.add(
                    model(
                        title=title,
                        body=body,
                        category_id=categories[category],
                        status="published",
                        demo=True,
                    )
                )
    db.flush()
    publication = db.scalar(
        select(Publication).where(
            Publication.title == "UAE Corporate Tax, chapter by chapter",
            Publication.demo.is_(True),
        )
    )
    for position, title in enumerate(
        [
            "Who is a taxable person",
            "Free zone persons and QFZP",
            "From accounting profit to taxable income",
        ],
        1,
    ):
        if not db.scalar(
            select(PublicationChapter.id).where(
                PublicationChapter.publication_id == publication.id,
                PublicationChapter.position == position,
            )
        ):
            db.add(
                PublicationChapter(
                    publication_id=publication.id,
                    title=title,
                    position=position,
                    pages=12 + 4 * position,
                )
            )
    if user_email:
        user = db.scalar(select(User).where(User.email == user_email.lower()))
        if not user:
            raise ValueError("Register the demo user before seeding private records")
        company = db.scalar(
            select(Company).where(
                Company.owner_id == user.id, Company.name == "Demonstration Trading LLC"
            )
        )
        if not company:
            company = Company(owner_id=user.id, name="Demonstration Trading LLC")
            db.add(company)
            db.flush()
            db.add(
                CompanyPerson(
                    company_id=company.id, name="Demo Partner", role="partner"
                )
            )
            for i, category in enumerate(
                [
                    "Trade Licence",
                    "Passport",
                    "Tenancy Contract",
                    "Emirates ID",
                    "Residence Visa",
                ]
            ):
                doc = CompanyDocument(
                    company_id=company.id,
                    category=category,
                    title=category,
                    expires_on=(
                        now() + timedelta(days=[18, 45, 64, 180, 210][i])
                    ).date(),
                )
                db.add(doc)
                db.flush()
                db.add(
                    CompanyReminder(
                        company_id=company.id,
                        document_id=doc.id,
                        title="Renew " + category,
                        due_on=doc.expires_on - timedelta(days=7),
                    )
                )
        for category, title, days in [
            ("Expiry", "Trade licence expires soon", 18),
            ("Deadline", "Review your upcoming return", 10),
            ("Webinar", "UAE DMTT introduction", 1),
            ("New video", titles[0], 0),
        ]:
            notification = db.scalar(
                select(Notification).where(
                    Notification.title == title, Notification.demo.is_(True)
                )
            )
            if not notification:
                notification = Notification(
                    title=title,
                    body="Demonstration notification. Review your actual records.",
                    category=category,
                    status="published",
                    demo=True,
                    deep_link="/reminders" if category == "Expiry" else "/updates",
                )
                db.add(notification)
                db.flush()
            if not db.scalar(
                select(NotificationRecipient.id).where(
                    NotificationRecipient.user_id == user.id,
                    NotificationRecipient.notification_id == notification.id,
                )
            ):
                db.add(
                    NotificationRecipient(
                        user_id=user.id, notification_id=notification.id
                    )
                )
    db.commit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-email")
    args = parser.parse_args()
    with Session(engine()) as session:
        seed(session, args.user_email)
    print("Demonstration content seeded. No accounts or media URLs fabricated.")
