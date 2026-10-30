# Private-IIP in gitops-demo — GitOps-controlled start on main

Updated 2026-10-30. GitHub main is now **ENABLED** with one requested replica
for each of: api, web, worker, scheduler, postgres, valkey, minio and caddy.
The shared ops/openshift/base remains disabled (0), intentionally.
Source: ops/openshift/overlays/gitops-demo. Application: openshift-gitops/privat-iip.

**Do not confuse manifest readiness with cluster acceptance.** The final
readiness of these workloads, PostgreSQL/NFS permissions, and the new image
build digests have NOT been verified against the actual OpenShift cluster.
The app remains offline until Argo CD Sync succeeds, and may stop on any gate.

## Operation via Argo CD only

1. Ensure the existing Argo CD Application privat-iip still points to
   GitHub main, path ops/openshift/overlays/gitops-demo, namespace gitops-demo.
   Leave the scoped spec.ignoreDifferences rule for iip-service-ca /data.
2. In Argo UI: Refresh, inspect Diff, and verify no resource called gitops-lab
   is changed or deleted. Verify the three existing PVCs remain.
3. Run a MANUAL full Sync via Argo with Prune OFF (not a selective Sync).
   Do not run oc start-build, oc apply, oc scale, oc delete, or copy images.
   If auto-sync is enabled, inspect its ongoing operation first.
4. OpenShift builds five images (pinned Git commit 4f3b8b83) sequentially.
   Build observers are Argo Sync hooks with read-only limited Kubernetes
   credentials. If a build fails, the next build will not start.
5. Infrastructure pods start after images are available. PostgreSQL
   uses nss_wrapper to support arbitrary OpenShift UIDs and an initContainer
   that checks NFS directory write access without modifying storage.
   A failed Postgres readiness blocks later waves. Preserve logs and PVCs.
6. When infrastructure is Healthy, a scoped SeaweedFS hook creates bucket
   raw-ingestions if missing. Another hook runs initial Alembic migrations
   ONLY on an empty PostgreSQL user schema. Any existing unknown/old schema
   is never modified automatically. A final read-only gate verifies
   exact Alembic head and S3 bucket access before application writers start.
7. API, web, worker, scheduler start with one replica each. The private
   reencrypt Route privat-iip is applied after application pods become
   Healthy. No financial data collection, forward shadow or SEC scraping
   is enabled by this deployment.

## Recovery: Caddy BuildPodDeleted by Descheduler

On 2026-10-30 the first Caddy build `iip-caddy-1` was evicted by the
cluster Descheduler and ended with `BuildPodDeleted`. The earlier PostgreSQL
and SeaweedFS image builds had succeeded.

The Argo CD recovery changes ONLY Caddy build orchestration:
- `BuildConfig/iip-caddy-retry-1` is a distinct, new build configuration,
  pinning the SAME Git source, Dockerfile, build arguments and ImageStreamTag
  as `iip-caddy`. Its ConfigChange trigger starts the retry upon its first
  GitOps creation. The old failed Build and original BuildConfig are retained.
- The existing Argo `iip-wait-caddy-4f3b` Sync hook is re-created by its
  BeforeHookCreation policy, and now reads the retry BuildConfig and its
  Build status. It still validates `iip-caddy:bootstrap-4f3b8b83`.
- PostgreSQL, SeaweedFS, API and web BuildConfigs and all eight runtime
  images, PVCs, credentials and the `gitops-lab` Deployment remain unchanged.

After this fix is reviewed and committed on main, **Refresh the full Argo
Diff before starting another manual Sync (Prune OFF)**. Do not manually run
`oc start-build`, delete old Build objects or reconfigure the Descheduler.
If the retry is also evicted, save read-only Build/Pod events and involve
the cluster administrator for a policy/capacity assessment; do not turn off
the namespace-wide Descheduler or modify cluster-wide scheduling policies.

## Safety/approval limitations

- Existing postgres-data (20Gi), valkey-data (2Gi) and seaweed-data (100Gi)
  PVCs have Prune=false,Delete=false. Never delete/replace them blindly.
- Existing deployment gitops-lab and its route are unrelated and must not
  be modified by this Application.
- Namespace ServiceAccount iip-runtime references existing runtime and
  Seaweed identities. Secrets are not in Git.
- Build observer uses a dedicated get-only Role with no permission to
  create/restart builds.
- The SeaweedFS bucket setup Job has a namespaced internal management
  Service limited by ingress/egress NetworkPolicies to one Job identity.
  Review that boundary before accepting data workloads.
- The private Route host
  privat-iip-gitops-demo.apps.test-slieu0202.slieu0201.local
  was inferred from gitops-lab route naming and is NOT proof of DNS/TLS
  availability for the client.
- Previous PostgreSQL CrashLoop logs were not retained; the exact previous
  cause is unknown. OpenShift may require admin verification/correction
  of TrueNAS NFS ownership/group and SELinux access. Never run privileged
  chown or delete PVC data as a shortcut.
- The five build images do not yet have independently accepted runtime
  vulnerability scan and acceptance records for these exact digests.
- No initial end-user account is created automatically. Account creation
  requires an authorized private admin workflow; never store passwords
  unencrypted in Git.

## Read-only checks after Argo Sync

    oc -n gitops-demo get deploy,sts,pods
    oc -n gitops-demo get bc,build,is,istag
    oc -n gitops-demo get route privat-iip
    oc -n openshift-gitops get application privat-iip -o jsonpath='{.status.sync.status} {.status.health.status}'

In a successful deployment, the eight workloads should report 1/1,
the Route should exist and App health must be verified. If any hook or pod
is failing, inspect read-only logs/events and halt further changes.
Argo Healthy/Synced is not a substitute for functional HTTPS/login tests.

## Offline tests

    python ops/openshift/overlays/gitops-demo/namespace-contract-test.py
    python -m unittest discover -s ops/tests -p test_gitops_candidate.py -v
    oc kustomize ops/openshift/overlays/gitops-demo

The CI checks and render are not a test of the real cluster's SCC, NFS,
Registry, Route, service-CA, login, migration contents or end-to-end UX.

## Emergency rollback

If the Argo operation stops in error, preserve pod/job logs and PVCs.
The last verified disabled desired state is commit
dbf6b892f16f380f4784acf1884ef964f7a13e8a. An authorized operator
can temporarily point Application privat-iip targetRevision to that
immutable commit in Argo and Sync WITHOUT PRUNE to return all eight IIP
replicas to 0, or create a reviewed revert commit on main. This does
NOT automatically prune newly built images, delete PVs or undo audit logs.

Reference: https://argo-cd.readthedocs.io/en/stable/user-guide/sync-waves/
Reference: https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/builds_using_buildconfig/triggering-builds-build-hooks
