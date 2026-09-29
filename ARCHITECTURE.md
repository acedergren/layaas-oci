# Architecture

```mermaid
flowchart LR
  User[API client in approved private CIDR] -->|Bearer auth, TCP 8000| NSG[Dedicated OCI NSG]
  NSG --> VM["Private Ubuntu VM<br/>Layaas API + pinned CPU model"]
  VM -->|Instance principal; exact VM rule| Vault[One existing OCI Vault secret]
  VM -->|HTTPS at first boot| Sources[Pinned Python dependencies\nand immutable model revision]
  Stack[OCI Resource Manager stack\nTerraform in this repository] -->|Creates| NSG
  Stack -->|Creates| VM
  Stack -->|Creates exact-instance IAM| Vault
```

The deployment stack owns the compute instance, its NSG, an exact-instance
dynamic group and a policy limited to one secret OCID. It consumes a pre-existing
private subnet and Vault secret. It does not create a public IP, a public DNS name,
an SSH rule or an external edge service.

The secret value is fetched by instance principal at boot into root-only runtime
storage and exposed to the service through systemd credentials. Terraform and
cloud-init receive only its OCID. Model files are downloaded at the pinned commit
and cached on the VM; the API does not accept model selection from callers.

The public repository owns reusable application code, the stack package and
generic docs. The private production repository owns the running deployment's
resource configuration, owner procedures and live evidence. Production should
pin a tagged public release and record its commit; it must not deploy from a
moving default branch.
