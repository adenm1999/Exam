output "artifact_registry_repo" {
  description = "Full Artifact Registry repository path"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.du_etl.repository_id}"
}

output "cloud_run_job_name" {
  description = "Cloud Run Job name (use with: gcloud run jobs execute)"
  value       = google_cloud_run_v2_job.du_etl.name
}

output "scheduler_job_name" {
  description = "Cloud Scheduler job name"
  value       = google_cloud_scheduler_job.du_etl_daily.name
}
