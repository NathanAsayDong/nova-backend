import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.header import Header
from email import encoders
import os
from typing import Optional, List


class EmailService:
    def __init__(self):
        self.smtp_server = "smtp.gmail.com"
        self.port = 587  # For starttls
        self.sender_email = os.getenv("EMAIL_SENDER", "your-email@gmail.com")
        self.sender_password = os.getenv("EMAIL_APP_PASSWORD")
        
    def send_email(self, to: list[str], subject: str, body: str, is_html: bool = False, attachments: Optional[List[str]] = None):
        """
        Send an email using Gmail SMTP
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body content
            is_html: Whether the body is HTML formatted
            attachments: List of file paths to attach
        """
        try:
            # Create message container
            message = MIMEMultipart()
            message["From"] = self.sender_email
            message["To"] = ", ".join(to)
            message["Subject"] = Header(subject, "utf-8")
            
            # Add body to email
            if is_html:
                message.attach(MIMEText(body, "html", "utf-8"))
            else:
                message.attach(MIMEText(body, "plain", "utf-8"))
            
            # Add attachments if any
            if attachments:
                for file_path in attachments:
                    if os.path.isfile(file_path):
                        with open(file_path, "rb") as attachment:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(attachment.read())
                        
                        encoders.encode_base64(part)
                        part.add_header(
                            'Content-Disposition',
                            f'attachment; filename= {os.path.basename(file_path)}'
                        )
                        message.attach(part)
            
            # Create SMTP session
            server = smtplib.SMTP(self.smtp_server, self.port)
            server.starttls()  # Enable security
            server.login(self.sender_email, self.sender_password)
            
            # Send email
            text = message.as_string()
            server.sendmail(self.sender_email, to, text)
            server.quit()
            
            return True
            
        except Exception as e:
            print(f"Error sending email: {e}")
            return False