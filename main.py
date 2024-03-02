import json
import os
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import oci
import requests

REQUEST_URL_TEMPLATE = "https://iaas.{region}.oraclecloud.com/20160918/instances/"
INVALID_RESPONSES = [
    {"code": "InternalError", "message": "Out of host capaciy."},
    {"code": "InternalError", "message": "TooManyRequests"},
]

EMAIL_ADDRESS = os.environ.get("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
EMAIL_SMTP_PORT = int(os.environ.get("EMAIL_SMTP_PORT", 587))
EMAIL_SMTP_SERVER = os.environ.get("EMAIL_SMTP_SERVER", "smtp.gmail.com")
OCI_FINGERPRINT = os.environ["OCI_FINGERPRINT"]
OCI_KEY_FILE_PATH = os.environ.get("OCI_KEY_FILE_PATH", "./private_key.pem")
OCI_REGION = os.environ["OCI_REGION"]
OCI_TENANCY = os.environ["OCI_TENANCY"]
OCI_USER = os.environ["OCI_USER"]
REQUEST_JSON_PATH = os.environ.get("REQUEST_JSON_PATH", "./request.json")
WAIT_TIME = int(os.environ.get("WAIT_TIME", 120))

with open(REQUEST_JSON_PATH) as f:
    request_json = json.load(f)

config = {
    "fingerprint": OCI_FINGERPRINT,
    "key_file": OCI_KEY_FILE_PATH,
    "region": OCI_REGION,
    "tenancy": OCI_TENANCY,
    "user": OCI_USER,
}
signer = oci.Signer.from_config(config)
request_url = REQUEST_URL_TEMPLATE.format(region=config["region"])


def create_instance():
    response = requests.post(
        request_url,
        json=request_json,
        auth=signer,
    )
    return response


def is_response_invalid(response):
    return response.json() in INVALID_RESPONSES


def validate_email_credentials(
    smtp_server,
    smtp_port,
    username,
    password,
):
    server = smtplib.SMTP(smtp_server, smtp_port)
    server.starttls()
    server.login(username, password)
    server.quit()


def send_status_email_and_quit_server(
    smtp_server,
    smtp_port,
    username,
    password,
    from_address,
    to_address,
    subject,
    body,
):
    server = smtplib.SMTP(smtp_server, smtp_port)
    server.starttls()
    server.login(username, password)
    msg = MIMEMultipart()
    msg["From"] = from_address
    msg["To"] = to_address
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    server.sendmail(from_address, to_address, msg.as_string())
    server.quit()


def main():
    if EMAIL_ADDRESS and EMAIL_PASSWORD:
        validate_email_credentials(
            EMAIL_SMTP_SERVER,
            EMAIL_SMTP_PORT,
            EMAIL_ADDRESS,
            EMAIL_PASSWORD,
        )
        send_email = True
    else:
        send_email = False
    while True:
        response = create_instance()
        if is_response_invalid(response):
            time.sleep(WAIT_TIME)
        else:
            if send_email:
                send_status_email_and_quit_server(
                    EMAIL_SMTP_SERVER,
                    EMAIL_SMTP_PORT,
                    EMAIL_ADDRESS,
                    EMAIL_PASSWORD,
                    EMAIL_ADDRESS,
                    EMAIL_ADDRESS,
                    "Oracle Cloud instance creation status",
                    response.text,
                )
            print(response.text)
            break


if __name__ == "__main__":
    main()
