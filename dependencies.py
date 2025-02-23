from groq import Groq
from dotenv import load_dotenv
import os

load_dotenv()

client = Groq(api_key=os.getenv("groq_api_key"))