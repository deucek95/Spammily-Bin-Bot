import os
import re
import csv
import html
import zipfile
import logging
import httpx
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TOKEN = os.environ.get("BOT_TOKEN")
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL")
PORT = int(os.environ.get("PORT", 10000))

if not TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable not found")

if not RENDER_EXTERNAL_URL:
    raise RuntimeError(
        "RENDER_EXTERNAL_URL environment variable not found"
    )

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

BIN_REGEX = re.compile(
    r"^(?:!bin|!ibin|/bin)\s+(\d{6,8})$",
    re.IGNORECASE,
)

LOCAL_BINS = {}
CACHE = {}


def load_local_bins():
    try:
        with zipfile.ZipFile(
            "bin-list-data.zip",
            "r",
        ) as z:

            filename = z.namelist()[0]

            with z.open(filename) as f:

                reader = csv.DictReader(
                    (
                        line.decode("utf-8")
                        for line in f
                    )
                )

                count = 0

                for row in reader:

                    bin_number = (
                        row.get("BIN", "")
                        .strip()
                    )

                    if (
                        not bin_number.isdigit()
                        or len(bin_number) < 6
                    ):
                        continue

                    LOCAL_BINS[
                        bin_number[:6]
                    ] = {
                        "scheme":
                            row.get(
                                "Brand",
                                "",
                            ),
                        "type":
                            row.get(
                                "Type",
                                "",
                            ),
                        "brand":
                            row.get(
                                "Category",
                                "",
                            ),
                        "issuer":
                            row.get(
                                "Issuer",
                                "",
                            ),
                        "country":
                            row.get(
                                "CountryName",
                                "",
                            ),
                        "phone":
                            row.get(
                                "IssuerPhone",
                                "",
                            ),
                        "url":
                            row.get(
                                "IssuerUrl",
                                "",
                            ),
                    }

                    count += 1

        logging.info(
            f"Loaded {count:,} local BINs"
        )

    except Exception as e:
        logging.exception(e)
        raise


async def lookup_binlist(
    bin_number: str,
):
    try:
        async with httpx.AsyncClient(
            timeout=10,
        ) as client:

            response = await client.get(
                f"https://lookup.binlist.net/{bin_number}",
                headers={
                    "User-Agent":
                        "TelegramBinBot/1.0"
                },
            )

        if response.status_code == 200:
            return response.json()

    except Exception:
        pass

    return None


async def lookup_bin(
    bin_number: str,
):
    key = bin_number[:6]

    if key in CACHE:
        return CACHE[key]

    if key in LOCAL_BINS:

        result = {
            "source":
                "LOCAL",
            "data":
                LOCAL_BINS[key],
        }

        CACHE[key] = result

        return result

    remote = await lookup_binlist(
        bin_number
    )

    if remote:

        result = {
            "source":
                "BINLIST",
            "data":
                remote,
        }

        CACHE[key] = result

        return result

    return None


async def bin_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if (
        not update.message
        or not update.message.text
    ):
        return

    text = (
        update.message.text
        .strip()
    )

    match = BIN_REGEX.match(
        text
    )

    if not match:
        return

    bin_number = match.group(
        1
    )

    try:
        result = await lookup_bin(
            bin_number
        )

        if not result:
            await update.message.reply_text(
                f"❌ BIN <code>{bin_number}</code> not found.",
                parse_mode="HTML",
            )
            return

        user = html.escape(
            update.effective_user.username
            or update.effective_user.first_name
        )

        if (
            result["source"]
            == "LOCAL"
        ):
            data = result[
                "data"
            ]

            country = html.escape(
                data.get(
                    "country"
                )
                or "N/A"
            )

            bank = html.escape(
                data.get(
                    "issuer"
                )
                or "N/A"
            )

            scheme = html.escape(
                str(
                    data.get(
                        "scheme"
                    )
                    or "N/A"
                ).upper()
            )

            card_type = html.escape(
                str(
                    data.get(
                        "type"
                    )
                    or "N/A"
                ).upper()
            )

            level = html.escape(
                data.get(
                    "brand"
                )
                or "N/A"
            )

        else:
            data = result[
                "data"
            ]

            bank_data = (
                data.get(
                    "bank"
                )
                or {}
            )

            country_data = (
                data.get(
                    "country"
                )
                or {}
            )

            country = html.escape(
                country_data.get(
                    "name",
                    "N/A",
                )
            )

            emoji = (
                country_data.get(
                    "emoji",
                    "",
                )
            )

            if emoji:
                country += (
                    " "
                    + emoji
                )

            bank = html.escape(
                bank_data.get(
                    "name",
                    "N/A",
                )
            )

            scheme = html.escape(
                str(
                    data.get(
                        "scheme",
                        "N/A",
                    )
                ).upper()
            )

            card_type = html.escape(
                str(
                    data.get(
                        "type",
                        "N/A",
                    )
                ).upper()
            )

            level = html.escape(
                str(
                    data.get(
                        "brand",
                        "N/A",
                    )
                )
            )

        response = f"""
💳 <b>BIN Lookup Result</b>

🔢 <b>BIN:</b> {bin_number}
🌍 <b>Country:</b> {country}
🏦 <b>Bank:</b> {bank}
💳 <b>Brand:</b> {scheme}
💰 <b>Type:</b> {card_type}
🏆 <b>Level:</b> {level}

<b>{scheme} CARD</b>

📚 <b>Source:</b> {result["source"]}

👤 <b>Sent by:</b> @{user}
""".strip()

        await update.message.reply_text(
            response,
            parse_mode="HTML",
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
    load_local_bins()

    app = (
        Application
        .builder()
        .token(TOKEN)
        .build()
    )

    app.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    app.add_handler(
        CommandHandler(
            "bin",
            bin_handler,
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT
            & ~filters.COMMAND,
            bin_handler,
        )
    )

    WEBHOOK_PATH = "telegram"

    print(
        f"Webhook URL: "
        f"{RENDER_EXTERNAL_URL}/{WEBHOOK_PATH}"
    )

    print(
        f"Loaded "
        f"{len(LOCAL_BINS):,} "
        f"BINs"
    )

    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=WEBHOOK_PATH,
        webhook_url=(
            f"{RENDER_EXTERNAL_URL}/"
            f"{WEBHOOK_PATH}"
        ),
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
