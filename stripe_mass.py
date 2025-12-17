import aiohttp
import asyncio
import json
import random
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# သင့် domain နှင့် Stripe key
DOMAIN = "https://dainte.com"
PK = "pk_live_51F0CDkINGBagf8ROVbhXA43bHPn9cGEHEO55TN2mfNGYsbv2DAPuv6K0LoVywNJKNuzFZ4xGw94nVElyYg1Aniaf00QDrdzPhf"

# သင့် ppc() function ကို ဒီအတိုင်းထားပါ (မပြင်ပါနဲ့)
# parseX() နှင့် make_request() functions များလည်း ထည့်ထားပါ

# ===================== Telegram Bot Functions =====================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start command ကို လက်ခံပါ"""
    welcome_text = (
        "🔄 Credit Card Checker Bot မှ ကြိုဆိုပါတယ်\n\n"
        "📁 .txt ဖိုင်တစ်ခု ပို့ပါ\n"
        "ဖိုင်ထဲမှာ ကတ်အချက်အလက် ရိုက်ထည့်ပါ:\n"
        "ကတ်နံပါတ်|လ|နှစ်|CVV\n\n"
        "ဥပမာ:\n4111111111111111|12|2026|123"
    )
    await update.message.reply_text(welcome_text)

async def handle_text_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """အသုံးပြုသူ ဖိုင် ပို့လာရင် လက်ခံပါ"""
    document = update.message.document
    
    # .txt ဖိုင်သာ လက်ခံမယ်
    if not document.file_name.endswith('.txt'):
        await update.message.reply_text("❌ .txt ဖိုင်သာ ပို့ပါ")
        return
    
    await update.message.reply_text("📥 ဖိုင်လက်ခံရရှိပြီး၊ စစ်ဆေးနေပါ...")
    
    # ဖိုင်ကို download လုပ်မယ်
    file = await document.get_file()
    temp_file = f"temp_{document.file_name}"
    await file.download_to_drive(temp_file)
    
    try:
        # ကတ်နံပါတ်များ ဖတ်မယ်
        with open(temp_file, 'r', encoding='utf-8') as f:
            cards = [line.strip() for line in f if line.strip()]
        
        if not cards:
            await update.message.reply_text("❌ ဖိုင်အလွတ် သို့မဟုတ် ပုံစံမှားယွင်းနေပါတယ်")
            return
        
        total_cards = len(cards)
        await update.message.reply_text(f"🔍 ကတ်အရေအတွက်: {total_cards}\nစစ်ဆေးနေပါ...")
        
        approved = 0
        declined = 0
        results = []
        
        # တစ်ကတ်ချင်း စစ်ဆေးမယ်
        for i, card in enumerate(cards, 1):
            result = await ppc(card, i, total_cards)
            results.append(result)
            
            if "✅ ᴀᴘᴘʀᴏᴠᴇᴅ 🔥" in result:
                approved += 1
            else:
                declined += 1
            
            # 10 ကတ်တိုင်း ရလဒ်တွေ ပို့မယ်
            if i % 10 == 0 or i == total_cards:
                await update.message.reply_text('\n'.join(results[-10:]))
            
            # ကတ်ခြားအချိန် (မူရင်း ကုဒ်အတိုင်း)
            if i < total_cards:
                await asyncio.sleep(random.uniform(10, 15))
        
        # နောက်ဆုံး ရလဒ်စာရင်း
        summary = [
            "🎯 စစ်ဆေးမှု ပြီးဆုံးပါပြီ",
            f"✅ အောင်မြင်သော ကတ်များ: {approved}",
            f"❌ ငြင်းပယ်ခံရသော ကတ်များ: {declined}",
            f"📊 အောင်မြင်မှုရာခိုင်နှုန်း: {(approved/total_cards)*100:.1f}%"
        ]
        await update.message.reply_text('\n'.join(summary))
        
    except Exception as e:
        await update.message.reply_text(f"❌ အမှားတစ်ခု ဖြစ်ပွားခဲ့ပါ: {str(e)}")
    finally:
        # ယာယီဖိုင် ဖျက်မယ်
        if os.path.exists(temp_file):
            os.remove(temp_file)

# ===================== Main Function =====================

def main():
    """Bot ကို စတင်မယ်"""
    # သင့် Bot Token ကို ဒီမှာ ထည့်ပါ
    # BotFather ကနေ token ရယူပါ (@BotFather on Telegram)
    BOT_TOKEN = "8569583023:AAFNKM3mkumVNrpj9uOZ-32fV3sP3nZ0TSo"
    
    # Application ဖန်တီးမယ်
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Command နှင့် Message Handlers များ
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_text_file))
    
    # Bot စတင်မယ်
    print("🤖 Bot စတင်နေပါတယ်...")
    app.run_polling()

if __name__ == "__main__":
    main()
