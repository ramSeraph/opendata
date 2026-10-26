"""Preview a built Pages directory at its /opendata/ project path."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(302)
            self.send_header('Location', '/opendata/')
            self.end_headers()
            return
        super().do_GET()

    def translate_path(self, path):
        if path.startswith('/opendata/'):
            path = path[len('/opendata'):]
        return super().translate_path(path)

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', default='.pages-build')
    parser.add_argument('--port', type=int, default=8030)
    args = parser.parse_args()
    server = ThreadingHTTPServer(('127.0.0.1', args.port), partial(Handler, directory=args.directory))
    print(f'Preview: http://localhost:{args.port}/opendata/', flush=True)
    server.serve_forever()
