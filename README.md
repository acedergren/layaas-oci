# Layaas OCI

**Laya as a Service.** *From context to choice.*

![Layaas Clear Signal identity](assets/layaas-clear-signal-logo.png)

[![Deploy to Oracle Cloud](https://oci-resourcemanager-plugin.plugins.oci.oraclecloud.com/latest/deploy-to-oracle-cloud.svg)](https://cloud.oracle.com/resourcemanager/stacks/create?zipUrl=https://github.com/acedergren/layaas-oci/releases/latest/download/layaas-oci-stack.zip)

Deploy a pinned, multilingual Laya decision API as a private CPU service in your
own Oracle Cloud Infrastructure tenancy. The public repo contains the reusable
service and OCI Resource Manager/Terraform stack. It does not contain or control
the separate private production deployment.

## Deploy to OCI

The stack creates one private compute instance, its dedicated NSG, an
instance-specific dynamic group, and a policy granting that instance access to
one pre-existing OCI Vault secret. It assigns **no public IP**, opens no SSH port,
and accepts API traffic only from explicit private RFC1918 client ranges.

Before creating the stack, prepare an existing private subnet that:

- prohibits public IPs and has NAT egress for HTTPS package/model downloads;
- has an OCI Service Gateway route for Vault access;
- is reachable from the private client CIDRs you will authorize.

Create an OCI Vault secret containing a random API bearer credential of at least
32 characters. Enter **only its secret OCID** in the stack. The VM retrieves the
current secret version through its instance principal at boot. The stack requires
permissions to create the VM, NSG, exact-instance dynamic group, and Vault-scoped
IAM policy. It does not create a VCN, subnet, Vault, key, or secret value.

1. Open [OCI Resource Manager Stacks](https://cloud.oracle.com/resourcemanager/stacks).
2. Use the Deploy to Oracle Cloud button above, or upload the
   `layaas-oci-stack.zip` asset from the latest GitHub release.
3. Enter your compartment, private subnet, region, Ubuntu 24.04 amd64 image,
   Vault secret OCID and private client CIDRs. Flex shape defaults are one OCPU,
   8 GB RAM and a 50 GB boot volume; choose values supported in your region.
4. Create the stack **without automatic apply**. Review the plan, then apply it.
5. Read the `api_url` output and use it only from an allowed private network or
   through an encrypted private access path.

The first boot installs pinned dependencies and downloads the pinned model before
starting the listener. The API remains unavailable if the model or Vault secret
is not ready. Review boot logs in the instance console if initialization fails.

See [DEPLOYMENT.md](DEPLOYMENT.md) for full prerequisites, IAM requirements,
network behavior, cost guidance and destroy steps. [ARCHITECTURE.md](ARCHITECTURE.md)
describes the boundary between the public project and private production repo.

## Call the API

Use an approved secret-injection mechanism to populate `LAYA_API_KEY`; do not put
the value in source, command arguments, URLs, shell history or Terraform inputs.
The checked-in Python client sends synthetic sample data by default:

```sh
python examples/client.py "$LAYAAS_API_URL" --health
python examples/client.py "$LAYAAS_API_URL" --sample samples/typed-sv.json
```

See [QUICKSTART.md](QUICKSTART.md) and [API.md](API.md) for the full request
contract and responses. The model handles typed `choice`, `score`, and `noul`
questions; it does not generate free-form text.

## Development

The runtime lock targets Ubuntu 24.04 amd64 with Python 3.12. Follow
[CONTRIBUTING.md](CONTRIBUTING.md). CI runs contract and stack-safety checks,
Terraform validation, and stack-package checks. CI does not apply infrastructure
or prove model quality, regional capacity, latency or recovery in your tenancy.

Layaas is an independent community deployment project and is not affiliated with
or endorsed by Oracle or Convai Innovations. OCI, Oracle and Laya are their
respective owners' marks. This project uses the Clear Signal identity and does
not use Oracle branding.
