import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

LOG_FILE = r"D:\Coding\themis\n8n_high_risk_flags.log"

class LogHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != '/log':
            self.send_response(404)
            self.end_headers()
            return

        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')

        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self.send_response(400)
            self.end_headers()
            return

        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "data": data
        }

        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry) + '\n')

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(b'{"status": "ok"}')

    def log_message(self, format, *args):
        pass

if __name__ == '__main__':
    server = HTTPServer(('0.0.0.0', 8001), LogHandler)
    print("Server running on port 8001...")
    server.serve_forever()