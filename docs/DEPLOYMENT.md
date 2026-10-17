# Deployment

Run the demo locally first using the root README. This work does not deploy cloud resources.

The Dockerfile installs the exact runtime snapshot and runs as user 10001. Build with `docker build -t luxe-demo .` and run with `docker run --rm -p 127.0.0.1:8000:8000 --env-file .env luxe-demo`, using a MongoDB URI reachable from inside the container. `127.0.0.1` inside that container is not your host MongoDB. Docker execution was not available in the review environment.

Expose the API only behind HTTPS. Never bake `.env` into an image. Configure least-privilege MongoDB access, backups, restricted ingress, external body/rate limits and spending alerts. `/health` checks process liveness only; application startup creates indexes and fails if MongoDB cannot be reached. Add a database readiness check for your deployment platform.

The Docker command disables forwarded-header trust by default. For a real reverse proxy, configure Uvicorn's forwarded allowlist for that exact proxy network; do not trust arbitrary forwarded headers. Confirm shared MongoDB rate counters group the expected client IPs. Test throttling through the real proxy.

`cloudbuild.yaml` is an inherited GCP example using Secret Manager, a regional Artifact Registry and Cloud Run. It is not an immediately runnable deployment: review project identity, service-account permissions, region, secrets, network access and privacy jurisdiction. Do not deploy it unchanged simply because a build succeeds.

Before an existing database upgrade, back it up and resolve duplicate cart rows or case-insensitive usernames. New unique indexes may correctly stop startup. This project does not perform destructive automatic data cleanup.
