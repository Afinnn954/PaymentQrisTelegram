import os
import json
import time
import random
from telegram import Update, InputFile, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from dotenv import load_dotenv
from qris_payment import QRISPayment

# Load environment variables
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
ADMIN_USER_ID = os.getenv('ADMIN_USER_ID')
QRIS_CONFIG = {
    'auth_username': os.getenv('QRIS_AUTH_USERNAME'),
    'auth_token': os.getenv('QRIS_AUTH_TOKEN'),
    'base_qr_string': os.getenv('QRIS_BASE_QR_STRING'),
    'logo_path': os.getenv('QRIS_LOGO_PATH')
}
USER_JSON_PATH = 'user.json'

# Helper functions

def load_users():
    if not os.path.exists(USER_JSON_PATH):
        return {}
    with open(USER_JSON_PATH, 'r') as f:
        data = json.load(f)
    return data.get('users', {})

def save_users(users):
    with open(USER_JSON_PATH, 'w') as f:
        json.dump({'users': users}, f, indent=2)

def get_user(user_id):
    users = load_users()
    return users.get(str(user_id), {'saldo': 0})

def update_user(user_id, saldo, invoice=None, amount=None, status=None):
    users = load_users()
    user_data = users.get(str(user_id), {'saldo': 0, 'invoices': []})
    user_data['saldo'] = saldo
    if invoice and amount:
        invoice_data = {
            'invoice': invoice,
            'amount': amount,
            'status': status or 'PENDING'
        }
        # Hindari duplikat invoice
        if 'invoices' not in user_data:
            user_data['invoices'] = []
        user_data['invoices'].append(invoice_data)
    users[str(user_id)] = user_data
    save_users(users)

MENU_KEYBOARD = ReplyKeyboardMarkup([
    ["Top Up"],
    ["Cek Saldo"],
    ["Bantuan"]
], resize_keyboard=True)

