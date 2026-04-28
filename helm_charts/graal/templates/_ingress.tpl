{{- define "graal.ingress" -}}
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {{ .resource.ingress.name }}
  labels:
    {{- include "graal.labels" .root | nindent 4 }}
    component: {{ .resource.component }}
  annotations:
      cert-manager.io/cluster-issuer: letsencrypt
      cert-manager.io/private-key-size: "4096"
spec:
  ingressClassName: public
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
