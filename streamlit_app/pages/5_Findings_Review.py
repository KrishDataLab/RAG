import streamlit as st
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from app.db.repositories import DatabaseRepository, SessionLocal
from app.comparison.findings import FindingsManager

st.set_page_config(page_title="Findings Review - AHITA", page_icon="🛡️", layout="wide")

st.title("🛡️ Human Review & Governance Workflow")
st.markdown("Human-in-the-Loop review dashboard for AUTOSAR architects to inspect, confirm, or dismiss flagged inconsistencies with complete audit trails.")

db = SessionLocal()
repo = DatabaseRepository(db)
manager = FindingsManager(repo)

status_filter = st.selectbox("Filter Status", ["ALL", "NEEDS_REVIEW", "CONFIRMED", "FALSE_POSITIVE"])
st_val = None if status_filter == "ALL" else status_filter

findings = manager.list_findings(project_id="P001", status=st_val)

if not findings:
    st.info("No findings matching the selected filter.")
else:
    for f in findings:
        st.markdown(f"""
        <div style="background: rgba(30, 41, 59, 0.7); border-left: 4px solid {'#EF4444' if f['severity']=='HIGH' else '#F59E0B'}; border-radius: 8px; padding: 15px; margin-bottom: 15px;">
            <span style="font-size: 12px; font-weight: bold; background: #334155; padding: 3px 8px; border-radius: 4px;">{f['status']}</span>
            <span style="font-size: 12px; font-weight: bold; background: #991B1B; padding: 3px 8px; border-radius: 4px; margin-left: 10px;">{f['severity']}</span>
            <h4 style="margin-top: 10px; color: #F8FAFC;">{f['summary']}</h4>
            <p style="color: #94A3B8; font-size: 14px;">Finding ID: <code>{f['id']}</code> | Type: <code>{f['type']}</code></p>
        </div>
        """, unsafe_allow_html=True)

        with st.expander(f"Review Details & Evidence for {f['id']}"):
            st.write("**Description:**")
            st.write(f['description'])

            st.write("**Document Evidence:**")
            for ev in f.get("evidences", []):
                st.write(f"• Document: `{ev['document_id']}` | Page: `{ev['page_number']}` | Claim: *{ev['claim_text']}*")

            if f.get("reviews"):
                st.write("**Previous Review Logs:**")
                for r in f["reviews"]:
                    st.write(f"• `{r['reviewer_id']}` changed status from `{r['old_status']}` ➔ `{r['new_status']}`. Comment: *{r['comment']}* ({r['created_at'][:16]})")

            st.markdown("---")
            st.write("**Submit Architect Review Decision:**")
            r_col1, r_col2 = st.columns([1, 2])
            with r_col1:
                new_st = st.selectbox("New Decision", ["CONFIRMED", "FALSE_POSITIVE", "NEEDS_REVIEW"], key=f"sel_{f['id']}")
                reviewer_id = st.text_input("Reviewer ID / Name", value="Lead_AUTOSAR_Architect", key=f"rev_{f['id']}")
            with r_col2:
                comment = st.text_area("Architect Rationale / Comment", key=f"txt_{f['id']}")
                if st.button("Save Review Decision", key=f"btn_{f['id']}"):
                    manager.review(finding_id=f['id'], reviewer_id=reviewer_id, new_status=new_st, comment=comment)
                    st.success("Decision recorded in audit log!")
                    st.rerun()

st.markdown("---")
st.subheader("📜 Audit Log Trail")
logs = repo.get_audit_logs("P001")
if logs:
    log_table = [
        {
            "Timestamp": l.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "User": l.user_id,
            "Action": l.action,
            "Resource": f"{l.resource_type} ({l.resource_id})",
            "Metadata": l.metadata_json
        } for l in logs[:15]
    ]
    st.dataframe(log_table, use_container_width=True)
