import logging
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = "YOUR_BOT_TOKEN_HERE"   # ← Replace with your token

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

async def bin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().lower()
    
    # Support !bin , !ibin , /bin
    if not any(text.startswith(cmd) for cmd in ['!bin ', '!ibin ', '/bin ']):
        return

    try:
        bin_number = text.split(maxsplit=1)[1].strip()[:8]
    except:
        await update.message.reply_text("❌ Usage: `!bin 411111`", parse_mode='Markdown')
        return

    if not bin_number.isdigit() or len(bin_number) < 6:
        await update.message.reply_text("❌ Valid 6-8 digit BIN required.")
        return

    try:
        resp = requests.get(f"https://lookup.binlist.net/{bin_number}", timeout=10)
        
        if resp.status_code != 200:
            await update.message.reply_text(f"❌ BIN `{bin_number}` not found or invalid.")
            return

        data = resp.json()
        bank = data.get('bank', {}) or {}
        country = data.get('country', {}) or {}

        flag = country.get('emoji', '')
        country_name = country.get('name', 'N/A')

        result = f"""
✅ **Bin:** {bin_number}
🌍 **Country:** {country_name}({flag})
🏦 **Bank:** {bank.get('name', 'N/A')}
💳 **Brand:** {data.get('scheme', 'N/A').upper()}
💰 **Type:** {data.get('type', 'N/A').upper()}
🏆 **Level:** {data.get('brand', 'N/A')}

**{data.get('scheme', 'N/A').upper()} CARD**
👤 Sent by: @{update.message.from_user.username or update.message.from_user.first_name}
        """.strip()

        await update.message.reply_text(result, parse_mode='Markdown')
        
    except Exception:
        await update.message.reply_text("⚠️ Could not fetch BIN info right now.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✅ **BIN Checker Bot Ready**\n\n"
        "Commands:\n"
        "`!bin 544612`\n"
        "`!ibin 223613`\n"
        "or `/bin 411111`"
    )

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("bin", bin_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bin_handler))
    
    print("🤖 Bot started - matching Shervano style")
    app.run_polling()

if __name__ == '__main__':
    main()