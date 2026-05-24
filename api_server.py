"""
API 服务 — 接收手动刷新请求，触发 main.py 重新抓取与渲染。
仅监听 127.0.0.1:8001，由 Nginx 反向代理，不直接暴露。
"""
import json
import os
import subprocess
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
REFRESH_TOKEN = os.getenv("REFRESH_TOKEN", "")


class RefreshHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # 静默日志，避免干扰

    def _json_response(self, code, data):
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def do_POST(self):
        if self.path != "/api/refresh":
            self._json_response(404, {"ok": False, "error": "not found"})
            return

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        params = parse_qs(body)
        token = params.get("token", [""])[0]

        if not REFRESH_TOKEN or token != REFRESH_TOKEN:
            self._json_response(403, {"ok": False, "error": "invalid token"})
            return

        print(f"[API] 收到刷新请求，开始执行 main.py ...")
        try:
            project_dir = os.path.dirname(os.path.abspath(__file__))
            result = subprocess.run(
                [sys.executable, "main.py"],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=180,
            )
            output_tail = result.stdout[-800:] if len(result.stdout) > 800 else result.stdout
            print(f"[API] main.py 执行完毕 (exit={result.returncode})")
            self._json_response(200, {
                "ok": True,
                "returncode": result.returncode,
                "output": output_tail,
            })
        except subprocess.TimeoutExpired:
            print("[API] main.py 执行超时")
            self._json_response(504, {"ok": False, "error": "timeout"})
        except Exception as e:
            print(f"[API] 异常: {e}")
            self._json_response(500, {"ok": False, "error": str(e)})

    def do_GET(self):
        self._json_response(405, {"ok": False, "error": "method not allowed"})


if __name__ == "__main__":
    port = 8001
    server = HTTPServer(("127.0.0.1", port), RefreshHandler)
    print(f"[API] 服务已启动: 127.0.0.1:{port}")
    server.serve_forever()
