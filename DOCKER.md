# Hướng Dẫn Triển Khai Docker

## 🔧 Environment Variables Flow

Trước tiên, hiểu cách biến môi trường được áp dụng:

```
┌─────────────────────────────────────────────────────────────┐
│                      .env file                              │
│  GEMINI_API_KEY=...                                         │
│  BACKEND_PORT=8000 (hoặc 9003, 3001, ...)                   │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌──────────────────────────────────────────────────────────────┐
│              docker-compose.yml                              │ 
│  Đọc từ .env và inject vào containers:                       │
│                                                              │
│  backend:                                                    │
│    build:                                                    │
│      args: BACKEND_PORT=${BACKEND_PORT}  ← Pass to build     │
│    environment:                                              │
│      - GEMINI_API_KEY=${GEMINI_API_KEY}                      │
│      - BACKEND_PORT=${BACKEND_PORT}                          │
│    ports:                                                    │
│      - "${BACKEND_PORT}:${BACKEND_PORT}" ← Same port!        │
│    command: uvicorn ... --port ${BACKEND_PORT}               │
│                                                              │
│  frontend:                                                   │
│    environment:                                              │
│      - NEXT_PUBLIC_BACKEND_URL=http://backend:${BACKEND_PORT}│
└──────────────────────────────────────────────────────────────┘
                        ↓
┌──────────────────────────────────────────────────────────────┐
│            Containers                                        │
│  backend:                                                    │
│    - EXPOSE: ${BACKEND_PORT} (from ARG at build time)        │
│    - Container listen: 0.0.0.0:${BACKEND_PORT}               │
│    - Host access: http://localhost:${BACKEND_PORT}           │
│    - Docker network: http://backend:${BACKEND_PORT}          │
│                                                              │
│  frontend:                                                   │
│    - NEXT_PUBLIC_BACKEND_URL: http://backend:${BACKEND_PORT} │ 
│      (Docker network internal URL)                           │
│    - Port 9002:9002                                          │
└──────────────────────────────────────────────────────────────┘
```

## Bắt Đầu Nhanh với Docker Compose

