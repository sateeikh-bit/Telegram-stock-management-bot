import sqlite3
from aiogram import Bot, Dispatcher, executor, types
import os
from datetime import datetime

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

db = sqlite3.connect("stock.db", check_same_thread=False)
cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS products (
    id TEXT PRIMARY KEY,
    stock INTEGER
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS history (
    product TEXT,
    user TEXT,
    action TEXT,
    time TEXT
)
""")
db.commit()

def keyboard(pid):
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("➕ Add", callback_data=f"add:{pid}"),
        types.InlineKeyboardButton("➖ Sell", callback_data=f"sell:{pid}"),
        types.InlineKeyboardButton("📜 History", callback_data=f"hist:{pid}")
    )
    return kb

@dp.message_handler(commands=["addproduct"])
async def add_product(msg: types.Message):
    _, pid, qty = msg.text.split()
    cur.execute("INSERT OR REPLACE INTO products VALUES (?,?)", (pid, int(qty)))
    db.commit()
    await msg.reply(f"✅ {pid} added with stock {qty}")

@dp.message_handler(commands=["stock"])
async def show_stock(msg: types.Message):
    for pid, stock in cur.execute("SELECT * FROM products"):
        await msg.answer(
            f"📦 Product: {pid}\n📊 Available: {stock}",
            reply_markup=keyboard(pid)
        )

@dp.callback_query_handler(lambda c: ":" in c.data)
async def action(call: types.CallbackQuery):
    action, pid = call.data.split(":")
    cur.execute("SELECT stock FROM products WHERE id=?", (pid,))
    row = cur.fetchone()
    if not row:
        await call.answer("Product not found", show_alert=True)
        return

    stock = row[0]
    if action == "sell" and stock <= 0:
        await call.answer("Out of stock", show_alert=True)
        return

    stock += 1 if action == "add" else -1
    cur.execute("UPDATE products SET stock=? WHERE id=?", (stock, pid))
    cur.execute(
        "INSERT INTO history VALUES (?,?,?,?)",
        (pid, call.from_user.username or call.from_user.id, action, datetime.now().isoformat())
    )
    db.commit()

    await call.message.edit_text(
        f"📦 Product: {pid}\n📊 Available: {stock}",
        reply_markup=keyboard(pid)
    )
    await call.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("hist"))
async def history(call: types.CallbackQuery):
    pid = call.data.split(":")[1]
    rows = cur.execute(
        "SELECT user, action, time FROM history WHERE product=? ORDER BY time DESC LIMIT 5",
        (pid,)
    ).fetchall()
    text = "\n".join([f"{u} {a} @ {t[:16]}" for u, a, t in rows]) or "No history"
    await call.answer(text, show_alert=True)

executor.start_polling(dp)
