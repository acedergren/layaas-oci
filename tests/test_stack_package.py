from zipfile import ZipFile

from scripts.package_stack import package_stack


def test_package_contains_stack_and_runtime_but_no_tests_or_local_state(tmp_path):
    output = tmp_path / "stack.zip"
    package_stack(output)

    with ZipFile(output) as archive:
        names = set(archive.namelist())
    assert "main.tf" in names
    assert "schema.yaml" in names
    assert ".terraform.lock.hcl" in names
    assert "LICENSE" in names
    assert "cloud-init.yaml.tftpl" in names
    assert "server.py" in names
    assert "deploy/bootstrap.sh" in names
    assert not any(name.startswith(("tests/", "evidence/", ".git/")) for name in names)
    assert not any("tfstate" in name or ".tfplan" in name for name in names)
