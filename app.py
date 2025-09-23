from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import datetime, date
import webbrowser
import smtplib
from email.message import EmailMessage
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import urllib.parse   # ✅ added for encoding WhatsApp text

app = Flask(__name__)
DB = 'bookings.db'

# --- Translations (EN/TR/AR) ---
translations = {
    'en': {'name':'Name','email':'Email','room':'Room','guests':'Guests','checkin':'Check-in','checkout':'Check-out',
           'source':'Source','price_night':'Price per night','amount':'Amount total','currency':'Currency',
           'method':'Payment Method','notes':'Notes','submit':'Book & Send Email','history':'History',
           'rooms':'Room Status','bosses':'Send Receipt','yunus':'Yunus Abi','memet':'Memet Abi','search':'Search',
           'pending_box':'Pending Payments','mark_paid':'Mark Paid'},
    'tr': {'name':'İsim','email':'E-posta','room':'Oda','guests':'Kişi','checkin':'Giriş','checkout':'Çıkış',
           'source':'Kaynak','price_night':'Gecelik Fiyat','amount':'Toplam','currency':'Para Birimi',
           'method':'Ödeme Yöntemi','notes':'Notlar','submit':'Rezerv Et & Gönder','history':'Geçmiş',
           'rooms':'Oda Durumu','bosses':'Fatura Gönder','yunus':'Yunus Abi','memet':'Memet Abi','search':'Ara',
           'pending_box':'Bekleyen Ödemeler','mark_paid':'Ödendi olarak işaretle'},
    'ar': {'name':'الاسم','email':'البريد','room':'الغرفة','guests':'الاشخاص','checkin':'تاريخ الدخول','checkout':'تاريخ الخروج',
           'source':'المصدر','price_night':'سعر الليلة','amount':'المجموع','currency':'العملة',
           'method':'طريقة الدفع','notes':'ملاحظات','submit':'احجز & أرسل','history':'السجل',
           'rooms':'حالة الغرف','bosses':'إرسال الفاتورة','yunus':'يونس آبي','memet':'ميمت آبي','search':'بحث',
           'pending_box':'الدفعات المعلقة','mark_paid':'تم الدفع'}
}

# --- Room list (room number, bed type s/d/t) ---
rooms = [
    ('100','d'),('101','d'),('102','t'),('103','d'),('104','d'),('105','s'),('106','s'),
    ('201','d'),('202','t'),('203','d'),('204','d'),('205','s'),('206','s'),
    ('301','d'),('302','t'),('303','d'),('304','d'),('305','s'),('306','s'),
    ('401','d'),('402','t'),('403','t'),('404','d'),('405','s'),('406','s')
]