### Yêu Cầu
- Docker & Docker Compose đã được cài đặt
- Gemini API Key từ [Google AI Studio](https://aistudio.google.com/app/apikey)

### Cài Đặt

1. **Tạo file `.env`** từ template:
```bash
cp .env.example .env
```

Chỉnh sửa `.env` và thêm Gemini API Key + Backend Port:
```env
GEMINI_API_KEY=your_actual_api_key_here
BACKEND_PORT=8000  # Thay đổi nếu cần (VD: 9003, 3001, ...)
```

2. **Build và khởi động các dịch vụ**:
```bash
docker-compose up -d
```

Điều này sẽ:
- ✅ Build và khởi động Backend (FastAPI) trên port `${BACKEND_PORT}`
- ✅ Chờ Backend healthy
- ⏳ Build và khởi động Frontend (Next.js) trên port 9002
- 🔗 Tự động kết nối Frontend với Backend qua Docker network (http://backend:${BACKEND_PORT})

3. **Truy cập ứng dụng**:
- Frontend: http://localhost:9002
- Backend API: http://localhost:${BACKEND_PORT} (VD: http://localhost:8000)
- Backend Health: http://localhost:${BACKEND_PORT}/health (VD: http://localhost:8000/health)

### Xem Logs

```bash
# Tất cả dịch vụ
docker-compose logs -f

# Dịch vụ cụ thể
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Dừng Dịch Vụ

```bash
docker-compose down
```

### Rebuild (sau khi thay đổi code)

```bash
# Chế độ phát triển (với hot-reload)
docker-compose up -d --build

# Hoặc rebuild dịch vụ cụ thể
docker-compose build frontend
docker-compose up -d frontend
```

## Kiến Trúc

### Environment Variables Chi Tiết

**Biến từ `.env` được tự động inject vào containers:**

#### Backend Container
- `GEMINI_API_KEY` - Được pass từ environment
  ```bash
  docker-compose config | grep GEMINI_API_KEY
  ```
- `BACKEND_PORT` - Port được set tại build time (ARG) và runtime (command)
  - Frontend code will automatically read this via `NEXT_PUBLIC_BACKEND_URL`.
  - The React config helper (`src/lib/config.ts`) also checks `process.env.BACKEND_PORT`
    on the server-side to construct a URL when `NEXT_PUBLIC_BACKEND_URL` is missing.
  - Dockerfile nhận ARG: `BACKEND_PORT=${BACKEND_PORT}`
  - docker-compose.yml chỉ định: `command: uvicorn main:app --host 0.0.0.0 --port ${BACKEND_PORT}`
- Chạy trên port `${BACKEND_PORT}` bên trong container
- Được map tới **cùng port** trên host: `${BACKEND_PORT}:${BACKEND_PORT}`

#### Frontend Container  
- `NEXT_PUBLIC_BACKEND_URL` - Set tới `http://backend:${BACKEND_PORT}`
  - `backend` là DNS name của backend service trong Docker network
  - `${BACKEND_PORT}` là container port (nhận từ .env)
- Truy cập backend qua Docker internal network

**Ví dụ Port Mapping:**

```bash
# .env
BACKEND_PORT=9003

# docker-compose (tự động interpolate từ .env)
backend:
  build:
    args:
      - BACKEND_PORT=${BACKEND_PORT}  # Pass to Dockerfile as ARG
  environment:
    - BACKEND_PORT=${BACKEND_PORT}
  ports:
    - "${BACKEND_PORT}:${BACKEND_PORT}"  # 9003:9003 ← Cùng port!
  command: uvicorn main:app --host 0.0.0.0 --port ${BACKEND_PORT}
    
frontend:
  environment:
    - NEXT_PUBLIC_BACKEND_URL=http://backend:${BACKEND_PORT}  # http://backend:9003

# Kết quả:
# - Container backend listen: 0.0.0.0:9003
# - Host access: http://localhost:9003 ✓
# - Frontend access: http://backend:9003 ✓ (via Docker network)
```

### Health Checks
- **Backend** health check endpoint: `/health` trên port `${BACKEND_PORT}`
- **Frontend** phụ thuộc vào Backend healthy trước khi khởi động
- Cả hai dịch vụ sẽ báo cáo `healthy` khi hoàn toàn sẵn sàng

### Biến Môi Trường

**Backend**:
- `GEMINI_API_KEY` - Google Generative AI API Key
- `BACKEND_PORT` - Port chạy backend (từ .env)
- `PYTHONUNBUFFERED=1` - Direct Python output

**Frontend**:
- `NEXT_PUBLIC_BACKEND_URL` - Backend API URL (`http://backend:${BACKEND_PORT}`)
- `NODE_ENV=production`

## Chế Độ Phát Triển

Các commands được cấu hình trong `docker-compose.yml`:

```yaml
backend:
  command: uvicorn main:app --host 0.0.0.0 --port ${BACKEND_PORT} --reload
  
frontend:
  command: sh -c "npm run dev"
```

Volumes được mount nên changes sẽ được phản ánh ngay lập tức:
- Backend volumes: `./backend:/app/backend` (code reload)
- Frontend volumes: `./src:/app/src` (hot reload)

## Triển Khai Production

Để triển khai production, sửa đổi `docker-compose.yml`:

1. **Loại bỏ `--reload` flag** (không cần hot-reload):
```yaml
backend:
  command: uvicorn main:app --host 0.0.0.0 --port ${BACKEND_PORT}

frontend:
  command: node_modules/.bin/next start --port 9002
```

2. **Loại bỏ hoặc giới hạn volumes** (code không cần thay đổi)

```yaml
backend:
  # volumes: [] # Hoặc xóa volumes section

frontend:
  # volumes: [] # Hoặc xóa volumes section
```

2. **Build production images**:
```bash
docker-compose build --no-cache
```

3. **Triển khai**:
```bash
docker-compose -f docker-compose.yml up -d
```

## Khắc Phục Sự Cố

### Environment Variables không được apply

**Vấn đề**: .env file có `BACKEND_PORT=9003` nhưng docker-compose vẫn dùng port 8000

**Cách verification**:
```bash
# Kiểm tra docker-compose config
docker-compose config | grep -A 5 "ports:"

# Xem container port mapping
docker-compose ps

# Kiểm tra env variables trong container
docker-compose exec backend env | grep GEMINI
```

**Giải pháp**:
- Đảm bảo file `.env` tồn tại cùng thư mục docker-compose.yml
- Docker-compose sẽ tự động load .env file
- Nếu không work, load explicit: `docker-compose --env-file .env up`

### Frontend hiển thị "Backend connection error"
- Kiểm tra Backend đang chạy: `docker-compose logs backend`
- Kiểm tra Frontend logs: `docker-compose logs frontend`
- Xác minh BACKEND_PORT trong .env: `cat .env | grep BACKEND_PORT`
- Xác minh GEMINI_API_KEY được set: `docker-compose config | grep GEMINI_API_KEY`
- Xác minh Backend health: `curl http://localhost:$(grep BACKEND_PORT .env | cut -d= -f2)/health`

### Backend not ready yet
- Bình thường trong quá trình khởi động - healthcheck đang tiến hành
- Nếu vẫn persistent sau 1 phút, kiểm tra Backend logs: `docker-compose logs -f backend`
- Kiểm tra API key hợp lệ
- Kiểm tra port không bị occupy: `lsof -i :$(grep BACKEND_PORT .env | cut -d= -f2)`

### Port đã được sử dụng
```bash
# Kiểm tra port đang sử dụng (macOS/Linux)
lsof -i :8000

# Windows
netstat -ano | findstr :8000

# Sửa .env
BACKEND_PORT=9999  # Thay đổi port

# Rebuild
docker-compose up -d --build
```

### Rebuild/Reset hoàn toàn
```bash
# Dừng và xóa containers
docker-compose down

# Xóa images
docker-compose down --rmi all

# Rebuild từ đầu
docker-compose up -d --build
```

## Docker Images

- **Backend**: Base image `python:3.11-slim` (~200MB)
- **Frontend**: Base image `node:20-alpine` (~170MB)

Cả hai sử dụng multi-stage builds để tối ưu hóa final images.

## Best Practices

### Development
- Sử dụng `docker-compose up -d` thường xuyên để test
- Logs: `docker-compose logs -f backend frontend`
- Code changes được reflect ngay (volumes mounted)

### Production
- Build images trước: `docker-compose build`
- Loại bỏ volumes hoặc chỉ mount config
- Sử dụng environment-specific compose files
- Enable resource limits trong compose

### Monitoring
```bash
# Real-time stats
docker stats

# Health status
docker-compose ps

# Logs streaming
docker-compose logs -f --tail=50 backend

# Container inspection
docker inspect gemini-backend
```
