# Security Checklist and Threat Model

**Scope:** Amrutam telemedicine backend, API clients, PostgreSQL, optional Redis, container build, CI pipeline, and external payment/notification integrations.

**Status:** This is a design and review checklist. A checked control must be verified against code/configuration and deployment evidence. It is not a certification or a claim of regulatory compliance.

## 1. Data classification

| Class | Examples | Required handling |
|---|---|---|
| Restricted clinical | prescriptions, consultation details, patient-linked records | Least-privilege access, TLS, encryption at rest, audited reads/writes, retention controls |
| Sensitive identity | email, phone, profile, auth/token data | TLS, protected storage, access control, log redaction |
| Financial/integration | payment references, webhook payloads | Verify signatures, minimize stored data, avoid storing card data, audit state changes |
| Operational | request IDs, service metrics, error metadata | Avoid personal/clinical payloads; restrict access and define retention |
| Public | public doctor specialty/profile fields approved for discovery | Validate and expose only intended fields |

## 2. Attack surface

- Public REST endpoints: malformed payloads, injection, brute force, enumeration, resource exhaustion.
- Authentication/token endpoints: credential stuffing, token theft, refresh-token replay, weak secrets.
- Patient/doctor records: broken object-level authorization (BOLA/IDOR), privilege escalation, unauthorized clinical data access.
- Booking: race conditions, replay, idempotency-key abuse, slot double booking.
- Payments/webhooks: forged callbacks, replay, duplicate settlement, amount/status tampering.
- PostgreSQL/Redis: exposed ports, overprivileged credentials, injection, data exfiltration.
- CI/container supply chain: compromised dependency, leaked secret, untrusted build artifact.
- Logs/metrics/docs: accidental PHI or secret exposure, public admin endpoints, high-cardinality labels.
- Backups: unauthorized restore/download, stale credentials, untested recovery.

## 3. STRIDE threat table

| Threat | Example | Mitigation and verification |
|---|---|---|
| Spoofing | Stolen or forged identity token | Strong token validation, short-lived access tokens, refresh-token rotation/revocation where supported, MFA for sensitive roles |
| Tampering | Modify prescription or payment status | Server-side authorization, schema validation, constrained state transitions, signed webhook verification, audit records |
| Repudiation | User denies a clinical change | Append-only or tamper-evident audit storage, actor/action/resource/time/request ID, restricted audit access |
| Information disclosure | Patient reads another patient's prescription | Object-level checks on every resource access, negative authorization tests, log redaction |
| Denial of service | Login or search flood | Rate limits, request size/time limits, bounded pagination, DB pool limits, quotas and alerts |
| Elevation of privilege | Patient calls doctor/admin operation | Role and ownership checks on server side, deny-by-default, least-privilege service/database accounts |

## 4. OWASP-aligned controls

- **Broken access control:** authorize every object access, not just route entry; test cross-patient and cross-doctor access denial.
- **Cryptographic failures:** HTTPS/TLS in production; strong managed secrets; encryption at rest for DB, disks and backups; never log tokens or clinical payloads.
- **Injection:** SQLAlchemy parameterized expressions; avoid string-built SQL; validate inputs and apply output-safe serialization.
- **Insecure design:** explicit consultation state machine, idempotent writes, bounded retries, threat review for payment and booking flows.
- **Security misconfiguration:** production debug off, restrictive CORS, non-default secrets, private DB/Redis networking, hardened container.
- **Vulnerable components:** dependency pin/review, automated dependency scanning, patch SLAs, minimal base images.
- **Authentication failures:** rate limit login, safe error messages, password hashing using a suitable password-hashing algorithm, MFA where required, revoke sessions on compromise.
- **Integrity failures:** protect CI credentials, review changes, use trusted build provenance where available, verify webhook signatures.
- **Logging/monitoring failures:** structured logs, correlation IDs, redaction, alert on repeated auth failures and privilege denials.
- **SSRF:** if URLs can be supplied to integrations, allowlist destinations and block private/link-local metadata addresses.
- **Sensitive business flows:** prevent repeated booking/payment abuse with idempotency, per-user quotas, and reconciliation.

## 5. Secrets, encryption, and key rotation

- `.env` is local-only and must remain ignored by Git. `.env.example` contains placeholders only.
- Use a managed secret store in deployed environments; do not bake secrets into images or CI artifacts.
- Use separate, high-entropy secrets per environment and purpose; never reuse development secrets in production.
- Encrypt transport with TLS. Enable managed database/storage encryption and encrypted backups.
- Rotate JWT signing keys, MFA encryption keys, webhook secrets, DB passwords, and CI tokens on a documented schedule and immediately after suspected compromise.
- Plan key versioning and a transition window so existing encrypted data/tokens can be handled safely. Test rotation before production.
- Restrict key access and log key-management actions without logging key material.

## 6. Compliance and audit

- Audit security-sensitive events: authentication changes, role changes, booking transitions, prescription issue/access where required, payment changes, admin actions.
- Record actor, action, resource type/ID, timestamp, outcome, request/correlation ID; do not include full clinical notes, credentials, or secrets in audit metadata.
- Restrict audit-log modification/deletion; export to protected storage if tamper resistance is required.
- Define purpose, lawful basis, retention/deletion, patient access/correction, breach response, and data-residency requirements with qualified privacy/legal stakeholders before handling real patient data.
- Treat demo data as synthetic. No regulatory compliance claim is made by this project.

## 7. Pre-release checklist

- [ ] Confirm `.env`, logs, tokens, database dumps, and real patient data are absent from Git history.
- [ ] Verify `.env.example` contains no working secrets.
- [ ] Verify patient A cannot access patient B's consultations/prescriptions.
- [ ] Verify one doctor cannot modify another doctor's consultations/prescriptions.
- [ ] Verify admin-only endpoints deny patient/doctor roles.
- [ ] Verify request validation, bounded pagination, and safe error responses.
- [ ] Verify booking idempotency under concurrent duplicate requests.
- [ ] Verify webhook signature, timestamp/replay protection, and duplicate delivery handling.
- [ ] Verify MFA behavior for all roles and sensitive operations; document any gaps.
- [ ] Verify rate limiting works when Redis is unavailable.
- [ ] Run dependency and container image scans; triage findings.
- [ ] Confirm TLS, database encryption, backup encryption, and secret-manager configuration in target deployment.
- [ ] Confirm logs and metrics contain no PHI, tokens, or high-cardinality sensitive labels.
- [ ] Perform restore and failover drills.
- [ ] Obtain security/privacy review before production.

## 8. Known production gates

Before describing the system as production-grade, collect evidence for MFA coverage, object-level authorization tests, rate-limit behavior, TLS and at-rest encryption in deployment, key rotation, dependency/container scans, tracing/alerting, backup restoration, load testing, and multi-zone failover. Mark a control as implemented only after verifying the code and runtime configuration.
