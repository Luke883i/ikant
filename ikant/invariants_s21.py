from __future__ import annotations

from ._invariants_base import Invariant

S21_INVARIANTS=(
 Invariant('IPR-001','intent_plan_reconciliation_s21','Natural or reactive intent can influence planning only through one typed zero-authority intent reconciliation feeding the canonical ikant.planning.finalize_planning entrypoint. S15 reactive structure remains derivative work/command structure and is never a second planner.',"CRITICAL",'tests.test_intent_reconciliation_s21'),
 Invariant('IPR-002','intent_plan_reconciliation_s21','Intent reconciliation is authority-monotonic: MATCH may preserve only canonical Action Ledger candidates, while DEMOTE or BLOCK feed no candidate into planning. Reconciliation and planning never approve, grant, lease, execute or report a world mutation.',"CRITICAL",'tests.test_intent_reconciliation_s21'),
 Invariant('IPR-003','intent_plan_reconciliation_s21','Planning input revalidates current memory and temporal availability before preserving a material candidate. Forgotten, missing or unavailable governing references fail closed, and reminder intent remains governed temporal intent even when its text contains nested material language.',"CRITICAL",'tests.test_intent_reconciliation_s21'),
 Invariant('IPR-004','intent_plan_reconciliation_s21','The canonical Plan Ledger binds its source Action Ledger, planner-input digest and intent-reconciliation digest; the durable causal lifecycle binds the resulting Plan Ledger digest. Production census must prove exactly one planner and no reactive shortcut into execution or handoff.',"CRITICAL",'tests.test_intent_reconciliation_s21'),
)
