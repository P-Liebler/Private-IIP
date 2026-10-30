# Private-IIP: Argo CD start candidate (NOT VERIFIED)

**Branch:** feature/gitops-controlled-start-20261030
**Source code pin:** dbf6b892f16f380f4784acf1884ef964f7a13e8a

This is an optional release candidate, NOT a verified or approved deployment.
**Do not change the Argo Application revision or Sync until authorized review.**
The live main branch remains rolled back, with all eight IIP workloads at zero.

## Changes in this opt-in overlay

1. Five GitOps-managed OpenShift BuildConfigs and five ImageStreams use an
   immutable source commit. ConfigChange triggers ONE initial build per
   BuildConfig creation. Updating Git or clicking Sync again does not
   automatically start a new build.
2. Five read-only Argo Sync Jobs watch build completion and the matching
   ImageStreamTag. They run in strict sequence: postgres, seaweed, caddy,
   backend, web. Each build must complete before the next is created.
   Their own service account has only get permissions for BuildConfigs,
   Builds and ImageStreamTags. They cannot create or restart builds.
   No manual oc start-build, file transfer or local image building is needed.
3. GitOps then applies existing namespaced services, scoped NetworkPolicies,
   PVCs, ConfigMaps and ServiceAccounts. The three PVCs remain protected
   from pruning and deletion. There is no cluster-scoped registry change.
4. PostgreSQL, Valkey, SeaweedFS and Caddy use one replica each.
   A PostgreSQL initContainer only checks volume write access. It does
   not chmod, chown, delete or reinitialize an existing volume.
5. A read-only Sync Job validates the exact Alembic schema heads and
   checks that the raw-ingestions S3 bucket exists. It does not run a
   database migration or create a bucket. It blocks later waves on failure.
6. API, web, worker and scheduler only start after the gates pass.
   The private re-encrypt HTTPS route is applied afterwards.

## Known blockers — deployment is not yet usable

- The previous PostgreSQL pod crashed. Its logs were not captured, so the
  cause is NOT known. NFS permissions and OpenShift arbitrary UID remain
  possible issues, not proven causes. No PVC must be reset to work around this.
- A schema migration is not approved or automated for existing data.
  A fresh database has no Alembic version and will correctly fail the gate.
  An independently backed-up, reviewed, GitOps-managed migration is required.
- The raw-ingestions bucket was previously missing. The application S3
  identity cannot create it, so an authorized administrator must provision
  it and verify the least-privilege permissions.
- The proposed Route host is
  privat-iip-gitops-demo.apps.test-slieu0202.slieu0201.local.
  Its naming is inferred from the observed gitops-lab host. Actual routing,
  DNS, VPN source-IP and TLS have NOT been verified. Verify it before Sync.
- Role/RoleBinding, Job, BuildConfig, ImageStream and Route permissions for
  the Argo CD controller, availability of the openshift/cli image, resources
  and quotas have NOT been tested against this cluster.
- New resulting image digests have NOT passed release/security acceptance.
  Existing financial collection, model and recommendation gates remain off.
- The runtime gate uses a read-only S3 HEAD/exists request; the service
  identity must be allowed to check its configured bucket.
- The initial ConfigChange build will not rerun on later Syncs. A failed
  build needs a reviewed new build release; never use manual oc start-build
  as a shortcut.

## Safe offline checks

    python ops/openshift/overlays/gitops-demo/namespace-contract-test.py
    oc kustomize ops/openshift/overlays/gitops-demo

The assistant has run static JSON patch/path checks. A full Kustomize render,
server-side API/SCC admission, real image build and functional acceptance
have NOT been completed and must not be inferred.

## Read-only cluster inventory before reviewing any deployment

    oc -n openshift-gitops get application privat-iip
    oc -n gitops-demo get pvc
    oc -n gitops-demo get secret iip-runtime-secrets iip-s3-identities
    oc -n gitops-demo get route gitops-lab
    oc -n gitops-demo get deploy,sts,pods,bc,build,is,route

Do not print Secret values.

## Activation — only after permissions, data and backup review

The current Argo CD Application uses source.path
ops/openshift/overlays/gitops-demo and namespace gitops-demo. An authorized
reviewer can change ONLY its source.targetRevision from main to this
feature branch in the Argo CD UI, inspect the full Diff, and explicitly
Sync with Prune OFF and no AutoSync. This is a REAL cluster build and
deployment, not a preview. Read hook logs; halt on a failed gate.
Do not manually patch the cluster or reset PVCs.

Rollback: targetRevision back to main, Refresh, review Diff, Sync without
prune to stop the eight IIP replicas. Afterwards selectively review new
IIP build and route resources for authorized removal. Preserve gitops-lab,
the namespace, PVCs and audit logs.

References:
- https://argo-cd.readthedocs.io/en/stable/user-guide/sync-waves/
- https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/builds_using_buildconfig/triggering-builds-build-hooks
