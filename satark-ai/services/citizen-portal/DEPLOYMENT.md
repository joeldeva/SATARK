# Citizen Portal - Deployment Guide

## Quick Start (Development)

### Backend Setup

```bash
cd satark-ai/services/citizen-portal/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download Whisper model (optional, for voice input)
python -c "import whisper; whisper.load_model('base')"

# Set environment variables
export JWT_SECRET="your-secret-key-change-in-production"
export POSTGRES_URL="postgresql://satark:satark123@localhost:5432/satark_db"
export REDIS_URL="redis://localhost:6379"

# Run backend
uvicorn app:app --reload --port 8004
```

Backend will be available at: http://localhost:8004

### Frontend Setup

```bash
cd satark-ai/services/citizen-portal/frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

Frontend will be available at: http://localhost:5173

## Production Deployment

### 1. Backend (Docker)

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8004

# Run application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8004"]
```

Build and run:

```bash
docker build -t satark/citizen-portal-backend:latest .
docker run -d -p 8004:8004 \
  -e JWT_SECRET="your-secret" \
  -e POSTGRES_URL="postgresql://..." \
  -e REDIS_URL="redis://..." \
  satark/citizen-portal-backend:latest
```

### 2. Frontend (Docker)

Create `Dockerfile`:

```dockerfile
FROM node:18-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./
RUN npm ci

# Copy source
COPY . .

# Build
RUN npm run build

# Production image
FROM nginx:alpine

# Copy built files
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

Create `nginx.conf`:

```nginx
server {
    listen 80;
    server_name _;

    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://backend:8004;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    gzip on;
    gzip_types text/plain text/css application/json application/javascript;
}
```

Build and run:

```bash
docker build -t satark/citizen-portal-frontend:latest .
docker run -d -p 80:80 satark/citizen-portal-frontend:latest
```

### 3. Kubernetes Deployment

Create `k8s-deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: citizen-portal-backend
  namespace: satark
spec:
  replicas: 3
  selector:
    matchLabels:
      app: citizen-portal-backend
  template:
    metadata:
      labels:
        app: citizen-portal-backend
    spec:
      containers:
      - name: backend
        image: satark/citizen-portal-backend:latest
        ports:
        - containerPort: 8004
        env:
        - name: JWT_SECRET
          valueFrom:
            secretKeyRef:
              name: satark-secrets
              key: jwt-secret
        - name: POSTGRES_URL
          valueFrom:
            secretKeyRef:
              name: satark-secrets
              key: postgres-url
        - name: REDIS_URL
          value: "redis://redis-service:6379"
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
---
apiVersion: v1
kind: Service
metadata:
  name: citizen-portal-backend-service
  namespace: satark
spec:
  selector:
    app: citizen-portal-backend
  ports:
  - port: 8004
    targetPort: 8004
  type: ClusterIP
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: citizen-portal-frontend
  namespace: satark
spec:
  replicas: 2
  selector:
    matchLabels:
      app: citizen-portal-frontend
  template:
    metadata:
      labels:
        app: citizen-portal-frontend
    spec:
      containers:
      - name: frontend
        image: satark/citizen-portal-frontend:latest
        ports:
        - containerPort: 80
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "200m"
---
apiVersion: v1
kind: Service
metadata:
  name: citizen-portal-frontend-service
  namespace: satark
spec:
  selector:
    app: citizen-portal-frontend
  ports:
  - port: 80
    targetPort: 80
  type: LoadBalancer
```

Deploy:

```bash
kubectl apply -f k8s-deployment.yaml
kubectl get pods -n satark
kubectl get services -n satark
```

## Integration with External Services

### 1. SMS Gateway (Twilio)

```python
# In app.py, add Twilio integration
from twilio.rest import Client

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

def send_sms(to_number, message):
    client.messages.create(
        body=message,
        from_=TWILIO_PHONE_NUMBER,
        to=to_number
    )
```

### 2. WhatsApp Business API

```python
# WhatsApp webhook handler
@app.post("/whatsapp/webhook")
async def whatsapp_webhook(request: Request):
    data = await request.json()
    
    # Extract message
    from_number = data['from']
    message = data['message']['text']
    
    # Process message and send response
    response_text = process_whatsapp_message(from_number, message)
    
    # Send response via Twilio WhatsApp API
    client.messages.create(
        body=response_text,
        from_='whatsapp:+14155238886',  # Twilio sandbox
        to=f'whatsapp:{from_number}'
    )
    
    return {"status": "success"}
