
from openai import OpenAI
import base64, streamlit as st, json, re

client = OpenAI(
    api_key=st.secrets["GROQ_API_KEY"],
    base_url="https://api.groq.com/openai/v1"
)

MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"


def chat(messages: list, system: str = "") -> str:
    full_messages = []
    if system:
        full_messages.append({"role": "system", "content": system})
    full_messages.extend(messages)
    response = client.chat.completions.create(
        model=MODEL,
        messages=full_messages,
        max_tokens=1024,
    )
    return response.choices[0].message.content


def describe_photo(image_bytes: bytes, mime_type: str = "image/jpeg") -> dict:
    b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime_type};base64,{b64}"}
                },
                {
                    "type": "text",
                    "text": (
                        "You are a construction site safety inspector. "
                        "Describe what you see in this photo in 2-3 sentences, "
                        "focusing on safety conditions. Then answer: "
                        "is there a visible safety hazard? "
                        "Respond ONLY as JSON, no other text: "
                        "{\"description\": \"...\", "
                        "\"hazard_flag\": true/false, \"hazard_details\": \"...\"}"
                    )
                }
            ]
        }],
        max_tokens=512,
    )
    text = response.choices[0].message.content
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {"description": text, "hazard_flag": False, "hazard_details": ""}


def generate_text(prompt: str, system: str = "") -> str:
    return chat([{"role": "user", "content": prompt}], system=system)
