# Kubernetes / Helm — Code Review Checklist

> Check sibling manifests and charts for existing patterns before flagging a convention (see Consistency Check step). Report an item only with a concrete trigger → effect in the changed configuration. A problem that a validator or scanner the repository runs, such as kubeconform, kube-linter, Checkov or `helm lint`, already reports is not a finding. This file covers Kubernetes manifests, Kustomize overlays, and Helm charts (`Chart.yaml`, `values*.yaml` and `templates/`). For a chart, judge the rendered result: a template together with the defaults in `values.yaml` and the overrides that the repository passes. Read the target Kubernetes version from the repository (for example `kubeVersion` in `Chart.yaml`), and apply an item that names a version only from that version. Admission policies in the repository, such as Pod Security labels on the namespace, Kyverno or Gatekeeper policies, can already reject a setting. An image name never shows the language or the framework of the application.

## Workload Security

- **Privileged containers and host access**: `privileged: true`, a `hostPath` volume (above all `/`, `/var/run/docker.sock` or `/var/lib/kubelet`) and added capabilities such as `SYS_ADMIN` can let a compromised container take over the node. `hostNetwork`, `hostPID` and `hostIPC` give access to the node's network, process or IPC namespaces, which is host resource access and reaches takeover only where a capability or path supports it. `allowPrivilegeEscalation` alone gives no node access: on Linux, a change from `false` to `true` lets setuid or setgid binaries and file capabilities gain privileges inside the container, while a newly explicit `true` where the field was unset (already allowed by default) changes nothing. Read the effective guards: a `privileged` container or one with `CAP_SYS_ADMIN` escalates regardless of the field, so `false` protects nothing there. Report a change that adds one of these to a workload that does not need node access, with its concrete effect; a weaker hardening setting or a field name alone is not enough. **Not a finding:** node agents, such as a CNI plugin, a log collector or a CSI driver, whose documented function needs it, and namespaces whose enforced Pod Security level rejects the pod, a broken deployment rather than a running exposure (see Precedents).
- **Broad RBAC for a workload**: a `Role` or `ClusterRole` with `"*"` in `verbs` or `resources`, `get`, `list` or `watch` on `secrets`, `create` on `pods` (a pod can mount any Secret of its namespace), `pods/exec`, or `escalate`, `bind` or `impersonate`, bound to the service account of an application, gives that application, and anyone who controls it, those powers. A `ClusterRoleBinding` grants them in every namespace. Report the concrete verb and resource. **Not a finding:** operators and controllers whose documented function needs the access, scoped to their namespace where they can be.
- **Service account tokens**: `automountServiceAccountToken` defaults to `true`, so every pod of a service account gets its token. Report a change that binds a powerful role to the `default` service account, which every pod in the namespace uses unless it names another one.
- **Secrets in manifests and values**: the `data` of a `Secret` is base64, not encryption. A `Secret` manifest, a `stringData` block or a `values.yaml` committed with a real password, key or token exposes it to everyone who can read the repository. **Not a finding:** encrypted forms such as Sealed Secrets or SOPS files, External Secrets references, and placeholder values that the deployment replaces.

**Bad** — the container runs privileged with the host's Docker socket:

```yaml
spec:
  containers:
    - name: report-worker
      image: registry.example.com/report-worker:1.4.2
      securityContext:
        privileged: true
      volumeMounts:
        - name: docker
          mountPath: /var/run/docker.sock
  volumes:
    - name: docker
      hostPath:
        path: /var/run/docker.sock
```

**Good** — no host access, and the restricted profile's settings:

```yaml
spec:
  containers:
    - name: report-worker
      image: registry.example.com/report-worker:1.4.2
      securityContext:
        runAsNonRoot: true
        allowPrivilegeEscalation: false
        capabilities:
          drop: ["ALL"]
        seccompProfile:
          type: RuntimeDefault
```

## Availability and Rollouts

- **Liveness probes that check dependencies**: a liveness probe that calls the database or another service restarts every replica when that dependency is slow or down, which turns a dependency outage into a full outage and adds restart load. A liveness probe without a `startupProbe` (or a long enough `initialDelaySeconds`) on an application that starts slowly restarts it before it is up. Point liveness at the process itself, and dependencies at readiness, if at all.
- **Memory limit below the runtime's heap**: a container whose memory `limits` is lower than the heap or cache that the application is configured to use (for example `-Xmx2g` with a `1Gi` limit) is killed with `OOMKilled` under load instead of failing gracefully.
- **Selector changes**: `spec.selector` of a `Deployment`, `StatefulSet` or `DaemonSet` (`apps/v1`) is immutable, so a change to it, often through Helm `selectorLabels` or a Kustomize `commonLabels`, makes the apply or `helm upgrade` fail for existing releases. The same holds for Job `spec.template` and several `StatefulSet` fields. A `Service` selector change can instead silently send traffic to no pods.
- **Disruption budgets that block drains**: a `PodDisruptionBudget` with `minAvailable` equal to the number of replicas, `minAvailable: 100%` or `maxUnavailable: 0` blocks every voluntary eviction, so node drains and cluster upgrades hang. Report it unless the repository documents that drains are handled by hand.
- **Mutable image tags**: an image referenced by a tag such as `latest` or `main` can change between pulls, so replicas can run different code and a rollback to an earlier revision does not bring back the earlier image. For `latest` or no tag, `imagePullPolicy` also defaults to `Always`. **Not a finding:** an image pinned by digest, and release tags that the registry makes immutable.

