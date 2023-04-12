from http.server import BaseHTTPRequestHandler
import json

class notif_handler(BaseHTTPRequestHandler):
    def do_POST(self):
        print('Headers:', self.headers)
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        parsed_data = json.loads(post_data.decode('utf-8'))
        print("Data:", parsed_data)
        self.send_response(200)