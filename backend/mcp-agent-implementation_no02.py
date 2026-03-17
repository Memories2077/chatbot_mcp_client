from flask import Flask, request, jsonify, render_template
from google import genai
from google.genai import types
from dotenv import load_dotenv
import os
import requests
import json

load_dotenv()

app = Flask(__name__)

# ─── Config ────────────────────────────────────────────────────────────────
client         = genai.Client(api_key=os.getenv("GOOGLEAPIKEY"))
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://192.168.165.135:9090")
MODEL          = "gemini-2.5-flash"


# ═══════════════════════════════════════════════════════════════════════════
#  PROMETHEUS HELPER FUNCTIONS  (được Agent gọi khi cần)
# ═══════════════════════════════════════════════════════════════════════════

def _prom_instant(promql: str) -> dict:
    """Chạy instant query, trả về dict kết quả."""
    try:
        r = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": promql},
            timeout=5
        )
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def _prom_range(promql: str, minutes: int = 5) -> dict:
    """Chạy range query trong N phút gần nhất."""
    import time
    now   = int(time.time())
    start = now - minutes * 60
    step  = max(10, minutes * 2)
    try:
        r = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query_range",
            params={"query": promql, "start": start, "end": now, "step": f"{step}s"},
            timeout=10
        )
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def _snapshot() -> dict:
    """Lấy snapshot 4 metrics chính của demo-app."""
    QUERIES = {
        "replicas":     'kube_deployment_spec_replicas{deployment="demo-app"}',
        "cpu_usage_pct":'sum(rate(container_cpu_usage_seconds_total{pod=~"demo-app-.*", container="nginx"}[2m])) * 100',
        "ram_usage_mb": 'sum(container_memory_working_set_bytes{pod=~"demo-app-.*", container="nginx"}) / 1024 / 1024',
        "req_rate_rps": 'sum(rate(nginx_http_requests_total{namespace="default"}[1m]))',
    }
    results = {}
    for key, promql in QUERIES.items():
        data = _prom_instant(promql)
        result_list = data.get("data", {}).get("result", [])
        results[key] = float(result_list[0]["value"][1]) if result_list else None
    return results


# ═══════════════════════════════════════════════════════════════════════════
#  MCP-STYLE TOOL DEFINITIONS  (Gemini function calling)
# ═══════════════════════════════════════════════════════════════════════════

TOOLS = [
    types.Tool(function_declarations=[

        types.FunctionDeclaration(
            name="get_metrics_snapshot",
            description=(
                "Lấy snapshot tức thời của 4 metrics chính của demo-app: "
                "số replicas, CPU usage (%), RAM usage (MB), request rate (req/s). "
                "Dùng khi user hỏi về trạng thái tổng quan của hệ thống."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={},
                required=[]
            )
        ),

        types.FunctionDeclaration(
            name="query_prometheus",
            description=(
                "Chạy một PromQL query tùy ý lên Prometheus (instant query). "
                "Dùng khi user hỏi về một metric cụ thể hoặc cần viết query phức tạp. "
                "Trả về raw JSON result từ Prometheus."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "promql": types.Schema(
                        type=types.Type.STRING,
                        description="PromQL query string, ví dụ: rate(http_requests_total[5m])"
                    )
                },
                required=["promql"]
            )
        ),

        types.FunctionDeclaration(
            name="query_prometheus_range",
            description=(
                "Chạy PromQL range query để xem xu hướng theo thời gian. "
                "Dùng khi user hỏi về trend, lịch sử, hoặc so sánh trong khoảng thời gian."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "promql": types.Schema(
                        type=types.Type.STRING,
                        description="PromQL query string"
                    ),
                    "minutes": types.Schema(
                        type=types.Type.INTEGER,
                        description="Số phút cần lấy dữ liệu (mặc định 5, tối đa 60)"
                    )
                },
                required=["promql"]
            )
        ),

    ])
]

# Tool executor: ánh xạ tên tool → function thực thi
def execute_tool(name: str, args: dict) -> str:
    if name == "get_metrics_snapshot":
        result = _snapshot()
        return json.dumps(result, ensure_ascii=False)

    elif name == "query_prometheus":
        result = _prom_instant(args.get("promql", ""))
        return json.dumps(result, ensure_ascii=False)

    elif name == "query_prometheus_range":
        result = _prom_range(
            args.get("promql", ""),
            args.get("minutes", 5)
        )
        return json.dumps(result, ensure_ascii=False)

    return json.dumps({"error": f"Unknown tool: {name}"})


# ═══════════════════════════════════════════════════════════════════════════
#  AI AGENT — agentic loop với tool use
# ═══════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """Bạn là một AI Agent chuyên về vận hành hệ thống (SRE/DevOps).
Bạn có quyền truy cập vào Prometheus để lấy metrics của hệ thống demo-app chạy trên K3s.

