# API Reference

## Fingerprint Ingestor

### Submit Fingerprint
```
POST /api/v1/fingerprints
Content-Type: application/json

{
  "device_id": "uuid",
  "user_agent": "Mozilla/5.0...",
  "ip_address": "203.0.113.1",
  "metadata": {
    "timezone": "UTC",
    "language": "en"
  }
}

Response: 202 Accepted
```

## Advertiser API

### List Campaigns
```
GET /api/v1/campaigns?limit=100
Authorization: Bearer <token>

Response: 200 OK
{
  "campaigns": [],
  "total": 0
}
```

### Get Matches
```
GET /api/v1/matches?campaign_id=campaign123&limit=100
Authorization: Bearer <token>

Response: 200 OK
{
  "matches": [],
  "total": 0
}
```

## Privacy Service

### Get Consents
```
GET /api/v1/consents?user_id=user123

Response: 200 OK
{
  "user_id": "user123",
  "consents": []
}
```

### Grant Consent
```
POST /api/v1/consents
Content-Type: application/json

{
  "user_id": "user123",
  "consent_type": "marketing",
  "granted": true
}

Response: 201 Created
```
