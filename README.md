# DU University Chapters ETL

An end-to-end ETL pipeline that extracts Ducks Unlimited university chapter data from the [DU ArcGIS FeatureServer API](https://gis.ducks.org/datasets/du-university-chapters/api), filters to California (`CA`), and loads the results into a PostgreSQL table. The pipeline is containerised with Docker, deployed to **GCP Cloud Run** on a daily schedule, and shipped via a GitHub Actions CI/CD pipeline using Terraform.

---

## Architecture

```
┌─────────────────────────────┐
│  DU ArcGIS FeatureServer    │  ← Public REST API (GeoJSON)
│  gis.ducks.org              │
└────────────┬────────────────┘
             │ HTTP GET (paginated)
             ▼
┌─────────────────────────────┐
│  Extract  (etl/extract.py)  │  Fetches all chapters with pagination
│  Transform (etl/transform.py)│  Filters to CA, maps + validates fields
│  Load     (etl/load.py)     │  Upserts to Postgres (idempotent)
└────────────┬────────────────┘
             │ psycopg2 (UPSERT)
             ▼
┌─────────────────────────────┐
│  PostgreSQL  du_chapters    │
│  (Docker locally /          │
│   Cloud SQL in production)  │
└─────────────────────────────┘

Deployment:
  GitHub Actions → Docker image → Artifact Registry
  Terraform → Cloud Run Job + Cloud Scheduler (daily 06:00 UTC)
```

---

## Project Structure

```
du-etl/
├── etl/
│   ├── __init__.py
│   ├── extract.py      # API fetch with pagination
│   ├── transform.py    # Filter CA, map + validate fields
│   ├── load.py         # Postgres upsert via psycopg2
│   └── pipeline.py     # Orchestration entrypoint
├── tests/
│   ├── test_extract.py
│   ├── test_transform.py
│   └── test_load.py
├── sql/
│   └── init.sql        # Table DDL (auto-run by Docker Postgres)
├── terraform/
│   ├── main.tf         # GCP resources (Artifact Registry, Cloud Run, Scheduler)
│   ├── variables.tf
│   ├── outputs.tf
│   └── terraform.tfvars.example
├── .github/
│   └── workflows/
│       └── deploy.yml  # CI/CD: test → build → push → terraform apply
├── Dockerfile
├── docker-compose.yml  # Local dev/test
├── requirements.txt
└── .env.example
```

---

## Prerequisites

| Tool | Version | Purpose |
|---|---|---|
| Python | 3.12+ | Local development |
| Docker & Docker Compose | 24+ | Local end-to-end run |
| Terraform | 1.6+ | Cloud deployment |
| GCP account | — | Cloud Run, Artifact Registry, Cloud Scheduler |
| `gcloud` CLI | — | Auth + Docker config |

---

## Local Setup

### 1. Clone and configure environment

```bash
git clone https://github.com/your-org/du-etl.git
cd du-etl
cp .env.example .env
```

Open `.env` and set `DU_API_URL` to the ArcGIS FeatureServer query endpoint. Find it by visiting:

```
https://gis.ducks.org/datasets/du-university-chapters/api
```

Look for the **Query URL** in the API Explorer — it will look like:

```
https://services.arcgis.com/<org_id>/arcgis/rest/services/DU_University_Chapters/FeatureServer/0/query
```

### 2. Run locally with Docker Compose

```bash
docker compose up --build
```

This will:
1. Start a Postgres 16 container and run `sql/init.sql` to create the `du_chapters` table
2. Build the ETL image and run the pipeline against the live API
3. Exit once all CA chapters are loaded

To inspect the results:

```bash
docker exec -it du_etl_db psql -U du_user -d du_etl -c "SELECT * FROM du_chapters LIMIT 10;"
```

### 3. Run the pipeline directly (without Docker)

```bash
pip install -r requirements.txt

# Ensure Postgres is running locally (or use the Docker db service with port 5432 exposed)
export $(cat .env | xargs)

python -m etl.pipeline
```

---

## Running Tests

```bash
pip install -r requirements.txt
pytest tests/ -v --cov=etl --cov-report=term-missing
```

All tests are unit tests with mocked dependencies — no database or network connection required.

Expected output: **24 tests passing**, ≥80% coverage on business logic modules.

---

## Database Schema

```sql
CREATE TABLE du_chapters (
    chapter_id   TEXT        PRIMARY KEY,
    chapter_name TEXT        NOT NULL,
    city         TEXT,
    state        TEXT        NOT NULL,
    coordinates  JSONB,                    -- {"latitude": float, "longitude": float}
    loaded_at    TIMESTAMPTZ DEFAULT NOW()
);
```

The pipeline uses `INSERT ... ON CONFLICT (chapter_id) DO UPDATE` — re-runs are fully idempotent.

---

## Cloud Deployment (GCP)

### One-time setup

```bash
# Authenticate
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Enable required APIs
gcloud services enable \
  run.googleapis.com \
  cloudscheduler.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com

# Create a service account for Terraform with appropriate roles
# (or use an existing one with Owner / Editor permissions for initial setup)
```

### Deploy with Terraform

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your project_id, du_api_url, database_url

terraform init
terraform plan -var-file=terraform.tfvars
terraform apply -var-file=terraform.tfvars
```

Terraform provisions:

| Resource | Purpose |
|---|---|
| Artifact Registry repo | Stores Docker images |
| Cloud Run Job | Runs the ETL container |
| Cloud Scheduler Job | Triggers ETL daily at 06:00 UTC |
| Service Account | Least-privilege runner identity |
| Secret Manager secret | Stores `DATABASE_URL` securely |

### Run the job manually

```bash
gcloud run jobs execute du-etl-job --region=europe-west2
```

---

## CI/CD Pipeline

Push to `main` triggers the GitHub Actions workflow (`.github/workflows/deploy.yml`):

```
Push to main
  └─► test          pytest, --cov-fail-under=80
  └─► build-and-push  Docker image → Artifact Registry (tagged with git SHA)
  └─► terraform       terraform apply (updates Cloud Run Job with new image tag)
```

Pull requests run `test` only — no deployment.

### Required GitHub Secrets

| Secret | Value |
|---|---|
| `GCP_PROJECT_ID` | Your GCP project ID |
| `GCP_SA_KEY` | JSON key for a GCP service account |
| `TF_DU_API_URL` | DU FeatureServer query URL |
| `TF_DATABASE_URL` | PostgreSQL DSN for Cloud SQL |

The GCP service account needs these roles:
- `Artifact Registry Writer`
- `Cloud Run Developer`
- `Cloud Scheduler Admin`
- `Secret Manager Admin`
- `Service Account User`

---

## Configuration Reference

All configuration is via environment variables:

| Variable | Required | Default | Description |
|---|---|---|---|
| `DU_API_URL` | ✅ | — | ArcGIS FeatureServer query endpoint |
| `DATABASE_URL` | ✅ | — | PostgreSQL DSN |
| `TARGET_STATE` | ❌ | `CA` | Two-letter state code to filter on |
| `LOG_LEVEL` | ❌ | `INFO` | Python logging level |

---

## Design Decisions

**Why GCP Cloud Run Jobs?** — Cloud Run Jobs are purpose-built for short-lived batch workloads: pay per execution, no idle cost, scales to zero. Given existing familiarity with the GCP stack (BigQuery, Cloud Run), this was the most natural fit.

**Why psycopg2 over an ORM?** — The schema is a single table with a simple upsert. An ORM would add abstraction without benefit here; psycopg2 keeps dependencies minimal and the intent clear.

**Why JSONB for coordinates?** — Avoids a PostGIS dependency while still allowing JSON operators for querying. Coordinates can be promoted to a geometry column later if spatial queries are needed.

**Why paginate the API?** — ArcGIS FeatureServer services enforce a `maxRecordCount` (often 1,000–2,000). Pagination via `resultOffset` ensures the pipeline is robust regardless of dataset size.

**Why `ON CONFLICT DO UPDATE`?** — Makes the pipeline idempotent. The daily scheduler can re-run without creating duplicate rows, and will naturally pick up any chapter name or location changes.

---

## Troubleshooting

**Pipeline exits with `Required environment variable 'DU_API_URL' is not set`**
→ Ensure `.env` is populated and loaded, or that the env var is set in your shell.

**`psycopg2.OperationalError: Connection refused`**
→ Check that the `db` Docker service is healthy: `docker compose ps`. Wait a few seconds for Postgres to initialise.

**Terraform: `Error creating Cloud Run Job: googleapi: Error 403`**
→ The service account lacks required IAM roles. Check the GCP IAM console.

**No rows loaded, but pipeline reports success**
→ The API may have changed field names. Run `python -c "from etl.extract import fetch_chapters; import os; print(fetch_chapters(os.environ['DU_API_URL'])[0])"` and compare property keys against `etl/transform.py::FIELD_MAP`.
