import asyncio
import feedparser
import json
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# =========================
# CONFIG
# =========================
API_TOKEN = "8435764061:AAFPjMNl_of5Oq_X5bLElMANZ549wqg58KI"
ADMIN_ID = 6803968373  # আপনার ID দিয়ে new user notification যাবে

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# =========================
# Feeds per Category
# =========================
RSS_FEEDS = {
    "general": [
        "https://www.prothomalo.com/feed/",
        "https://banglatribune.com/rss",
        "https://bangla.bdnews24.com/rss/",
        "https://www.jagonews24.com/rss/rss.xml",
    ],
    "sports": [
        "https://www.tbsnews.net/rss/sports",
        "https://www.dhakatribune.com/sports/feed"
    ],
    "tech": [
        "https://www.tbsnews.net/rss/tech",
        "https://www.dhakatribune.com/technology/feed"
    ],
    "entertainment": [
        "https://www.tbsnews.net/rss/entertainment",
        "https://www.dhakatribune.com/showtime/feed"
    ]
}

# =========================
# Posted Links & Subscribers Storage
# =========================
try:
    with open("posted.json", "r") as f:
        posted_links = set(json.load(f))
except:
    posted_links = set()

try:
    with open("users.json", "r") as f:
        subscribers = json.load(f)
except:
    subscribers = {}  # {user_id: ["general","sports"]}

# =========================
# Helper Functions
# =========================
def save_posted():
    with open("posted.json", "w") as f:
        json.dump(list(posted_links), f)

def save_subscribers():
    with open("users.json", "w") as f:
        json.dump(subscribers, f)

def get_image(entry):
    image_url = None
    if "media_content" in entry:
        image_url = entry.media_content[0].get('url')
    elif "links" in entry:
        for l in entry.links:
            if l.get("type", "").startswith("image"):
                image_url = l.get("href")
    return image_url

def build_buttons(link):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("📰 বিস্তারিত পড়ুন", url=link))
    return kb

async def notify_admin_new_user(user_id, username):
    try:
        msg = f"👤 নতুন ইউজার সাবস্ক্রাইব করেছে:\nID: {user_id}\nUsername: @{username}"
        await bot.send_message(ADMIN_ID, msg)
    except:
        pass

async def alert_admin_error(error_msg):
    try:
        await bot.send_message(ADMIN_ID, f"⚠️ Bot Error: {error_msg}")
    except:
        pass

# =========================
# Command Handlers
# =========================
@dp.message_handler(commands=["start"])
async def start_handler(message: types.Message):
    user_id = str(message.from_user.id)
    username = message.from_user.username or "NoUsername"

    if user_id not in subscribers:
        subscribers[user_id] = ["general"]  # default category
        save_subscribers()
        await notify_admin_new_user(user_id, username)

    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🗞️ General", callback_data="cat_general"),
        InlineKeyboardButton("🏆 Sports", callback_data="cat_sports"),
        InlineKeyboardButton("💻 Tech", callback_data="cat_tech"),
        InlineKeyboardButton("🎬 Entertainment", callback_data="cat_entertainment")
    )

    await message.reply(
        "স্বাগতম! আপনি কোন ক্যাটাগরির নিউজ পেতে চান? নিচের বাটন থেকে সিলেক্ট করুন:",
        reply_markup=kb
    )

@dp.callback_query_handler(lambda c: c.data.startswith("cat_"))
async def category_select(c: types.CallbackQuery):
    user_id = str(c.from_user.id)
    category = c.data.split("_")[1]
    if user_id not in subscribers:
        subscribers[user_id] = []
    if category not in subscribers[user_id]:
        subscribers[user_id].append(category)
    save_subscribers()
    await c.answer(f"✅ আপনি {category.capitalize()} নিউজ সাবস্ক্রাইব করেছেন।")

@dp.message_handler(commands=["subscribe"])
async def subscribe_handler(message: types.Message):
    user_id = str(message.from_user.id)
    cats = message.get_args().lower().replace(" ", "").split(",")
    if user_id not in subscribers:
        subscribers[user_id] = []
    for c in cats:
        if c not in subscribers[user_id]:
            subscribers[user_id].append(c)
    save_subscribers()
    await message.reply(f"✅ সাবস্ক্রাইবড: {', '.join(subscribers[user_id])}")

@dp.message_handler(commands=["unsubscribe"])
async def unsubscribe_handler(message: types.Message):
    user_id = str(message.from_user.id)
    cats = message.get_args().lower().replace(" ", "").split(",")
    if user_id not in subscribers:
        subscribers[user_id] = []
    for c in cats:
        if c in subscribers[user_id]:
            subscribers[user_id].remove(c)
    save_subscribers()
    await message.reply(f"❌ আনসাবস্ক্রাইবড: {', '.join(subscribers[user_id])}")

# =========================
# Fetch & Post News
# =========================
async def fetch_and_post_news():
    while True:
        for category, feeds in RSS_FEEDS.items():
            for feed_url in feeds:
                try:
                    feed = feedparser.parse(feed_url)
                    for entry in feed.entries[:5]:
                        if entry.link not in posted_links:
                            posted_links.add(entry.link)
                            save_posted()

                            caption = (
                                f"🗞️ <b>{entry.title}</b>\n\n"
                                f"{entry.summary[:250]}...\n\n"
                                f"📌 <i>Source: {feed.feed.title}</i>"
                            )

                            image_url = get_image(entry)
                            kb = build_buttons(entry.link)

                            # Send to all users subscribed to this category
                            for user_id, cats in subscribers.items():
                                if category in cats:
                                    try:
                                        if image_url:
                                            await bot.send_photo(
                                                chat_id=int(user_id),
                                                photo=image_url,
                                                caption=caption,
                                                parse_mode="HTML",
                                                reply_markup=kb
                                            )
                                        else:
                                            await bot.send_message(
                                                chat_id=int(user_id),
                                                text=caption,
                                                parse_mode="HTML",
                                                reply_markup=kb
                                            )
                                    except Exception as e:
                                        await alert_admin_error(f"Error sending to {user_id}: {e}")

                except Exception as e:
                    await alert_admin_error(f"Error fetching {feed_url}: {e}")

        await asyncio.sleep(1800)  # 30 মিনিট পর পুনরায় চেক

# =========================
# Main
# =========================
async def main():
    asyncio.create_task(fetch_and_post_news())
    await dp.start_polling()

if __name__ == "__main__":
    asyncio.run(main())