{{- define "pulseops.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "pulseops.fullname" -}}
{{- if .Values.fullnameOverride }}{{ .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}{{ else }}{{ printf "%s-%s" .Release.Name (include "pulseops.name" .) | trunc 63 | trimSuffix "-" }}{{ end }}
{{- end }}

{{- define "pulseops.labels" -}}
helm.sh/chart: {{ include "pulseops.name" . }}-{{ .Chart.Version | replace "+" "_" }}
app.kubernetes.io/name: {{ include "pulseops.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- define "pulseops.selectorLabels" -}}
app.kubernetes.io/name: {{ include "pulseops.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "pulseops.serviceAccountName" -}}
{{- if .Values.serviceAccount.name }}{{ .Values.serviceAccount.name }}{{ else }}{{ include "pulseops.fullname" . }}{{ end }}
{{- end }}
