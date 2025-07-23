from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

from market_data import fetch_spot_price
from risk_engine import calculate_delta, calculate_var
from hedge_logger import log_hedge
from datetime import datetime
import json
from threshold_utils import set_user_threshold, get_user_threshold
import asyncio
from asyncio import create_task, sleep
from analytics import generate_delta_chart
from portfolio import get_portfolio_status
from database import init_db
from database import DB  # Ensure this is imported at the top if DB is in separate module
import sqlite3
from telegram.request import HTTPXRequest



# Track running monitor tasks per user
monitor_tasks = {}
#user_auto_hedge_jobs = {}

TOKEN = "---"

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 Welcome! I'm your Spot Hedging Bot.")


# /monitor command with buttons
async def monitor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        threshold = get_user_threshold(user_id)
        asset = context.args[0] if len(context.args) > 0 else "ETH/USDT"
        position_size = float(context.args[1]) if len(context.args) > 1 else 1.2
        exchange = "bybit"
        price_history = [3000, 3020, 3010, 3035, 3040, 3032]

        price = fetch_spot_price(asset, exchange)
        if price is None:
            raise ValueError(f"Could not fetch price for {asset} from {exchange}")

        delta = calculate_delta(position_size)
        var = calculate_var(price_history)

        msg = (
            f"📱 Live Monitoring: {asset}\n"
            f"------------------------------\n"
            f"💰 Current Price: ${price}\n"
            f"📈 Position Size: {position_size} {asset.split('/')[0]}\n"
            f"📉 Delta Exposure: {delta:.2f} {asset.split('/')[0]}\n"
            f"⚠️ Value at Risk (95%): {round(var * 100, 2)}%\n"
            f"{'🚨 Delta exceeds threshold (' + str(threshold) + ')!' if abs(delta) > threshold else '✅ Delta within safe range (' + str(threshold) + ').'}"
        )

        buttons = [
            [InlineKeyboardButton("✅ Hedge Now", callback_data="hedge_now")],
            [InlineKeyboardButton("⚙️ Adjust Threshold", callback_data="adjust_threshold")],
            [InlineKeyboardButton("📊 View Analytics", callback_data="view_analytics")]
        ]
        reply_markup = InlineKeyboardMarkup(buttons)

        await update.message.reply_text(msg, reply_markup=reply_markup)

    except Exception as e:
        await update.message.reply_text(
            f"⚠️ Error: {str(e)}\n\n"
            "Usage: /monitor <asset> <position_size>\n"
            "Example: /monitor ETH/USDT 2.5"
        )

async def add_position(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        asset = context.args[0]
        size = float(context.args[1])
        price = fetch_spot_price(asset, "bybit") or 0  # Fallback to 0 if API fails

        conn = sqlite3.connect(DB)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO positions (user_id, asset, size, price)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, asset) DO UPDATE SET size = size + excluded.size
        """, (user_id, asset, size, price))
        conn.commit()
        conn.close()

        await update.message.reply_text(f"✅ Added {size} units of {asset} to your portfolio.")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Usage: /add_position <asset> <size>\nError: {str(e)}")

# Button click handler
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "hedge_now":
        asset = "ETH/USDT"
        size = 1.2
        price = fetch_spot_price(asset, "bybit")
        user_id = update.effective_user.id
        log_hedge(asset, size, price, reason="manual_hedge", user_id=user_id)

        await query.edit_message_text(f"✅ Hedge executed for {size} {asset.split('/')[0]} at ${price}")

    elif query.data == "adjust_threshold":
        await query.edit_message_text("⚙️ You can change threshold anytime using:\n/set_threshold <value>\nExample: /set_threshold 1.2")
    elif query.data == "view_analytics":
        await query.edit_message_text("📊 Analytics coming soon! Use /hedge_history to see recent hedges.")


async def hedge_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT asset, size, price, reason, time
        FROM hedges
        WHERE user_id = ?
        ORDER BY time DESC
        LIMIT 5
    """, (user_id,))
    logs = cursor.fetchall()
    conn.close()

    if not logs:
        await update.message.reply_text("📟 No hedge history found.")
        return

    msg = "📘 Recent Hedge History:\n------------------------------\n"
    for asset, size, price, reason, time_str in logs:
        formatted_time = datetime.fromisoformat(time_str).strftime("%Y-%m-%d %H:%M")
        msg += (
            f"🗕 {formatted_time}\n"
            f"🪙 Asset: {asset}\n"
            f"📈 Size: {size}\n"
            f"💵 Price: ${price}\n"
            f"📜 Reason: {reason}\n"
            f"------------------------------\n"
        )

    await update.message.reply_text(msg)
   


async def set_threshold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        new_threshold = float(context.args[0])
        set_user_threshold(user_id, new_threshold)
        await update.message.reply_text(f"✅ Threshold set to {new_threshold}")
    except (IndexError, ValueError):
        await update.message.reply_text("⚠️ Usage: /set_threshold <value>\nExample: /set_threshold 1.5")



                    
                    
