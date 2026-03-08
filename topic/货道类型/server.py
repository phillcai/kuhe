#!/usr/bin/env python3
"""本地代理服务器，解决 Metabase CORS 问题"""
import http.server
import json
import urllib.request
import ssl
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# 加载项目根目录的 .env 文件
load_dotenv(Path(__file__).parents[2] / '.env')

PORT = 8765
METABASE_URL = os.environ.get('METABASE_URL', 'https://metabase.cookhere.com')
METABASE_API_KEY = os.environ['METABASE_API_KEY']
ERP_URL = os.environ.get('ERP_URL', 'http://47.236.190.163:3000')

# 忽略 SSL 证书校验（内网环境）
ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/api/dataset':
            self._proxy_metabase()
        elif self.path == '/api/erp':
            self._proxy_erp()
        else:
            self.send_error(404)

    def _proxy_metabase(self):
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)

        req = urllib.request.Request(
            f'{METABASE_URL}/api/dataset',
            data=body,
            headers={
                'Content-Type': 'application/json',
                'x-api-key': METABASE_API_KEY,
            },
            method='POST',
        )

        try:
            with urllib.request.urlopen(req, context=ssl_ctx, timeout=30) as resp:
                data = resp.read()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            self.send_response(502)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())

    def _proxy_erp(self):
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)

        req = urllib.request.Request(
            f'{ERP_URL}/gen_api',
            data=body,
            headers={'Content-Type': 'application/json'},
            method='POST',
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            self.send_response(502)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def log_message(self, fmt, *args):
        sys.stderr.write(f'[proxy] {fmt % args}\n')


if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    server = http.server.HTTPServer(('127.0.0.1', PORT), Handler)
    print(f'✅ 服务已启动: http://localhost:{PORT}/index.html')
    print('   按 Ctrl+C 停止')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n已停止')
