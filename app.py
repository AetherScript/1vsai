from flask import Flask, request, jsonify
import smtplib
from email.message import EmailMessage
import os
import requests
import logging
from flask_cors import CORS

# Initialisation
app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)

# Vérification des variables d'environnement obligatoires
required_vars = ["EMAIL_SENDER", "EMAIL_PASSWORD", "PUSHOVER_TOKEN", "PUSHOVER_USER"]
missing = [var for var in required_vars if not os.getenv(var)]
if missing:
    raise RuntimeError(f"❌ Variables d’environnement manquantes : {', '.join(missing)}")

# Config
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
PUSHOVER_TOKEN = os.getenv("PUSHOVER_TOKEN")
PUSHOVER_USER = os.getenv("PUSHOVER_USER")

COMBO_FILE = "/tmp/combolist.txt"

# Copier le stock de comptes au démarrage
if os.path.exists("combolist.txt"):
    with open("combolist.txt", "r") as src, open(COMBO_FILE, "w") as dst:
        dst.write(src.read())
    logging.info("📄 'combolist.txt' copié vers /tmp")
else:
    logging.warning("⚠️ Fichier 'combolist.txt' introuvable au démarrage")

def send_email(winner_email, account_email, account_password):
    msg = EmailMessage()
    msg['Subject'] = "Encore bien joué pour ta victoire !"
    msg['From'] = EMAIL_SENDER
    msg['To'] = winner_email

    text = f"""Félicitations 🎉

Voici ton compte Crunchyroll :
Email : {account_email}
Mot de passe : {account_password}

Reviens jouer sur 1vsAI : https://1vsai.xyz

Bon visionnage 🍿"""

    html = f"""<html>
  <body>
    <p>Félicitations pour ta victoire ! 🎉</p>
    <p>Voici ton compte Crunchyroll :<br>
       <b>Email</b> : {account_email}<br>
       <b>Mot de passe</b> : {account_password}</p>
    <p>👉 <a href="https://1vsai.xyz">Reviens jouer sur 1vsAI</a></p>
    <p>Bon visionnage 🍿</p>
  </body>
</html>"""

    msg.set_content(text)
    msg.add_alternative(html, subtype='html')

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
            smtp.send_message(msg)
        logging.info(f"[OK] Compte envoyé à {winner_email}")
        return True
    except Exception as e:
        logging.error(f"[ERREUR] Envoi email : {e}")
        return False

def get_next_account():
    if not os.path.exists(COMBO_FILE):
        return None

    with open(COMBO_FILE, 'r') as f:
        lines = [line.strip() for line in f if line.strip()]

    if not lines:
        return None

    next_account = lines[0]
    remaining = lines[1:]

    with open(COMBO_FILE, 'w') as f:
        f.write('\n'.join(remaining))

    email, password = next_account.split(':', 1)
    return email.strip(), password.strip()

def send_pushover_alert(message):
    try:
        requests.post('https://api.pushover.net/1/messages.json', data={
            'token': PUSHOVER_TOKEN,
            'user': PUSHOVER_USER,
            'message': message,
            'title': '⚠️ STOCK VIDE - 1 VS AI',
            'priority': 1
        })
        logging.warning("[ALERTE] Stock vide - Pushover envoyé.")
    except Exception as e:
        logging.error(f"[ERREUR] Pushover : {e}")

@app.route("/api/winner", methods=["POST"])
def handle_winner():
    data = request.get_json()
    winner_email = data.get("email")

    if not winner_email or "@" not in winner_email:
        return jsonify({"success": False, "message": "Email invalide"}), 400

    account = get_next_account()
    if not account:
        send_pushover_alert("Le stock de comptes Crunchyroll est vide ! Refill nécessaire.")
        return jsonify({"success": False, "message": "Stock épuisé"}), 503

    acc_email, acc_pwd = account
    success = send_email(winner_email, acc_email, acc_pwd)

    if success:
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "message": "Erreur envoi email"}), 500

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
