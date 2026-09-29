#!/usr/bin/env bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
exec 9>/var/lock/layaas-bootstrap.lock
flock -n 9 || { echo 'Another Layaas bootstrap is running'; exit 1; }
rm -f /opt/laya/.ready
systemctl stop layaas-api.service layaas-secrets.service 2>/dev/null || true
trap 'rm -f /opt/laya/.ready; systemctl stop layaas-api.service 2>/dev/null || true' ERR
apt-get update -qq
apt-get install -y --no-install-recommends python3-venv ca-certificates
id laya >/dev/null 2>&1 || useradd --system --home-dir /var/lib/laya --create-home --shell /usr/sbin/nologin laya
install -d -o laya -g laya -m 0700 /var/lib/laya/huggingface
python3 -m venv /opt/laya/venv
/opt/laya/venv/bin/pip install --disable-pip-version-check -r /opt/laya/requirements-linux.lock
systemctl daemon-reload
systemctl reset-failed layaas-secrets.service layaas-api.service || true
systemctl enable layaas-secrets.service layaas-api.service
systemctl start layaas-secrets.service
runuser -u laya -- env HF_HOME=/var/lib/laya/huggingface /opt/laya/venv/bin/python /opt/laya/preload.py
touch /opt/laya/.ready
systemctl start layaas-api.service
echo 'Layaas bootstrap completed'
