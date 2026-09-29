# OCI deployment

## Stack behavior

The Terraform root is also an OCI Resource Manager configuration. It creates:

- one Ubuntu 24.04 amd64 Flex compute instance with configurable CPU, memory and
  encrypted boot-volume size;
- a dedicated NSG attached only to that instance;
- ingress to TCP/8000 only from the supplied RFC1918 private CIDRs;
- HTTPS egress for pinned package and model downloads, DNS to the VCN and NTP to
  OCI link-local services;
- a dynamic group matched to the exact created instance OCID;
- a tenancy IAM policy that grants that group `read secret-bundles` for the one
  supplied Vault secret OCID in its specified compartment.

The VM receives no public IP; there is no ingress for SSH or Internet CIDRs. The
API listens on the private interface at TCP/8000 and requires an origin bearer key
on inference, health, and API documentation routes. HTTP is suitable only when
the private network path is trusted. Use VPN/TLS or a TLS-terminating private
gateway when traffic crosses an untrusted network. This stack does not create a
public endpoint, DNS record, TLS certificate, Cloudflare Tunnel or Access app.

## Prerequisites

1. An OCI tenancy and a compartment for the workload.
2. Permission for the Resource Manager job principal to create compute, VNIC/NSG,
   dynamic group and IAM policy resources. The identity policy must be created in
   the tenancy root; the dynamic group matches only this instance. Follow your
   organization's approval process for IAM changes.
3. An existing private subnet in the selected VCN, configured to prohibit public
   IPs and routed to NAT for HTTPS downloads and Service Gateway for OCI services.
4. A client network with a private RFC1918 range routable to the subnet. Supply
   only the smallest client CIDR(s) needed.
5. An Ubuntu 24.04 amd64 image compatible with the selected Flex shape in the
   selected region.
6. A pre-created OCI Vault secret in the same tenancy, encrypted with a key
   accessible by the Vault service. Store a cryptographically random bearer
   credential of at least 32 non-whitespace ASCII characters in it. The API
   accepts only the **secret OCID**; the secret value never enters Terraform.

The deployment caller still needs permission to create stacks/jobs and the
Resource Manager job principal needs the corresponding permissions in target
compartments. Set these according to current OCI identity-domain and compartment
policy requirements; do not grant broad tenancy administration merely to avoid
scoping the deployment.

## Apply and verify

Create the stack from this repo or a generated stack zip. Configure the stack
without selecting automatic apply. Review the planned resources and changes,
confirm the subnet, CIDRs, compartment, image, instance size and secret scope,
then apply explicitly.

After apply:

1. Confirm the instance has no public IP and the expected dedicated NSG.
2. Confirm the dynamic-group rule contains only the created instance OCID and the
   IAM policy condition names only the supplied secret OCID.
3. Wait for cloud-init to complete. The service starts only after dependencies,
   model weights and the current Vault secret are ready.
4. From an allowed private client, set `LAYAAS_API_URL` from the stack output and
   inject the same Vault credential into `LAYA_API_KEY` using your approved
   secret manager. Run `python examples/client.py "$LAYAAS_API_URL" --health`.
5. Run the synthetic inference example from `QUICKSTART.md`.

If startup fails, inspect cloud-init and systemd journal output through the OCI
instance console. Logs omit request bodies, authorization headers and secret
values. Do not enable access logs containing request content.

## Cost and limits

This stack does not set a billing cap. Compute, boot storage, Vault, networking,
model-download egress and any private access gateway are billed to the deploying
tenancy under its region, shape, negotiated rate, use and tax conditions. Use the
OCI Cost Estimator and budget alarms before applying. The default 1 OCPU/8 GB/50 GB
profile is a small reference profile, not an availability or performance promise.
CPU readiness and model size should be measured in the target region before
production workloads are assigned.

## Upgrade and teardown

Treat each public release as immutable. Review source and Terraform changes,
create a new stack configuration version, inspect a Resource Manager plan, and
apply only after reviewing replacements and downtime. Back up any user data before
upgrading or destroying the boot volume; the stack does not configure backups.

To remove a deployment, use Resource Manager's Destroy job after reviewing the
plan. Confirm the stack owns only its dedicated instance, NSG, dynamic group and
policy. Terraform does not destroy the pre-existing VCN/subnet, Vault, key or
secret. Delete the secret separately only if it is dedicated to this deployment
and retention requirements permit it. Remove any external VPN, gateway or DNS
configuration separately.

## Immutable model preparation (v0.1.1)

`model-manifest.json` is reviewed release input, bound by SHA-256 in `release.json`.
It records the exact five source and finalized files from the pinned checkpoint.
The clean source tokenizer was already normalized; its source and final digests
are identical. The installer accepts only these known bytes, invokes the pinned
upstream normalizer and verifies all finalized bytes. An unknown cache variant
fails closed; do not generate replacement hashes on the target host.

Bootstrap runs model preparation separately from inference. It copies validated
bytes into a staging directory and atomically publishes
`/opt/laya/models/<model-revision>-<manifest-sha256>`, owned by root, with files
0444 and directories 0555. Files are independent copies, without symlinks or
hardlinks into the writable download cache. Existing matching bundles are reused;
conflicts stop installation. Interrupted stages are never selected by the loader.
The bootstrap lock serializes retries; rerun `/opt/laya/bootstrap.sh` after fixing
dependency/download/IAM failures. No readiness marker is retained on failure.

The API validates ownership, all ancestor permissions, exact file inventory and
hashes before constructing a local `Agent` and attaching it to the router. Model
identity is assigned after successful load. The process has no writable model
cache and runs with `HF_HUB_OFFLINE=1`; temporary files use systemd's private /tmp.
Local development that exercises real inference needs an equivalent root-owned
model copy on Linux. Fake-router tests do not require root or weights.

Allow room for download cache, staging, finalized copy, previous model and both
Python environments. Check actual free space before upgrades rather than deleting
a working cache. The release's preparation/startup/disk/RSS measurements are
synthetic Linux-runner evidence; operators must measure their own VM before
approving adoption. Do not run the new-stack bootstrap over an existing private
installation: stage the released runtime separately, build its own venv, verify
its bundle, then switch the whole runtime/model pair under an approved runbook.