async def auto_hedge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args

    if len(args) < 2:
        await update.message.reply_text("⚠️ Usage: /auto_hedge <asset> <position_size>")
        return

    asset = args[0]
    try:
        position_size = float(args[1])
    except ValueError:
        await update.message.reply_text("⚠️ Position size must be a number.")
        return

    if user_id in monitor_tasks:
        await update.message.reply_text("🔁 Auto hedge already running. Use /stop_hedge to cancel.")
        return

    async def monitor_loop():
        while True:
            try:
                price = fetch_spot_price(asset, "bybit")
                delta = calculate_delta(position_size)
                var = calculate_var([price - 30, price, price + 20, price - 10, price + 5])
                threshold = get_user_threshold(user_id)

                if abs(delta) > threshold:
                    log_hedge(asset, position_size, price, reason="auto_hedge", user_id=user_id)
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=f"🤖 Auto-Hedge Triggered!\nAsset: {asset}\nPrice: ${price}\nDelta: {delta:.2f}\nVaR: {round(var * 100, 2)}%\nThreshold: {threshold}"
                    )
                else:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=f"✅ Auto-check OK: Delta ({delta:.2f}) within threshold ({threshold})"
                    )

                await asyncio.sleep(30)

            except Exception as e:
                await context.bot.send_message(chat_id=user_id, text=f"⚠️ Error in auto-hedge: {str(e)}")
                break

    task = asyncio.create_task(monitor_loop())
    monitor_tasks[user_id] = task
    await update.message.reply_text(f"✅ Auto hedge started for {asset} with position {position_size}")





async def stop_hedge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    task = monitor_tasks.pop(user_id, None)
    if task:
        task.cancel()
        conn = sqlite3.connect(DB)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM auto_hedge_jobs WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()

        await update.message.reply_text("🛑 Auto hedge stopped.")
    else:
        await update.message.reply_text("⚠️ No auto-hedge running.")



async def risk_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    path = generate_delta_chart()
    if path:
        await update.message.reply_photo(photo=open(path, "rb"), caption="📊 Recent Hedge Sizes")
    else:
        await update.message.reply_text("⚠️ Not enough data to generate chart.")


async def portfolio_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    summary, total_delta, total_var = get_portfolio_status(user_id)

    if not summary:
        await update.message.reply_text("⚠️ No portfolio data available.")
        return

    msg = "📊 Portfolio Risk Summary:\n------------------------------\n"
    for entry in summary:
        msg += (
            f"🪙 {entry['asset']}\n"
            f"💰 Price: ${entry['price']}\n"
            f"📦 Position: {entry['size']} units\n"
            f"📉 Delta: {entry['delta']:.2f}\n"
            f"⚠️ VaR: {round(entry['var'] * 100, 2)}%\n"
            f"------------------------------\n"
        )

    msg += f"✅ Total Delta: {round(total_delta, 2)}\n"
    msg += f"⚠️ Total Portfolio VaR: {round(total_var * 100, 2)}%"
    await update.message.reply_text(msg)







async def reset_portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM positions WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    await update.message.reply_text("🧹 Your portfolio has been reset.")


async def restore_auto_hedge_jobs(app):
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, asset, size FROM auto_hedge_jobs")
    jobs = cursor.fetchall()
    conn.close()

    for user_id, asset, size in jobs:
        async def monitor_loop(user_id=user_id, asset=asset, size=size):
            while True:
                try:
                    price = fetch_spot_price(asset, "bybit")
                    delta = calculate_delta(size)
                    var = calculate_var([price - 30, price, price + 20, price - 10, price + 5])
                    threshold = get_user_threshold(user_id)

                    if abs(delta) > threshold:
                        log_hedge(asset, size, price, reason="auto_hedge", user_id=user_id)
                        await app.bot.send_message(
                            chat_id=user_id,
                            text=(
                                f"🤖 Auto-Hedge Triggered!\n"
                                f"Asset: {asset}\n"
                                f"Price: ${price}\n"
                                f"Delta: {delta:.2f}\n"
                                f"VaR: {round(var * 100, 2)}%\n"
                                f"Threshold: {threshold}"
                            )
                        )
                    else:
                        await app.bot.send_message(
                            chat_id=user_id,
                            text=f"✅ Auto-check OK: Delta ({delta:.2f}) within threshold ({threshold})"
                        )

                    await asyncio.sleep(30)

                except Exception as e:
                    await app.bot.send_message(chat_id=user_id, text=f"⚠️ Error in auto-hedge: {str(e)}")
                    break

        task = asyncio.create_task(monitor_loop())
        monitor_tasks[user_id] = task
        
async def active_hedges(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute("SELECT asset, size FROM auto_hedge_jobs WHERE user_id = ?", (update.effective_user.id,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("🛑 No active auto-hedge jobs.")
        return

    msg = "📡 Active Auto-Hedge Jobs:\n------------------------------\n"
    for asset, size in rows:
        msg += f"🪙 Asset: {asset}\n📦 Size: {size}\n------------------------------\n"

    await update.message.reply_text(msg)


# App setup
#app = ApplicationBuilder().token(TOKEN).build()


request = HTTPXRequest(
    connect_timeout=20,
    read_timeout=60,
    write_timeout=20,
    pool_timeout=20
)

app = ApplicationBuilder().token(TOKEN).request(request).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("monitor", monitor))
app.add_handler(CallbackQueryHandler(button_handler))
app.add_handler(CommandHandler("hedge_history", hedge_history))
app.add_handler(CommandHandler("set_threshold", set_threshold))
app.add_handler(CommandHandler("auto_hedge", auto_hedge))
app.add_handler(CommandHandler("stop_hedge", stop_hedge))
app.add_handler(CommandHandler("risk_summary", risk_summary))
app.add_handler(CommandHandler("portfolio_status", portfolio_status))
app.add_handler(CommandHandler("add_position", add_position)) # type: ignore
app.add_handler(CommandHandler("reset_portfolio", reset_portfolio))
app.add_handler(CommandHandler("active_hedges", active_hedges))



import nest_asyncio
import asyncio

if __name__ == "__main__":
    init_db()
    print("🤖 Bot is running...")

    nest_asyncio.apply()

    async def main():
        await restore_auto_hedge_jobs(app)
        await app.run_polling()  # This handles initialize, start, idle, shutdown

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())