```

### 3. IVR System (Exotel)

```python
# IVR callback handler
@app.post("/ivr/callback")
async def ivr_callback(request: Request):
    data = await request.form()
    
    dtmf_input = data.get('Digits')
    call_sid = data.get('CallSid')
    
    # Map DTMF to response
    response_value = map_dtmf_to_response(dtmf_input)
    
    # Generate next prompt
    next_prompt = get_next_question(call_sid)
    
    # Return TwiML response
    return f"""
    <Response>
        <Say language="hi-IN">{next_prompt}</Say>
        <Gather numDigits="1" action="/ivr/callback">
            <Say>Press 1 for yes, 2 for no</Say>
        </Gather>
    </Response>
    """
```

### 4. DigiLocker Integration

```python
# DigiLocker OAuth flow
@app.get("/auth/digilocker/initiate")
async def digilocker_initiate():
    auth_url = f"https://digilocker.gov.in/public/oauth2/1/authorize"
    params = {
        "response_type": "code",
        "client_id": DIGILOCKER_CLIENT_ID,
        "redirect_uri": DIGILOCKER_REDIRECT_URI,
        "state": generate_state_token()
    }
    return RedirectResponse(f"{auth_url}?{urlencode(params)}")

@app.get("/auth/digilocker/callback")
async def digilocker_callback(code: str, state: str):
    # Exchange code for access token
    token_response = requests.post(
        "https://digilocker.gov.in/public/oauth2/1/token",
        data={
            "code": code,
            "grant_type": "authorization_code",
            "client_id": DIGILOCKER_CLIENT_ID,
            "client_secret": DIGILOCKER_CLIENT_SECRET,
            "redirect_uri": DIGILOCKER_REDIRECT_URI
        }
    )
    
    access_token = token_response.json()["access_token"]
    
    # Fetch user details
    user_response = requests.get(
        "https://digilocker.gov.in/public/oauth2/1/user",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    user_data = user_response.json()
    
    # Create JWT token
    jwt_token = create_jwt_token(user_data["mobile"], user_data)
    
    return {"token": jwt_token, "user": user_data}
```

## Monitoring & Logging

### Prometheus Metrics

```python
from prometheus_client import Counter, Histogram, generate_latest

# Metrics
otp_requests = Counter('satark_otp_requests_total', 'Total OTP requests')
survey_submissions = Counter('satark_survey_submissions_total', 'Total survey submissions')
response_time = Histogram('satark_response_time_seconds', 'Response time')

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

### Logging

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('citizen-portal.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Use in endpoints
logger.info(f"OTP sent to {mobile_number}")
logger.error(f"Failed to verify OTP: {error}")
```

## Security Checklist

- [ ] Change JWT_SECRET to strong random value
- [ ] Enable HTTPS/TLS
- [ ] Configure CORS properly
- [ ] Implement rate limiting
- [ ] Enable SQL injection protection
- [ ] Sanitize user inputs
- [ ] Implement CSRF protection
- [ ] Set secure cookie flags
- [ ] Enable audit logging
- [ ] Regular security scans
- [ ] Dependency vulnerability checks
- [ ] Implement WAF rules

## Performance Optimization

### Backend

1. **Enable Redis caching**
```python
import redis
cache = redis.Redis(host='localhost', port=6379, db=0)

@app.get("/survey/{survey_id}")
async def get_survey(survey_id: str):
    # Check cache first
    cached = cache.get(f"survey:{survey_id}")
    if cached:
        return json.loads(cached)
    
    # Fetch from database
    survey = fetch_survey_from_db(survey_id)
    
    # Cache for 1 hour
    cache.setex(f"survey:{survey_id}", 3600, json.dumps(survey))
    
    return survey
```

2. **Database connection pooling**
```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    POSTGRES_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=40
)
```

3. **Async database queries**
```python
from databases import Database

database = Database(POSTGRES_URL)

@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()
```

### Frontend

1. **Code splitting**
```javascript
// Use React.lazy for code splitting
const SurveyScreen = React.lazy(() => import('./components/SurveyScreen'));
```

2. **Image optimization**
```javascript
// Use WebP format with fallback
<picture>
  <source srcSet="logo.webp" type="image/webp" />
  <img src="logo.png" alt="SATARK.AI" />
</picture>
```

3. **Service Worker for offline support**
```javascript
// Register service worker
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/sw.js');
}
```

## Troubleshooting

### Backend won't start
```bash
# Check Python version
python --version  # Should be 3.11+

# Check dependencies
pip list

# Check logs
tail -f citizen-portal.log
```

### Frontend build fails
```bash
# Clear node_modules
rm -rf node_modules package-lock.json
npm install

# Check Node version
node --version  # Should be 18+
```

### Database connection errors
```bash
# Test PostgreSQL connection
psql -h localhost -U satark -d satark_db

# Check connection string
echo $POSTGRES_URL
```

## Support

- Documentation: http://localhost:8004/docs
- Issues: https://github.com/mospi/satark-ai/issues
- Email: support@satark.gov.in
