from fastapi import FastAPI
import os
import openai

app = FastAPI()

openai.api_key = os.getenv("OPENAI_API_KEY")

@app.get("/health")
def health():
    return {"status": "great"}

@app.get("/explain-wine")
def explain_wine(
    name: str,
    region: str = "",
    grape: str = "",
    vintage: str = ""
):
    prompt = f"""
Explain this wine in simple terms.

Wine name: {name}
Region: {region}
Grape: {grape}
Vintage: {vintage}

Describe:
- Likely flavor profile
- Body and acidity
- What kind of person might enjoy it
"""

    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    explanation = response["choices"][0]["message"]["content"]

    return {
        "wine": name,
        "explanation": explanation
    }
