# ============================================================
# Container Security Falcon — Oracle Cloud Always Free Tier
#
# This Terraform configuration provisions:
#   - 1x ARM Ampere A1 instance (1 OCPU, 6GB RAM)
#   - VCN with public subnet
#   - Security list allowing HTTP (80, 443) and SSH (22)
#   - Cloud-init to install Docker and deploy containers
#
# Cost: $0.00 — Always Free tier
#
# Usage:
#   terraform init
#   terraform plan
#   terraform apply
# ============================================================

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    oci = {
      source  = "oracle/oci"
      version = "~> 6.0"
    }
  }
}

# ── Provider Configuration ───────────────────────────────────
provider "oci" {
  region = var.region
}

# ── Data Sources ─────────────────────────────────────────────
data "oci_identity_availability_domains" "ads" {
  compartment_id = var.compartment_id
}

data "oci_core_images" "ubuntu" {
  compartment_id           = var.compartment_id
  operating_system         = "Canonical Ubuntu"
  operating_system_version = "22.04"
  shape                    = var.instance_shape
  sort_by                  = "TIMECREATED"
  sort_order               = "DESC"
}

# ── Networking ───────────────────────────────────────────────

resource "oci_core_vcn" "falcon_vcn" {
  compartment_id = var.compartment_id
  display_name   = "falcon-vcn"
  cidr_blocks    = ["10.0.0.0/16"]
  dns_label      = "falconvcn"
}

resource "oci_core_internet_gateway" "falcon_igw" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.falcon_vcn.id
  display_name   = "falcon-internet-gateway"
  enabled        = true
}

resource "oci_core_route_table" "falcon_rt" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.falcon_vcn.id
  display_name   = "falcon-route-table"

  route_rules {
    destination       = "0.0.0.0/0"
    network_entity_id = oci_core_internet_gateway.falcon_igw.id
  }
}

resource "oci_core_security_list" "falcon_sl" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.falcon_vcn.id
  display_name   = "falcon-security-list"

  # Allow all outbound traffic
  egress_security_rules {
    protocol    = "all"
    destination = "0.0.0.0/0"
  }

  # SSH access
  ingress_security_rules {
    protocol = "6" # TCP
    source   = var.ssh_allowed_cidr
    tcp_options {
      min = 22
      max = 22
    }
  }

  # HTTP
  ingress_security_rules {
    protocol = "6"
    source   = "0.0.0.0/0"
    tcp_options {
      min = 80
      max = 80
    }
  }

  # HTTPS
  ingress_security_rules {
    protocol = "6"
    source   = "0.0.0.0/0"
    tcp_options {
      min = 443
      max = 443
    }
  }

  # Grafana (restrict in production)
  ingress_security_rules {
    protocol = "6"
    source   = var.ssh_allowed_cidr
    tcp_options {
      min = 3000
      max = 3000
    }
  }
}

resource "oci_core_subnet" "falcon_subnet" {
  compartment_id             = var.compartment_id
  vcn_id                     = oci_core_vcn.falcon_vcn.id
  display_name               = "falcon-public-subnet"
  cidr_block                 = "10.0.1.0/24"
  route_table_id             = oci_core_route_table.falcon_rt.id
  security_list_ids          = [oci_core_security_list.falcon_sl.id]
  dns_label                  = "falconsubnet"
  prohibit_public_ip_on_vnic = false
}

# ── Compute Instance (Always Free ARM) ──────────────────────

resource "oci_core_instance" "falcon_instance" {
  compartment_id      = var.compartment_id
  availability_domain = data.oci_identity_availability_domains.ads.availability_domains[0].name
  display_name        = "falcon-server"
  shape               = var.instance_shape

  shape_config {
    ocpus         = var.instance_ocpus
    memory_in_gbs = var.instance_memory_gb
  }

  source_details {
    source_type = "image"
    source_id   = data.oci_core_images.ubuntu.images[0].id
  }

  create_vnic_details {
    subnet_id        = oci_core_subnet.falcon_subnet.id
    assign_public_ip = true
  }

  metadata = {
    ssh_authorized_keys = var.ssh_public_key
    user_data           = base64encode(file("${path.module}/cloud-init.yaml"))
  }

  # Prevent accidental destruction
  lifecycle {
    prevent_destroy = false
  }
}
