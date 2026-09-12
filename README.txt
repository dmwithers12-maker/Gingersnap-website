GINGERSNAP SALES SITE — VERSION 4
QUOTE INTAKE / BACKEND-READY EDITION

WHAT CHANGED
• The customer quote form is now wired to POST to /api/quotes.
• Vehicle Year / Make / Model are preserved with the quote.
• Artwork and 3D files can be uploaded.
• The included Python server assigns a GingerSnap request number.
• Submitted jobs are stored server-side in data/quotes.jsonl.
• Uploaded files are stored in data/uploads/.
• Optional SMTP settings can send GingerSnap an email when a quote arrives.
• If index.html is opened without the server, Preview Mode safely stores demo leads only in that browser.

LOCAL TEST
1. Keep the folder structure together.
2. On a computer with Python installed, open a terminal in this folder.
3. Run: python server.py
4. Visit http://localhost:8000
5. Submit a test quote.
6. Look in data/quotes.jsonl and data/uploads/.

EMAIL NOTIFICATION
A production host can supply these environment variables:
GS_NOTIFY_EMAIL
GS_SMTP_HOST
GS_SMTP_PORT
GS_SMTP_USER
GS_SMTP_PASSWORD
GS_SMTP_FROM

SECURITY BEFORE PUBLIC LAUNCH
The production deployment should add HTTPS, spam/rate protection, upload size/type enforcement,
private file storage, backups, and an appropriate privacy policy. Customer uploads should not be
placed in a publicly browsable folder in a final deployment.

PAYMENTS — NEXT PHASE
Do not collect card numbers in this custom form. Use a PCI-compliant hosted checkout/payment
provider. Recommended workflow:
1. Quote request arrives.
2. GingerSnap reviews artwork/specs and determines final price.
3. Customer approves proof/quote.
4. Server creates a hosted checkout/payment link for that approved amount.
5. Customer pays on the payment provider's secure page.
6. Payment webhook marks the GingerSnap job as paid.
7. Production begins.

For fixed-price products, hosted checkout can start directly from the product page.

VERSION 5 VEHICLE DECAL UPDATE
• Customer chooses Self-install, GingerSnap installation, or Need advice.
• Self-install means decal purchase only with no GingerSnap installation labor.
• GingerSnap installation is explicitly identified as an additional charge.
• The installation choice travels with the quote request and can be priced after review.
• No arbitrary installation price is hard-coded because labor varies by vehicle, decal size, placement and complexity.
