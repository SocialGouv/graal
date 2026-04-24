{{- define "graal.ingress" -}}
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {{ .resource.ingress.name }}
  labels:
    {{- include "graal.labels" .root | nindent 4 }}
    component: {{ .resource.component }}
  annotations:
    {{- toYaml .resource.ingress.annotations | nindent 4 }}
spec:
  ingressClassName: {{ .resource.ingress.ingressClassName }}
  rules:
    - host: {{ .resource.ingress.host }}
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: {{ .resource.name }}
                port:
                  name: {{ .resource.service.portName }}
  {{- if .resource.ingress.tls.enabled }}
  tls:
    - hosts:
        - {{ .resource.ingress.host }}
      secretName: {{ .resource.ingress.tls.secretName }}
  {{- end }}
{{- end -}}
