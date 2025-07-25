# PaymentBot Telegram

Bot Telegram untuk topup saldo via QRIS, cek saldo, dan fitur admin untuk manajemen user. Dibuat dengan Python dan menggunakan library QRIS dari [AutoFTbot/Qris-OrderKuota](https://github.com/AutoFTbot/Qris-OrderKuota).

## Fitur
- Topup saldo dengan QRIS (otomatis generate QR dan monitoring pembayaran)
- Cek saldo user
- Menu Telegram yang rapih dan mudah digunakan
- Fitur admin: list user bersaldo, tambah/kurangi saldo user
- Semua transaksi tercatat dengan nomor invoice

## Instalasi
1. Clone repo ini 
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Buat file `.env` (lihat contoh di bawah)
4. Jalankan bot:
   ```bash
   python bot.py
   ```

## Konfigurasi .env
```
TELEGRAM_BOT_TOKEN=isi_token_bot_telegram
ADMIN_USER_ID=isi_user_id_admin
QRIS_AUTH_USERNAME=isi_username_qris
QRIS_AUTH_TOKEN=isi_token_qris
QRIS_BASE_QR_STRING=isi_base_qr_string
QRIS_LOGO_PATH=./logo.png
```

## Credit
- QRIS library by [AutoFTbot/Qris-OrderKuota](https://github.com/AutoFTbot/Qris-OrderKuota)

## Struktur File
- `bot.py` : Main bot Telegram
- `user.json` : Data user dan saldo
- `.env` : Konfigurasi rahasia
- `requirements.txt` : Daftar dependencies

## License
MIT
