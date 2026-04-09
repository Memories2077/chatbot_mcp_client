# Docker Deployment Guide

This guide provides detailed instructions for running the Gemini InsightLink application using Docker and Docker Compose.

## 🚀 Quick Start with Docker Compose

### Prerequisites
- Docker & Docker Compose installed
- A Google Gemini API Key from [Google AI Studio](https://aistudio.google.com/app/apikey)

### Step 1: Prepare Environment File

1.  Create a `.env` file in the project root by copying the example:
    ```bash
    cp .env.example .env
    ```

2.  Open the `.env` file and set the required variables.
    ```env
    # Your secret Gemini API Key
    GEMINI_API_KEY="your_gemini_api_key_here"

    # Port for the backend service. This will be exposed on the host.
    # The frontend is fixed to run on port 9002.
    NEXT_PUBLIC_BACKEND_PORT=8000
    ```

### Step 2: Build and Run Services

From the project root, run the following command to build the images and start the frontend and backend services in detached mode:
```bash
docker compose up --build -d
```
This command will:
1.  Read the `.env` file.
2.  Build the `backend` Docker image.
3.  Build the `frontend` Docker image, passing the backend URL as a build argument.
4.  Start both containers. The `frontend` will wait for the `backend` to be healthy before starting.

### Step 3: Access the Application

Once the services are running, you can access them at:
- **Frontend Application**: [http://localhost:9002](http://localhost:9002)
- **Backend API**: `http://localhost:8000` (or the port you set in `.env`)
- **Backend Health Check**: `http://localhost:8000/health`

## ⚙️ Environment Variable Flow

Understanding how environment variables are passed is key to this setup.

```
┌──────────────────────────────────────┐
│           .env file                  │
│  GEMINI_API_KEY=...                  │
│  NEXT_PUBLIC_BACKEND_PORT=8000       │
└──────────────────────────────────────┘
             │
             ▼
┌───────────────────────────────────────────────────────────┐
│                    docker-compose.yml                     │
│                                                           │
│  ▶ backend service:                                       │
│    - Receives NEXT_PUBLIC_BACKEND_PORT to set its port.   │
│    - Receives GEMINI_API_KEY.                             │
│                                                           │
│  ▶ frontend service:                                      │
│    - Receives NEXT_PUBLIC_BACKEND_PORT to construct a URL.│
│    - Passes NEXT_PUBLIC_BACKEND_URL as a build argument.  │
└───────────────────────────────────────────────────────────┘
             │
             ▼
┌───────────────────────────────────────────────────────────┐
│                    Build & Runtime                        │
│                                                           │
│  ▶ frontend (Build Time):                                 │
│    - Receives NEXT_PUBLIC_BACKEND_URL=http://localhost:8000 │
│    - This URL is "baked" into the static JavaScript files.│
│                                                           │
│  ▶ backend (Runtime):                                     │
│    - Runs on port 8000 inside the container.              │
│    - Exposes port 8000 on the host machine.               │
└───────────────────────────────────────────────────────────┘
```

## 🛠️ Useful Docker Commands

- **View Service Status**:
  ```bash
  docker compose ps
  ```

- **View Logs (Live)**:
  ```bash
  # Stream logs from all services
  docker compose logs -f

  # Stream logs from a specific service
  docker compose logs -f backend
  ```

- **Stop Services**:
  ```bash
  # Stop and remove containers, networks, and volumes
  docker compose down
  ```

- **Rebuild Images**:
  If you make changes to `Dockerfile` or related files, you need to rebuild.
  ```bash
  # Rebuild without using cache and restart services
  docker compose up -d --build --no-cache

  # Or just rebuild a specific service
  docker compose build frontend
  ```

- **Access a Container Shell**:
  This is useful for debugging inside a running container.
  ```bash
  # Shell into the backend container (bash)
  docker compose exec backend bash

  # Shell into the frontend container (sh)
  docker compose exec frontend sh
  ```

##  troubleshooting

### Port Conflict
If you see an error that a port is already in use, change `NEXT_PUBLIC_BACKEND_PORT` in your `.env` file to an unused port (e.g., `8001`), then restart with `docker compose up -d`.

### Frontend Shows Connection Error
1.  Check the backend logs: `docker compose logs backend`. Look for errors, especially related to the `GEMINI_API_KEY`.
2.  Ensure the backend is healthy: Visit `http://localhost:8000/health` (or your configured port). It should return `{"status":"healthy", ...}`.
3.  Rebuild your images to ensure the frontend has the correct backend URL: `docker compose up -d --build`.