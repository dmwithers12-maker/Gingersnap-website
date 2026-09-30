from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import json
import cgi
import uuid
import datetime
import os
import shutil
import mimetypes

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


def get_customer_email(record):
    """Find the customer's email address in the submitted form."""
    for key in ("customer_email", "email"):
        value = record.get(key)

        if value:
            if isinstance(value, list):
                value = value[0] if value else ""

            return str(value).strip()

    return ""


def get_customer_name(record):
    """Find the customer's name for the confirmation email."""
    for key in ("customer_name", "name"):
        value = record.get(key)

        if value:
            if isinstance(value, list):
                value = value[0] if value else ""

            return str(value).strip()

    return ""


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

        # Keep track of uploaded files
        email_attachments = []

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

                        values.append(safe)
                        email_attachments.append((dest, safe))

                    else:
                        values.append(
                            make_json_safe(subitem.value)
                        )

                record[key] = values
                continue

            # Handle uploaded files
            if getattr(item, "filename", None):
                safe = Path(item.filename).name
                dest = UPLOADS / f"{qid}-{safe}"

                with open(dest, "wb") as f:
                    shutil.copyfileobj(item.file, f)

                record[key] = safe
                email_attachments.append((dest, safe))

            # Handle normal form fields
            else:
                record[key] = make_json_safe(item.value)

        # Save quote
        with open(QUOTES, "a", encoding="utf-8") as f:
            f.write(
                json.dumps(record, ensure_ascii=False) + "\n"
            )

        print(
            f"Quote received successfully: {qid}",
            flush=True
        )

        # -----------------------------------------------------
        # EMAIL SYSTEM
        # -----------------------------------------------------

        if os.getenv("GS_NOTIFY_EMAIL"):
            try:
                import smtplib
                from email.message import EmailMessage

                smtp_host = os.getenv("GS_SMTP_HOST")

                smtp_port = int(
                    os.getenv(
                        "GS_SMTP_PORT",
                        "50587"
                    )
                )

                smtp_user = os.getenv("GS_SMTP_USER")
                smtp_password = os.getenv("GS_SMTP_PASSWORD")

                from_address = os.getenv(
                    "GS_SMTP_FROM",
                    smtp_user
                )

                # -------------------------------------------------
                # EMAIL #1 - GINGERSNAP BUSINESS NOTIFICATION
                # -------------------------------------------------

                message = EmailMessage()

                message["Subject"] = (
                    f"New GingerSnap quote {qid}"
                )

                message["From"] = from_address
                message["To"] = os.getenv(
                    "GS_NOTIFY_EMAIL"
                )

                def clean_label(key):
                    labels = {
                        "name": "Customer Name",
                        "customer_name": "Customer Name",
                        "email": "Customer Email",
                        "customer_email": "Customer Email",
                        "phone": "Phone",
                        "customer_phone": "Phone",
                        "service": "Service",
                        "product": "Product",
                        "quantity": "Quantity",
                        "vehicle": "Vehicle",
                        "vehicle_year": "Vehicle Year",
                        "vehicle_make": "Vehicle Make",
                        "vehicle_model": "Vehicle Model",
                        "installation": "Installation",
                        "install": "Installation",
                        "description": "Description",
                        "details": "Job Description",
                        "notes": "Customer Notes",
                        "artwork": "Artwork",
                        "file": "Artwork",
                    }

                    return labels.get(
                        key.lower(),
                        key.replace("_", " ").title()
                    )

                lines = [
                    "========================================",
                    "        GINGERSNAP - NEW QUOTE",
                    "========================================",
                    "",
                    f"QUOTE NUMBER: {qid}",
                    "",
                    "----------------------------------------",
                    "CUSTOMER / JOB INFORMATION",
                    "----------------------------------------",
                ]

                for key, value in record.items():

                    if key in ("quote_id", "created_at"):
                        continue

                    value_text = str(value)

                    if any(
                        filename == value_text
                        for _, filename in email_attachments
                    ):
                        continue

                    lines.append(
                        f"{clean_label(key)}: {value}"
                    )

                lines.extend([
                    "",
                    "----------------------------------------",
                    "CUSTOMER ARTWORK",
                    "----------------------------------------",
                ])

                if email_attachments:

                    for _, filename in email_attachments:
                        lines.append(
                            f"Attached: {filename}"
                        )

                    lines.extend([
                        "",
                        "Customer artwork is attached to this email.",
                    ])

                else:
                    lines.append(
                        "No artwork was uploaded with this request."
                    )

                lines.extend([
                    "",
                    "----------------------------------------",
                    "GingerSnap",
                    "Your Ideas. Our Ink. Anywhere.",
                    "info@gsaswag.com",
                    "----------------------------------------",
                ])

                message.set_content(
                    "\n".join(lines)
                )

                # Attach customer artwork to GingerSnap email
                for file_path, original_name in email_attachments:

                    mime_type, encoding = (
                        mimetypes.guess_type(original_name)
                    )

                    if mime_type:
                        maintype, subtype = (
                            mime_type.split("/", 1)
                        )
                    else:
                        maintype = "application"
                        subtype = "octet-stream"

                    with open(file_path, "rb") as attachment:
                        message.add_attachment(
                            attachment.read(),
                            maintype=maintype,
                            subtype=subtype,
                            filename=original_name,
                        )

                # -------------------------------------------------
                # SEND GINGERSNAP EMAIL
                # -------------------------------------------------

                with smtplib.SMTP(
                    smtp_host,
                    smtp_port,
                    timeout=30
                ) as smtp:

                    smtp.ehlo()
                    smtp.starttls()
                    smtp.ehlo()

                    smtp.login(
                        smtp_user,
                        smtp_password,
                    )

                    smtp.send_message(message)

                print(
                    f"GingerSnap notification sent successfully "
                    f"for {qid} with "
                    f"{len(email_attachments)} attachment(s)",
                    flush=True,
                )

                # -------------------------------------------------
                # EMAIL #2 - CUSTOMER CONFIRMATION
                # -------------------------------------------------

                customer_email = get_customer_email(record)
                customer_name = get_customer_name(record)

                if customer_email:

                    confirmation = EmailMessage()

                    confirmation["Subject"] = (
                        f"GingerSnap received your quote request - {qid}"
                    )

                    confirmation["From"] = from_address
                    confirmation["To"] = customer_email
                    confirmation["Reply-To"] = (
                        "info@gsaswag.com"
                    )

                    if customer_name:
                        greeting = f"Hi {customer_name},"
                    else:
                        greeting = "Hello,"

                    confirmation_lines = [
                        greeting,
                        "",
                        "Thank you for contacting GingerSnap!",
                        "",
                        "We have received your quote request.",
                        "",
                        f"Quote Request: {qid}",
                        "",
                    ]

                    if email_attachments:
                        confirmation_lines.extend([
                            "We also received the artwork/file "
                            "you submitted with your request.",
                            "",
                        ])

                    confirmation_lines.extend([
                        "We will review your project details "
                        "and contact you with pricing and next steps.",
                        "",
                        "Please keep your quote number for reference.",
                        "",
                        "Thank you!",
                        "",
                        "GingerSnap",
                        "Your Ideas. Our Ink. Anywhere.",
                        "info@gsaswag.com",
                    ])

                    confirmation.set_content(
                        "\n".join(confirmation_lines)
                    )

                    # Send customer confirmation
                    with smtplib.SMTP(
                        smtp_host,
                        smtp_port,
                        timeout=30
                    ) as smtp:

                        smtp.ehlo()
                        smtp.starttls()
                        smtp.ehlo()

                        smtp.login(
                            smtp_user,
                            smtp_password,
                        )

                        smtp.send_message(
                            confirmation
                        )

                    print(
                        f"Customer confirmation sent successfully "
                        f"for {qid} to {customer_email}",
                        flush=True,
                    )

                else:
                    print(
                        f"No customer email found for {qid}; "
                        f"confirmation not sent.",
                        flush=True,
                    )

            except Exception as ex:
                print(
                    f"Email system failed for {qid}: "
                    f"{type(ex).__name__}: {ex}",
                    flush=True,
                )

        # -----------------------------------------------------
        # RETURN SUCCESS TO WEBSITE
        # -----------------------------------------------------

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

    port = int(
        os.environ.get("PORT", "8000")
    )

    print(
        f"GingerSnap server starting on port {port}",
        flush=True,
    )

    ThreadingHTTPServer(
        ("0.0.0.0", port),
        Handler
    ).serve_forever()
