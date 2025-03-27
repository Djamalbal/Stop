import os
from flask import Flask, request, jsonify
import requests
import json
from datetime import datetime, timedelta
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
PAGE_ACCESS_TOKEN = os.environ.get('PAGE_ACCESS_TOKEN')
VERIFY_TOKEN = os.environ.get('VERIFY_TOKEN', 'denja19')  # Utilisation de 'denja19' comme valeur par défaut

# Dictionnaire pour suivre les utilisateurs qui ont déjà reçu le message de maintenance
# Clé: user_id, Valeur: True si le message complet a déjà été envoyé
users_notified = {}

# Message de maintenance complet (envoyé la première fois)
maintenance_message = """🚨 Mise à jour importante ! 🚨

Salut à tous ! C'est Djamaldine, et je voulais vous prévenir d'un petit changement concernant le bot !

⚙️ Le bot sera mis en pause pendant 12 heures pour l'implantation de la nouvelle fonctionnalité YouTube.
Cela nous permettra de finaliser les ajustements nécessaires et de vous offrir une meilleure expérience avec YouTube ! 📹

⏳ Durée de la pause : 12 heures
🔧 Pendant ce temps, le bot ne sera pas accessible, mais ne vous inquiétez pas, il reviendra avec de nouvelles améliorations très bientôt !

🙏 Merci pour votre patience et compréhension !
👉 Pour toute question, vous pouvez me contacter sur Facebook.

Restez connectés, on revient très vite avec la fonctionnalité YouTube et bien plus ! 🚀."""

# Message court pour les messages suivants
response_during_maintenance = "🔧 Le bot est en pause pour l'implémentation de la fonctionnalité YouTube. Il sera de retour dans environ 12 heures."

# Bouton "Contactez-moi"
contact_button = [{
    "type": "web_url",
    "url": "https://www.facebook.com/DjamalDixneuf",
    "title": "Contactez-moi"
}]

@app.route('/', methods=['GET'])
def verify():
    """
    Webhook verification pour Facebook Messenger
    """
    logger.info(f"Received verification request with params: {request.args}")
    
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.challenge"):
        if request.args.get("hub.verify_token") == VERIFY_TOKEN:
            challenge = request.args.get("hub.challenge")
            logger.info(f"Verification successful, returning challenge: {challenge}")
            return challenge, 200
        logger.error(f"Verification token mismatch: {request.args.get('hub.verify_token')} vs {VERIFY_TOKEN}")
        return "Verification token mismatch", 403
    return "Hello world", 200

@app.route('/', methods=['POST'])
def webhook():
    """
    Endpoint pour recevoir les messages
    """
    data = request.get_json()
    logger.info(f"Received webhook data: {data}")
    
    if data["object"] == "page":
        for entry in data["entry"]:
            for messaging_event in entry["messaging"]:
                
                sender_id = messaging_event["sender"]["id"]
                
                # Si un message est reçu pendant la maintenance
                if "message" in messaging_event:
                    # Vérifier si l'utilisateur a déjà reçu le message complet
                    if sender_id not in users_notified:
                        # Première fois - envoyer le message complet avec le bouton
                        logger.info(f"Sending full maintenance message to new user {sender_id}")
                        send_message(sender_id, maintenance_message, contact_button)
                        users_notified[sender_id] = True
                    else:
                        # Messages suivants - envoyer le message court
                        logger.info(f"Sending short maintenance response to returning user {sender_id}")
                        send_message(sender_id, response_during_maintenance)
                    
    return "ok", 200

def send_message(recipient_id, message_text, buttons=None):
    """
    Envoie un message à un utilisateur spécifique
    """
    params = {
        "access_token": PAGE_ACCESS_TOKEN
    }
    
    if buttons:
        # Message avec bouton
        request_body = {
            "recipient": {
                "id": recipient_id
            },
            "message": {
                "attachment": {
                    "type": "template",
                    "payload": {
                        "template_type": "button",
                        "text": message_text,
                        "buttons": buttons
                    }
                }
            }
        }
    else:
        # Message simple
        request_body = {
            "recipient": {
                "id": recipient_id
            },
            "message": {
                "text": message_text
            }
        }
    
    try:
        response = requests.post(
            "https://graph.facebook.com/v17.0/me/messages",
            params=params,
            json=request_body
        )
        
        response_data = response.json()
        
        if response.status_code != 200:
            logger.error(f"Erreur lors de l'envoi du message à {recipient_id}: {response.text}")
            return False
        else:
            logger.info(f"Message envoyé avec succès à {recipient_id}")
            return True
            
    except Exception as e:
        logger.error(f"Exception lors de l'envoi du message à {recipient_id}: {str(e)}")
        return False

@app.route('/status', methods=['GET'])
def status():
    """
    Endpoint pour vérifier le statut du bot et voir les statistiques
    """
    return jsonify({
        "status": "online",
        "maintenance_mode": True,
        "users_notified": len(users_notified),
        "verify_token": VERIFY_TOKEN[:3] + "***" if VERIFY_TOKEN else "Non configuré",
        "page_token": PAGE_ACCESS_TOKEN[:5] + "***" if PAGE_ACCESS_TOKEN else "Non configuré"
    }), 200

@app.route('/reset', methods=['GET'])
def reset_users():
    """
    Endpoint pour réinitialiser la liste des utilisateurs notifiés
    Utile si vous voulez renvoyer le message complet à tous les utilisateurs
    """
    global users_notified
    count = len(users_notified)
    users_notified = {}
    return jsonify({
        "success": True,
        "message": f"Liste des {count} utilisateurs notifiés réinitialisée"
    }), 200

if __name__ == "__main__":
    # Obtenir le port depuis les variables d'environnement pour Render
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
