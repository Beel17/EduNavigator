# Embedding Service

Lightweight FastAPI service for generating text embeddings using sentence-transformers models.

## Deployment on Hugging Face Spaces

### Setup

1. **Create a new Hugging Face Space** with Docker SDK

2. **Add files to your Space:**
   - `app.py` - FastAPI application
   - `requirements.txt` - Python dependencies
   - `README.md` - This file

3. **Configure Space settings:**
   - **SDK**: Docker
   - **Python version**: 3.9+
   - **Hardware**: CPU (or GPU for faster inference)

4. **Environment variables (optional):**
   - No environment variables required for basic setup
   - The service uses `sentence-transformers/all-MiniLM-L6-v2` by default

### Dockerfile (optional, for custom deployment)

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

EXPOSE 7860

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
```

### Usage

Once deployed, the service exposes:

- **POST `/embed`**: Generate embeddings
  ```json
  {
    "texts": ["Hello world", "This is a test"]
  }
  ```
  
  Response:
  ```json
  {
    "embeddings": [[0.1, 0.2, ...], [0.3, 0.4, ...]]
  }
  ```

- **GET `/health`**: Health check
  ```json
  {
    "status": "healthy",
    "model_loaded": true,
    "model_name": "sentence-transformers/all-MiniLM-L6-v2"
  }
  ```

### Integration with Main Application

Configure the main application to use this service:

```env
EMBEDDING_PROVIDER=remote
EMBEDDING_SERVICE_URL=https://your-space-name.hf.space
EMBEDDING_SERVICE_API_KEY=  # Optional, if authentication is added
```

### Notes

- The model is loaded once at startup for efficiency
- Port 7860 is the default Hugging Face Spaces port
- The service handles multiple texts in a single request for batch processing
- Memory usage is optimized by loading the model only once