# --- DB helpers ---
def get_db():
    conn = sqlite3.connect(DB, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    db = get_db()
    db.execute('''
        CREATE TABLE IF NOT EXISTS bookings(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            room TEXT,
            guests INTEGER,
            checkin TEXT,
            checkout TEXT,
            source TEXT,
            price_per_night REAL,
            amount_total REAL,
            currency TEXT,
            method TEXT,
            notes TEXT,
            pending INTEGER DEFAULT 0,
            time TEXT
        )
    ''')
    db.commit()

init_db()

# --- Utilities ---
def nights_between(start_str, end_str):
    s = date.fromisoformat(start_str)
    e = date.fromisoformat(end_str)
    delta = (e - s).days
    return max(delta, 0)

# --- Routes ---
@app.route("/", methods=['GET','POST'])
@app.route("/booking", methods=['GET','POST'])
def booking():
    lang = request.args.get('lang','en')
    t = translations.get(lang, translations['en'])
    db = get_db()

    today = datetime.now().strftime("%Y-%m-%d")
    room_status = {r:{'bed':b,'sold':False,'from':'-','until':'-','source':None,'booking_id':None} for r,b in rooms}

    rows = db.execute("SELECT * FROM bookings ORDER BY id DESC").fetchall()
    for row in rows:
        if row['checkin'] <= today < row['checkout']:
            room_status[row['room']].update({
                'sold':True,
                'from':row['checkin'],
                'until':row['checkout'],
                'source':row['source'],
                'booking_id':row['id']
            })

    pending_rows = db.execute("SELECT * FROM bookings WHERE pending=1 ORDER BY id DESC").fetchall()
    total_pending = sum(r['amount_total'] or 0 for r in pending_rows)

    if request.method == 'POST':
        name = request.form.get('name','').strip()
        email = request.form.get('email','').strip()
        room = request.form.get('room','').strip()
        guests = int(request.form.get('guests','1') or 1)
        checkin = request.form.get('checkin')
        checkout = request.form.get('checkout')
        source = request.form.get('source','')
        try:
            price_per_night = float(request.form.get('price_per_night','0') or 0)
        except:
            price_per_night = 0.0
        nights = nights_between(checkin, checkout) if (checkin and checkout) else 0
        amount_total = price_per_night * nights
        currency = request.form.get('currency','TRY')
        method = request.form.get('method','Pending')
        notes = request.form.get('notes','')
        pending = 1 if method.lower() == 'pending' else 0
        time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        db.execute('''
            INSERT INTO bookings(name,email,room,guests,checkin,checkout,source,price_per_night,amount_total,
                                 currency,method,notes,pending,time)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', (name,email,room,guests,checkin,checkout,source,price_per_night,amount_total,
              currency,method,notes,pending,time_str))
        db.commit()

        # --- Send email to customer ---
        try:
            msg = EmailMessage()
            msg['Subject'] = 'AX HOTEL PAYMENTS - Booking Confirmation'
            msg['From'] = 'izedinnursefa235@gmail.com'  # replace
            msg['To'] = email
            body = (f"AX HOTEL PAYMENTS\nName: {name}\nRoom: {room}\nGuests: {guests}\n"
                    f"Check-in: {checkin}\nCheck-out: {checkout}\nNights: {nights}\n"
                    f"Price/night: {price_per_night}\nTotal: {amount_total} {currency}\nMethod: {method}\nNotes: {notes}")
            msg.set_content(body)
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                smtp.login('izedinnursefa235@gmail.com','dpymomuezawalenr')  # replace
                smtp.send_message(msg)
        except Exception as e:
            print("Customer email send failed:", e)

        # --- Send professional HTML receipt to bosses ---
        try:
            boss_emails = {
                'yunus': 'yunus@example.com',  # replace
                'memet': 'memet@example.com'
            }

            html_body = f"""
            <html>
            <body style="font-family:Arial, sans-serif; background:#f2f2f2; padding:20px;">
                <div style="max-width:600px; margin:auto; background:white; padding:20px; border-radius:8px;">
                    <h2 style="color:#0b63b3;">AX HOTEL PAYMENTS - Booking Receipt</h2>
                    <table style="width:100%; border-collapse: collapse;">
                        <tr><td><strong>Name:</strong></td><td>{name}</td></tr>
                        <tr><td><strong>Room:</strong></td><td>{room}</td></tr>
                        <tr><td><strong>Guests:</strong></td><td>{guests}</td></tr>
                        <tr><td><strong>Check-in:</strong></td><td>{checkin}</td></tr>
                        <tr><td><strong>Check-out:</strong></td><td>{checkout}</td></tr>
                        <tr><td><strong>Nights:</strong></td><td>{nights}</td></tr>
                        <tr><td><strong>Price per night:</strong></td><td>{price_per_night}</td></tr>
                        <tr><td><strong>Total:</strong></td><td>{amount_total} {currency}</td></tr>
                        <tr><td><strong>Payment Method:</strong></td><td>{method}</td></tr>
                        <tr><td><strong>Notes:</strong></td><td>{notes}</td></tr>
                    </table>
                    <p style="margin-top:20px;">This is an automated receipt from AX Hotel.</p>
                </div>
            </body>
            </html>
            """

            for boss_email in boss_emails.values():
                msg_boss = MIMEMultipart('alternative')
                msg_boss['Subject'] = f"AX HOTEL PAYMENT RECEIPT - {name}"
                msg_boss['From'] = 'youremail@example.com'  # replace
                msg_boss['To'] = boss_email
                msg_boss.attach(MIMEText(html_body, 'html'))

                with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                    smtp.login('youremail@example.com','your_app_password')  # replace
                    smtp.send_message(msg_boss)

            print("Professional email sent to bosses successfully!")

        except Exception as e:
            print("Boss email send failed:", e)

        return redirect(url_for('booking', lang=lang))

    return render_template('booking.html', translations=t, lang=lang, room_status=room_status,
                           pending_rows=pending_rows, total_pending=total_pending)

@app.route("/room/<room>")
def room_detail(room):
    lang = request.args.get('lang','en')
    t = translations.get(lang, translations['en'])
    db = get_db()
    bookings = db.execute("SELECT * FROM bookings WHERE room=? ORDER BY id DESC", (room,)).fetchall()
    return render_template('room_detail.html', room=room, bookings=bookings, translations=t, lang=lang)

@app.route("/history")
def history():
    lang = request.args.get('lang','en')
    t = translations.get(lang, translations['en'])
    q = request.args.get('q','').strip()
    room_filter = request.args.get('room','').strip()
    db = get_db()
    if room_filter:
        rows = db.execute("SELECT * FROM bookings WHERE room=? ORDER BY id DESC", (room_filter,)).fetchall()
    elif q:
        rows = db.execute("SELECT * FROM bookings WHERE name LIKE ? ORDER BY id DESC", ('%'+q+'%',)).fetchall()
    else:
        rows = db.execute("SELECT * FROM bookings ORDER BY id DESC").fetchall()
    return render_template('history.html', history=rows, translations=t, lang=lang, query=q)

@app.route("/early_checkout/<int:booking_id>")
def early_checkout(booking_id):
    db = get_db()
    today = datetime.now().strftime("%Y-%m-%d")
    db.execute("UPDATE bookings SET checkout=?, pending=0 WHERE id=?", (today, booking_id))
    db.commit()
    return redirect(url_for('history'))

@app.route("/mark_paid/<int:booking_id>")
def mark_paid(booking_id):
    method = request.args.get('method','Cash')
    db = get_db()
    db.execute("UPDATE bookings SET pending=0, method=? WHERE id=?", (method, booking_id))
    db.commit()
    return redirect(url_for('booking'))

# --- ✅ FIXED WhatsApp Route ---
@app.route("/whatsapp/<string:boss>")
def whatsapp(boss):
    db = get_db()
    row = db.execute("SELECT * FROM bookings ORDER BY id DESC LIMIT 1").fetchone()
    if not row:
        return "No booking found"

    text = (f"AX HOTEL PAYMENTS\n"
            f"Name: {row['name']}\n"
            f"email: {row['email']}\n"
            f"Room: {row['room']}\n"
            f"Guests: {row['guests']}\n"
            f"Check-in: {row['checkin']}\n"
            f"Check-out: {row['checkout']}\n"
            f"Total: {row['amount_total']} {row['currency']}\n"
            f"Method: {row['method']}\n"
            f"source: {row['source']}\n"
            f"Notes: {row['notes']}")

    encoded_text = urllib.parse.quote(text)

    if boss == 'yunus':
        number = "+905353601136"
    else:
        number = "+905335247460"

    url = f"https://wa.me/{number[1:]}?text={encoded_text}"
    return redirect(url)   # ✅ opens WhatsApp in the user browser

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)



