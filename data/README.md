# Synthetic Workflow Scenario Dataset

This folder contains a small synthetic benchmark for the ICPM 2027 draft.

The dataset is intentionally stored as a single JSON file rather than separate
documents. Each scenario contains:

- `initial_description`: an underspecified first description that simulates what
  a domain expert might say at the beginning of an interview.
- `reference_workflow`: a more complete workflow used as the evaluation target.
- `intentionally_missing_in_initial_description`: fields that the elicitation
  method should ideally recover through clarification questions.

The current dataset has eight scenarios:

1. Verification Test Setup and Reporting
2. Equipment-Specific Measurement Workflow
3. Wafer Sample Transfer and Disposal Request
4. Defect Issue Triage and Risk Reporting
5. Specification Document Review
6. Vendor Meeting and Improvement Action Follow-up
7. Meeting Summary and Email Reporting
8. Meeting Room Reservation

The scenarios are grouped into three representative workflow types:

- Engineering execution workflows: S01-S03 cover verification, equipment-
  dependent measurement, and sample logistics. These tasks involve technical
  inputs, tools or systems, result artifacts, validity checks, approvals, and
  exception handling.
- Coordination and issue-resolution workflows: S04 and S06 cover defect triage
  and vendor follow-up. These tasks involve multiple roles, handoffs, ownership
  assignment, decisions, due dates, and action-item tracking.
- Document and administrative knowledge-work workflows: S05, S07, and S08 cover
  specification review, meeting summary reporting, and meeting room
  reservation. These tasks involve source documents, recipient lists, review or
  approval criteria, confidentiality checks, capacity constraints, and system
  updates.

For each scenario, the `initial_description` intentionally states only the
high-level task and leaves out information that would normally be elicited in a
follow-up interview. The missing fields were chosen from process-analysis and
automation-design categories: actors, systems, inputs, outputs, decisions,
exceptions, dependencies, and automation opportunity targets.

The scenarios are synthetic and written in generic terms. They do not contain
confidential company data, internal system names, product information,
equipment identifiers, logs, metrics, or personally identifiable information.
