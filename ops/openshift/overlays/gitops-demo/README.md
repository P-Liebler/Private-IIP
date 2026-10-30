# Private-IIP — OpenShift GitOps bootstrap in gitops-demo

This overlay is consumed by Argo CD Application `privat-iip` from **main**.
The base manifests stay disabled and unchanged. This overlay opts in to all
eight workloads (one replica each) and builds five different images **inside
OpenShift** from public GitHub commit
`907851def4f1851068d3a076ec0acdceb272aee6`.
No image transfer or local Docker is required. The initial ConfigChange
trigger runs **only when a BuildConfig is created**. Future Git commits require
a new reviewed build/image tag and release update, not a blind Sync.

## One Argo CD deployment

- Use exactly Application `privat-iip`, target revision `main`, source path
  `ops/openshift/overlays/gitops-demo`, destination namespace `gitops-demo`.
- Manual **Refresh → Sync**, **Prune unchecked**, no automatic self-heal or
  deletion. The manifests define BuildConfigs/ImageStreams, internal services,
  eight workloads, the existing three protected PVCs, and the separate
  `privat-iip` private re-encrypt HTTPS Route. `gitops-lab` is not changed.
- Required Argo controller/AppProject privileges: `build.openshift.io/BuildConfig`,
  `image.openshift.io/ImageStream`, `route.openshift.io/Route`, and existing
  workload/service/PVC/networkpolicy/configmap resources. The namespace
  also needs functioning OpenShift internal image registry and external
  upstream fetches from OpenShift build pods.
- Images are *new* builds and have new runtime digests; the historically audited
  PR11 digest claims do not apply. Base annotations still correctly identify
  production release status as **NOT_APPROVED**. This is a private staging
  bootstrap, not an approval to use actual portfolio assets.
- Because the app includes PostgreSQL and SeaweedFS data mounts, only use
  with verified fresh/disposable `postgres-data`, `seaweed-data` and
  `valkey-data`. Never delete or reformat existing volumes to make it start.

## Remaining runtime gates

- No automatic Alembic upgrade is included. A migration against a live PVC must
  have a verified backup and a checked destination before it is executed. The
  existing separate template is
  `ops/openshift/manual/migration-job.json` (suspended and excluded from Argo).
  API readiness may be green after SQL connectivity even if schema is absent.
  **Do not use real finance data before the database migration succeeds.**
- `FRONTEND_ORIGIN` / `API_PUBLIC_ORIGIN` still use their placeholder values
  until the actual automatically allocated Route host is known. After Sync,
  check `oc -n gitops-demo get route privat-iip`; update both origins to
  `https://<allocated-host>` in Git and Sync again before browser login.
- The `raw-ingestions` SeaweedFS bucket must exist. The currently provisioned
  S3 identity has least-privilege object actions and cannot create the bucket
  via `make_bucket`. Do not grant arbitrary administrator rights for convenience.
  Bootstrap the empty bucket with a separately authorized operation.
- A new private Route may be reachable **only** from RFC1918 source ranges
  (router source-IP checks). Verify the actual VPN address and router setup.
  If you are not on such a source address, the Route intentionally rejects
  traffic; do not remove the restriction without review.
- OpenShift arbitrary UID/restricted-v2, NFS write permissions, build result,
  image pulls, data health and Caddy service-CA TLS have not been validated on
  the user's cluster. A green Argo Sync alone does not prove a usable app.

## Read-only verification from PowerShell

```powershell
oc -n gitops-demo get builds,imagestreams,buildconfigs
oc -n gitops-demo get deployment,statefulset,pods
oc -n gitops-demo get route privat-iip
oc -n gitops-demo get events --sort-by=.lastTimestamp | Select-Object -Last 20
```

If the BuildConfigs are denied by the Argo AppProject or cluster RBAC, resolve
that **specific** permission rather than assigning broad cluster-admin.
If builds fail, inspect the named build logs; never use fabricated registry
digests. All IIP network policies remain scoped to
`app.kubernetes.io/part-of=investment`; verify unrelated projects are not
affected. No secrets, credential values, data collections, scheduled financial
recommendations or automatic database migrations are stored in Git.
