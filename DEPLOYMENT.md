# Fase 4: Guía de Deployment a Producción

## Índice
1. [Requisitos Previos](#requisitos-previos)
2. [Seguridad & Secretos](#seguridad--secretos)
3. [Deployment Local con Docker](#deployment-local-con-docker)
4. [Deployment a Producción (AWS ECS)](#deployment-a-producción-aws-ecs)
5. [Monitoreo & Alertas](#monitoreo--alertas)
6. [Backups & Restore](#backups--restore)
7. [Troubleshooting](#troubleshooting)
8. [Rollback & Recovery](#rollback--recovery)

---

## Requisitos Previos

### Local Development
- Python 3.11+
- Docker & Docker Compose
- Git
- PostgreSQL 16 (o usar Docker)
- Redis 7 (o usar Docker)

### Producción (AWS)
- AWS Account con permisos de:
  - ECS (Elastic Container Service)
  - ECR (Elastic Container Registry)
  - RDS (PostgreSQL managed)
  - ElastiCache (Redis managed)
  - S3 (backups)
  - CloudWatch (logs)
  - Route53 (DNS)
  - ALB (Application Load Balancer)

---

## Seguridad & Secretos

### 1. Generar Secretos Requeridos

```bash
# JWT Secret Key (32+ caracteres)
openssl rand -base64 32

# PostgreSQL Password
openssl rand -base64 24

# Redis Password
openssl rand -base64 24
```

### 2. GitHub Secrets (para CI/CD)

En tu repositorio GitHub:
1. Settings → Secrets and variables → Actions
2. Crear los siguientes secrets:

```
AWS_ACCESS_KEY_ID_STAGING=<tu-key>
AWS_SECRET_ACCESS_KEY_STAGING=<tu-secret>
AWS_ACCESS_KEY_ID_PRODUCTION=<tu-key>
AWS_SECRET_ACCESS_KEY_PRODUCTION=<tu-secret>
SLACK_WEBHOOK_URL=<tu-webhook>
DOCKER_USERNAME=<tu-usuario>
DOCKER_PASSWORD=<tu-token>
```

### 3. Variables de Entorno

**NUNCA** guardes .env en git. 

**Archivos recomendados:**
- `.env.example` - Plantilla (commitear a git)
- `.env` - Local (NO commitar)
- `.env.production` - Plantilla producción (NO commitar, ejemplo para referencia)

**Configurar en el servidor:**
```bash
# Copiar y editar
cp .env.example .env
# Editar con valores reales
nano .env

# Permisos restrictivos
chmod 600 .env
```

---

## Deployment Local con Docker

### 1. Setup Inicial

```bash
# Clonar y preparar
git clone <tu-repo>
cd nuevo-proyecto

# Crear archivos de configuración
cp .env.example .env
# Editar .env con valores locales

# Crear directorios requeridos
mkdir -p data/logs data/backups
```

### 2. Stack Básico (App + DB + Redis)

```bash
# Iniciar servicios
docker-compose up -d

# Verificar salud
docker-compose ps
docker-compose logs app

# Ver endpoints
curl http://localhost:8001/health
```

### 3. Stack Completo (+ Monitoreo)

```bash
# Agregar stack de monitoreo
docker-compose -f docker-compose.yml \
  -f docker-compose.monitoring.yml up -d

# Acceder a dashboards
# App: http://localhost:8001
# Grafana: http://localhost:3000 (admin/admin)
# Prometheus: http://localhost:9090
# Flower (Celery): http://localhost:5555
```

### 4. Migraciones de Base de Datos

```bash
# En el contenedor
docker-compose exec app alembic upgrade head

# O si ejecutas localmente
alembic upgrade head
```

### 5. Crear Datos de Prueba

```bash
docker-compose exec app python -c "
from backend.db import init_db
init_db()
"
```

---

## Deployment a Producción (AWS ECS)

### 1. Build & Push a ECR

```bash
# Configure AWS CLI
aws configure

# Login to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  <account-id>.dkr.ecr.us-east-1.amazonaws.com

# Build and tag
docker build -t radar-precios:latest .
docker tag radar-precios:latest \
  <account-id>.dkr.ecr.us-east-1.amazonaws.com/radar-precios:latest

# Push
docker push \
  <account-id>.dkr.ecr.us-east-1.amazonaws.com/radar-precios:latest
```

### 2. RDS PostgreSQL Setup

```bash
# Crear instancia RDS
aws rds create-db-instance \
  --db-instance-identifier radar-prod \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --master-username radar \
  --master-user-password <strong-password> \
  --allocated-storage 100 \
  --storage-type gp3 \
  --publicly-accessible false \
  --backup-retention-period 30

# Esperar a que esté disponible (5-10 min)
aws rds describe-db-instances \
  --db-instance-identifier radar-prod
```

### 3. ElastiCache Redis Setup

```bash
# Crear cluster Redis
aws elasticache create-cache-cluster \
  --cache-cluster-id radar-redis-prod \
  --engine redis \
  --cache-node-type cache.t3.micro \
  --num-cache-nodes 1 \
  --security-group-ids sg-xxxxx

# Obtener endpoint
aws elasticache describe-cache-clusters \
  --cache-cluster-id radar-redis-prod
```

### 4. ECS Task Definition

Crear `ecs-task-definition.json`:

```json
{
  "family": "radar-precios",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "containerDefinitions": [
    {
      "name": "radar-app",
      "image": "<account-id>.dkr.ecr.us-east-1.amazonaws.com/radar-precios:latest",
      "portMappings": [
        {
          "containerPort": 8001,
          "hostPort": 8001,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "ENVIRONMENT",
          "value": "production"
        },
        {
          "name": "DEBUG",
          "value": "false"
        }
      ],
      "secrets": [
        {
          "name": "DATABASE_URL",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:xxx:secret:radar/db-url"
        },
        {
          "name": "JWT_SECRET_KEY",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:xxx:secret:radar/jwt-key"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/radar-precios",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8001/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
```

### 5. Registrar y Deploy a ECS

```bash
# Registrar task definition
aws ecs register-task-definition \
  --cli-input-json file://ecs-task-definition.json

# Crear cluster
aws ecs create-cluster --cluster-name radar-production

# Crear service
aws ecs create-service \
  --cluster radar-production \
  --service-name radar-app \
  --task-definition radar-precios \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxxxx],securityGroups=[sg-xxxxx],assignPublicIp=DISABLED}" \
  --load-balancers "targetGroupArn=arn:aws:elasticloadbalancing:...,containerName=radar-app,containerPort=8001"
```

---

## Monitoreo & Alertas

### 1. Acceder a Prometheus

```
http://your-domain:9090
```

Verificar:
- Targets → All endpoints green
- Alerts → Ver reglas definidas

### 2. Acceder a Grafana

```
http://your-domain:3000
```

Default: admin/admin

- Dashboard: Radar Overview
- Configurar alertas
- Integrar Slack/PagerDuty

### 3. Configurar Alertas Slack

En `alertmanager.yml`:
```yaml
receivers:
  - name: 'slack'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL'
        channel: '#alerts'
```

Reload:
```bash
docker-compose exec alertmanager \
  kill -HUP 1
```

---

## Backups & Restore

### 1. Backup Automático

Ya está configurado en Celery beat cada 24 horas.

Ver logs:
```bash
docker-compose logs celery_beat
```

### 2. Backup Manual

```bash
# En el contenedor
docker-compose exec app python -c "
from backend.backup import BackupManager
manager = BackupManager()
results = manager.backup_all()
print(results)
"

# Archivos guardados en data/backups/
```

### 3. Subir a S3

```bash
# Configurar AWS credentials
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...

# Script de backup
docker-compose exec app python -c "
from backend.backup import BackupManager
manager = BackupManager()
manager.backup_all()
manager.upload_to_s3()
"
```

### 4. Restore desde Backup

```bash
docker-compose exec app python -c "
from backend.backup import BackupManager
manager = BackupManager()
# Usar timestamp del backup
manager.restore_database('20240428_143022')
"
```

---

## Troubleshooting

### App no inicia

```bash
# Ver logs
docker-compose logs app -f

# Verificar conectividad
docker-compose exec app curl http://redis:6379
docker-compose exec app psql postgresql://...
```

### Redis connection refused

```bash
# Verificar Redis
docker-compose logs redis
docker-compose exec redis redis-cli ping

# Reiniciar
docker-compose restart redis
```

### High latency

1. Ver Grafana → Request Latency
2. Revisar database metrics
3. Verificar Celery queue size
4. Escalizar si es necesario

### Out of memory

```bash
# Ver uso
docker stats

# Aumentar limits en docker-compose.yml
# Reiniciar
docker-compose restart
```

---

## Rollback & Recovery

### 1. Rollback de Código

```bash
# Volver a tag anterior
git checkout v0.1.0

# Reconstruir y deploy
docker build -t radar-precios:v0.1.0 .
docker push ...

# Actualizar ECS task definition con image:v0.1.0
aws ecs update-service \
  --cluster radar-production \
  --service radar-app \
  --force-new-deployment
```

### 2. Restore de Base de Datos

```bash
# Verificar backups disponibles
ls -la data/backups/

# Restore
docker-compose exec app python -c "
from backend.backup import BackupManager
manager = BackupManager()
success, msg = manager.restore_database('20240428_120000')
print(msg)
"
```

### 3. Rollback a Checkpoint

- Para RDS: usar AWS RDS snapshots (automated backups)
- Para Redis: restore desde dump

---

## Checklist de Deployment

- [ ] Secretos generados y configurados
- [ ] GitHub secrets configurados
- [ ] .env creado (NO en git)
- [ ] Database migrada (alembic upgrade head)
- [ ] Tests pasando (`pytest`)
- [ ] Docker builds sin errores
- [ ] Health checks responden
- [ ] Backups funcionan
- [ ] Monitoring accesible
- [ ] Alertas configuradas
- [ ] DNS actualizado
- [ ] SSL/TLS certificado
- [ ] Load balancer configurado
- [ ] Documentación actualizada
- [ ] Plan de incidentes definido

---

## Links Útiles

- [AWS ECS Best Practices](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/recommended-practices.html)
- [PostgreSQL Performance Tuning](https://www.postgresql.org/docs/current/performance-tips.html)
- [Redis Production Guidelines](https://redis.io/documentation#using-redis)
- [Prometheus Alerting](https://prometheus.io/docs/alerting/latest/overview/)
- [Grafana Dashboards](https://grafana.com/docs/grafana/latest/dashboards/)
