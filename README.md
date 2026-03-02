# Gemini InsightLink 🤖

Một ứng dụng chatbot hiện đại được xây dựng với **Next.js** (Frontend) và **FastAPI** (Backend), tích hợp Google Gemini AI với khả năng kết nối các máy chủ MCP (Model Context Protocol) để thực thi công cụ động.

## ✨ Các Tính Năng Chính

### 💬 Giao Diện Chat Tương Tác
- Giao diện người dùng hiện đại, sạch sẽ và trực quan
- Lịch sử cuộc trò chuyện liên tục với hỗ trợ markdown
- Hiển thị trực quan cho các cuộc gọi công cụ MCP trong luồng tin nhắn
- Cuộn tự động đến tin nhắn mới nhất

### 🤖 Hỗ Trợ Mô Hình Gemini Linh Hoạt
- Chọn và chuyển đổi giữa các mô hình Gemini khác nhau (gemini-2.5-flash, gemini-2.5-pro)
- Điều chỉnh các thông số LLM như nhiệt độ (temperature) và số token tối đa

### 🔧 Tích Hợp MCP Server
- Tùy chỉnh động các máy chủ MCP tùy chỉnh thông qua URL
- Tự động tải công cụ từ các máy chủ MCP
- Thực thi công cụ thông minh với tính năng agent của LangChain

### 💾 Lưu Trữ Thông Minh
- Lưu trữ lịch sử cuộc trò chuyện tại local (localStorage)
- Duy trì ngữ cảnh trên nhiều lần tương tác

