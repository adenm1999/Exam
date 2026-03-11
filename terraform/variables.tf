variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region for all resources"
  type        = string
  default     = "europe-west2"
}

variable "image_tag" {
  description = "Docker image tag to deploy (git SHA set by CI/CD)"
  type        = string
  default     = "latest"
}

variable "database_url" {
  description = "PostgreSQL connection string for the Cloud SQL instance"
  type        = string
  sensitive   = true
}

variable "du_api_url" {
  description = "DU ArcGIS FeatureServer query URL"
  type        = string
}

variable "target_state" {
  description = "Two-letter state abbreviation to filter chapters by"
  type        = string
  default     = "CA"
}

variable "schedule" {
  description = "Cron schedule for the Cloud Scheduler job (UTC)"
  type        = string
  default     = "0 6 * * *"  # 06:00 UTC daily
}
