
import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise RuntimeError(
        "GEMINI_API_KEY not found. Check your .env file in the project root."
    )

model = ChatGoogleGenerativeAI(
    model="gemini-3.8-flash",
    google_api_key=api_key,
    temperature=0,
)

response = model.invoke(
    "You are helping CloudOps AI investigate AWS incidents. "
    "In one sentence, explain what high CPU utilization means."
)

print("Gemini response:")
print(response.content)
