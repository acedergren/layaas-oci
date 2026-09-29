# Quickstart

You need an OCI stack already applied, private network access from an allowed
client CIDR, and a secure way to inject your Vault API key into the process
environment. Never type a credential into source code, an issue, a URL or a
command-line argument.

Set `LAYAAS_API_URL` to the stack's private `api_url` output and populate
`LAYA_API_KEY` through your approved secret manager. Then check readiness:

```sh
python examples/client.py "$LAYAAS_API_URL" --health
```

The sample request is synthetic and exercises all three typed question kinds:

```sh
python examples/client.py "$LAYAAS_API_URL" --sample samples/typed-sv.json
```

Use `samples/typed-en.json` for the English variant. The client verifies HTTPS
certificates when the URL uses HTTPS, disables redirects, sets a 30-second
timeout and suppresses error bodies. The default private endpoint is HTTP; only
use it over a trusted private network. Add a TLS gateway for paths where the
bearer credential could otherwise be observed.
