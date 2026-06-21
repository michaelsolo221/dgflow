# Night Line Landing — Deployment

## Prerequisites

- `gcloud` CLI authenticated with a GCP account that has Storage Admin (`roles/storage.admin`) on the target project.

## Deploy

Replace `<project>` with your GCP project ID in every command below.

### 1. Create the bucket

```bash
gcloud storage buckets create gs://<project>-night-line-landing \
  --no-uniform-bucket-level-access \
  --location=us-central1
```

If creation fails due to org policy constraints (e.g. `publicAccessPrevention` or `uniformBucketLevelAccess`), escalate to the project owner to lift the restriction or grant an exemption.

### 2. Upload files

```bash
gcloud storage cp --cache-control="max-age=300" landing/index.html landing/style.css gs://<project>-night-line-landing/
```

### 3. Make public

```bash
gcloud storage buckets add-iam-policy-binding gs://<project>-night-line-landing \
  --member=allUsers \
  --role=roles/storage.objectViewer
```

### 4. Verify

```bash
curl -sI "https://storage.googleapis.com/<project>-night-line-landing/index.html" | grep -E "HTTP|content-type"
```

Expected:

```
HTTP/2 200
content-type: text/html
```
