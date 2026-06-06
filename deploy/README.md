# Deploying Mentis (single Graviton EC2)

One small arm64 instance runs everything: Caddy (HTTPS + static frontend + API
proxy), the FastAPI backend, the Docker code sandbox, SQLite, and per-project
file workspaces. No re-architecture from local — the same code runs as-is.

```
https://<eip>.sslip.io ──Caddy──► / (React static)  +  /api/* → uvicorn :8080
                                                              │→ Bedrock (IAM role)
                                                              │→ Docker sandbox
                                                              └→ SQLite + workspaces (EBS)
```

**Cost:** ~€15/mo (t4g.small + ~30 GB gp3). Reversible: `terraform destroy`.

## Prerequisites
- AWS credentials with permission to create EC2/IAM/SSM/EIP (the `mentis-poc-admin`
  user works). Bedrock model access enabled in the region (eu-south-2).
- Terraform ≥ 1.5.
- If the repo is private: a GitHub PAT with read access.
- The branch you want to deploy is pushed to GitHub (default `git_ref = "main"`).

## Deploy
```bash
cd deploy/terraform
cp terraform.tfvars.example terraform.tfvars   # then edit — at minimum set auth_password
terraform init
terraform apply
```
On success, `terraform output url` prints e.g. `https://13.37.x.x.sslip.io`.

First boot runs the bootstrap (clone, build sandbox image, pip install, npm build,
start services) — **allow ~5–10 minutes** before the URL responds. Then open the
URL, log in with your `auth_username` / `auth_password`.

## No domain needed
By default the app is served on `<elastic-ip>.sslip.io`, which resolves to the IP
with zero DNS setup and still gets a real Let's Encrypt certificate. To use your
own domain instead, set `domain` (and point its DNS A record at the Elastic IP)
and optionally `acme_email`.

## Operating it
- **Shell (no SSH port):** `aws ssm start-session --target <instance_id>` (see
  `terraform output ssm_connect`).
- **Logs:** `journalctl -u mentis -f` and `journalctl -u caddy -f`; bootstrap log at
  `/var/log/mentis-bootstrap.log`; `cat /opt/mentis/BOOTSTRAP_DONE` to confirm.
- **Update to new code:** `cd /opt/mentis && sudo git pull && \
  sudo /opt/mentis/backend/.venv/bin/pip install -r backend/requirements.txt && \
  (cd frontend && sudo VITE_API_BASE_URL=/api npm run build) && \
  sudo docker build -t mentis-sandbox:latest backend/sandbox && \
  sudo systemctl restart mentis` (only rebuild what changed).
- **Change a secret:** update the SSM parameter (or `terraform apply` with a new
  value), then re-run the relevant part of the bootstrap or edit `/opt/mentis/backend/.env`
  and `sudo systemctl restart mentis`.

## Teardown
```bash
terraform destroy
```
Removes the instance, EIP, IAM role, security group, and SSM secrets. (The EBS
root volume goes with the instance — back up `/opt/mentis/backend/.data` first if
you want to keep projects.)

## Notes / hardening later
- The backend runs as root so it can reach the Docker socket; the sandbox
  container (no network, read-only root, non-root user, capped memory) is the
  isolation boundary. A dedicated docker-group user is a future hardening step.
- Data lives on the instance's EBS volume. For durability across instance
  replacement, move `.data` to a separate EBS volume or back it up to S3.
- Claude models need the Anthropic use-case form accepted on the account; until
  then the agents run on Nova (the app falls back automatically).
