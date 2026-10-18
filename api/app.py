"""Tiny lead-capture API for agentcontentkit.pro (Python stdlib only).

POST /api/subscribe   {"email", "source", "company"(honeypot)} -> saves to SQLite
GET  /api/leads.csv   ?token=<ADMIN_TOKEN> (or Authorization: Bearer) -> CSV export
GET  /api/health      -> {"ok": true, "leads": N}

Env: DATA_DIR (default /data), ADMIN_TOKEN (export disabled if empty),
     WEBHOOK_URL (optional: every new lead is also POSTed there as JSON).
"""
import csv, hmac, io, json, os, re, sqlite3, threading, time, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DATA_DIR = os.environ.get('DATA_DIR', '/data')
ADMIN_TOKEN = os.environ.get('ADMIN_TOKEN', '')
WEBHOOK_URL = os.environ.get('WEBHOOK_URL', '')
EMAIL_RE = re.compile(r'^[^@\s<>"]{1,64}@[A-Za-z0-9.-]{1,190}\.[A-Za-z]{2,24}$')
SOURCES = {'guide', 'guide-final', 'kit-waitlist', 'thanks'}
os.makedirs(DATA_DIR, exist_ok=True)
DB = os.path.join(DATA_DIR, 'leads.db')
lock = threading.Lock()
hits = {}  # ip -> recent request times (simple rate limit)


def db():
    con = sqlite3.connect(DB)
    con.execute('''CREATE TABLE IF NOT EXISTS leads(
        email TEXT PRIMARY KEY, source TEXT, created TEXT, updated TEXT,
        ip TEXT, user_agent TEXT, referrer TEXT, utm TEXT, count INTEGER DEFAULT 1)''')
    return con


def limited(ip):
    now = time.time()
    with lock:
        recent = [t for t in hits.get(ip, []) if now - t < 600]
        recent.append(now)
        hits[ip] = recent
        if len(hits) > 5000:
            hits.clear()
    return len(recent) > 10


def webhook(lead):
    if not WEBHOOK_URL:
        return
    try:
        req = urllib.request.Request(WEBHOOK_URL, json.dumps(lead).encode(),
                                     {'Content-Type': 'application/json'})
        urllib.request.urlopen(req, timeout=5).read()
    except Exception as e:  # never lose the lead because of the webhook
        print('webhook failed:', e, flush=True)


class H(BaseHTTPRequestHandler):
    server_version = 'ack'

    def send(self, code, body, ctype='application/json', extra=None):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def ip(self):
        # first X-Forwarded-For entry = the visitor (set by Traefik, passed on by nginx)
        return (self.headers.get('X-Forwarded-For', '').split(',')[0].strip()
                or self.headers.get('X-Real-IP') or self.client_address[0]).strip()

    def do_GET(self):
        path = self.path.split('?')[0]
        if path == '/api/health':
            with db() as con:
                n = con.execute('SELECT COUNT(*) FROM leads').fetchone()[0]
            return self.send(200, {'ok': True, 'leads': n})
        if path == '/api/leads.csv':
            q = dict(x.split('=', 1) for x in self.path.partition('?')[2].split('&') if '=' in x)
            auth = self.headers.get('Authorization', '') or 'Bearer ' + q.get('token', '')
            if not ADMIN_TOKEN or not hmac.compare_digest(auth, 'Bearer ' + ADMIN_TOKEN):
                return self.send(404, {'ok': False})
            out = io.StringIO()
            w = csv.writer(out)
            w.writerow(['email', 'source', 'created', 'updated', 'count', 'referrer', 'utm'])
            with db() as con:
                for row in con.execute('SELECT email,source,created,updated,count,referrer,utm FROM leads ORDER BY created'):
                    w.writerow(row)
            return self.send(200, out.getvalue().encode(), 'text/csv; charset=utf-8',
                             {'Content-Disposition': 'attachment; filename="leads.csv"'})
        self.send(404, {'ok': False})

    def do_POST(self):
        if self.path.split('?')[0] != '/api/subscribe':
            return self.send(404, {'ok': False})
        try:
            n = int(self.headers.get('Content-Length', 0))
            if n > 4096:
                raise ValueError
            body = json.loads(self.rfile.read(n) or b'{}')
        except Exception:
            return self.send(400, {'ok': False, 'error': 'Bad request.'})
        if body.get('company'):  # honeypot: bots fill hidden fields
            return self.send(200, {'ok': True})
        ip = self.ip()
        if limited(ip):
            return self.send(429, {'ok': False, 'error': 'Too many tries. Please wait a few minutes.'})
        email = str(body.get('email', '')).strip().lower()
        if not EMAIL_RE.match(email):
            return self.send(400, {'ok': False, 'error': 'Please enter a valid email.'})
        source = str(body.get('source', 'guide'))
        source = source if source in SOURCES else 'guide'
        now = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        lead = {'email': email, 'source': source, 'created': now,
                'referrer': str(body.get('referrer', ''))[:300], 'utm': str(body.get('utm', ''))[:300]}
        with lock, db() as con:
            con.execute('''INSERT INTO leads(email,source,created,updated,ip,user_agent,referrer,utm)
                VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(email) DO UPDATE SET updated=excluded.updated,
                count=count+1, source=CASE WHEN leads.source='kit-waitlist' THEN leads.source ELSE excluded.source END''',
                        (email, source, now, now, ip, self.headers.get('User-Agent', '')[:300],
                         lead['referrer'], lead['utm']))
        print('lead', source, flush=True)
        threading.Thread(target=webhook, args=(lead,), daemon=True).start()
        self.send(200, {'ok': True})

    def log_message(self, *a):
        pass


if __name__ == '__main__':
    db().close()
    ThreadingHTTPServer(('127.0.0.1', 8000), H).serve_forever()