## Helm Templates

- **Values with the wrong YAML type**: `value: {{ .Values.port }}` or `value: {{ .Values.enabled }}` renders a number or a boolean, but an `env` value must be a string, so the API rejects the manifest; a value such as `0123` or `on` changes meaning as YAML. Use `quote` for strings.
- **Indentation of included blocks**: `{{ toYaml .Values.resources | indent 8 }}` placed after other text on the same line, or with the wrong width, renders YAML that nests the block under the wrong key or is invalid. Use `nindent` with the width of the target key.
- **Generated secrets that change on every upgrade**: `randAlphaNum` or `uuidv4` in a `Secret` template produces a new value on every `helm upgrade`, which breaks applications that stored the old password. Read the existing value with `lookup` first, and note that `lookup` returns an empty result during `helm template` and `--dry-run`, so the fallback runs there.
- **CRDs in `crds/`**: Helm installs the files in a chart's `crds/` directory only on the first install and never upgrades or deletes them, so a change there does not reach existing releases.

**Bad** — every `helm upgrade` writes a new password into the Secret:

```gotmpl
data:
  password: {{ randAlphaNum 24 | b64enc | quote }}
```

**Good** — the existing password is kept, and a new one is generated only on the first install:

```gotmpl
{{- $existing := lookup "v1" "Secret" .Release.Namespace "app-db" }}
data:
  {{- if $existing }}
  password: {{ index $existing.data "password" | quote }}
  {{- else }}
  password: {{ randAlphaNum 24 | b64enc | quote }}
  {{- end }}
```

## Conventions, not defects

- Labels and annotations beyond those that selectors, policies or tools read, resource request values without a measured problem, and the choice between Helm, Kustomize and plain manifests follow the repository's conventions.
- Missing `NetworkPolicy`, resource limits or probes on a workload are hardening suggestions, findings only with a concrete effect in the changed configuration.

## Sources

- Pod Security Standards and admission: https://kubernetes.io/docs/concepts/security/pod-security-standards/, https://kubernetes.io/docs/concepts/security/pod-security-admission/
- RBAC good practices: https://kubernetes.io/docs/concepts/security/rbac-good-practices/; service accounts: https://kubernetes.io/docs/tasks/configure-pod-container/configure-service-account/
- Secrets: https://kubernetes.io/docs/concepts/configuration/secret/
- Probes: https://kubernetes.io/docs/concepts/configuration/liveness-readiness-startup-probes/, https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/
- Deployments, rolling updates and selector updates: https://kubernetes.io/docs/concepts/workloads/controllers/deployment/; disruption budgets: https://kubernetes.io/docs/tasks/run-application/configure-pdb/
- Images and pull policy: https://kubernetes.io/docs/concepts/containers/images/; environment variable values: https://kubernetes.io/docs/reference/kubernetes-api/workload-resources/pod-v1/#environment-variables
- Helm templates, `quote`, `nindent`, `lookup`: https://helm.sh/docs/chart_template_guide/function_list/, https://helm.sh/docs/chart_template_guide/functions_and_pipelines/; CRDs: https://helm.sh/docs/chart_best_practices/custom_resource_definitions/

## Precedents

- **Pod Security admission rejects forbidden pods**: when a namespace has the label `pod-security.kubernetes.io/enforce` set to `baseline` or `restricted` (stable since Kubernetes 1.25), the API server rejects pods that break that level, such as privileged containers or `hostPath` volumes. Do not report such a setting as an exposure in that namespace. **Exception:** `warn` or `audit` labels without `enforce`, the `privileged` level, namespaces or users exempted in the admission configuration, workloads deployed to other namespaces, a change that also edits the namespace labels, and clusters older than 1.23 without the admission controller; the rejected pod is still a broken deployment.
- **Rolling updates keep a bounded number of pods available**: with the default `RollingUpdate` strategy (25% `maxUnavailable`, rounded down, and 25% `maxSurge`, rounded up), a `Deployment` may remove an old pod before its replacement is ready, but it keeps at least the desired replicas minus `maxUnavailable` pods available, and only ready pods count. The rounded-down budget is 0 for 1 to 3 replicas, so an old pod goes only after its replacement is ready; from 4 replicas one old pod can go first, leaving three of four serving. Do not report a full outage, or the overlap of old and new pods alone, from a rollout of such a `Deployment` whose pods have a readiness probe and whose remaining ready pods carry the load. **Exception:** `strategy.type: Recreate`; a `maxUnavailable` that equals or exceeds the replica count; a positive `maxUnavailable` below the replica count where the remaining pods lack the capacity for the load; pods without a readiness probe, which count as ready as soon as their containers start; pods that do not stop serving on SIGTERM (no `preStop` hook or connection draining), which drop requests when the controller removes them; `StatefulSet` and `DaemonSet` rollouts; and changes to the `Service` in front of the pods.
- **Secret references do not copy values**: `secretKeyRef`, `envFrom` with `secretRef` and Secret volumes read the value from the cluster when the pod starts, so a manifest that names a Secret holds no credential. Do not report a credential exposed in a manifest that only references a Secret by name. **Exception:** the referenced `Secret` committed with real values in `data` or `stringData`, the value copied into a `ConfigMap`, an annotation or a command-line argument, and applications that print their environment in logs.
