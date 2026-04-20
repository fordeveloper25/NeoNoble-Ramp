"""One-shot script: generate OG-image 1200x630 for /sto landing via Nano Banana.
Saves to /app/frontend/public/og-sto.png.
"""
import asyncio
import base64
import os
from pathlib import Path

from dotenv import load_dotenv
from emergentintegrations.llm.chat import LlmChat, UserMessage

load_dotenv("/app/backend/.env")

OUT = Path("/app/frontend/public/og-sto.png")

PROMPT = (
    "Wide cinematic social-sharing hero image, 1200x630 aspect ratio, dark indigo "
    "to deep purple gradient background with subtle grid lines and bokeh dots. "
    "Modern fintech security-token theme. Centered bold white headline: "
    "'NeoNoble Ramp STO · Revenue Share Security Token'. "
    "Below headline, smaller amber text: 'Polygon PoS · Redemption at NAV · MiCA compliant'. "
    "Left side: stylized glowing vault icon with a purple-to-pink shield. "
    "Right side: upward trending chart made of glowing indigo bars, with small "
    "token hexagon graphics floating. Subtle chromatic aberration, grain texture. "
    "Professional, investor-grade aesthetic. No people, no stock photo look."
)


async def main():
    key = os.environ["EMERGENT_LLM_KEY"]
    chat = (
        LlmChat(api_key=key, session_id="og-sto-1200x630",
                system_message="You are an image generation assistant.")
        .with_model("gemini", "gemini-3.1-flash-image-preview")
        .with_params(modalities=["image", "text"])
    )
    text, images = await chat.send_message_multimodal_response(UserMessage(text=PROMPT))
    print("text snippet:", (text or "")[:100])
    if not images:
        raise SystemExit("no image returned")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    data = base64.b64decode(images[0]["data"])
    OUT.write_bytes(data)
    print(f"saved {len(data)} bytes -> {OUT}")


if __name__ == "__main__":
    asyncio.run(main())
