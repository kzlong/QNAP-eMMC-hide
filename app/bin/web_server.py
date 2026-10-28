#!/usr/bin/env python3
import json, os, subprocess, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

APPDEST = os.environ.get('TRIM_APPDEST', '/vol1/@appcenter/qnap-emmc-hide')
PKGVAR = os.environ.get('TRIM_PKGVAR', '/var/apps/qnap-emmc-hide/var')
MAIN = os.environ.get('TRIM_MAIN', '/var/apps/qnap-emmc-hide/cmd/main')
LOG = os.path.join(PKGVAR, 'hide-qnap-emmc.log')
PORT = int(os.environ.get('QNAP_EMMC_PORT', '9528'))
UI = os.path.join(APPDEST, 'ui')
os.makedirs(PKGVAR, exist_ok=True)

def run_main(action):
    env = os.environ.copy(); env['TRIM_PKGVAR'] = PKGVAR; env['TRIM_APPDEST'] = APPDEST
    try:
        p = subprocess.run([MAIN, action], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=20)
        return p.returncode == 0, p.stdout.strip()
    except Exception as e:
        return False, str(e)

def status_data():
    ok, out = run_main('status')
    mounts = []
    for n in (1,2,3,5,6,7):
        dev=f'/dev/mmcblk0p{n}'
        try:
            p=subprocess.run(['findmnt','-rn','-S',dev,'-o','TARGET'],capture_output=True,text=True,timeout=3)
            targets=[x for x in p.stdout.splitlines() if x]
        except Exception: targets=[]
        mounts.append({'device':dev,'mounted_targets':targets,'hidden':not any(t=='/vol00/RemovableDisk' or t.startswith('/vol00/RemovableDisk_') for t in targets)})
    return {'running':ok and out=='running','service_status':out or ('running' if ok else 'stopped'),'partitions':mounts}

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args): pass
    def send_json(self, data, code=200):
        body=json.dumps(data,ensure_ascii=False).encode()
        self.send_response(code); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Content-Length',str(len(body))); self.send_header('Cache-Control','no-store'); self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        path=urlparse(self.path).path
        if path=='/api/status': self.send_json(status_data()); return
        if path=='/api/logs':
            try:
                with open(LOG,encoding='utf-8',errors='replace') as f: lines=f.readlines()[-150:]
            except FileNotFoundError: lines=[]
            self.send_json({'path':LOG,'lines':''.join(lines)}); return
        if path in ('/','/index.html'):
            try: body=open(os.path.join(UI,'index.html'),'rb').read()
            except OSError: body=b'UI missing'
            self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body); return
        self.send_json({'error':'not found'},404)
    def do_POST(self):
        path=urlparse(self.path).path
        if path not in ('/api/hide-now','/api/start','/api/stop'):
            self.send_json({'ok':False,'message':'not found'},404); return
        action={'/api/hide-now':'hide-now','/api/start':'start','/api/stop':'pause'}[path]
        if action=='hide-now':
            env=os.environ.copy(); env['TRIM_PKGVAR']=PKGVAR; env['TRIM_APPDEST']=APPDEST
            script=os.path.join(APPDEST,'bin','hide-qnap-emmc.sh')
            try:
                p=subprocess.run([script,'once'],env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=20)
                self.send_json({'ok':p.returncode==0,'message':p.stdout.strip() or '已执行立即隐藏，请查看日志'}); return
            except Exception as e: self.send_json({'ok':False,'message':str(e)},500); return
        ok,msg=run_main(action); self.send_json({'ok':ok,'message':msg or action},200 if ok else 500)

if __name__=='__main__':
    # Bind all interfaces so the fnOS desktop iframe/proxy can reach the service port.
    # The control API is intended for trusted LAN access only.
    server=ThreadingHTTPServer(('0.0.0.0',PORT),Handler)
    server.serve_forever()
