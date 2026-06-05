# ============================================================
# Container Security Falcon — Terraform Outputs
# ============================================================

output "instance_public_ip" {
  description = "Public IP address of the Falcon server"
  value       = oci_core_instance.falcon_instance.public_ip
}

output "instance_id" {
  description = "OCID of the compute instance"
  value       = oci_core_instance.falcon_instance.id
}

output "ssh_command" {
  description = "SSH command to connect to the instance"
  value       = "ssh ubuntu@${oci_core_instance.falcon_instance.public_ip}"
}

output "app_url" {
  description = "Application URL"
  value       = "http://${oci_core_instance.falcon_instance.public_ip}"
}

output "grafana_url" {
  description = "Grafana dashboard URL"
  value       = "http://${oci_core_instance.falcon_instance.public_ip}:3000"
}

output "vcn_id" {
  description = "VCN OCID"
  value       = oci_core_vcn.falcon_vcn.id
}
