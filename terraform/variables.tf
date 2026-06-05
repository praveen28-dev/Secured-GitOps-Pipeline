# ============================================================
# Container Security Falcon — Terraform Variables
# ============================================================

variable "region" {
  description = "OCI region (e.g., us-ashburn-1, eu-frankfurt-1)"
  type        = string
  default     = "us-ashburn-1"
}

variable "compartment_id" {
  description = "OCI compartment OCID"
  type        = string
}

variable "instance_shape" {
  description = "Compute instance shape (Always Free: VM.Standard.A1.Flex)"
  type        = string
  default     = "VM.Standard.A1.Flex"
}

variable "instance_ocpus" {
  description = "Number of OCPUs (Always Free allows up to 4 total)"
  type        = number
  default     = 1
}

variable "instance_memory_gb" {
  description = "Memory in GB (Always Free allows up to 24GB total)"
  type        = number
  default     = 6
}

variable "ssh_public_key" {
  description = "SSH public key for instance access"
  type        = string
}

variable "ssh_allowed_cidr" {
  description = "CIDR block allowed for SSH access (restrict to your IP)"
  type        = string
  default     = "0.0.0.0/0"
}

variable "github_user" {
  description = "GitHub username for pulling images from GHCR"
  type        = string
  default     = ""
}

variable "github_token" {
  description = "GitHub Personal Access Token for GHCR (read:packages scope)"
  type        = string
  sensitive   = true
  default     = ""
}
