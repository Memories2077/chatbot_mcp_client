# 🌌 Ethereal Intelligence

**Ethereal Intelligence** là một nền tảng Agentic Chatbot thế hệ mới, được thiết kế với giao diện hiện đại và khả năng mở rộng không giới hạn thông qua **Model Context Protocol (MCP)**. Ứng dụng kết hợp sức mạnh của **Gemini 2.5 Flash** và các mô hình ngôn ngữ tiên tiến nhất để tạo ra một trợ lý AI có khả năng thực thi công cụ (tools) linh hoạt trong thời gian thực.

![Ethereal Intelligence Preview](img/demo.gif)

## ✨ Tính năng nổi bật

- **Giao diện "Ethereal" Hiện Đại**: Ngôn ngữ thiết kế tinh tế với tông màu Deep Purple (#8340FF) và Dark Gray (#201C21), tối ưu cho trải nghiệm người dùng chuyên nghiệp.
- **Agentic Tool Execution**: Tận dụng LangChain để tạo ra vòng lặp Agentic. Chatbot không chỉ trả lời mà còn biết tự suy nghĩ và sử dụng các MCP Servers để truy xuất dữ liệu bên ngoài.
- **Tích hợp Gemini 2.5 Flash**: Hỗ trợ mô hình mới nhất từ Google với tốc độ xử lý cực nhanh và khả năng xử lý ngữ cảnh sâu.
- **Dynamic MCP Integration**: Cho phép đăng ký các MCP Server (tool endpoints) trực tiếp từ giao diện thông qua URL, tự động nhận diện metadata và trạng thái kết nối.
- **Quản lý Hội thoại Thông minh**: 
    - Lưu trữ lịch sử (Persist) tự động vào `localStorage`.
    - Cơ chế **Auto-Archive**: Tự động lưu trữ các phiên chat cũ sau 1 giờ không hoạt động để giữ không gian làm việc sạch sẽ.
- **Multi-Provider Support**: Linh hoạt chuyển đổi giữa Google Gemini và Groq (Llama 3, Mixtral) để tối ưu chi phí và hiệu năng.

## 🛠️ Công nghệ sử dụng

### Frontend (The "Ethereal" UI)
- **Framework**: Next.js 15 (App Router), TypeScript.
- **State Management**: Zustand (với middleware Persist).
- **Styling**: Tailwind CSS, Radix UI, Lucide Icons.
- **Animations**: Framer Motion cho các hiệu ứng chuyển cảnh mượt mà.

### Backend (The "Intelligence" Engine)
- **Framework**: FastAPI (Python 3.12+).
- **AI Orchestration**: LangChain, LangGraph (dành cho Agentic workflows).
- **MCP Client**: MCP SDK (kết nối với các tool server qua HTTP/SSE).
- **Models**: Gemini 2.5 Flash, Groq API.

## 🚀 Hướng dẫn cài đặt

### 1. Cấu hình môi trường

Tạo file `.env` tại thư mục gốc từ mẫu `.env.example`:
```env
GEMINI_API_KEY="your_gemini_api_key_here"
GROQ_API_KEY="your_groq_api_key_here" # Tùy chọn
NEXT_PUBLIC_BACKEND_PORT=8000
```

### 2. Triển khai Backend

```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate | Unix: source venv/bin/activate
pip install -r requirements.txt
python main.py
```

### 3. Triển khai Frontend

```bash
npm install
npm run dev
```
Truy cập ứng dụng tại: `http://localhost:9002`

### 4. Sử dụng Docker (Khuyên dùng)

```bash
docker compose up --build -d
```

## 🔌 Kết nối MCP Servers

Để mở rộng khả năng của **Ethereal Intelligence**, bạn có thể thêm các URL của MCP Server vào mục Settings:
- Ví dụ: `http://localhost:5000/mcp` (Server quản lý file, tra cứu database, hoặc điều khiển hệ thống).
- Agent sẽ tự động nhận diện các Tools khả dụng và sử dụng chúng khi cần thiết dựa trên yêu cầu của bạn.

---

**Ethereal Intelligence** — *Fluid. Intelligent. Boundless.*
