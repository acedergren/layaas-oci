from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_stack_keeps_instance_private_and_requires_explicit_client_ranges():
    config = (ROOT / "main.tf").read_text()
    variables = (ROOT / "variables.tf").read_text()
    assert "assign_public_ip = false" in config
    assert 'direction                 = "INGRESS"' in config
    assert 'min = 8000\n      max = 8000' in config
    assert "source                    = each.value" in config
    assert 'startswith(cidrhost(trimspace(cidr), 0), "10.")' in variables
    assert 'startswith(cidrhost(trimspace(cidr), 0), "192.168.")' in variables
    assert "port_range { min = 22" not in config


def test_stack_grants_exact_instance_read_access_to_secret_reference_only():
    config = (ROOT / "main.tf").read_text()
    variables = (ROOT / "variables.tf").read_text()
    assert 'matching_rule  = "instance.id = ' in config
    assert "read secret-bundles" in config
    assert "target.secret.id = '${var.api_secret_ocid}'" in config
    assert 'variable "api_secret_value"' not in variables
    assert 'variable "secret_compartment_ocid"' in variables
    assert 'ocid1\\\\.compartment\\\\.oc1\\\\.' in variables
    assert 'sensitive   = true' in variables


def test_cloud_init_compresses_release_files_and_contains_no_secret_value():
    cloud_init = (ROOT / "cloud-init.yaml.tftpl").read_text()
    assert "encoding: gz+b64" in cloud_init
    assert '${api_secret_ocid}' in cloud_init
    assert '${api_secret_value}' not in cloud_init
    assert "#cloud-config" in cloud_init
