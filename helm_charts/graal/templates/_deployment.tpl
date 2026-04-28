{{- define "graal.deployment" -}}
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ .resource.name }}
  labels:
    {{- include "graal.labels" .root | nindent 4 }}
    component: {{ .resource.component }}
spec:
  replicas: {{ .resource.replicaCount }}
  selector:
    matchLabels:
      {{- include "graal.componentLabels" (dict "root" .root "component" .resource.component) | nindent 6 }}
  template:
    metadata:
      labels:
        {{- include "graal.componentLabels" (dict "root" .root "component" .resource.component) | nindent 8 }}
    spec:
      imagePullSecrets:
        - name: graal-registry-secret
      containers:
        - name: {{ .resource.container.name }}
          image: "{{ .resource.image.repository }}:{{ .resource.image.tag }}"
          imagePullPolicy: {{ .resource.image.pullPolicy }}
          ports:
            - name: {{ .resource.service.portName }}
              containerPort: {{ .resource.container.port }}
          livenessProbe:
            {{- toYaml .resource.probes.liveness | nindent 12 }}
          readinessProbe:
            {{- toYaml .resource.probes.readiness | nindent 12 }}
          startupProbe:
            {{- toYaml .resource.probes.startup | nindent 12 }}
          {{- if .resource.container.env }}
          env:
            {{- toYaml .resource.container.env | nindent 12 }}
          {{- end }}
          {{- if .resource.container.envFrom }}
          envFrom:
            {{- toYaml .resource.container.envFrom | nindent 12 }}
          {{- end }}
          resources:
            {{- toYaml .resource.resources | nindent 12 }}
{{- end -}}
