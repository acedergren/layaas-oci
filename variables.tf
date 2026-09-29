variable "region" {
  description = "OCI region identifier that contains the selected subnet and image."
  type        = string
}

variable "tenancy_ocid" {
  description = "Tenancy OCID; required for the exact-instance dynamic group and least-privilege policy."
  type        = string
  validation {
    condition     = can(regex("^ocid1\\.tenancy\\.oc1\\.[A-Za-z0-9._-]+$", var.tenancy_ocid))
    error_message = "tenancy_ocid must be an OCI tenancy OCID."
  }
}

variable "compartment_ocid" {
  description = "Compartment in which the private VM and API network security group are created."
  type        = string
  validation {
    condition     = can(regex("^ocid1\\.compartment\\.oc1\\.[A-Za-z0-9._-]+$", var.compartment_ocid))
    error_message = "compartment_ocid must be an OCI compartment OCID."
  }
}

variable "subnet_ocid" {
  description = "Existing private subnet with NAT egress for HTTPS and a Service Gateway route for OCI Vault."
  type        = string
}

variable "availability_domain" {
  description = "Availability domain for the compute instance."
  type        = string
}

variable "image_ocid" {
  description = "Ubuntu 24.04 amd64 image OCID in the selected region."
  type        = string
}

variable "secret_compartment_ocid" {
  description = "Compartment containing the pre-created OCI Vault API-key secret."
  type        = string
  validation {
    condition     = can(regex("^ocid1\\.compartment\\.oc1\\.[A-Za-z0-9._-]+$", var.secret_compartment_ocid))
    error_message = "secret_compartment_ocid must be an OCI compartment OCID."
  }
}

variable "api_secret_ocid" {
  description = "OCID of a pre-created Vault secret containing a random API bearer credential of at least 32 characters; the secret value is never passed to Terraform."
  type        = string
  sensitive   = true
  validation {
    condition     = can(regex("^ocid1\\.vaultsecret\\.[A-Za-z0-9._-]+$", var.api_secret_ocid))
    error_message = "api_secret_ocid must be an OCI Vault secret OCID."
  }
}

variable "deployment_name" {
  description = "Unique resource name prefix for this deployment in the tenancy."
  type        = string
  default     = "layaas"
  validation {
    condition     = can(regex("^[a-zA-Z][a-zA-Z0-9-]{2,29}$", var.deployment_name))
    error_message = "deployment_name must be 3-30 letters, digits, or hyphens and start with a letter."
  }
}

variable "allowed_client_cidrs" {
  description = "Comma-separated RFC1918 private IPv4 CIDR ranges allowed to call TCP/8000."
  type        = string
  validation {
    condition = length(trimspace(var.allowed_client_cidrs)) > 0 && alltrue([
      for cidr in split(",", var.allowed_client_cidrs) : try(
        (
          (startswith(cidrhost(trimspace(cidr), 0), "10.") &&
          startswith(cidrhost(trimspace(cidr), -1), "10.")) ||
          (startswith(cidrhost(trimspace(cidr), 0), "192.168.") &&
          startswith(cidrhost(trimspace(cidr), -1), "192.168.")) ||
          (startswith(cidrhost(trimspace(cidr), 0), "172.") &&
            startswith(cidrhost(trimspace(cidr), -1), "172.") &&
            tonumber(split(".", cidrhost(trimspace(cidr), 0))[1]) >= 16 &&
            tonumber(split(".", cidrhost(trimspace(cidr), 0))[1]) <= 31 &&
            tonumber(split(".", cidrhost(trimspace(cidr), -1))[1]) >= 16 &&
          tonumber(split(".", cidrhost(trimspace(cidr), -1))[1]) <= 31)
        ),
        false
      )
    ])
    error_message = "Supply comma-separated private IPv4 client CIDRs within RFC1918 ranges."
  }
}

variable "shape" {
  description = "OCI x86_64 Flex compute shape."
  type        = string
  default     = "VM.Standard.E5.Flex"
  validation {
    condition     = endswith(var.shape, ".Flex")
    error_message = "shape must be an OCI Flex shape."
  }
}

variable "ocpus" {
  description = "Flex shape OCPUs. One OCPU is a small CPU-only reference configuration."
  type        = number
  default     = 1
  validation {
    condition     = var.ocpus >= 1 && var.ocpus <= 64
    error_message = "ocpus must be between 1 and 64."
  }
}

variable "memory_in_gbs" {
  description = "Flex shape RAM. Eight GB is a small reference configuration; adjust for workload."
  type        = number
  default     = 8
  validation {
    condition     = var.memory_in_gbs >= 8 && var.memory_in_gbs <= 1024
    error_message = "memory_in_gbs must be between 8 and 1024."
  }
}

variable "boot_volume_size_gbs" {
  description = "Encrypted boot volume size. The pinned model cache uses additional space."
  type        = number
  default     = 50
  validation {
    condition     = var.boot_volume_size_gbs >= 50 && var.boot_volume_size_gbs <= 32768
    error_message = "boot_volume_size_gbs must be between 50 and 32768."
  }
}
