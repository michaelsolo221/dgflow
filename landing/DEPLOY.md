# Night Line Landing — Deployment

## Prerequisites

- `gcloud` CLI authenticated with a GCP account that has Storage Admin (`roles/storage.admin`) on the target project.

## Deploy

Replace `<project>` with your GCP project ID and `<phone>` with the real Night Line number (e.g. `+1 (555) 000-0000`) in every command below.

### 1. Patch the phone number locally

Do this **before** uploading so the placeholder never goes live.

```bash
sed -i '' 's/(XXX) XXX-XXXX/<phone>/' landing/index.html
```

Replace `<phone>` with the real Night Line number before running.

### 2. Create the bucket

```bash
gcloud storage buckets create gs://<project>-night-line-landing \
  --uniform-bucket-level-access \
  --location=us-central1
```

### 3. Upload files

HTML gets a short TTL so updates propagate quickly; CSS/assets get a longer TTL since they change rarely.

```bash
gcloud storage cp \
  --cache-control="max-age=60" \
  landing/index.html \
  gs://<project>-night-line-landing/

gcloud storage cp \
  --cache-control="max-age=3600" \
  landing/style.css \
  gs://<project>-night-line-landing/
```

### 4. Configure the default object for the bucket root

```bash
gsutil web set -m index.html -e 404.html gs://<project>-night-line-landing
```

This makes the bucket root URL resolve to `index.html` instead of returning 404.

### 5. Make public

```bash
gcloud storage buckets add-iam-policy-binding gs://<project>-night-line-landing \
  --member=allUsers \
  --role=roles/storage.objectViewer
```

### 6. Verify

```bash
curl -sI "https://storage.googleapis.com/<project>-night-line-landing/index.html" | grep -E "HTTP|content-type"
```

Expected:

```
HTTP/2 200
content-type: text/html
```

⚠️ **Security:** Uniform bucket-level access is enabled by default above. Direct GCS public access is acceptable for a static landing page, but for anything beyond that, serve via Cloud CDN, Load Balancer, or Firebase Hosting instead.
