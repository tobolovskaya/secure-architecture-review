# Secure architecture review: a small FastAPI service, before and after

A security review of one service across five layers: app code, Dockerfile, CI pipeline, Kubernetes and Terraform. Every original file sits in `before/`, every fixed file in `after/`, and CI proves both sides on each push.

## Result

| Scanner | `before/` | `after/` |
|---|---|---|
| Checkov (Kubernetes, Dockerfile, Terraform) | **24 failed** (20 k8s, 2 Docker, 2 AWS) | **0 failed**, 1 documented skip per framework |
| hadolint | DL3013, DL3042 | clean |
| Bandit (SAST) | 0 findings | 0 findings |
| pytest on the fixed app | n/a | 4 passed |

**Main lesson / Hovedpoeng:** the scanners found configuration problems, but the most serious issues were found only by reading the code and the design.

## What the scanners caught and what only the review caught

| # | Finding | Layer | Caught by a scanner? | Fix in `after/` |
|---|---|---|---|---|
| 1 | Hardcoded password `"secret"` in the login check | App | **No** (Bandit missed it) | scrypt hash from env, `hmac.compare_digest`, fails closed when not configured |
| 2 | `request.json()` is not awaited, so `/login` always returns 500 | App | **No** | Pydantic model `LoginIn` with `extra="forbid"`, 401 on wrong password |
| 3 | `/user?id=abc` accepts any value, no response model | App | **No** | `/user/{user_id}` with `int` type and `UserOut` response model |
| 4 | Plain-text `API_KEY` in pod env | Kubernetes | **No** | Secret mounted from a CSI secrets-store volume |
| 5 | Security group open on 443 to `0.0.0.0/0` | Terraform | **No** | `allowed_cidrs` variable with validation that rejects `0.0.0.0/0` |
| 6 | CI only runs `docker build`, no tests or scans | CI | **No** | Reference pipeline `after/ci/ci.yml` (tests, Bandit, pip-audit, hadolint, Checkov, Trivy, Syft SBOM) |
| 7 | Container runs as root, no healthcheck | Dockerfile | Yes (CKV_DOCKER_3, CKV_DOCKER_2) | `python:3.12-slim`, uid 10001, `HEALTHCHECK` |
| 8 | Unpinned pip installs, pip cache kept | Dockerfile | Yes (DL3013, DL3042) | Pinned `requirements.txt`, `--no-cache-dir` |
| 9 | No securityContext, limits, probes, NetworkPolicy; default namespace | Kubernetes | Yes (20 checks, e.g. CKV_K8S_20, 23, 28, 31, CKV2_K8S_6) | Non-root, read-only root FS, drop ALL capabilities, seccomp RuntimeDefault, limits, probes, NetworkPolicy |
| 10 | Security group without description or VPC | Terraform | Yes (CKV_AWS_23, CKV2_AWS_5) | Description, `vpc_id`, egress limited to 443 |

Six of the ten findings were found only by manual review.

## Documented skips

Each skip has a written reason next to it in the file:

- `CKV_K8S_43` (image digest): the digest is set by the release pipeline after the image is built.
- `CKV_SECRET_6` on `secretProviderClass`: it is a class name, not a secret.
- `CKV2_AWS_5` (SG not attached): the group is meant to be attached by a load balancer module, which is outside this review.

## Corrections to the original report

The first version of this lab was a set of notebooks and a report. While turning it into real files I corrected these points:

- **The Kubernetes manifest was missing.** `deployment.yaml` in the template was a copy of the CI file. `before/k8s/deployment.yaml` was rebuilt from the lab example, with a fake key `FAKE_API_KEY_123`.
- **SBOM inside the Dockerfile.** The report suggested `RUN syft` in the image build. The SBOM is now produced in CI from the built image, so the scanner is not shipped inside the image.
- **Security group fix.** The report changed `0.0.0.0/0` to `192.168.1.0/24`, a private range that cannot reach an internet-facing service. The fix is now a validated variable.
- **"Semgrep can't detect SQL injection without types"** was removed. It is not accurate, and this service has no database layer to test it on.

## Verification

CI (`.github/workflows/review.yml`) runs on every push and pull request:

1. Tests for the fixed app (`pytest`).
2. `after/` must pass Checkov, hadolint and Bandit.
3. `before/` must be caught by Checkov and hadolint, so a scanner that silently stops working fails the build.

All tools are pinned (`requirements-scan.txt`), actions are pinned to a commit SHA, and the hadolint binary is checked against its SHA-256.

## How to run

```bash
python3 -m venv .scan && .scan/bin/pip install -r requirements-scan.txt
python3 -m venv .test && .test/bin/pip install -r requirements-test.txt

.test/bin/python -m pytest -q
.scan/bin/checkov -d after --compact --skip-download   # expect 0 failed
.scan/bin/checkov -d before --compact --skip-download  # expect 24 failed
hadolint after/Dockerfile before/Dockerfile
```

## Scope

Nothing here is deployed. The Terraform and Kubernetes files are reviewed and scanned only; no AWS resources were created.

## Hva jeg lærte / What I learned

- Scannere fanger konfigurasjon, ikke logikk. Bandit missed a hardcoded password, and no scanner saw that login always failed.
- A "fix" must be tested against the threat: a private CIDR on a public service is not a fix.
- Every skip needs a written reason, or it becomes a hidden risk.
- Testing that `before/` still fails proves the scanners actually run.

## License

MIT