ADMIN_MENU_KEYBOARD = ReplyKeyboardMarkup([
    ["List User"],
    ["Tambah Saldo"],
    ["Kurangi Saldo"],
    ["Bantuan"]
], resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    is_admin = str(user_id) == str(ADMIN_USER_ID)
    keyboard = ADMIN_MENU_KEYBOARD if is_admin else MENU_KEYBOARD
    await update.message.reply_text(
        f"👋 Hai, selamat datang di PaymentBot!\nSaldo kamu sekarang: Rp {user['saldo']} 💸\n\nPilih menu di bawah atau ketik /help buat info lengkap.",
        reply_markup=keyboard
    )

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_admin = str(user_id) == str(ADMIN_USER_ID)
    msg = """
🤖 *Menu User:*
Top Up — Untuk topup saldo (atau ketik /topup <nominal>)
Cek Saldo — Untuk cek saldo kamu (atau ketik /saldo)
Bantuan — Info menu dan cara pakai (atau ketik /help)
"""
    if is_admin:
        msg += """

*Menu Admin:*
List User — Liat user yang punya saldo (atau ketik /listuser)
Tambah Saldo — Tambah saldo user (atau ketik /addsaldo <user_id> <nominal>)
Kurangi Saldo — Kurangi saldo user (atau ketik /minsaldo <user_id> <nominal>)
Bantuan — Info menu admin (atau ketik /help)
"""
    msg += """

Semua transaksi ada invoice, bisa dipake buat konfirmasi ke admin kalau ada error. Jangan lupa scan QR sesuai nominal ya! 😉
"""
    await update.message.reply_text(msg, parse_mode="Markdown")

async def topup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args
    if not args or not args[0].isdigit():
        await update.message.reply_text("❌ Format salah, bro! Ketik: /topup <nominal>\nContoh: /topup 10000")
        return
    amount = int(args[0])
    invoice = f"INV{user_id}{int(time.time())}{random.randint(100,999)}"
    qris = QRISPayment(QRIS_CONFIG)
    result = qris.generate_qr(amount, invoice=invoice) if 'invoice' in qris.generate_qr.__code__.co_varnames else qris.generate_qr(amount)
    qr_path = f"qr_{user_id}_{amount}.png"
    result['qr_image'].save(qr_path)
    detail_msg = (
        f"🧾 *Nomor Invoice:* `{invoice}`\n"
        f"💰 *Nominal:* Rp {amount}\n"
        f"⏳ *Status:* PENDING\n"
        f"Scan QR di bawah buat topup, jangan sampe salah nominal ya!\n"
        f"Invoice ini bisa dipake buat konfirmasi ke admin kalo ada masalah."
    )
    await update.message.reply_photo(InputFile(qr_path), caption=detail_msg, parse_mode="Markdown")
    os.remove(qr_path)
    update_user(user_id, get_user(user_id)['saldo'], invoice=invoice, amount=amount, status='PENDING')
    start_time = time.time()
    while time.time() - start_time < 300:
        payment_result = qris.check_payment(invoice, amount)
        if payment_result['success']:
            status = payment_result['data']['status']
            detail = payment_result['data']
            saldo = get_user(user_id)['saldo']
            if status == 'PAID':
                saldo += amount
            update_user(user_id, saldo, invoice=invoice, amount=amount, status=status)
            await update.message.reply_text(
                f"🧾 Invoice: `{invoice}`\n💰 Nominal: Rp {amount}\n📊 Status: {status}\n📋 Detail: {detail}",
                parse_mode="Markdown"
            )
            if status == 'PAID':
                await update.message.reply_text(f"🎉 Mantap! Topup berhasil, saldo kamu sekarang: Rp {saldo} 💸")
                return
        await update.message.reply_text(f"⏳ Lagi nunggu pembayaran...\nInvoice: `{invoice}`", parse_mode="Markdown")
        time.sleep(3)
    await update.message.reply_text(f"⌛ Timeout bro, pembayaran ga diterima.\nInvoice: `{invoice}`", parse_mode="Markdown")

async def saldo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    await update.message.reply_text(f"💸 Saldo kamu: Rp {user['saldo']}")

# ================= ADMIN COMMANDS =================
async def listuser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if str(user_id) != str(ADMIN_USER_ID):
        await update.message.reply_text("❌ Cuma admin yang bisa pake menu ini!")
        return
    users = load_users()
    msg = "📋 Daftar user yang punya saldo > 0:\n"
    found = False
    for uid, data in users.items():
        if data.get('saldo', 0) > 0:
            found = True
            msg += f"👤 User ID: {uid} | 💸 Saldo: Rp {data['saldo']}\n"
    if not found:
        msg += "Belum ada user yang punya saldo, bro."
    await update.message.reply_text(msg)

async def addsaldo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if str(user_id) != str(ADMIN_USER_ID):
        await update.message.reply_text("❌ Cuma admin yang bisa pake menu ini!")
        return
    args = context.args
    if len(args) != 2 or not args[0].isdigit() or not args[1].isdigit():
        await update.message.reply_text("Format: /addsaldo <user_id> <nominal>")
        return
    target_id = args[0]
    nominal = int(args[1])
    user = get_user(target_id)
    saldo = user.get('saldo', 0) + nominal
    update_user(target_id, saldo)
    await update.message.reply_text(f"✅ Saldo user {target_id} udah ditambah Rp {nominal}. Saldo sekarang: Rp {saldo}")

async def minsaldo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if str(user_id) != str(ADMIN_USER_ID):
        await update.message.reply_text("❌ Cuma admin yang bisa pake menu ini!")
        return
    args = context.args
    if len(args) != 2 or not args[0].isdigit() or not args[1].isdigit():
        await update.message.reply_text("Format: /minsaldo <user_id> <nominal>")
        return
    target_id = args[0]
    nominal = int(args[1])
    user = get_user(target_id)
    saldo = max(user.get('saldo', 0) - nominal, 0)
    update_user(target_id, saldo)
    await update.message.reply_text(f"✅ Saldo user {target_id} udah dikurangin Rp {nominal}. Saldo sekarang: Rp {saldo}")

async def handle_keyboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    is_admin = str(user_id) == str(ADMIN_USER_ID)
    if text == "Top Up":
        await update.message.reply_text("Ketik /topup <nominal> untuk topup saldo. Contoh: /topup 10000")
    elif text == "Cek Saldo":
        await saldo(update, context)
    elif text == "Bantuan":
        await help(update, context)
    elif is_admin and text == "List User":
        await listuser(update, context)
    elif is_admin and text == "Tambah Saldo":
        await update.message.reply_text("Ketik /addsaldo <user_id> <nominal> untuk tambah saldo user.")
    elif is_admin and text == "Kurangi Saldo":
        await update.message.reply_text("Ketik /minsaldo <user_id> <nominal> untuk kurangi saldo user.")

# Main

def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("topup", topup))
    app.add_handler(CommandHandler("saldo", saldo))
    app.add_handler(CommandHandler("help", help))
    app.add_handler(CommandHandler("listuser", listuser))
    app.add_handler(CommandHandler("addsaldo", addsaldo))
    app.add_handler(CommandHandler("minsaldo", minsaldo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_keyboard))
    print("Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()
