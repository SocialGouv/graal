{{- define "graal.configmap" -}}
apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ include "graal.name" . }}
  labels:
{{ include "graal.labels" . | indent 4 }}
data:
{{ toYaml .Values.configMap.data | indent 2 }}
{{- end -}}
