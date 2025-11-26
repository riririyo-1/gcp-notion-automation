variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "asia-northeast1"
}

variable "notion_api_key" {
  description = "Notion API Key"
  type        = string
  sensitive   = true
}

variable "notion_database_id" {
  description = "Notion Database ID"
  type        = string
  sensitive   = true
}

variable "openai_api_key" {
  description = "OpenAI API Key"
  type        = string
  sensitive   = true
}

variable "schedule" {
  description = "Cloud Scheduler cron schedule"
  type        = string
  default     = "0 6,10,13,24 * * *"  # 6時、10時、13時、24時
}