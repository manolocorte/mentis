# Mentis Frontend

Static React + TypeScript + Vite SPA for the Mentis research assistant.
Served from S3 behind CloudFront in production.

## Prerequisites

- Node.js 18+

## Local development

```bash
cd frontend

# Install dependencies
npm install

# Copy and edit environment variables
cp .env.example .env.local
# Set VITE_API_BASE_URL to your API Gateway URL (or leave default for local backend)

# Start dev server on http://localhost:3000
npm run dev
```

The dev server proxies nothing — it calls `VITE_API_BASE_URL` directly. If you
are running the backend locally at `http://localhost:8000`, just leave
`VITE_API_BASE_URL` unset (the client falls back to that value).

## Production build

```bash
npm run build
```

Output goes to `dist/`. That directory is what gets uploaded to the S3 bucket
that sits behind CloudFront. Every file in `dist/` is a static asset — no
server-side rendering.

```bash
# Upload to S3 (adjust bucket name and distribution ID)
aws s3 sync dist/ s3://your-mentis-frontend-bucket/ --delete
aws cloudfront create-invalidation --distribution-id EXXXXXXXXXXXXX --paths "/*"
```

## Preview build locally

```bash
npm run preview
```

Starts a static server on `http://localhost:4173` serving the built `dist/`.

## Environment variables

| Variable            | Required | Default                   | Description                              |
|---------------------|----------|---------------------------|------------------------------------------|
| `VITE_API_BASE_URL` | No       | `http://localhost:8000`   | Base URL of the Mentis API (no trailing slash) |
| `VITE_API_KEY`      | No       | _(none)_                  | Sent as `x-api-key` header on every request |

Create a `.env.local` file (git-ignored) for local overrides.
