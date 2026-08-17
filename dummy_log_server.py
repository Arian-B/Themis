import json
from http.server import HTTPServer, BaseHTTPRequestHandler

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)
        with open("n8n_high_risk_flags.log", "a") as f:
            f.write(body.decode('utf-8') + "\n")
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Logged")

httpd = HTTPServer(('0.0.0.0', 8001), SimpleHTTPRequestHandler)
print("Listening on port 8001")
httpd.serve_forever()
