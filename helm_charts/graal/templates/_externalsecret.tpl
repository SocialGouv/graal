{{- define "graal.externalSecret" -}}
apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata:
  name: {{ .secret.name }}
  labels:
    {{- include "graal.labels" .root | nindent 4 }}
spec:
  dataFrom:
    - extract:
        key: {{ .secret.dataFromKey }}
  refreshInterval: {{ .root.Values.externalSecrets.refreshInterval }}
  secretStoreRef:
    kind: {{ .root.Values.externalSecrets.secretStoreRef.kind }}
    name: {{ .root.Values.externalSecrets.secretStoreRef.name }}
  target:
    name: {{ .secret.name }}
    template:
      {{- if hasKey .secret.template "data" }}
      {{- toYaml .secret.template | nindent 6 }}
      {{- else }}
      data:
        {{- range $key, $value := .secret.template }}
        {{ $key }}: {{ $value | quote }}
        {{- end }}
      {{- end }}
{{- end -}}
