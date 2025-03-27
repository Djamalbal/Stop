import os
from flask import Flask, request
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
VERIFY_TOKEN = os.environ.get('VERIFY_TOKEN')

# Heure de fin de maintenance (12 heures à partir du démarrage)
maintenance_end_time = datetime.now() + timedelta(hours=12)

# Message de maintenance
maintenance_message = """🚨 Mise à jour importante ! 🚨

Salut à tous ! C'est Djamaldine, et je voulais vous prévenir d'un petit changement concernant le bot !

⚙️ Le bot sera mis en pause pendant 12 heures pour l'implantation de la nouvelle fonctionnalité YouTube.
Cela nous permettra de finaliser les ajustements nécessaires et de vous offrir une meilleure expérience avec YouTube ! 📹

⏳ Durée de la pause : 12 heures
🔧 Pendant ce temps, le bot ne sera pas accessible, mais ne vous inquiétez pas, il reviendra avec de nouvelles améliorations très bientôt !

🙏 Merci pour votre patience et compréhension !
👉 Pour toute question, vous pouvez me contacter sur Facebook.

Restez connectés, on revient très vite avec la fonctionnalité YouTube et bien plus ! 🚀."""

# Message de réponse pendant la maintenance
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
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.challenge"):
        if request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return request.args.get("hub.challenge"), 200
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
                    logger.info(f"Sending maintenance response to user {sender_id}")
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
    
    response = requests.post(
        "https://graph.facebook.com/v17.0/me/messages",
        params=params,
        json=request_body
    )
    
    if response.status_code != 200:
        logger.error(f"Erreur lors de l'envoi du message: {response.text}")
    else:
        logger.info(f"Message envoyé avec succès à {recipient_id}")

@app.route('/broadcast', methods=['GET'])
def trigger_broadcast():
    """
    Endpoint pour déclencher l'envoi du message de maintenance à tous les utilisateurs
    Accessible via /broadcast
    """
    if not PAGE_ACCESS_TOKEN:
        return "PAGE_ACCESS_TOKEN non configuré", 500
    
    try:
        # Récupérer la liste des conversations actives
        params = {
            "access_token": PAGE_ACCESS_TOKEN,
            "fields": "participants"
        }
        
        response = requests.get(
            "https://graph.facebook.com/v17.0/me/conversations",
            params=params
        )
        
        if response.status_code != 200:
            logger.error(f"Erreur lors de la récupération des conversations: {response.text}")
            return f"Erreur: {response.text}", 500
        
        data = response.json()
        user_ids = []
        
        # Extraire les IDs des utilisateurs
        if "data" in data:
            for conversation in data["data"]:
                if "participants" in conversation and "data" in conversation["participants"]:
                    for participant in conversation["participants"]["data"]:
                        if participant.get("id") and participant.get("id") != "61573963893697":  # Remplacer PAGE_ID par l'ID de votre page
                            user_ids.append(participant["id"])
        
        # Éliminer les doublons
        user_ids = list(set(user_ids))
        
        # Envoyer le message à chaque utilisateur
        for user_id in user_ids:
            send_message(user_id, maintenance_message, contact_button)
        
        return f"Message de maintenance envoyé à {len(user_ids)} utilisateurs", 200
    
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi du broadcast: {str(e)}")
        return f"Erreur: {str(e)}", 500

if __name__ == "__main__":
    # Obtenir le port depuis les variables d'environnement pour Render
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
