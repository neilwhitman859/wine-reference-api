from fastapi import FastAPI
import os
from openai import OpenAI

app = FastAPI()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/explain-wine")
def explain_wine(name: str):
    prompt = f"""
Explain this wine in simple terms:

{name}

Describe:
- Likely flavor profile
- Body and acidity
- Who might enjoy it
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    explanation = response.choices[0].message.content

    return {
        "wine": name,
        "explanation": explanation
    }
