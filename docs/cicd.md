# CI/CD

`main` is the **single deployable branch** — every push to `main` ships to **prod**.
There are no non-prod environments.

| Workflow | Trigger | Does |
|---|---|---|
| `.github/workflows/ci.yml` | PRs + pushes | pytest, frontend type-check + build, `terraform validate` |
| `.github/workflows/deploy.yml` | push to `main` (or manual) | build/push ARM64 image → `terraform apply` → frontend → S3 + CloudFront invalidation |

Auth uses **GitHub OIDC** (no long-lived AWS keys).

## One-time bootstrap

### 1. Terraform state bucket

```bash
aws s3api create-bucket --bucket <your-state-bucket> --region us-east-1
aws s3api put-bucket-versioning --bucket <your-state-bucket> \
  --versioning-configuration Status=Enabled
```

### 2. GitHub OIDC provider + deploy role

Create the OIDC provider (once per account):

```bash
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1
```

Create a role `mentis-github-deploy` trusting **only this repo's `main`** branch:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Federated": "arn:aws:iam::<ACCOUNT_ID>:oidc-provider/token.actions.githubusercontent.com" },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": { "token.actions.githubusercontent.com:aud": "sts.amazonaws.com" },
      "StringLike": { "token.actions.githubusercontent.com:sub": "repo:<OWNER>/<REPO>:ref:refs/heads/main" }
    }
  }]
}
```

The role needs permissions to manage the stack: ECR (push), Lambda, API Gateway,
DynamoDB, S3 (incl. `s3vectors:*`), SQS, EventBridge Scheduler, CloudFront,
IAM (create the Lambda roles), SSM, and read/write on the state bucket. For a
solo project, attaching `PowerUserAccess` + a small inline policy for `iam:*` on
`mentis-*` roles is the pragmatic choice; tighten later.

### 3. GitHub repo configuration

**Secrets** (Settings → Secrets and variables → Actions → Secrets):

| Secret | Value |
|---|---|
| `AWS_DEPLOY_ROLE_ARN` | `arn:aws:iam::<ACCOUNT_ID>:role/mentis-github-deploy` |
| `API_KEY` | the API key the frontend sends as `x-api-key` (must match SSM `/mentis/prod/api_key`) |

**Variables** (… → Variables):

| Variable | Value |
|---|---|
| `TF_STATE_BUCKET` | your state bucket from step 1 |
| `AWS_REGION` | `us-east-1` (optional; default) |
| `SITE_ORIGIN` | *(set after first deploy — see below)* |
| `HARVEST_ENABLED` | `false` (set `true` to enable the nightly scraper) |

## First deploy

1. Push to `main` (or run the **Deploy (prod)** workflow manually).
2. The job summary prints the **API URL** and **site URL**.
3. Tighten CORS: set the `SITE_ORIGIN` repo variable to the site URL, then re-run deploy.
4. Set runtime secrets (once):
   ```bash
   aws ssm put-parameter --name /mentis/prod/api_key --type SecureString --overwrite --value "<same as GH API_KEY secret>"
   aws ssm put-parameter --name /mentis/prod/unpaywall_email --type SecureString --overwrite --value "you@uni.edu"
   # later, to enable the university/Scopus source:
   aws ssm put-parameter --name /mentis/prod/university_api_key --type SecureString --overwrite --value "<scopus key>"
   ```
5. Request **Bedrock model access** (console → Bedrock → Model access) for the Claude + Titan model IDs in `infra/variables.tf`.

## Notes

- The image is tagged with the commit SHA, so each deploy produces a new
  `lambda_image_uri` and Terraform rolls all three Lambdas to the new image.
- The ECR repo keeps only the last 5 images (lifecycle policy).
- ARM64 images are built with `docker buildx` under QEMU emulation on the
  x86 runner. To speed this up later, switch `runs-on:` to `ubuntu-24.04-arm`.
