{{- define "graal.ingress" -}}
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {{ .resource.ingress.name }}
  labels:
{{ include "graal.resourceLabels" (dict "root" .root "component" .resource.component) | indent 4 }}
{{- with .root.Values.ingressDefaults.annotations }}
  annotations:
{{ toYaml . | indent 4 }}
{{- end }}
spec:
  ingressClassName: {{ .root.Values.ingressDefaults.className }}
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
  tls:
    - hosts:
        - {{ .resource.ingress.host }}
      secretName: {{ .resource.ingress.tls.secretName }}
{{- end -}}
