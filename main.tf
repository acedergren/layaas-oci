terraform {
  required_version = ">= 1.5.0, < 2.0.0"
  required_providers {
    oci = {
      source  = "oracle/oci"
      version = "~> 8.23.0"
    }
  }
}

provider "oci" {
  region = var.region
}

data "oci_core_subnet" "target" {
  subnet_id = var.subnet_ocid
}

data "oci_core_vcn" "target" {
  vcn_id = data.oci_core_subnet.target.vcn_id
}

locals {
  labels = {
    service    = "layaas"
    managed_by = "terraform"
  }
  user_data = templatefile("${path.module}/cloud-init.yaml.tftpl", {
    api_secret_ocid = var.api_secret_ocid
    bootstrap       = base64gzip(file("${path.module}/deploy/bootstrap.sh"))
    server          = base64gzip(file("${path.module}/server.py"))
    release_py      = base64gzip(file("${path.module}/release.py"))
    release_json    = base64gzip(file("${path.module}/release.json"))
    requirements    = base64gzip(file("${path.module}/requirements-linux.lock"))
    preload         = base64gzip(file("${path.module}/deploy/preload.py"))
    fetch_secret    = base64gzip(file("${path.module}/deploy/fetch_secret.py"))
    api_service     = base64gzip(file("${path.module}/deploy/layaas-api.service"))
    secrets_service = base64gzip(file("${path.module}/deploy/layaas-secrets.service"))
  })
  allowed_client_cidrs = [for cidr in split(",", var.allowed_client_cidrs) : trimspace(cidr)]
}

resource "oci_core_network_security_group" "api" {
  compartment_id = var.compartment_ocid
  vcn_id         = data.oci_core_subnet.target.vcn_id
  display_name   = "${var.deployment_name}-api"
  freeform_tags  = local.labels
}

resource "oci_core_network_security_group_security_rule" "api_ingress" {
  for_each                  = toset(local.allowed_client_cidrs)
  network_security_group_id = oci_core_network_security_group.api.id
  direction                 = "INGRESS"
  protocol                  = "6"
  source                    = each.value
  source_type               = "CIDR_BLOCK"
  description               = "Authenticated Layaas API from an explicitly allowed private client range"
  tcp_options {
    destination_port_range {
      min = 8000
      max = 8000
    }
  }
}

resource "oci_core_network_security_group_security_rule" "https_egress" {
  network_security_group_id = oci_core_network_security_group.api.id
  direction                 = "EGRESS"
  protocol                  = "6"
  destination               = "0.0.0.0/0"
  destination_type          = "CIDR_BLOCK"
  description               = "HTTPS for package and pinned model downloads plus OCI service access"
  tcp_options {
    destination_port_range {
      min = 443
      max = 443
    }
  }
}

resource "oci_core_network_security_group_security_rule" "dns_egress" {
  network_security_group_id = oci_core_network_security_group.api.id
  direction                 = "EGRESS"
  protocol                  = "17"
  destination               = data.oci_core_vcn.target.cidr_block
  destination_type          = "CIDR_BLOCK"
  description               = "DNS to the VCN resolver"
  udp_options {
    destination_port_range {
      min = 53
      max = 53
    }
  }
}

resource "oci_core_network_security_group_security_rule" "dns_tcp_egress" {
  network_security_group_id = oci_core_network_security_group.api.id
  direction                 = "EGRESS"
  protocol                  = "6"
  destination               = data.oci_core_vcn.target.cidr_block
  destination_type          = "CIDR_BLOCK"
  description               = "TCP DNS fallback to the VCN resolver"
  tcp_options {
    destination_port_range {
      min = 53
      max = 53
    }
  }
}

resource "oci_core_network_security_group_security_rule" "ntp_egress" {
  network_security_group_id = oci_core_network_security_group.api.id
  direction                 = "EGRESS"
  protocol                  = "17"
  destination               = "169.254.0.0/16"
  destination_type          = "CIDR_BLOCK"
  description               = "Time synchronization to OCI link-local services"
  udp_options {
    destination_port_range {
      min = 123
      max = 123
    }
  }
}

resource "oci_core_instance" "api" {
  availability_domain = var.availability_domain
  compartment_id      = var.compartment_ocid
  display_name        = var.deployment_name
  shape               = var.shape
  freeform_tags       = local.labels

  shape_config {
    ocpus         = var.ocpus
    memory_in_gbs = var.memory_in_gbs
  }

  create_vnic_details {
    subnet_id        = var.subnet_ocid
    assign_public_ip = false
    nsg_ids          = [oci_core_network_security_group.api.id]
  }

  instance_options {
    are_legacy_imds_endpoints_disabled = true
  }

  source_details {
    source_type             = "image"
    source_id               = var.image_ocid
    boot_volume_size_in_gbs = var.boot_volume_size_gbs
  }

  metadata = {
    user_data = base64encode(local.user_data)
  }

  lifecycle {
    precondition {
      condition     = data.oci_core_subnet.target.prohibit_public_ip_on_vnic
      error_message = "Select a private subnet that prohibits public IP addresses."
    }
  }
}

resource "oci_identity_dynamic_group" "api" {
  compartment_id = var.tenancy_ocid
  name           = "${var.deployment_name}-instance"
  description    = "Only the Layaas instance created by this stack"
  matching_rule  = "instance.id = '${oci_core_instance.api.id}'"
}

resource "oci_identity_policy" "api_secret" {
  compartment_id = var.tenancy_ocid
  name           = "${var.deployment_name}-vault-read"
  description    = "Allows only this Layaas instance to read its API-key secret"
  statements = [
    "Allow dynamic-group ${oci_identity_dynamic_group.api.name} to read secret-bundles in compartment id ${var.secret_compartment_ocid} where target.secret.id = '${var.api_secret_ocid}'"
  ]
}
