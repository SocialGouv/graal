{{- define "graal.deployment" -}}
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ .resource.name }}
  labels:
{{ include "graal.resourceLabels" (dict "root" .root "component" .resource.component) | indent 4 }}
spec:
  replicas: {{ .resource.replicaCount }}
  selector:
    matchLabels:
{{ include "graal.componentLabels" (dict "root" .root "component" .resource.component) | indent 6 }}
  template:
    metadata:
      labels:
{{ include "graal.componentLabels" (dict "root" .root "component" .resource.component) | indent 8 }}
    spec:
{{- with .root.Values.imagePullSecrets }}
      imagePullSecrets:
{{ toYaml . | indent 8 }}
{{- end }}
      containers:
        - name: {{ .resource.container.name }}
          image: "{{ .resource.image.repository }}:{{ .resource.image.tag }}"
          imagePullPolicy: {{ .resource.image.pullPolicy }}
          ports:
            - name: {{ .resource.service.portName }}
              containerPort: {{ .resource.container.port }}
          livenessProbe:
{{ toYaml .resource.probes.liveness | indent 12 }}
          readinessProbe:
{{ toYaml .resource.probes.readiness | indent 12 }}
          startupProbe:
{{ toYaml .resource.probes.startup | indent 12 }}
{{- with .resource.container.env }}
          env:
{{ toYaml . | indent 12 }}
{{- end }}
{{- with .resource.container.envFrom }}
          envFrom:
{{ toYaml . | indent 12 }}
{{- end }}
          resources:
{{ toYaml .resource.resources | indent 12 }}
{{- end -}}