### 🎨 Giao Diện Dark Theme Hiện Đại
- Chủ đề tối tinh tế với bảng màu cao cấp:
  - Purple-Indigo chính (#8340FF) cho các phần tử tương tác
  - Background xám sẫm (#201C21)
  - Accent xanh Sky (#7CA9FF)
- Font Inter cho trải nghiệm sạch sẽ và hiện đại
- Bố cục đạp không gian với thiết kế phản ứng

## 🏗️ Kiến Trúc Dự Án

```
chatbot_mcp_client/
├── frontend (Next.js)
│   ├── src/
│   │   ├── app/              # Trang chính ứng dụng
│   │   ├── components/       # Các thành phần React
│   │   │   ├── chat/        # Các thành phần chat chính
│   │   │   └── ui/          # Thư viện UI Radix tái sử dụng
│   │   ├── hooks/           # React hooks tùy chỉnh
│   │   ├── lib/             # Utility functions và types
│   │   └── styles/          # CSS toàn cục
│   ├── package.json
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   └── next.config.ts
│
└── backend (FastAPI)
    ├── main.py              # Ứng dụng FastAPI chính
    └── requirements.txt     # Các phụ thuộc Python
```

## 🚀 Bắt Đầu Nhanh

### Yêu Cầu Hệ Thống
- Node.js 18+ (frontend)
- Python 3.9+ (backend)
- Google Gemini API Key

### Cài Đặt Frontend

```bash
cd chatbot_mcp_client
npm install
```

Tạo file `.env.local`:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```

Chạy máy chủ phát triển:
```bash
npm run dev
```

Ứng dụng sẽ khả dụng tại `http://localhost:9002`

### Cài Đặt Backend

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

Chạy máy chủ backend:
```bash
python main.py
```

Backend sẽ chạy tại `http://localhost:8000`

> **Lưu ý:** Cập nhật endpoint API trong [use-chat-store.ts](src/lib/hooks/use-chat-store.ts#L55) nếu backend chạy trên địa chỉ khác.

## 📦 Tech Stack

### Frontend
- **Framework**: Next.js 15.5 (Turbopack support)
- **Language**: TypeScript
- **UI Library**: React 19
- **UI Components**: Radix UI
- **Styling**: Tailwind CSS, Framer Motion
- **State Management**: Zustand
- **Form**: React Hook Form + Zod
- **Markdown**: React Markdown + Remark GFM
- **Icons**: Lucide React
- **Charts**: Recharts

### Backend
- **Framework**: FastAPI
- **Language**: Python 3.9+
- **LLM**: Google Generative AI (Gemini)
- **Agent**: LangChain + LangGraph
- **MCP**: Model Context Protocol Client
- **CORS**: Middleware hỗ trợ CORS

## 📚 Các Phụ Thuộc Chính

### Frontend
```json
{
  "next": "^15.5.12",
  "react": "^19.2.1",
  "typescript": "^5",
  "zustand": "^4.5.2",
  "tailwindcss": "^3.4.1",
  "@radix-ui": "latest"
}
```

### Backend
```
fastapi
uvicorn
mcp
langchain
langchain-mcp-adapters
langchain-google-genai
langgraph
python-dotenv
```

## 🔧 Cấu Hình

### Frontend - Environment Variables
Tạo `.env.local` trong thư mục gốc:
```env
GEMINI_API_KEY=your_api_key
NEXT_PUBLIC_BACKEND_URL=http://100.78.98.117:8000
```

### Backend - Environment Variables
Tạo `.env` trong thư mục `backend/`:
```env
GEMINI_API_KEY=your_api_key
```

## 💬 Cách Sử Dụng

### Tương Tác Chat Cơ Bản
1. Nhập thông điệp vào ô input ở dưới cùng
2. Nhấn Enter hoặc click nút gửi
3. Xem phản hồi từ Gemini AI

### Cấu Hình Mô Hình
1. Click nút ⚙️ (Settings) ở góc trên phải
2. Chọn mô hình Gemini mong muốn
3. Điều chỉnh nhiệt độ (temperature) và token tối đa
4. Lưu cài đặt

### Thêm MCP Server
1. Mở cài đặt chat
2. Trong phần "MCP Servers", nhập URL máy chủ MCP
3. Nhấn "Add Server"
4. Agent sẽ tự động tải công cụ từ máy chủ

### Quản Lý Lịch Sử
- Click nút 🗑️ ở góc trên phải để xóa toàn bộ lịch sử chat
- Lịch sử được lưu tự động trong localStorage

## 🔄 Quy Trình Agent

1. **Nhập tin nhắn**: Người dùng gửi tin nhắn từ giao diện
2. **Xử lý MCP**: Backend kết nối và tải công cụ từ MCP servers
3. **Tạo Agent**: LangChain tạo agent với các công cụ được tải
4. **Thực thi**: Agent xử lý tin nhắn, có thể gọi các công cụ MCP
5. **Phản hồi**: Kết quả được gửi trở lại frontend
6. **Hiển thị**: Tin nhắn được hiển thị trong chat timeline

## 📁 Cấu Trúc Thư Mục Chi Tiết

```
src/
├── app/
│   ├── layout.tsx           # Layout chính
│   ├── page.tsx             # Trang home
│   └── globals.css          # Styles toàn cục
├── components/
│   ├── chat/
│   │   ├── chat-layout.tsx  # Layout chat chính
│   │   ├── chat-message.tsx # Hiển thị tin nhắn
│   │   └── chat-settings.tsx # Cấu hình chat
│   ├── ui/                  # Thành phần UI Radix
│   └── icons.tsx            # Icon components
├── hooks/
│   ├── use-chat-store.ts    # Zustand store cho chat
│   ├── use-mobile.tsx       # Detect mobile device
│   └── use-toast.ts         # Toast notifications
└── lib/
    ├── types.ts             # TypeScript types
    ├── utils.ts             # Utility functions
    ├── placeholder-images.* # Hình ảnh đơn chủng
    └── hooks/
        └── use-chat-store.ts
```

## 🛠️ Phát Triển

### Linting
```bash
npm run lint
```

### Type Checking
```bash
npm run typecheck
```

### Build Production
```bash
npm run build
npm run start
```

## 🐛 Troubleshooting

### Backend không kết nối được
- Đảm bảo backend đang chạy trên `http://localhost:8000`
- Kiểm tra endpoint trong `use-chat-store.ts`
- Kiểm tra CORS headers

### MCP Server kết nối thất bại
- Xác minh URL của MCP server là chính xác
- Kiểm tra logs backend để xem lỗi kết nối
- Đảm bảo MCP server đang chạy và có thể truy cập

### API Key không hợp lệ
- Kiểm tra `GEMINI_API_KEY` được đặt đúng cách
- Xác minh key từ [Google AI Console](https://aistudio.google.com/apikey)
- Tải lại ứng dụng sau khi cập nhật

## 📝 Ghi Chú Phát Triển

- **State Management**: Zustand được dùng cho quản lý trạng thái chat với persistence
- **Styling**: Tailwind CSS với custom colors theo blueprint
- **API Communication**: Fetch API với error handling
- **Agent Pattern**: LangChain agent với dynamic tool loading

## 🤝 Đóng Góp

Hãy tự do fork, kiểm tra lỗi, và gửi pull requests!

## 📄 License

MIT

---

**Phiên Bản**: 0.1.0  
**Cập nhật Lần Cuối**: Tháng 3 năm 2026
