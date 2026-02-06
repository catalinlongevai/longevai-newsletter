from datetime import datetime

from jinja2 import Template
from sqlalchemy.orm import Session

from app.models.entities import BundleStatus, Document, DocumentStatus, EditorStatus, Insight, PublishBundle
from app.state_machine.document_status import enforce_transition

EMAIL_TEMPLATE = """
<h1>LongevAI Weekly Brief</h1>
{% for item in items %}
<section>
  <h2>{{ item.wow_factor }}</h2>
  <div>{{ item.summary_markdown }}</div>
  <p><strong>Confidence:</strong> {{ item.confidence_label }}</p>
</section>
{% endfor %}
""".strip()


def build_bundle(
    db: Session, period_start: datetime, period_end: datetime, insight_ids: list[int] | None = None
) -> PublishBundle:
    query = (
        db.query(Insight)
        .join(Document, Document.id == Insight.document_id)
        .filter(Insight.editor_status == EditorStatus.approved)
        .filter(Insight.created_at >= period_start, Insight.created_at <= period_end)
        .order_by(Insight.novelty_score.desc())
    )
    if insight_ids:
        query = query.filter(Insight.id.in_(insight_ids))
    items = query.all()
    html = Template(EMAIL_TEMPLATE).render(items=items)
    linkedin_lines = ["LongevAI Weekly Highlights"]
    for item in items:
        linkedin_lines.append(f"- {item.wow_factor}")
    linkedin = "\n".join(linkedin_lines)

    bundle = PublishBundle(
        period_start=period_start,
        period_end=period_end,
        beehiiv_html=html,
        linkedin_text=linkedin,
        status=BundleStatus.draft,
    )
    db.add(bundle)
    db.flush()

    for item in items:
        doc = db.query(Document).filter(Document.id == item.document_id).one()
        if doc.status == DocumentStatus.approved:
            enforce_transition(doc.status, DocumentStatus.bundled)
            doc.status = DocumentStatus.bundled
    return bundle
