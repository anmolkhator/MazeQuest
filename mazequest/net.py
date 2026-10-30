"""Talks to the MazeQuest server (app.py). Requests run in threads so the pygame window never freezes."""
import http.cookiejar, json, logging, queue, socket, threading, time
import urllib.error, urllib.request
from urllib.parse import urlparse


class ApiError(Exception):
    pass


def normalize(addr):
    """'' -> host here; '192.168.1.20' -> http://192.168.1.20:8000; 'name.ngrok.app' -> https://name.ngrok.app"""
    a = (addr or "").strip().rstrip("/")
    if not a:
        return "http://127.0.0.1:8000"
    if "://" in a:
        return a
    host = a.split("/")[0].split(":")[0]
    if host == "localhost" or host.replace(".", "").isdigit():
        return "http://" + a + ("" if ":" in a else ":8000")
    return "https://" + a


def split(url):
    u = urlparse(url if "://" in url else "http://" + url)
    return u.hostname or "127.0.0.1", u.port or 8000


def lan_ip():                                    # the address friends on your Wi-Fi can use
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


class Net:
    def __init__(self, base):
        self.base = normalize(base)
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.done = queue.Queue()

    def request(self, path, body=None, timeout=5):           # blocking call: GET without a body, POST with one
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(self.base + path, data=data, headers={"Content-Type": "application/json"})
        try:
            with self.opener.open(req, timeout=timeout) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            try:
                msg = json.loads(e.read()).get("error")
            except Exception:
                msg = None
            raise ApiError(msg or f"Server error {e.code}")
        except (urllib.error.URLError, OSError):
            raise ApiError("Cannot reach the server")

    def reachable(self):
        try:
            self.request("/api/me", timeout=1)
            return True
        except ApiError:
            return False

    def call(self, path, body=None, cb=None):                # non-blocking: cb(result, error) runs in pump()
        def work():
            try:
                res, err = self.request(path, body), None
            except ApiError as e:
                res, err = None, str(e)
            self.done.put((cb, res, err))
        threading.Thread(target=work, daemon=True).start()

    def pump(self):
        while not self.done.empty():
            cb, res, err = self.done.get()
            if cb:
                cb(res, err)


def ensure_server(url):
    """Use the server at url. If it is this computer and nothing is running, start the game server here."""
    url = normalize(url)
    host, port = split(url)
    net = Net(url)
    if net.reachable():
        return
    if host not in ("127.0.0.1", "localhost"):
        raise ApiError(f"Cannot reach {net.base}")
    try:
        import app as server
    except ImportError:
        raise ApiError("Flask is missing: pip install flask")
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    threading.Thread(target=lambda: server.app.run(host="0.0.0.0", port=port, threaded=True, use_reloader=False),
                     daemon=True).start()
    for _ in range(40):
        time.sleep(0.1)
        if net.reachable():
            return
    raise ApiError("The local server did not start")
