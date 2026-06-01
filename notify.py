import smtplib, json, os
from datetime import date
from email.mime.text import MIMEText

with open("config.json") as f:
    CONFIG = json.load(f)

CARRIER_GATEWAYS = {
    "bell":    "txt.bell.ca",
    "rogers":  "pcs.rogers.com",
    "telus":   "msg.telus.com",
    "fido":    "fido.ca",
    "freedom": "txt.freedommobile.ca",
    "virgin":  "vmobile.ca",
    "koodo":   "msg.koodo.com",
    "chatr":   "pcs.rogers.com",
    "public":  "msg.telus.com"
}

def send_text(gmail_user, gmail_pass, to_email, subject, body):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"]    = gmail_user
    msg["To"]      = to_email
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(gmail_user, gmail_pass)
        smtp.sendmail(gmail_user, to_email, msg.as_string())

def get_email_gateway(phone, carrier):
    domain = CARRIER_GATEWAYS.get(carrier.lower(), "")
    if not domain:
        return None
    digits = "".join(filter(str.isdigit, phone))
    if digits.startswith("1") and len(digits) == 11:
        digits = digits[1:]
    return f"{digits}@{domain}"

def main():
    gmail_user = os.environ.get("GMAIL_USER", CONFIG.get("gmail_user", ""))
    gmail_pass = os.environ.get("GMAIL_PASSWORD", "")
    today      = date.today().strftime("%Y%m%d")

    # TEST MODE: send a test text to a single named employee
    test_user = os.environ.get("TEST_USER", "").strip().lower()
    if test_user:
        for emp in CONFIG["employees"]:
            if emp["name"].lower() == test_user and emp.get("active", True):
                name    = emp["name"]
                phone   = emp.get("phone", "")
                carrier = emp.get("carrier", "")
                to_email = get_email_gateway(phone, carrier) if phone and carrier else None
                if to_email:
                    send_text(gmail_user, gmail_pass, to_email,
                              f"Test: {name} on-call reminder",
                              f"Test message: {name}, you are on call today!")
                    print(f"Test text sent to {name} at {to_email}")
                else:
                    print(f"No valid phone/carrier for {name}")
                return
        print(f"Employee '{test_user}' not found in config")
        return

    # NORMAL MODE: check who is on call today
    oncall_today = []

    for emp in CONFIG["employees"]:
        if not emp.get("active", True):
            continue
        name    = emp["name"]
        phone   = emp.get("phone", "")
        carrier = emp.get("carrier", "")

        ics_file = f"docs/{name.lower()}_schedule.ics"
        if not os.path.exists(ics_file):
            print(f"  No ICS for {name}, skipping")
            continue

        with open(ics_file) as f:
            content = f.read()

        if f"DTSTART;VALUE=DATE:{today}" in content:
            oncall_today.append(name)
            print(f"  {name} is on call today")

            if phone and carrier:
                to_email = get_email_gateway(phone, carrier)
                if to_email:
                    try:
                        send_text(gmail_user, gmail_pass, to_email,
                                  f"Reminder: {name} is on call today!",
                                  f"Reminder: {name}, you are on call today!")
                        print(f"    Texted {name} at {to_email}")
                    except Exception as e:
                        print(f"    Failed to text {name}: {e}")
        else:
            print(f"  {name} is NOT on call today")

    # Text the office listing everyone on call by name
    office = CONFIG.get("office", {})
    if office.get("active") and office.get("phone") and office.get("carrier") and oncall_today:
        to_email = get_email_gateway(office["phone"], office["carrier"])
        if to_email:
            names = ", ".join(oncall_today)
            try:
                send_text(gmail_user, gmail_pass, to_email,
                          f"On-Call Today: {names}",
                          f"On call today: {names}")
                print(f"  Office notified: {names}")
            except Exception as e:
                print(f"  Failed to notify office: {e}")

    if not oncall_today:
        print("  Nobody on call today")

if __name__ == "__main__":
    main()
