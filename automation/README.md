# Themis n8n Workflows

Pre-built n8n automation workflows for Themis. Import these via the n8n UI
(**Settings → Import Workflow**) after starting n8n with `docker compose up n8n -d`.

## Workflows

| File | Trigger | Purpose |
|---|---|---|
| `deadline_reminder.json` | Daily schedule | Polls `/api/v1/portfolio/obligations?days_ahead=30`, emails reminder |
| `high_risk_escalation.json` | Webhook (POST) | Receives webhook from Regulatory Monitoring Agent when risk ≥ HIGH |
| `regulatory_alert_digest.json` | Weekly (Monday 08:00) | Polls `/api/v1/regulatory-alerts`, emails formatted digest |

## Required n8n Environment Variables

Set these in n8n **Settings → Environment Variables** or via Docker env:

```
THEMIS_API_URL=http://api:8000          # Internal docker network URL
THEMIS_FRONTEND_URL=http://localhost:5173
ALERT_EMAIL=team@yourcompany.com
ESCALATION_EMAIL=legal@yourcompany.com  # For CRITICAL alerts only
```

## API Authentication

All HTTP Request nodes need a credential of type **Header Auth**:
- Name: `Authorization`
- Value: `Bearer <service-account-jwt>`

Generate a long-lived service account JWT for n8n → Themis API calls using:
```bash
python -c "
from jose import jwt
import time, os
token = jwt.encode(
    {'sub': 'n8n-service', 'tenant_id': 'platform', 'exp': time.time() + 86400*365},
    os.environ['JWT_SECRET_KEY'], algorithm='HS256'
)
print(token)
"
```

## High-Risk Escalation Webhook URL

After importing `high_risk_escalation.json`, get the webhook URL from n8n UI.
Add it to your `.env`:
```
N8N_ESCALATION_WEBHOOK_URL=http://n8n:5678/webhook/themis-high-risk-escalation
```
The Regulatory Monitoring Agent reads this env var and fires the webhook when
`impact_level >= HIGH`.
