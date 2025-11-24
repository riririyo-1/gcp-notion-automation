terraform {
  backend "gcs" {
    bucket = "gcp-notion-automation-terraform-state"
    prefix = "terraform/state"
  }
}