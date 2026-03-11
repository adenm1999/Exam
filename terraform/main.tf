terraform {
  required_version = ">= 1.7"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  # Remote state — update bucket name before first apply.
  backend "gcs" {
    bucket = "tfstate-du-etl"
    prefix = "du-etl"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# ── Enable required APIs ───────────────────────────────────────────────────────
resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "cloudscheduler.googleapis.com",
    "artifactregistry.googleapis.com",
    "secretmanager.googleapis.com",
  ])
  service            = each.value
  disable_on_destroy = false
}

# ── Artifact Registry ──────────────────────────────────────────────────────────
resource "google_artifact_registry_repository" "du_etl" {
  repository_id = "du-etl"
  location      = var.region
  format        = "DOCKER"
  description   = "Docker images for the DU university chapters ETL pipeline"

  depends_on = [google_project_service.apis]
}

locals {
  image_uri = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.du_etl.repository_id}/du-etl:${var.image_tag}"
}

# ── Secret Manager — store the DSN so it is never in plain env vars ────────────
resource "google_secret_manager_secret" "database_url" {
  secret_id = "du-etl-database-url"

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_version" "database_url" {
  secret      = google_secret_manager_secret.database_url.id
  secret_data = var.database_url
}

# ── Service account for Cloud Run Job ─────────────────────────────────────────
resource "google_service_account" "du_etl_runner" {
  account_id   = "du-etl-runner"
  display_name = "DU ETL Cloud Run Job SA"
}

resource "google_secret_manager_secret_iam_member" "runner_can_read_secret" {
  secret_id = google_secret_manager_secret.database_url.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.du_etl_runner.email}"
}

# ── Cloud Run Job ──────────────────────────────────────────────────────────────
resource "google_cloud_run_v2_job" "du_etl" {
  name     = "du-etl-job"
  location = var.region

  template {
    template {
      service_account = google_service_account.du_etl_runner.email

      containers {
        image = local.image_uri

        env {
          name  = "DU_API_URL"
          value = var.du_api_url
        }
        env {
          name  = "TARGET_STATE"
          value = var.target_state
        }
        env {
          name  = "LOG_LEVEL"
          value = "INFO"
        }
        # DATABASE_URL pulled from Secret Manager at runtime
        env {
          name = "DATABASE_URL"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.database_url.secret_id
              version = "latest"
            }
          }
        }

        resources {
          limits = {
            cpu    = "1"
            memory = "512Mi"
          }
        }
      }

      max_retries = 2
      timeout     = "300s"
    }
  }

  depends_on = [
    google_project_service.apis,
    google_artifact_registry_repository.du_etl,
    google_secret_manager_secret_version.database_url,
  ]
}

# ── Service account for Cloud Scheduler ───────────────────────────────────────
resource "google_service_account" "scheduler_invoker" {
  account_id   = "du-etl-scheduler"
  display_name = "DU ETL Cloud Scheduler invoker SA"
}

resource "google_cloud_run_v2_job_iam_member" "scheduler_can_run_job" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_job.du_etl.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.scheduler_invoker.email}"
}

# ── Cloud Scheduler — daily trigger ───────────────────────────────────────────
resource "google_cloud_scheduler_job" "du_etl_daily" {
  name      = "du-etl-daily"
  region    = var.region
  schedule  = var.schedule
  time_zone = "UTC"

  http_target {
    http_method = "POST"
    uri         = "https://${var.region}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${var.project_id}/jobs/${google_cloud_run_v2_job.du_etl.name}:run"

    oauth_token {
      service_account_email = google_service_account.scheduler_invoker.email
    }
  }

  depends_on = [google_project_service.apis]
}
