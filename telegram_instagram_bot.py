import os
import random
from collections import defaultdict
import telebot
import instaloader
from flask import Flask
from threading import Thread
from dotenv import load_dotenv
import sqlite3

load_dotenv()  # Load environment variables from .env file

# Flask app to keep the bot alive
app = Flask('')

@app.route('/')
def home():
    return "I'm alive"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# Start the Flask app in a thread
keep_alive()

# Initialize the Telegram bot
API_TOKEN = os.getenv("API_TOKEN")
bot = telebot.TeleBot(API_TOKEN)

# Database setup
conn = sqlite3.connect('users.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)''')
conn.commit()

# List of keywords for different report categories
report_keywords = {
    "HATE": ["devil", "666", "savage", "love", "hate", "followers", "selling", "sold", "seller", "dick", "ban", "banned", "free", "method", "paid"],
    "SELF": ["suicide", "blood", "death", "dead", "kill myself"],
    "BULLY": ["@"],
    "VIOLENT": ["hitler", "osama bin laden", "guns", "soldiers", "masks", "flags"],
    "ILLEGAL": ["drugs", "cocaine", "plants", "trees", "medicines"],
    "PRETENDING": ["verified", "tick"],
    "NUDITY": ["nude", "sex", "send nudes"],
    "SPAM": ["phone number"]
}

FORCE_JOIN_CHANNEL = os.getenv("FORCE_JOIN_CHANNEL")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

def check_keywords(text, keywords):
    return any(keyword in text.lower() for keyword in keywords)

def analyze_profile(profile_info):
    reports = defaultdict(int)
    profile_texts = [
        profile_info.get("username", ""),
        profile_info.get("biography", ""),
    ]

    for text in profile_texts:
        for category, keywords in report_keywords.items():
            if check_keywords(text, keywords):
                reports[category] += 1

    if reports:
        unique_counts = random.sample(range(1, 6), min(len(reports), 4))
        formatted_reports = {
            category: f"{count}x - {category}" for category, count in zip(reports.keys(), unique_counts)
        }
    else:
        all_categories = list(report_keywords.keys())
        num_categories = random.randint(2, 5)
        selected_categories = random.sample(all_categories, num_categories)
        unique_counts = random.sample(range(1, 6), num_categories)
        formatted_reports = {
            category: f"{count}x - {category}" for category, count in zip(selected_categories, unique_counts)
        }

    return formatted_reports

def get_public_instagram_info(username):
    L = instaloader.Instaloader()
    try:
        profile = instaloader.Profile.from_username(L.context, username)
        info = {
            "username": profile.username,
            "full_name": profile.full_name,
            "biography": profile.biography,
            "follower_count": profile.followers,
            "following_count": profile.followees,
            "is_private": profile.is_private,
            "post_count": profile.mediacount,
            "external_url": profile.external_url,
        }
        return info
    except instaloader.exceptions.ProfileNotExistsException:
        return None
    except instaloader.exceptions.InstaloaderException as e:
        print(f"An error occurred: {e}")
        return None

def force_join(message):
    user_id = message.from_user.id
    try:
        member = bot.get_chat_member(FORCE_JOIN_CHANNEL, user_id)
        if member.status not in ['member', 'administrator', 'creator']:
            bot.send_message(message.chat.id, f"Please join [this channel](https://t.me/{FORCE_JOIN_CHANNEL}) to use the bot.", parse_mode="Markdown")
            return False
        return True
    except Exception as e:
        bot.send_message(message.chat.id, f"Error: {str(e)}")
        return False

def register_user(user_id):
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()

@bot.message_handler(commands=['start'])
def start(message):
    if not force_join(message):
        return
    user_id = message.from_user.id
    register_user(user_id)
    bot.reply_to(message, "Welcome! Use /getmeth <username> to analyze an Instagram profile.")

@bot.message_handler(commands=['getmeth'])
def analyze(message):
    if not force_join(message):
        return
    username = message.text.split()[1:]  # Get username from command
    if not username:
        bot.reply_to(message, "Please provide an Instagram username.")
        return

    username = ' '.join(username)
    bot.reply_to(message, f"🔍 Analyzing profile: {username}. Please wait...")

    profile_info = get_public_instagram_info(username)
    if profile_info:
        reports_to_file = analyze_profile(profile_info)

        result_text = f"**Public Information for {username}:\n"
        result_text += f"Username: {profile_info.get('username', 'N/A')}\n"
        result_text += f"Full Name: {profile_info.get('full_name', 'N/A')}\n"
        result_text += f"Biography: {profile_info.get('biography', 'N/A')}\n"
        result_text += f"Followers: {profile_info.get('follower_count', 'N/A')}\n"
        result_text += f"Following: {profile_info.get('following_count', 'N/A')}\n"
        result_text += f"Private Account: {'Yes' if profile_info.get('is_private') else 'No'}\n"
        result_text += f"Posts: {profile_info.get('post_count', 'N/A')}\n"
        result_text += f"External URL: {profile_info.get('external_url', 'N/A')}\n\n"

        result_text += "Suggested Reports to File:\n"
        for report in reports_to_file.values():
            result_text += f"• {report}\n"

        result_text += "\n*Note: This Method is based on available data and may not be fully accurate.*\n"

        # Include inline buttons
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("Visit Profile", url=f"https://instagram.com/{profile_info['username']}"))
        markup.add(telebot.types.InlineKeyboardButton("Developer", callback_data='t.me/ifeelscam'))

        bot.send_message(message.chat.id, result_text, reply_markup=markup, parse_mode='Markdown')
    else:
        bot.reply_to(message, f"❌ Profile {username} not found or an error occurred.")

@bot.message_handler(commands=['totalusers'])
def total_users(message):
    if message.from_user.id == ADMIN_ID:
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        bot.reply_to(message, f"Total users: {count}")
    else:
        bot.reply_to(message, "You are not authorized to use this command.")

@bot.message_handler(commands=['broadcast'])
def broadcast(message):
    if message.from_user.id == ADMIN_ID:
        text = ' '.join(message.text.split()[1:])
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()
        for user in users:
            try:
                bot.send_message(user[0], text)
            except Exception as e:
                print(f"Error sending message to {user[0]}: {str(e)}")
        bot.reply_to(message, "Broadcast sent.")
    else:
        bot.reply_to(message, "You are not authorized to use this command.")

if __name__ == "__main__":
    print("Starting the bot...")
    bot.polling()
        
