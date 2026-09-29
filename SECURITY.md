# Security

Report suspected vulnerabilities privately through GitHub's **Report a
vulnerability** option in the Security tab. Do not include API keys, secret
values, customer data, private addresses, OCI OCIDs or production deployment
details in public issues.

The stack defaults to a private VM, no public IP, no SSH ingress, private
RFC1918-only API ingress and a bearer-authenticated API. It retrieves the bearer
credential from one existing Vault secret using a dynamic group matched to the
exact VM. Terraform receives the secret OCID, never the secret value.

The API listener uses HTTP on the private interface. Use a trusted private path
or terminate TLS before sending requests across any untrusted network. Do not
expose TCP/8000 directly to the Internet. The deployment operator is responsible
for OCI IAM review, client credential distribution/revocation, patching, backups,
capacity, and cost monitoring.
