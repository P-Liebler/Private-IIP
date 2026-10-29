# OpenShift preparation — DRAFT / NOT_APPROVED

This is an additional deployment target for the existing application. Every
workload has zero replicas, and the separate Alembic Job is suspended. Images use
`registry.invalid` with the measured PR9 candidate digests. No cluster was used;
restricted-v2 admission, storage, TLS, recovery and release approval remain open.

Render locally, without cluster discovery or deployment:

```powershell
kubectl kustomize ops/openshift/overlays/example
kubectl kustomize ops/openshift/overlays/staging
kubectl kustomize ops/openshift/overlays/staging-infra
python ops/openshift/preflight.py
python -m unittest discover -s ops/tests -p test_openshift_manifests.py -v
```

The preflight intentionally exits **2**, including when its offline contracts
pass. It has no apply, sync or approval capability. JSON resource files and the
JSON-formatted `kustomization.yaml` files are valid YAML 1.2 and avoid adding a
mandatory YAML runtime dependency to the repository's operational tools.

`bootstrap/`, `manual/` and `examples/` are deliberately outside the active
Kustomization. The separately selected `staging` overlay sets replicas to one
and requires reviewed target inputs and external approval before use. The
example Argo CD Application points to this explicit opt-in overlay. Prometheus
is an optional disabled component. No ML, LLM,
collector egress, migration hook, backup CronJob, public ingress or automatic
Argo CD synchronization is installed.

Preparation and operator gates: [OpenShift and Argo CD](../../docs/operations/OPENSHIFT_ARGOCD.md).
