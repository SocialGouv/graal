{{- define "graal.service" -}}
apiVersion: v1
kind: Service
metadata:
  name: {{ .resource.name }}
  labels:
    {{- include "graal.labels" .root | nindent 4 }}
    component: {{ .resource.component }}
spec:
  type: {{ .resource.service.type }}
  selector:
    {{- include "graal.componentLabels" (dict "root" .root "component" .resource.component) | nindent 4 }}
  ports:
    - name: {{ .resource.service.portName }}
      port: {{ .resource.service.port }}
      targetPort: {{ .resource.service.targetPort }}
{{- end -}}
