# Talent Agency Automation Backend

FastAPI service for operational automation of a talent agency. It receives webhooks from Pipedrive and executes business logic that n8n cannot handle adequately. Runs alongside n8n on the same server.

## What it does

- **M1 – Lead Enrichment**: Adds talent tags, extracts Mexican phone numbers from notes, and detects duplicate contacts.
- **M2 – Pipedrive → Trello Sync**: When a deal reaches the "Contrato y factura" stage, creates cards in the talent's individual Trello board, "Admin TA", and "TA Campañas".
- **M3 – Contract Generation** *(coming soon)*: Generates `.docx` contracts using Claude API to extract fiscal data from the CSF attached to the Trello card.

## Prerequisites

- Python 3.11+
- Access to the server where n8n is running (for deployment)
- Pipedrive API token
- Trello API key and token
- Anthropic API key (for M3)

## Installation

```bash
git clone <repo-url>
cd talent-agency-backend

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your actual credentials
```

## Running in development

```bash
uvicorn app.main:app --reload --port 8001
```

The API will be available at `http://localhost:8001`.  
Interactive docs: `http://localhost:8001/docs`

## Running in production alongside n8n

### Option A – Docker

```bash
# Build the image
docker build -t talent-agency-backend .

# Run the container (n8n typically runs on port 5678)
docker run -d \
  --name talent-agency-backend \
  --env-file .env \
  -p 8001:8001 \
  --restart unless-stopped \
  talent-agency-backend
```

### Option B – systemd service

Create `/etc/systemd/system/talent-agency.service`:

```ini
[Unit]
Description=Talent Agency Automation Backend
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/talent-agency-backend
EnvironmentFile=/path/to/talent-agency-backend/.env
ExecStart=/path/to/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8001
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable talent-agency
sudo systemctl start talent-agency
sudo systemctl status talent-agency
```

## Available endpoints

### Health check
```bash
curl http://localhost:8001/
# {"status":"ok","service":"talent-agency-automation","version":"1.0.0"}
```

### Manual endpoints

```bash
# Enrich a lead manually
curl -X POST http://localhost:8001/manual/enrich-lead/12345

# Sync a deal to Trello manually
curl -X POST http://localhost:8001/manual/sync-to-trello/12345

# Check service status and configuration
curl http://localhost:8001/manual/status
```

### Webhook endpoint

```bash
# Pipedrive sends payloads here automatically
POST http://your-server:8001/webhooks/pipedrive
```

## Configuring the Pipedrive webhook

1. In Pipedrive, go to **Settings → Webhooks → Add webhook**.
2. Set the **Event action** to `*` (all events) or at minimum `updated.deal` and `added.deal`.
3. Set the **Event object** to `deal` (and optionally `person`).
4. Set the **Endpoint URL** to `http://your-server-ip:8001/webhooks/pipedrive`.
5. Leave HTTP auth empty (unless you set `WEBHOOK_SECRET` and add validation).
6. Save. Pipedrive will send a test request — the service should respond with `{"received": true}`.

## Running tests

```bash
pytest tests/ -v
```
