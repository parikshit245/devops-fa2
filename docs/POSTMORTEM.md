# Post-mortem: <short title, e.g. "PulseOps API unavailable - database outage">

> Blameless: we describe what the **system and process** allowed to happen, not who made a mistake.

| | |
|---|---|
| **Date** | YYYY-MM-DD |
| **Authors** | |
| **Status** | Draft / Reviewed / Action items complete |
| **Severity** | SEV-1 (full outage) / SEV-2 (partial) / SEV-3 (degraded) |
| **Duration** | detection → resolution, e.g. 19:34:42 → 19:37:49 IST (3 min 7 s) |
| **SLO impact** | e.g. availability SLI dropped to 87 % for 5 min; ~X % of the 30-day error budget consumed |

## Summary
Two or three sentences: what broke, what users saw, how it was fixed.

## Impact
- Users affected / requests failed (Grafana → "Responses by status code", "Errors: 5xx ratio")
- Features affected (login, service checks, dashboards ...)
- Error budget burned (Grafana → "Error budget remaining" before vs after)

## Timeline (IST)
| Time | Event |
|---|---|
| 19:34:42 | Trigger: PostgreSQL deployment scaled to 0 (incident drill / root cause) |
| 19:35:xx | `PulseOpsDatabaseUnhealthy` pending → firing (Prometheus /alerts) |
| 19:35:xx | Backend pod NotReady; Traefik stops routing to it; 5xx/503 seen by users |
| 19:37:43 | Mitigation: PostgreSQL scaled back to 1 |
| 19:37:49 | Recovered: readiness OK, alerts resolved |

## Root cause
The underlying technical cause. Use the "5 whys".

## Detection
How we found out (which alert, how fast). Did monitoring catch it before users did?

## Resolution and recovery
What was done to mitigate, and why it worked.

## What went well / what went badly / where we got lucky
- 
- 

## Action items
| Action | Type (prevent / detect / mitigate) | Owner | Due |
|---|---|---|---|
| e.g. Add Alertmanager → email so alerts page someone | detect | | |
| e.g. Move PostgreSQL to a managed DB (RDS) with automated backups | prevent | | |

## Evidence
Screenshots: Grafana SRE Overview during the incident, Prometheus /alerts, `kubectl get pods` output.
