from twilio.rest import Client
from dotenv import load_dotenv
import os

load_dotenv()

class TwilioService:
    def __init__(self):
        self.client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))

    def make_call(self, to):
        self.client.calls.create(
            url="http://demo.twilio.com/docs/voice.xml",
            to=to,
            from_=os.getenv("TWILIO_PHONE_NUMBER"),
        )