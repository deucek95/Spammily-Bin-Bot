import os
import re
import html
import logging
import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = os.environ.get("BOT_TOKEN")
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL")
PORT = int(os.environ.get("PORT", 10000))

if not TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable not found")

if not RENDER_EXTERNAL_URL:
    raise RuntimeError("RENDER_EXTERNAL_URL environment variable not found")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

BIN_REGEX = re.compile(
    r"^(?:!bin|!ibin|/bin)\s+(\d{6,8})$",
    re.IGNORECASE,
)


async def lookup_bin(bin_number: str):
    headers = {
        "User-Agent": "TelegramBinBot/1.0"
    }

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            f"https://lookup.binlist.net/{bin_number}",
            headers=headers,
        )

    return response


async def bin_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()

    match = BIN_REGEX.match(text)

    if not match:
        return

    bin_number = match.group(1)

    try:
        response = await lookup_bin(bin_number)

        if response.status_code != 200:
            await update.message.reply_text(
                f"❌ BIN <code>{bin_number}</code> not found or invalid.",
                parse_mode="HTML",
            )
            return

        data = response.json()

        bank = data.get("bank") or {}
        country = data.get("country") or {}

        country_name = html.escape(
            country.get("name", "N/A")
        )

        flag = country.get("emoji", "")

        bank_name = html.escape(
            bank.get("name", "N/A")
        )

        scheme = html.escape(
            str(data.get("scheme", "N/A")).upper()
        )

        card_type = html.escape(
            str(data.get("type", "N/A")).upper()
        )

        level = html.escape(
            str(data.get("brand", "N/A"))
        )

        user = html.escape(
            update.effective_user.username
            or update.effective_user.first_name
        )

        result = f"""
💳 <b>BIN Lookup Result</b>

🔢 <b>BIN:</b> {bin_number}
🌍 <b>Country:</b> {country_name} {flag}
🏦 <b>Bank:</b> {bank_name}
💳 <b>Brand:</b> {scheme}
💰 <b>Type:</b> {card_type}
🏆 <b>Level:</b> {level}

<b>{scheme} CARD</b>

👤 <b>Sent by:</b> @{user}
""".strip()

        await update.message.reply_text(
            result,
            parse_mode="HTML",
        )

    except httpx.RequestError:
        await update.message.reply_text(
            "⚠️ Could not fetch BIN info right now."
        )
    except Exception as e:
        logging.exception(e)
        await update.message.reply_text(
            "⚠️ An unexpected error occurred."
        )


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    await update.message.reply_text(
        "✅ BIN Checker Bot Ready\n\n"
        "Commands:\n"
        "!bin 544612\n"
        "!ibin 223613\n"
        "/bin 411111"
    )


def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("bin", bin_handler)
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            bin_handler,
        )
    )

    WEBHOOK_PATH = "telegram"

    print(f"Webhook URL: {RENDER_EXTERNAL_URL}/{WEBHOOK_PATH}")
    print(f"Port: {PORT}")

    app.run_webhook(
    listen="0.0.0.0",
    port=PORT,
    url_path=WEBHOOK_PATH,
    webhook_url=f"{RENDER_EXTERNAL_URL}/{WEBHOOK_PATH}",
    drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
