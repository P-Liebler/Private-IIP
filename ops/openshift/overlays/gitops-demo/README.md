# Private-IIP: Argo CD start candidate (NOT VERIFIED)

**Branch:** feature/gitops-controlled-start-20261030
**Source code pin:** 4f3b8b83e58554fd74fc21c3c338ee0af62bb07a

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
   The active Sync Jobs and read-only Role are defined in the separately
   opt-in ops/gitops-startup Kustomize base. The pre-existing draft
   preflight under ops/openshift remains untouched and cannot be used
   to approve this deployment. A separate admission/security review is mandatory.
3. GitOps then applies existing namespaced services, scoped NetworkPolicies,
   PVCs, ConfigMaps and ServiceAccounts. The three PVCs remain protected
   from pruning and deletion. There is no cluster-scoped registry change.
4. PostgreSQL, Valkey, SeaweedFS and Caddy use one replica each.
   A PostgreSQL initContainer only checks volume write access. It does
   not chmod, chown, delete or reinitialize an existing volume.
5. A first-use Argo Sync Job runs Alembic upgrade head ONLY if the PostgreSQL
   database has no user relations. Existing databases with an unknown or
   outdated schema are rejected; data is never wiped or migrated blindly.
   Another Argo Sync Job creates ONLY the named SeaweedFS raw-ingestions
   bucket through its namespace-restricted internal management endpoint,
   if absent. A subsequent read-only gate checks schema and S3 access.
6. API, web, worker and scheduler only start after the gates pass.
   The private re-encrypt HTTPS route is applied afterwards.

## Known blockers — deployment is not yet usable

- The previous PostgreSQL pod crashed. Its logs were not captured, so the
  cause is NOT known. NFS permissions and OpenShift arbitrary UID remain
  possible issues, not proven causes. No PVC must be reset to work around this.
- A schema migration is not approved or automated for existing data.
  A verified empty database is initialized by the new Argo migration job.
  Any existing/outdated user schema still requires a reviewed backup and
  migration outside this first-use path.
- The raw-ingestions bucket was previously missing. A new scoped internal
  SeaweedFS bootstrap Job creates it by name without giving the application
  S3 identity global Admin rights. This internal management path and
  resulting credentials still require a runtime acceptance check.
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

## Data-safety invariant

The new database hook checks for existing PostgreSQL relations and refuses
all writes to any non-empty schema without an exact matching Alembic head.
It cannot fix PostgreSQL's previous CrashLoop if NFS permissions still fail.
The S3 hook can create one bucket named raw-ingestions, but cannot delete
existing objects. Its internal master/filer endpoint is namespaced and
NetworkPolicy-restricted; operator approval of that management boundary
is required before the first real sync.
