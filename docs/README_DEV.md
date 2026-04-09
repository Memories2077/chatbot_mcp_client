# Hướng dẫn Dành cho Lập trình viên (Developer Guide)

Tài liệu này cung cấp cái nhìn tổng quan về cấu trúc mã nguồn (source code), kiến trúc hệ thống và cách thức hoạt động của dự án chatbot_mcp_client. Tài liệu này nhằm giúp các lập trình viên mới dễ dàng nắm bắt, hiểu rõ chức năng của từng luồng (flow) và từng phần/thư mục.

## 📂 1. Cấu trúc thư mục khối mã nguồn

Khái quát cấu trúc chính yếu của dự án:
```tree
chatbot_mcp_client/
├── backend/                  # Chứa toàn bộ logic xử lý API (FastAPI + Python)
│   ├── main.py               # Entry point xử lý API chính (endpoint /chat, /health, kết nối Agent)
│   ├── requirements.txt      # Các thư viện Python cần thiết
│   └── venv/                 # Virtual environment (môi trường ảo máy cục bộ)
├── src/                      # Chứa toàn bộ giao diện logic Web (Next.js + TypeScript)
│   ├── app/                  # App Router của Next.js (chứa các route giao diện người dùng)
│   ├── components/           # Các UI component tái sử dụng (Button, Input, Chat box...)
│   ├── hooks/                # Custom React hooks xử lý logic tái sử dụng
│   └── lib/                  # Các utilities, cấu hình và quản lý state cốt lõi (Zustand)
├── docs/                     # Chứa các tài liệu liên quan đến hình ảnh và dự án khác
├── package.json              # Chứa thông tin thư viện (dependencies) và scripts của Node.js
├── docker-compose.yml        # Tệp cấu hình chạy toàn bộ hệ thống bằng Docker
├── README.md                 # Hướng dẫn build và khởi chạy project
└── .env                      # File chứa biến môi trường (Ví dụ: GEMINI_API_KEY)
```

## 🖥 2. Frontend (Giao diện người dùng)

Frontend được xây dựng với tư duy Component-based hiện đại với bộ công cụ:
* **Core Framework**: Next.js 15 (sử dụng App Router tiên tiến).
* **Ngôn ngữ**: TypeScript & React 19.
* **Quản lý trạng thái (State Management)**: Ứng dụng dùng Zustand để lưu trữ nhanh trạng thái (lịch sử đoạn chat, cài đặt của hệ thống máy chủ, tham số model) mà người dùng không cần load lại trạng thái cũ. Trạng thái cũng được persist trong `localStorage`.
* **Giao diện & UI**: Sử dụng Tailwind CSS, kèm theo thư viện Headless UI là Radix (thương hiệu shadcn/ui). Hỗ trợ hiệu ứng hiển thị với Framer Motion.

### Nhiệm vụ cốt lõi của Frontend:
* **Giao diện thao tác**: Cung cấp giao diện hiện đại cho tương tác chat, kèm khả năng chọn model cung cấp (`gemini`, `groq`) cũng như cài đặt nhiệt độ (temperature).
* **Quản lý MCP Servers URL**: Giao diện hỗ trợ kết nối Model Context Protocol (MCP) server bằng cách cho người dùng nhập một địa chỉ external server. Khi gọi backend, nó sẽ gói kèm các URL này lại để chuyển qua LLM sử dụng tool.

## ⚙️ 3. Backend (Hệ thống Xử lý AI & Công cụ)

Backend chịu trách nhiệm dịch chuỗi dữ liệu (LLM), kết hợp Tool bằng cách kết nối với các hệ lưu trữ MCP Protocol.

* **Framework Chính**: FastAPI (Xử lý request đồng thời cao, phục vụ async mượt mà qua các luồng).
* **Công cụ Suy Luận AI**: `LangChain` - Giao tiếp và đồng bộ với Google Generative AI (Gemini) hoặc Groq.

### Nhiệm vụ chính của `backend/main.py`:
`main.py` là trái tim luân chuyển dữ liệu của Backend. Có hai endpoint chính:
1. `/health`: Đầu mục Check sống còn cho Docker hoặc quá trình local dev.
2. `/chat`: Xử lý luồng chat khi user bấm gửi:
   - **Tạo Agent động (`get_or_create_agent`)**: Gồm việc đánh giá payload đầu vào. Nếu request từ người dùng gửi lên `mcpServers`, Backend sẽ khởi tạo ClientSession và connect tới địa chỉ MCP Server đó, trích xuất tất cả các Tools mà MCP Server cung cấp. Cấu hình LangChain qua đó thành công cấp Quyền Agent cho LLM (dùng function Calling).
   - **Dynamic System Prompt**: Liên tục nhúng nhắc nhở và thay đổi System message tùy thuộc vào việc người dùng có đang cấp Quyền Truy Cập Công Cụ hay không. Điều này giữ Agent đi không lệch hướng yêu cầu.

## 🔄 4. Luồng dữ liệu (Data Flow) Cơ bản

Một quy trình gửi tin nhắn diễn ra như sau:
1. **Người dùng nhắn tin**: Nội dung được đóng gói tại Frontend cùng các Setting hiện hành (loại model, lịch sử chat, URLs của MCP Server).
2. **Post Request**: Frontend thực hiện HTTP POST tới đường dẫn `http://localhost:8000/chat`.
3. **Backend khởi tạo kết nối Tool (Nếu có)**:
   - Qua `streamable_http_client` nó cố gắng call mcp_urls.
   - Nhận Load tools từ mcp session thành công.
   - Trở thành 1 `LangChain Agent`, truyền vào các tools đã được parse.
4. **LLM Suy luận (Reasoning)**: Agent phân tích câu hỏi người dùng, đối chiếu với list Tool đang có mcp cung cấp. Nếu cần thu thập dữ kiện thật, Agent trigger Tool đó, tổng hợp và đưa ra trả lời cuối.
5. **Trả dữ liệu về UI**: Trả text phản hồi. Frontend hiển thị trên UI bằng component hỗ trợ Markdown.

## 💡 5. Cách Mở Rộng / Sửa Đổi Code (Tips)

- **Cấu hình Model API Keys**: Thêm/xóa thông số thiết yếu (Provider / API Keys) tại `.env` và cập nhật logic `if/elif` xác định model ở hàm `get_or_create_agent` thuộc file `backend/main.py`.
- **Thêm tính năng UI mới**: Hãy tạo hoặc sửa các block file chứa ở `src/components/`, khi cần cập nhật trạng thái chung để chia sẻ đến các Component ngoài luồng, bổ sung logic store tại file hook/zustand trong folder `src/lib`.
- **Debug Lỗi LangChain/Tool**: Bạn có thể theo dõi biến `agent.ainvoke` tại dòng bắt Exception ở file `main.py` của Backend, các lỗi do gọi hàm sai định dạng của MCP Server đều tuồn về đoạn try/except này.
- **Tập trung vào Docker**: Toàn bộ luồng build production đều chịu cấu hình từ `Dockerfile.backend` & `Dockerfile.frontend` cũng như là `docker-compose.yml`. Nếu bạn thêm Library / Thư mục file mới, phải đảm bảo Dockerfile được cấp quyền thao tác hay copy vào image.

---
Vui lòng tham khảo file `README.md` chính để xem các bước thiết lập môi trường (pip, npm) và chạy project cơ bản!
