# gitops-demo namespace adaptation (DRAFT / NOT APPROVED)

This overlay resolves the manifest/destination namespace mismatch for an existing Argo CD Application targeting `gitops-demo`. It does **not** authorize deployment or make the application runnable.

Source path: `ops/openshift/overlays/gitops-demo`. Destination namespace: `gitops-demo`. Argo CD AppProject and controller RBAC must independently allow those namespaced resources; this repository does not grant permissions or create the namespace.

The example uses the disabled base: all eight workloads have **zero replicas**. Images remain at `registry.invalid`, secrets, valid storage class, approved images, TLS, operator and security approvals remain missing. The `MINIO_ENDPOINT` ConfigMap value is explicitly corrected to `caddy.gitops-demo.svc:9002`, because Kustomize namespace rewriting does not rewrite strings.

The baseline `default-deny` and `dns-only` policies have been narrowed to pods labeled `app.kubernetes.io/part-of=investment`. **Other baseline NetworkPolicies use common application labels and may still affect unrelated pods in a shared namespace.** Do not sync into a shared namespace without an operator review of all NetworkPolicy selectors and existing services, PVC names and permissions. A dedicated namespace is strongly preferred.

Verify before any possible manual sync:

```sh
kubectl kustomize ops/openshift/overlays/gitops-demo
oc get namespace gitops-demo
oc auth can-i create deployments -n gitops-demo --as=system:serviceaccount:openshift-gitops:openshift-gitops-argocd-application-controller
```

Do **not** enable auto-sync, prune, namespace auto-creation or running replicas to bypass existing security gates. The actual GitOps controller ServiceAccount may differ.
