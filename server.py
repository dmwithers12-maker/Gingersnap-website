from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import json
import cgi
import uuid
import datetime
import os
import shutil

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
UPLOADS = DATA / "uploads"

DATA.mkdir(exist_ok=True)
UPLOADS.mkdir(exist_ok=True)

QUOTES = DATA / "quotes.jsonl"


def make_json_safe(value):
    """Convert form values into text that JSON can safely store."""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")

    if isinstance(value, list):
        return [make_json_safe(v) for v in value]

    return value


class Handler(SimpleHTTPRequestHandler):

    def do_POST(self):
        if self.path != "/api/quotes":
            self.send_error(404)
            return

        ctype, pdict = cgi.parse_header(
            self.headers.get("content-type", "")
        )

        if ctype != "multipart/form-data":
            self.send_error(400, "Expected multipart form")
            return

        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={
                "REQUEST_METHOD": "POST",
                "CONTENT_TYPE": self.headers["content-type"],
            },
        )

        qid = (
            "GS-"
            + datetime.datetime.now().strftime("%y%m%d")
            + "-"
            + uuid.uuid4().hex[:5].upper()
        )

        record = {
            "quote_id": qid,
            "created_at": datetime.datetime.now(
                datetime.timezone.utc
            ).isoformat(),
        }

        for key in form.keys():
            item = form[key]

            # Handle repeated form fields
            if isinstance(item, list):
                values = []

                for subitem in item:
                    if getattr(subitem, "filename", None):
                        safe = Path(subitem.filename).name
                        dest = UPLOADS / f"{qid}-{safe}"

                        with open(dest, "wb") as f:
                            shutil.copyfileobj(subitem.file, f)

                        values.append(str(dest.relative_to(ROOT)))
                    else:
                        values.append(make_json_safe(subitem.value))

                record[key] = values
                continue

            # Handle uploaded files
            if getattr(item, "filename", None):
                safe = Path(item.filename).name
                dest = UPLOADS / f"{qid}-{safe}"

                with open(dest, "wb") as f:
                    shutil.copyfileobj(item.file, f)

                record[key] = str(dest.relative_to(ROOT))

            # Handle normal form fields
            else:
                record[key] = make_json_safe(item.value)

        # Save quote
        with open(QUOTES, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        print(f"Quote received successfully: {qid}", flush=True)

        # Email GingerSnap
        if os.getenv("GS_NOTIFY_EMAIL"):
            try:
                import smtplib
                from email.message import EmailMessage

                message = EmailMessage()

                message["Subject"] = f"New GingerSnap quote {qid}"
                message["From"] = os.getenv(
                    "GS_SMTP_FROM",
                    os.getenv("GS_SMTP_USER", "")
                )
                message["To"] = os.getenv("GS_NOTIFY_EMAIL")

                message.set_content(
                    "\n".join(
                        f"{key}: {value}"
                        for key, value in record.items()
                    )
                )

                smtp_host = os.getenv("GS_SMTP_HOST")
                smtp_port = int(
                    os.getenv("GS_SMTP_PORT", "587")
                )

                with smtplib.SMTP(
                    smtp_host,
                    smtp_port,
                    timeout=30
                ) as smtp:
                    smtp.ehlo()
                    smtp.starttls()
                    smtp.ehlo()
                    smtp.login(
                        os.getenv("GS_SMTP_USER"),
                        os.getenv("GS_SMTP_PASSWORD"),
                    )
                    smtp.send_message(message)

                print(
                    f"Email notification sent successfully for {qid}",
                    flush=True,
                )

            except Exception as ex:
                print(
                    f"Email notification failed for {qid}: "
                    f"{type(ex).__name__}: {ex}",
                    flush=True,
                )

        body = json.dumps(
            {
                "ok": True,
                "quote_id": qid,
            }
        ).encode("utf-8")

        self.send_response(201)
        self.send_header(
            "Content-Type",
            "application/json"
        )
        self.send_header(
            "Content-Length",
            str(len(body))
        )
        self.end_headers()

        self.wfile.write(body)


if __name__ == "__main__":
    os.chdir(ROOT)

    port = int(os.environ.get("PORT", "8000"))

    print(
        f"GingerSnap server starting on port {port}",
        flush=True,
    )

    ThreadingHTTPServer(
        ("0.0.0.0", port),
        Handler
    ).serve_forever()
