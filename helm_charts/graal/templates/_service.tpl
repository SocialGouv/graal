{{- define "graal.service" -}}
apiVersion: v1
kind: Service
metadata:
  name: {{ .resource.name }}
  labels:
{{ include "graal.resourceLabels" (dict "root" .root "component" .resource.component) | indent 4 }}
spec:
  type: {{ .resource.service.type }}
  selector:
{{ include "graal.componentLabels" (dict "root" .root "component" .resource.component) | indent 4 }}
  ports:
    - name: {{ .resource.service.portName }}
      port: {{ .resource.service.port }}
      targetPort: {{ .resource.service.targetPort }}
{{- end -}}
