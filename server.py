from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import json, cgi, uuid, datetime, os, shutil

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'; UPLOADS=DATA/'uploads'
DATA.mkdir(exist_ok=True);UPLOADS.mkdir(exist_ok=True)
QUOTES=DATA/'quotes.jsonl'

class Handler(SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path!='/api/quotes':
            self.send_error(404);return
        ctype,pdict=cgi.parse_header(self.headers.get('content-type',''))
        if ctype!='multipart/form-data':
            self.send_error(400,'Expected multipart form');return
        pdict['boundary']=bytes(pdict['boundary'],'utf-8')
        form=cgi.FieldStorage(fp=self.rfile,headers=self.headers,environ={'REQUEST_METHOD':'POST','CONTENT_TYPE':self.headers['content-type']})
        qid='GS-'+datetime.datetime.now().strftime('%y%m%d')+'-'+uuid.uuid4().hex[:5].upper()
        record={'quote_id':qid,'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
        for key in form.keys():
            item=form[key]
            if getattr(item,'filename',None):
                safe=Path(item.filename).name
                dest=UPLOADS/f'{qid}-{safe}'
                with open(dest,'wb') as f: shutil.copyfileobj(item.file,f)
                record[key]=str(dest.relative_to(ROOT))
            else: record[key]=item.value
        with open(QUOTES,'a',encoding='utf-8') as f:f.write(json.dumps(record)+'\n')
        # Optional email notification via standard SMTP environment settings.
        if os.getenv('GS_NOTIFY_EMAIL'):
            try:
                import smtplib
                from email.message import EmailMessage
                m=EmailMessage();m['Subject']=f'New GingerSnap quote {qid}';m['From']=os.getenv('GS_SMTP_FROM');m['To']=os.getenv('GS_NOTIFY_EMAIL')
                m.set_content('\n'.join(f'{k}: {v}' for k,v in record.items()))
                with smtplib.SMTP(os.getenv('GS_SMTP_HOST'),int(os.getenv('GS_SMTP_PORT','587'))) as s:
                    s.starttls();s.login(os.getenv('GS_SMTP_USER'),os.getenv('GS_SMTP_PASSWORD'));s.send_message(m)
            except Exception as ex: print('Email notification failed:',ex)
        body=json.dumps({'ok':True,'quote_id':qid}).encode()
        self.send_response(201);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)

if __name__=='__main__':
    os.chdir(ROOT)
    print('GingerSnap V4: http://localhost:8000')
    
    port = int(os.environ.get("PORT", "8000"))
ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
