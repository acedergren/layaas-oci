output "private_ip" {
  description = "Private address of the Layaas API instance. No public IP is assigned."
  value       = oci_core_instance.api.private_ip
}

output "api_url" {
  description = "Private, authenticated HTTP endpoint. Use only from an allowed private client network or an encrypted private access path."
  value       = "http://${oci_core_instance.api.private_ip}:8000"
}

output "network_security_group_id" {
  description = "Dedicated NSG attached to the API VM."
  value       = oci_core_network_security_group.api.id
}

output "instance_id" {
  description = "Compute instance OCID."
  value       = oci_core_instance.api.id
}
