# Deployment Guide

## Local Development

```bash
docker-compose up -d
./docker-compose.init.sh
```

## Kubernetes Deployment

```bash
helm install acraas ./infra/helm/fingerprint-ingestor
helm install acraas ./infra/helm/matching-engine
# ... etc
```

## Production Checklist

- [ ] Set strong JWT_SECRET
- [ ] Configure SSL/TLS
- [ ] Set up monitoring alerts
- [ ] Configure backup strategy
- [ ] Enable encryption at rest
- [ ] Set up disaster recovery
- [ ] Configure rate limiting
- [ ] Set up API gateway
