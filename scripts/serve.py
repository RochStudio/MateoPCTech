"""Local-only preview of Vercel clean URLs; never a production server."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent


class PreviewHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        path = urlsplit(self.path).path
        translated = Path(self.translate_path(path))
        if path != '/' and not translated.suffix and translated.with_suffix('.html').is_file():
            self.path = path + '.html'
        return super().do_GET()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=4174)
    args = parser.parse_args()
    server = ThreadingHTTPServer(('127.0.0.1', args.port), partial(PreviewHandler, directory=str(ROOT)))
    print(f'Local preview: http://127.0.0.1:{args.port}', flush=True)
    server.serve_forever()
