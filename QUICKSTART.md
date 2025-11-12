# Quick Start Guide

## Prerequisites
- Python 3.9+
- MySQL 8.0+ (or use SQLite for testing)
- WhatsApp Business API credentials

## Installation

1. **Clone and setup**
```bash
git clone <repository-url>
cd ai-agent-researcher
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

2. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your credentials
```

**Note:** For Hugging Face Space deployment, configure embedding service:
```env
EMBEDDING_PROVIDER=remote
EMBEDDING_SERVICE_URL=https://your-embedding-space.hf.space
```

**Switching WhatsApp Providers:**
```env
# Default Meta WhatsApp Cloud API
WHATSAPP_PROVIDER=meta

# Twilio WhatsApp (optional)
WHATSAPP_PROVIDER=twilio
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_WHATSAPP_NUMBER=whatsapp:+1234567890
```

3. **Setup database**
```bash
# Create database
mysql -u root -p -e "CREATE DATABASE nigerian_grants_db;"

# Initialize tables
python -c "from database.session import init_db; init_db()"
```

4. **Run application**
```bash
python run.py
```

## Testing Webhook (Local Development)

1. **Install ngrok**
```bash
# Download from https://ngrok.com/
ngrok http 8000
```

2. **Configure WhatsApp webhook**
   - Use ngrok URL: `https://your-ngrok-url.ngrok.io/webhook`
   - Set verify token: `your_verify_token_here`

3. **Test webhook verification**
```bash
curl "http://localhost:8000/webhook?hub.mode=subscribe&hub.verify_token=your_verify_token_here&hub.challenge=test123"
```

## Manual Testing

1. **Trigger crawl**
```bash
curl -X POST http://localhost:8000/cron/run
```

2. **Test health**
```bash
curl http://localhost:8000/health
```

## WhatsApp Testing

1. **Send message to your WhatsApp number**
   - `digest` - Get weekly digest
   - `1` - Get proposal for item 1
   - `phd scholarships STEM 2026` - Ask a question

2. **Check logs**
```bash
tail -f logs/app.log
```

## Common Issues

### Playwright not installed
```bash
playwright install chromium
```

### Database connection error
- Check MySQL is running
- Verify DATABASE_URL in .env
- Check user permissions

### WhatsApp webhook not working
- Verify ngrok is running
- Check webhook URL in WhatsApp Business settings
- Verify access token

### LLM API error
- Check API key in .env
- Verify base URL
- Check rate limits

## Next Steps

- Add more sources to `crawler/sources.yaml`
- Customize prompts in `agents/`
- Configure cron schedule in `.env`
- Deploy to production