Các metrics hiện có:
- replicas: số pod đang chạy (kube_deployment_spec_replicas)
- cpu_usage_pct: CPU usage của container nginx (%)
- ram_usage_mb: RAM usage của container nginx (MB)  
- req_rate_rps: request rate của nginx trong namespace default (req/s)

Khi user hỏi về trạng thái hệ thống, hãy chủ động gọi tool để lấy dữ liệu thực tế rồi trả lời.
Trả lời ngắn gọn, rõ ràng. Nếu có số liệu, hãy đưa ra nhận xét về tình trạng hệ thống.
Trả lời bằng tiếng Việt trừ khi user dùng ngôn ngữ khác."""


def run_agent(user_message: str) -> str:
    """
    Agentic loop:
    1. Gửi message đến Gemini kèm tool definitions
    2. Nếu Gemini muốn gọi tool → thực thi → gửi kết quả lại
    3. Lặp đến khi Gemini trả lời hoàn chỉnh (không gọi tool nữa)
    """
    messages = [types.Content(role="user", parts=[types.Part(text=user_message)])]

    for _ in range(5):  # max 5 vòng lặp tool call
        response = client.models.generate_content(
            model=MODEL,
            contents=messages,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                tools=TOOLS,
                temperature=0.3,
            )
        )

        # ── Null-safe: kiểm tra candidates trước khi truy cập ──────────────
        candidates = response.candidates or []
        if not candidates:
            return response.text or "Không có phản hồi từ model."

        candidate = candidates[0]
        content   = candidate.content
        if content is None:
            return response.text or "Không có phản hồi từ model."

        parts = content.parts or []

        # Append assistant response vào history
        messages.append(types.Content(role="model", parts=list(parts)))

        # Kiểm tra có function call không
        tool_calls = [p for p in parts if getattr(p, "function_call", None) is not None]

        if not tool_calls:
            # Không có tool call → trả về text cuối cùng
            text_parts = [str(p.text) for p in parts if getattr(p, "text", None)]
            return "\n".join(text_parts).strip() if text_parts else (response.text or "")

        # Thực thi tất cả tool calls, gửi kết quả lại
        tool_results = []
        for part in tool_calls:
            fc     = part.function_call
            name   = getattr(fc, "name", "")
            raw_args = getattr(fc, "args", None)
            args     = {k: v for k, v in raw_args.items()} if raw_args else {}
            output = execute_tool(name, args)
            tool_results.append(
                types.Part(
                    function_response=types.FunctionResponse(
                        name=name,
                        response={"result": output}
                    )
                )
            )

        messages.append(types.Content(role="user", parts=tool_results))

    return "Agent đã vượt quá số vòng lặp cho phép."


# ═══════════════════════════════════════════════════════════════════════════
#  FLASK ROUTES
# ═══════════════════════════════════════════════════════════════════════════

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message", "")
    if not user_message:
        return jsonify({"error": "Empty message"}), 400
    try:
        reply = run_agent(user_message)
        return jsonify({"response": reply})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── Prometheus proxy (vẫn giữ để frontend dashboard dùng) ────────────────
@app.route("/api/prom/query", methods=["GET"])
def prom_query():
    query = request.args.get("query")
    if not query:
        return jsonify({"error": "Missing query param"}), 400
    try:
        resp = requests.get(f"{PROMETHEUS_URL}/api/v1/query", params={"query": query}, timeout=5)
        return jsonify(resp.json()), resp.status_code
    except requests.exceptions.ConnectionError:
        return jsonify({"error": f"Cannot reach Prometheus at {PROMETHEUS_URL}"}), 503
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/prom/query_range", methods=["GET"])
def prom_query_range():
    query = request.args.get("query")
    start = request.args.get("start")
    end   = request.args.get("end")
    step  = request.args.get("step", "15s")
    if not all([query, start, end]):
        return jsonify({"error": "Missing query/start/end params"}), 400
    try:
        resp = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query_range",
            params={"query": query, "start": start, "end": end, "step": step},
            timeout=10
        )
        return jsonify(resp.json()), resp.status_code
    except requests.exceptions.ConnectionError:
        return jsonify({"error": f"Cannot reach Prometheus at {PROMETHEUS_URL}"}), 503
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/prom/snapshot", methods=["GET"])
def prom_snapshot():
    return jsonify(_snapshot())


@app.route("/api/prom/targets", methods=["GET"])
def prom_targets():
    try:
        resp = requests.get(f"{PROMETHEUS_URL}/api/v1/targets", timeout=5)
        return jsonify(resp.json()), resp.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── Entry point ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)