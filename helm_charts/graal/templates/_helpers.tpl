{{- define "graal.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "graal.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- include "graal.name" . -}}
{{- end -}}
{{- end -}}

{{- define "graal.labels" -}}
app.kubernetes.io/name: {{ include "graal.name" . }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{- define "graal.selectorLabels" -}}
app.kubernetes.io/name: {{ include "graal.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "graal.componentLabels" -}}
{{ include "graal.selectorLabels" .root }}
component: {{ .component }}
{{- end -}}

{{- define "graal.resourceLabels" -}}
{{ include "graal.labels" .root }}
component: {{ .component }}
{{- end -}}
