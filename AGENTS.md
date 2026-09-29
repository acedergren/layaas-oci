# Layaas OCI public project

This repository is the reusable public OCI deployment. The production API and
its account-specific operations live in the separate private repository.

- Never add production hostnames, OCIDs, private addresses, approvals, live
  evidence, Vault references, or secret values.
- Keep the default VM private, with no public IP or SSH ingress. Keep ingress
  scoped to validated private client CIDRs.
- Never pass a credential value through Terraform, Resource Manager variables,
  cloud-init, metadata, command arguments, source, or logs. Pass only a Vault
  secret OCID and retrieve the value through the exact-instance principal.
- Keep source/model dependencies pinned by immutable revision. Do not modify or
  vendor upstream Laya source or model weights.
- Run Python contract and stack safety tests, Terraform fmt/init/validate, shell
  syntax checks, stack package checks and `git diff --check` before release.
- Do not apply to any OCI tenancy from CI. Users review and apply their own stack.
