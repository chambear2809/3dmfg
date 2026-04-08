apiVersion: v1
kind: Secret
metadata:
  name: __SECRET_NAME__
  namespace: __NAMESPACE__
type: Opaque
stringData:
  TEAGENT_ACCOUNT_TOKEN: "__ACCOUNT_TOKEN__"
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: __PVC_NAME__
  namespace: __NAMESPACE__
spec:
  accessModes:
    - ReadWriteOnce
__STORAGE_CLASS_BLOCK__
  resources:
    requests:
      storage: __STORAGE_SIZE__
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: __DEPLOYMENT_NAME__
  namespace: __NAMESPACE__
spec:
  replicas: 1
  strategy:
    type: Recreate
  selector:
    matchLabels:
      app.kubernetes.io/name: thousandeyes-enterprise-agent
      app.kubernetes.io/instance: __DEPLOYMENT_NAME__
  template:
    metadata:
      labels:
        app.kubernetes.io/name: thousandeyes-enterprise-agent
        app.kubernetes.io/instance: __DEPLOYMENT_NAME__
    spec:
      hostname: __HOSTNAME__
      terminationGracePeriodSeconds: 30
      initContainers:
        - name: init-agent-state
          image: busybox:1.36
          imagePullPolicy: IfNotPresent
          command:
            - sh
            - -c
            - mkdir -p /state/te-agent /state/log
          volumeMounts:
            - name: agent-state
              mountPath: /state
      containers:
        - name: enterprise-agent
          image: __IMAGE__
          imagePullPolicy: IfNotPresent
          args:
            - /sbin/my_init
          env:
            - name: TEAGENT_ACCOUNT_TOKEN
              valueFrom:
                secretKeyRef:
                  name: __SECRET_NAME__
                  key: TEAGENT_ACCOUNT_TOKEN
            - name: TEAGENT_INET
              value: "__TEAGENT_INET__"
          resources:
            requests:
              cpu: "__CPU_REQUEST__"
              memory: "__MEMORY_REQUEST__"
            limits:
              memory: "__MEMORY_LIMIT__"
          securityContext:
            capabilities:
              add:
                - NET_ADMIN
          volumeMounts:
            - name: agent-state
              mountPath: /var/lib/te-agent
              subPath: te-agent
            - name: agent-state
              mountPath: /var/log/agent
              subPath: log
      volumes:
        - name: agent-state
          persistentVolumeClaim:
            claimName: __PVC_NAME__
