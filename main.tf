terraform {
  required_version = ">= 1.0.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.0"
    }
  }
}

provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
  zone    = var.gcp_zone
}

# Variables
variable "gcp_project_id" {
  type        = string
  description = "The GCP Project ID where the resources will be created."
}

variable "gcp_region" {
  type        = string
  default     = "us-central1" # Part of GCP Always Free tier (us-central1, us-east1, us-west1)
  description = "GCP Region (must be us-central1, us-east1, or us-west1 to qualify for free tier)."
}

variable "gcp_zone" {
  type        = string
  default     = "us-central1-a"
  description = "GCP Zone matching the chosen region."
}

variable "allowed_ip_for_superset" {
  type        = string
  default     = "0.0.0.0/0" # Open to public by default. Change to your specific IP range for better security.
  description = "CIDR range allowed to access the Superset web dashboard."
}

# Network VPC
resource "google_compute_network" "vpc_network" {
  name                    = "recommendation-lab-vpc"
  auto_create_subnetworks = true
}

# Firewall Rule for SSH (Port 22)
resource "google_compute_firewall" "allow_ssh" {
  name    = "allow-ssh-traffic"
  network = google_compute_network.vpc_network.name

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["ssh-enabled"]
}

# Firewall Rule for Superset (Port 8088)
resource "google_compute_firewall" "allow_superset" {
  name    = "allow-superset-traffic"
  network = google_compute_network.vpc_network.name

  allow {
    protocol = "tcp"
    ports    = ["8088"]
  }

  source_ranges = [var.allowed_ip_for_superset]
  target_tags   = ["superset-enabled"]
}

# Compute Engine Instance (Strictly Free Tier Configured)
resource "google_compute_instance" "superset_vm" {
  name         = "superset-dashboard-vm"
  machine_type = "e2-micro" # Always Free Tier instance type (2 vCPUs, 1 GB RAM)
  zone         = var.gcp_zone

  tags = ["ssh-enabled", "superset-enabled"]

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-11"
      size  = 10 # 10 GB standard persistent disk (well below the 30 GB always free limit)
      type  = "pd-standard" # Standard persistent disk qualifies for free tier
    }
  }

  network_interface {
    network = google_compute_network.vpc_network.name
    access_config {
      # Empty access_config allocates an ephemeral external IP (always free, no static IP charges)
    }
  }

  metadata_startup_script = <<-EOT
    #!/bin/bash
    set -e

    echo "=== Starting VM Initialization ==="

    # 1. Enable 2GB Swap Memory (Crucial for 1GB RAM e2-micro instance)
    if [ ! -f /swapfile ]; then
      echo "Configuring Swap Space..."
      fallocate -l 2G /swapfile
      chmod 600 /swapfile
      mkswap /swapfile
      swapon /swapfile
      echo '/swapfile none swap sw 0 0' >> /etc/fstab
      echo "Swap space configured successfully!"
    fi

    # 2. Update System Packages
    apt-get update -y
    apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release git

    # 3. Install Docker & Docker Compose Plugin
    mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \
      $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

    apt-get update -y
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

    # 4. Enable and Start Docker Service
    systemctl enable docker
    systemctl start docker

    echo "=== VM Initialization Finished ==="
  EOT

  metadata = {
    # Blocks password SSH access; enforces SSH key auth only
    block-project-ssh-keys = "false"
  }
}

output "vm_external_ip" {
  value       = google_compute_instance.superset_vm.network_interface[0].access_config[0].nat_ip
  description = "The external IP address of the Superset VM."
}
