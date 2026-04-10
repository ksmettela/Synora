# ACRaaS Platform API Reference
**Version 1.0 · Base URL: https://api.acraas.io**

## Table of Contents

1. [Authentication](#authentication)
2. [Rate Limits](#rate-limits)
3. [Error Handling](#error-handling)
4. [Endpoints](#endpoints)
   - [Authentication](#authentication-endpoints)
   - [Segment Management](#segment-management)
   - [Real-Time Bidding](#real-time-bidding-rtb)
   - [Targeting & Reach](#targeting--reach)
   - [Reports](#reports)
   - [Privacy](#privacy-endpoints)
   - [Billing](#billing-endpoints)
5. [Webhooks](#webhooks)
6. [SDKs & Client Libraries](#sdks--client-libraries)
7. [Changelog](#changelog)

---

## Authentication

ACRaaS uses OAuth2 client credentials flow for API authentication. All API requests must include a Bearer token in the Authorization header.

### Step 1: Obtain Credentials

1. Log in to https://portal.acraas.io/developers
2. Navigate to "API Credentials"
3. Create a new application
4. Copy your `client_id` and `client_secret` (store securely)

### Step 2: Request Access Token

**Endpoint**: `POST /v1/auth/token`

**Request**:
```bash
curl -X POST https://api.acraas.io/v1/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "client_secret=YOUR_CLIENT_SECRET"
```

**Response** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "scope": "read write"
}
```

### Step 3: Use Token in Requests

Include the Bearer token in all subsequent API calls:

```bash
curl -X GET https://api.acraas.io/v1/segments \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### Token Expiration & Refresh

- **Expiration**: Access tokens expire after 1 hour (`expires_in: 3600`)
- **Refresh Strategy**: Request a new token before expiry by calling `POST /v1/auth/token` again with the same credentials
- **No refresh tokens**: Use client credentials grant repeatedly for each new token

**Python Example**:
```python
import requests
from datetime import datetime, timedelta

class AcrAuthManager:
    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        self.token_expiry = None
    
    def get_token(self):
        if self.access_token and datetime.now() < self.token_expiry:
            return self.access_token
        
        response = requests.post(
            "https://api.acraas.io/v1/auth/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            }
        )
        response.raise_for_status()
        
        data = response.json()
        self.access_token = data["access_token"]
        self.token_expiry = datetime.now() + timedelta(seconds=data["expires_in"] - 60)
        
        return self.access_token
    
    def get_headers(self):
        return {"Authorization": f"Bearer {self.get_token()}"}

# Usage
auth = AcrAuthManager("YOUR_CLIENT_ID", "YOUR_CLIENT_SECRET")
response = requests.get(
    "https://api.acraas.io/v1/segments",
    headers=auth.get_headers()
)
```

---

## Rate Limits

ACRaaS enforces rate limits per endpoint to ensure fair resource usage and platform stability. Rate limits are applied per client (identified by `client_id`).

| Endpoint | Rate Limit | Burst Limit | Window |
|---|---|---|---|
| `POST /v1/sync/openrtb` | 10,000 req/min | 1,000 req/sec | 1 minute |
| `GET /v1/segments` | 100 req/min | 50 req/sec | 1 minute |
| `POST /v1/segments` | 10 req/min | 5 req/sec | 1 minute |
| `GET /v1/segments/{id}/size` | 100 req/min | 50 req/sec | 1 minute |
| `POST /v1/targeting/activate` | 100 req/min | 20 req/sec | 1 minute |
| `GET /v1/targeting/reach` | 100 req/min | 20 req/sec | 1 minute |
| `GET /v1/reports/*` | 50 req/min | 10 req/sec | 1 minute |
| All other endpoints | 100 req/min | 20 req/sec | 1 minute |

### Rate Limit Headers

All responses include rate limit information:

```
X-RateLimit-Limit: 10000
X-RateLimit-Remaining: 9950
X-RateLimit-Reset: 1712761800
```

- `X-RateLimit-Limit`: Maximum requests per window
- `X-RateLimit-Remaining`: Requests remaining in current window
- `X-RateLimit-Reset`: Unix timestamp when limit window resets

### Handling Rate Limits

If you exceed the rate limit, the API returns HTTP 429 (Too Many Requests):

```json
{
  "error": "rate_limit_exceeded",
  "message": "Rate limit exceeded: 10000 req/min",
  "retry_after": 45
}
```

**Recommended strategy**: Implement exponential backoff with jitter:

```python
import random
import time
import requests

def call_api_with_retry(url, headers, max_retries=5):
    for attempt in range(max_retries):
        response = requests.get(url, headers=headers)
        
        if response.status_code != 429:
            return response
        
        # Extract retry_after or use exponential backoff
        retry_after = int(response.headers.get("Retry-After", 2 ** attempt))
        jitter = random.uniform(0, retry_after * 0.1)
        
        print(f"Rate limited. Retrying in {retry_after + jitter:.1f}s...")
        time.sleep(retry_after + jitter)
    
    raise Exception("Max retries exceeded")
```

---

## Error Handling

All error responses follow a consistent JSON format with `error`, `message`, `details`, and `request_id` fields.

### Standard Error Response

```json
{
  "error": "invalid_segment_rule",
  "message": "Rule type 'watched_sport' is not a valid rule type.",
  "details": {
    "field": "rules[2].type",
    "provided": "watched_sport",
    "valid_types": ["watched_genre", "watched_network", "household_income", "dma", "daypart"]
  },
  "request_id": "req_abc123def456xyz"
}
```

- `error`: Machine-readable error code
- `message`: Human-readable error description
- `details`: Additional context (field name, provided value, valid options)
- `request_id`: Unique ID for debugging (include when contacting support)

### HTTP Status Codes

| Code | Meaning | Example |
|---|---|---|
| 200 | OK | Request succeeded |
| 201 | Created | New resource created |
| 202 | Accepted | Async request queued (check status later) |
| 400 | Bad Request | Invalid input (missing required field, invalid format) |
| 401 | Unauthorized | Missing or invalid authentication token |
| 403 | Forbidden | Authenticated but not authorized (insufficient permissions) |
| 404 | Not Found | Resource does not exist |
| 409 | Conflict | Resource already exists or constraint violated |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Server Error | Unexpected server error |
| 503 | Service Unavailable | API temporarily unavailable |

### Common Error Codes

| Error Code | HTTP Status | Cause | Resolution |
|---|---|---|---|
| `invalid_token` | 401 | Token is invalid, expired, or missing | Obtain a new token via `/v1/auth/token` |
| `insufficient_permissions` | 403 | Client doesn't have permission to access resource | Contact admin to grant permissions |
| `validation_error` | 400 | Request payload fails validation | Check field types, required fields, format |
| `resource_not_found` | 404 | Requested segment/device/report doesn't exist | Verify the resource ID is correct |
| `resource_exists` | 409 | Cannot create resource; already exists | Use PUT to update instead of POST |
| `rate_limit_exceeded` | 429 | Rate limit exceeded | Implement backoff, reduce request frequency |
| `invalid_query` | 400 | DSL query syntax error | Review segment rule syntax in documentation |
| `internal_error` | 500 | Unexpected server error | Retry with exponential backoff; contact support if persistent |

---

## Endpoints

### Authentication Endpoints

#### POST /v1/auth/token

Request OAuth2 client credentials access token.

**Request Parameters**:
```json
{
  "grant_type": "client_credentials",
  "client_id": "your_client_id",
  "client_secret": "your_client_secret"
}
```

**Response** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "scope": "read write"
}
```

**Errors**:
- `invalid_client` (401): Invalid client_id or client_secret
- `unsupported_grant_type` (400): grant_type must be "client_credentials"

**cURL Example**:
```bash
curl -X POST https://api.acraas.io/v1/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=YOUR_ID&client_secret=YOUR_SECRET"
```

---

### Segment Management

Segments are audience cohorts defined by rules (e.g., "viewers of sports content in DMA 100").

#### GET /v1/segments

List all segments created by this client.

**Query Parameters**:
- `limit` (int, optional): Max results (default: 20, max: 100)
- `offset` (int, optional): Pagination offset (default: 0)
- `status` (string, optional): Filter by status: `active`, `archived`

**Response** (200 OK):
```json
{
  "segments": [
    {
      "id": "seg_sports_male_25_54",
      "name": "Sports Fans (M25-54)",
      "description": "Male viewers aged 25-54 watching sports",
      "rules": [
        {
          "type": "watched_genre",
          "values": ["sports"]
        },
        {
          "type": "household_income",
          "operator": ">=",
          "value": 50000
        }
      ],
      "created_at": "2026-03-15T10:30:00Z",
      "status": "active",
      "estimated_size": 1250000,
      "estimated_size_at": "2026-04-10T00:00:00Z"
    }
  ],
  "total": 42,
  "limit": 20,
  "offset": 0
}
```

**Errors**:
- `invalid_query` (400): Invalid query parameter

**Python Example**:
```python
import requests

def list_segments(headers, limit=20, offset=0):
    response = requests.get(
        "https://api.acraas.io/v1/segments",
        headers=headers,
        params={"limit": limit, "offset": offset}
    )
    response.raise_for_status()
    return response.json()

segments = list_segments(auth_headers)
for seg in segments["segments"]:
    print(f"{seg['name']}: {seg['estimated_size']:,} users")
```

#### POST /v1/segments

Create a new audience segment with custom rules.

**Request Body**:
```json
{
  "name": "Tech Enthusiasts (CA, 18-35)",
  "description": "Tech-interested viewers in California, ages 18-35",
  "rules": [
    {
      "type": "watched_genre",
      "values": ["technology", "science"]
    },
    {
      "type": "dma",
      "values": ["801", "803", "804"]
    },
    {
      "type": "household_income",
      "operator": ">=",
      "value": 75000
    },
    {
      "type": "daypart",
      "values": ["primetime", "latenight"]
    }
  ]
}
```

**Segment Rule Types** (DSL Reference):

| Rule Type | Values | Description | Example |
|---|---|---|---|
| `watched_genre` | Array of genres | Content genres watched | `["sports", "news", "comedy"]` |
| `watched_network` | Array of networks | TV networks watched | `["ESPN", "HBO", "NBC"]` |
| `household_income` | int (>=, <=) | Household income range | `{"operator": ">=", "value": 50000}` |
| `dma` | Array of DMA codes | Designated Market Areas | `["801", "100", "203"]` |
| `daypart` | Array of dayparts | Time of day watching | `["morning", "afternoon", "primetime", "latenight"]` |

**Valid Genres**:
- sports, news, comedy, drama, reality, documentary, educational, animated, music, cooking, home_improvement, health_fitness, action, adventure, sci_fi, horror, romance, family, teen, talk_show, variety, award_shows, game_shows, movies, streaming_exclusive

**Valid Networks**:
- ESPN, HBO, NBC, ABC, CBS, FOX, HULU, NETFLIX, PRIME_VIDEO, APPLE_TV, YOUTUBE, BRAVO, AMC, FOOD_NETWORK, HISTORY, NATIONAL_GEOGRAPHIC, DISCOVERY, PARAMOUNT, SHOWTIME, STARZ, PEACOCK, MAX

**Valid DMA Codes**:
- 100 = New York, 200 = Los Angeles, 203 = San Francisco, 205 = Sacramento, 206 = Las Vegas, 213 = Phoenix, 301 = Dallas-Fort Worth, 303 = Houston, 308 = San Antonio, 500 = Denver, 501 = Salt Lake City, 506 = Albuquerque, 602 = Chicago, 603 = Indianapolis, 610 = St. Louis, ... [Complete list](https://dma-codes.acraas.io)

**Response** (201 Created):
```json
{
  "id": "seg_tech_enthusiasts_ca",
  "name": "Tech Enthusiasts (CA, 18-35)",
  "description": "Tech-interested viewers in California, ages 18-35",
  "rules": [
    {"type": "watched_genre", "values": ["technology", "science"]},
    {"type": "dma", "values": ["801", "803", "804"]},
    {"type": "household_income", "operator": ">=", "value": 75000},
    {"type": "daypart", "values": ["primetime", "latenight"]}
  ],
  "created_at": "2026-04-10T15:30:45Z",
  "status": "active",
  "estimated_size": 450000,
  "estimated_size_at": "2026-04-10T15:30:45Z"
}
```

**Errors**:
- `validation_error` (400): Invalid rule type or values
- `invalid_query` (400): Conflicting rules or logical error

**cURL Example**:
```bash
curl -X POST https://api.acraas.io/v1/segments \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Sports Fans",
    "rules": [
      {"type": "watched_genre", "values": ["sports"]}
    ]
  }'
```

#### GET /v1/segments/{segment_id}/size

Get real-time audience size estimate for a specific segment.

**Path Parameters**:
- `segment_id` (string): ID of the segment

**Response** (200 OK):
```json
{
  "segment_id": "seg_sports_fans",
  "estimated_size": 2500000,
  "size_range": {
    "low": 2400000,
    "high": 2600000,
    "confidence": 0.95
  },
  "sample_size": 150000,
  "updated_at": "2026-04-10T14:00:00Z"
}
```

- `estimated_size`: Point estimate of audience size
- `size_range`: 95% confidence interval (low/high bounds)
- `confidence`: Confidence level of estimate
- `sample_size`: Number of devices measured to create estimate
- `updated_at`: When this estimate was last computed

**Errors**:
- `resource_not_found` (404): Segment doesn't exist

#### DELETE /v1/segments/{segment_id}

Delete a segment and archive its history.

**Path Parameters**:
- `segment_id` (string): ID of the segment to delete

**Response** (202 Accepted):
```json
{
  "segment_id": "seg_sports_fans",
  "status": "archived",
  "archived_at": "2026-04-10T15:45:00Z",
  "message": "Segment archived. Historical data retained for 90 days."
}
```

**Notes**:
- Deletion is soft (archive). Historical data is retained for 90 days.
- Archived segments cannot be restored via API.
- Data is permanently deleted after 90 days.

**Errors**:
- `resource_not_found` (404): Segment doesn't exist
- `resource_in_use` (409): Segment is actively being targeted; stop campaigns first

---

### Real-Time Bidding (RTB)

The OpenRTB endpoint is the core API used by demand-side platforms (DSPs) during programmatic advertising auctions.

#### POST /v1/sync/openrtb

Synchronous OpenRTB auction request. DSPs call this endpoint to determine if a device matches a target audience segment during a bid request.

**Purpose**: When a DSP wants to bid on an ad impression for a user, it calls this endpoint with the device ID to check what segments that device belongs to. The response indicates if the device matches the target segment(s) and at what price.

**Latency SLA**: < 5ms (p99)

**Request Body** (OpenRTB 2.5 format):
```json
{
  "id": "bid_req_12345",
  "device": {
    "id": "acr_device_abc123def456",
    "ip": "192.168.1.100",
    "ua": "Mozilla/5.0 (SmartTV; Tizen) AppleWebKit/537.36"
  },
  "user": {
    "id": "user_xyz789"
  },
  "imp": [
    {
      "id": "imp_1",
      "bidfloor": 0.50,
      "bidfloorcur": "USD",
      "instl": 0
    }
  ],
  "bcat": ["IAB25-3"],
  "badv": ["example.com"],
  "ext": {
    "acraas": {
      "segment_ids": ["seg_sports_fans", "seg_premium_income"],
      "target_type": "any"
    }
  }
}
```

**Response** (200 OK):
```json
{
  "id": "bid_req_12345",
  "bidid": "bid_resp_xyz789",
  "seatbid": [
    {
      "bid": [
        {
          "id": "bid_1",
          "impid": "imp_1",
          "price": 2.50,
          "adid": "ad_sports_premium",
          "adomain": ["advertiser.com"],
          "cid": "campaign_123",
          "crid": "creative_456",
          "ext": {
            "acraas": {
              "matches": [
                {
                  "segment_id": "seg_sports_fans",
                  "match_type": "device",
                  "confidence": 0.98,
                  "price_multiplier": 1.2
                },
                {
                  "segment_id": "seg_premium_income",
                  "match_type": "household",
                  "confidence": 0.85,
                  "price_multiplier": 1.5
                }
              ],
              "device_profile": {
                "household_estimated_income": 150000,
                "dma": "100",
                "favorite_genres": ["sports", "news"]
              },
              "ttl_seconds": 300
            }
          }
        }
      ],
      "seat": "acraas"
    }
  ],
  "ext": {
    "acraas": {
      "request_id": "req_abc123"
    }
  }
}
```

**Key Fields**:

- `matches`: Array of matching segments
  - `segment_id`: The segment that matched
  - `match_type`: How device was matched ("device", "household", or "ip")
  - `confidence`: Confidence in match (0-1)
  - `price_multiplier`: Price adjustment for this segment match (1.0 = baseline)
- `device_profile`: Inferred demographic/interest data (when consent allows)
- `ttl_seconds`: How long this match result is valid (cache this long)

**Match Types**:
- `device`: Matched via unique ACRaaS device ID (highest confidence)
- `household`: Matched via IP household grouping (medium confidence)
- `ip`: Matched via IP prefix only (lowest confidence)

**cURL Example**:
```bash
curl -X POST https://api.acraas.io/v1/sync/openrtb \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "bid_req_1",
    "device": {"id": "acr_abc123"},
    "imp": [{"id": "imp_1", "bidfloor": 0.50}],
    "ext": {
      "acraas": {
        "segment_ids": ["seg_sports_fans"],
        "target_type": "any"
      }
    }
  }'
```

**Python Example** (DSP Integration):
```python
import requests

class AcraasDSP:
    def __init__(self, access_token):
        self.headers = {"Authorization": f"Bearer {access_token}"}
        self.base_url = "https://api.acraas.io/v1"
    
    def check_segment_match(self, device_id, segment_ids):
        request = {
            "device": {"id": device_id},
            "ext": {
                "acraas": {
                    "segment_ids": segment_ids,
                    "target_type": "any"
                }
            }
        }
        
        response = requests.post(
            f"{self.base_url}/sync/openrtb",
            json=request,
            headers=self.headers,
            timeout=0.100  # 100ms timeout for RTB latency
        )
        response.raise_for_status()
        
        result = response.json()
        if result.get("seatbid"):
            matches = result["seatbid"][0]["bid"][0]["ext"]["acraas"]["matches"]
            return {
                "matched": len(matches) > 0,
                "segments": matches,
                "ttl": result["seatbid"][0]["bid"][0]["ext"]["acraas"]["ttl_seconds"]
            }
        return {"matched": False, "segments": []}

# Usage in DSP bid logic
dsp = AcraasDSP("your_token")
result = dsp.check_segment_match("acr_device_123", ["seg_sports", "seg_premium"])
if result["matched"]:
    print(f"Device matches segments: {[m['segment_id'] for m in result['segments']]}")
    # Place a bid
```

**Integration Checklist for DSPs**:
- [ ] Implement 100ms timeout (5ms SLA with margin)
- [ ] Cache results for TTL seconds to reduce API calls
- [ ] Use `match_type` to adjust bid prices
- [ ] Apply `price_multiplier` to your baseline bid
- [ ] Parse `device_profile` to refine creative selection
- [ ] Implement retry logic with exponential backoff
- [ ] Monitor error rate and contact support if > 1%

#### POST /v1/targeting/activate

Activate a segment for campaign targeting (start delivering ads to segment).

**Request Body**:
```json
{
  "segment_id": "seg_sports_fans",
  "campaign_id": "camp_sports_promo_2026",
  "bid_adjustment": 1.5,
  "daily_cap": 1000000,
  "start_date": "2026-04-15T00:00:00Z",
  "end_date": "2026-05-15T23:59:59Z"
}
```

**Response** (201 Created):
```json
{
  "activation_id": "act_xyz789",
  "segment_id": "seg_sports_fans",
  "campaign_id": "camp_sports_promo_2026",
  "status": "active",
  "activated_at": "2026-04-10T16:00:00Z",
  "estimated_daily_reach": 500000,
  "estimated_monthly_spend": 125000
}
```

**Errors**:
- `resource_not_found` (404): Segment doesn't exist
- `invalid_campaign` (400): Campaign already at max segments

#### GET /v1/targeting/reach

Get reach estimates for segments and campaign pacing.

**Query Parameters**:
- `segment_ids` (array): Comma-separated segment IDs
- `start_date` (string): Start date (ISO 8601)
- `end_date` (string): End date (ISO 8601)
- `daypart` (string, optional): Restrict to daypart (morning, afternoon, primetime, latenight)

**Response** (200 OK):
```json
{
  "segments": [
    {
      "segment_id": "seg_sports_fans",
      "daily_reach": 500000,
      "monthly_reach": 12000000,
      "cost_per_reach": 0.0085,
      "daypart_breakdown": {
        "morning": 100000,
        "afternoon": 150000,
        "primetime": 200000,
        "latenight": 50000
      }
    }
  ]
}
```

---

### Reports

#### GET /v1/reports/delivery

Get delivery metrics for a campaign or segment.

**Query Parameters**:
- `segment_id` (string): Segment to report on
- `date` (string, optional): Date (YYYY-MM-DD) or "today"
- `campaign_id` (string, optional): Filter by campaign

**Response** (200 OK):
```json
{
  "date": "2026-04-10",
  "segment_id": "seg_sports_fans",
  "impressions": 5234890,
  "clicks": 12450,
  "conversions": 3200,
  "spend": 65000,
  "cpm": 12.43,
  "cpc": 5.22,
  "roi": 8.5
}
```

#### GET /v1/reports/overlap

Get audience overlap between two or more segments.

**Query Parameters**:
- `segment_ids` (array): Comma-separated segment IDs (min 2, max 5)

**Response** (200 OK):
```json
{
  "segment_ids": ["seg_sports_fans", "seg_premium_income"],
  "overlap_percentage": 45.6,
  "overlap_size": 550000,
  "segment_1_unique": 600000,
  "segment_2_unique": 800000,
  "union_size": 1950000
}
```

---

### Privacy Endpoints

#### POST /v1/consent/record

Record user consent decision on behalf of a device.

**Request Body**:
```json
{
  "device_id": "acr_device_abc123",
  "consent_status": true,
  "timestamp": "2026-04-10T14:30:00Z",
  "source": "tv_settings_ui"
}
```

**Response** (202 Accepted):
```json
{
  "device_id": "acr_device_abc123",
  "consent_status": true,
  "recorded_at": "2026-04-10T14:30:00Z"
}
```

#### POST /v1/privacy/opt-out

Permanently opt a device out of data collection.

**Request Body**:
```json
{
  "device_id": "acr_device_abc123",
  "reason": "user_requested"
}
```

**Response** (202 Accepted):
```json
{
  "device_id": "acr_device_abc123",
  "status": "opted_out",
  "opted_out_at": "2026-04-10T14:31:00Z",
  "note": "Device will not collect fingerprints or participate in audience segments."
}
```

#### GET /v1/privacy/data-export

Export all collected data for a device (GDPR/CCPA right to access).

**Query Parameters**:
- `device_id` (string): Device to export
- `format` (string, optional): "json" or "csv" (default: json)

**Response** (200 OK):
```json
{
  "device_id": "acr_device_abc123",
  "export_id": "export_xyz789",
  "status": "ready",
  "download_url": "https://downloads.acraas.io/exports/export_xyz789.json",
  "expires_at": "2026-04-17T14:32:00Z",
  "data_summary": {
    "fingerprints_count": 2450,
    "date_range": ["2026-03-15", "2026-04-10"],
    "segments": ["seg_sports_fans", "seg_news_watchers"],
    "estimated_size": "2.5 MB"
  }
}
```

#### DELETE /v1/privacy/erase

Permanently erase all collected data for a device (GDPR/CCPA right to be forgotten).

**Request Body**:
```json
{
  "device_id": "acr_device_abc123",
  "reason": "user_requested"
}
```

**Response** (202 Accepted):
```json
{
  "device_id": "acr_device_abc123",
  "erasure_status": "queued",
  "estimated_completion": "2026-04-11T00:00:00Z",
  "message": "All data will be permanently erased within 24 hours."
}
```

---

### Billing Endpoints

#### POST /v1/billing/customers

Create a new customer/brand account for campaigns.

**Request Body**:
```json
{
  "name": "Acme Corporation",
  "email": "billing@acme.com",
  "timezone": "America/Los_Angeles"
}
```

**Response** (201 Created):
```json
{
  "customer_id": "cust_acme_corp",
  "name": "Acme Corporation",
  "created_at": "2026-04-10T14:35:00Z"
}
```

#### GET /v1/billing/invoices/{customer_id}

Retrieve invoices and payment history for a customer.

**Path Parameters**:
- `customer_id` (string): Customer ID

**Response** (200 OK):
```json
{
  "customer_id": "cust_acme_corp",
  "invoices": [
    {
      "invoice_id": "inv_202604_acme",
      "amount": 125000,
      "currency": "USD",
      "period": "2026-04-01 to 2026-04-30",
      "status": "paid",
      "issued_at": "2026-05-01T00:00:00Z",
      "due_at": "2026-05-31T23:59:59Z",
      "paid_at": "2026-05-15T10:30:00Z"
    }
  ]
}
```

#### GET /v1/billing/revenue/summary

Get manufacturer revenue share summary (for SDK partners).

**Query Parameters**:
- `start_date` (string): Start date (YYYY-MM-DD)
- `end_date` (string): End date (YYYY-MM-DD)
- `manufacturer_id` (string, optional): Filter by manufacturer

**Response** (200 OK):
```json
{
  "period": {
    "start_date": "2026-03-01",
    "end_date": "2026-03-31"
  },
  "manufacturer_id": "mfr_samsung",
  "summary": {
    "gross_revenue": 1500000,
    "manufacturer_share_pct": 30,
    "manufacturer_payout": 450000,
    "fingerprints_collected": 45000000,
    "active_devices": 1250000
  },
  "payout": {
    "status": "pending",
    "scheduled_date": "2026-04-15T00:00:00Z",
    "method": "bank_transfer"
  }
}
```

---

## Webhooks

ACRaaS can send real-time webhook notifications to your application when important events occur.

### Registering Webhooks

1. Log in to https://portal.acraas.io/webhooks
2. Create a new webhook endpoint
3. Specify the events you want to receive
4. ACRaaS will POST event data to your URL

### Event Types

| Event | When Fired | Payload |
|---|---|---|
| `segment.populated` | Segment size estimate updated | Segment ID, estimated size, confidence |
| `opt_out.completed` | Device opt-out processed | Device ID, opt-out date |
| `invoice.paid` | Invoice payment received | Invoice ID, amount, customer |
| `invoice.payment_failed` | Payment processing failed | Invoice ID, reason, retry date |
| `campaign.paused` | Campaign auto-paused (e.g., budget limit) | Campaign ID, reason |
| `export.ready` | Data export ready for download | Export ID, download URL, expiry |

### Webhook Payload Format

```json
{
  "event_type": "segment.populated",
  "event_id": "evt_abc123xyz789",
  "timestamp": "2026-04-10T14:40:00Z",
  "data": {
    "segment_id": "seg_sports_fans",
    "estimated_size": 2500000,
    "confidence": 0.98,
    "updated_at": "2026-04-10T14:40:00Z"
  }
}
```

### Webhook Signature Verification

All webhooks are signed with HMAC-SHA256. Verify signatures to authenticate:

```python
import hmac
import hashlib
import json

def verify_webhook(request_body, signature_header, secret):
    """Verify ACRaaS webhook signature."""
    computed = hmac.new(
        secret.encode(),
        request_body.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(computed, signature_header)

# Flask example
from flask import Flask, request

app = Flask(__name__)
WEBHOOK_SECRET = "whk_secret_xyz789"

@app.route("/webhook", methods=["POST"])
def handle_webhook():
    signature = request.headers.get("X-ACRaaS-Signature")
    body = request.get_data(as_text=True)
    
    if not verify_webhook(body, signature, WEBHOOK_SECRET):
        return {"error": "Invalid signature"}, 401
    
    event = json.loads(body)
    
    if event["event_type"] == "segment.populated":
        print(f"Segment {event['data']['segment_id']} now has {event['data']['estimated_size']:,} users")
    
    return {"received": True}, 200
```

### Webhook Retry Policy

- **Max retries**: 3
- **Backoff strategy**: Exponential (2s, 4s, 8s)
- **Timeout**: 30 seconds per request
- **Final failure**: Event marked as undeliverable; manual retry available in portal

---

## SDKs & Client Libraries

ACRaaS publishes official SDK/client libraries in multiple languages for easier integration.

### Available Libraries

| Language | Package | Status | Docs |
|---|---|---|---|
| Python | `acraas` | Stable | https://pypi.org/project/acraas |
| Go | `github.com/acraas/go-sdk` | Stable | https://pkg.go.dev/github.com/acraas/go-sdk |
| Node.js | `@acraas/sdk` | Stable | https://www.npmjs.com/package/@acraas/sdk |
| Java | `io.acraas:acraas-sdk` | Beta | https://mvnrepository.com/artifact/io.acraas/acraas-sdk |
| Kotlin | `io.acraas:sdk-android` | Stable | https://mvnrepository.com/artifact/io.acraas/sdk-android |

### Python Example

```bash
pip install acraas
```

```python
from acraas import AcraaS, SegmentRules

# Initialize client
acr = AcraaS(
    client_id="your_client_id",
    client_secret="your_client_secret"
)

# Create a segment
segment = acr.segments.create(
    name="Sports Fans",
    rules=SegmentRules.watched_genre(["sports", "news"])
)
print(f"Created segment: {segment.id}")

# Check audience size
size = acr.segments.get_size(segment.id)
print(f"Audience size: {size.estimated_size:,}")

# Check device match (RTB)
match = acr.rtb.check_segment_match(
    device_id="acr_device_123",
    segment_ids=[segment.id]
)
if match.matched:
    print(f"Device matches: {match.segments}")
```

### OpenAPI Specification

Full OpenAPI 3.0 specification available at:
```
https://api.acraas.io/openapi.json
```

Generate client code in your language:
```bash
# Using OpenAPI Generator
openapi-generator-cli generate \
  -i https://api.acraas.io/openapi.json \
  -g python \
  -o ./acraas-python-client
```

### Postman Collection

Import the Postman collection for testing:
```
https://postman.acraas.io/acraas-api.json
```

---

## Changelog

### Version 1.0 (April 2026)

**New Features**:
- Initial stable API release
- Full OpenRTB 2.5 support
- Real-time segment sizing
- Webhook events
- Multi-segment audience overlap reporting

**Improvements**:
- Optimized RTB latency (< 5ms p99)
- Enhanced fraud detection
- Improved confidence scoring for household matches

**Breaking Changes**: None (initial release)

### Planned (May 2026)

- OpenRTB 3.0 support
- Lookalike audience creation (beta)
- Advanced cross-device matching
- GraphQL API option

---

**Last Updated**: April 2026  
**Support**: api-support@acraas.io  
**Status Page**: https://status.acraas.io
