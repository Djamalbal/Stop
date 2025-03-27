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
                    logger.info(f"Sending maintenance response to user {sender_id}")
                    
                    # Envoyer le message de maintenance avec le bouton de contact
                    send_message(sender_id, response_during_maintenance, contact_button)
                    
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

@app.route('/broadcast', methods=['GET'])
def trigger_broadcast():
    """
    Endpoint pour déclencher l'envoi du message de maintenance
    Cette version utilise l'API de Conversation pour trouver les utilisateurs récents
    """
    if not PAGE_ACCESS_TOKEN:
        return "PAGE_ACCESS_TOKEN non configuré", 500
    
    try:
        # Utiliser l'API Sponsored Messages pour envoyer un message à tous les utilisateurs
        # Cette méthode nécessite une approbation spéciale de Facebook et un budget publicitaire
        # C'est la seule façon officielle d'envoyer des messages en dehors de la fenêtre de 24h
        
        logger.info("Tentative d'envoi du message de maintenance via l'API de conversation")
        
        # Récupérer les conversations récentes (dernières 24h)
        params = {
            "access_token": PAGE_ACCESS_TOKEN,
            "fields": "participants",
            "limit": 50  # Limiter à 50 conversations pour éviter les problèmes de rate limiting
        }
        
        response = requests.get(
            "https://graph.facebook.com/v17.0/me/conversations",
            params=params
        )
        
        if response.status_code != 200:
            logger.error(f"Erreur lors de la récupération des conversations: {response.text}")
            return jsonify({
                "success": False,
                "error": f"Erreur lors de la récupération des conversations: {response.text}"
            }), 500
        
        data = response.json()
        user_ids = []
        success_count = 0
        error_count = 0
        
        # Extraire les IDs des utilisateurs
        if "data" in data:
            for conversation in data["data"]:
                if "participants" in conversation and "data" in conversation["participants"]:
                    for participant in conversation["participants"]["data"]:
                        if participant.get("id") and "PSID" in participant.get("id", ""):
                            user_id = participant["id"]
                            user_ids.append(user_id)
        
        # Éliminer les doublons
        user_ids = list(set(user_ids))
        logger.info(f"Nombre d'utilisateurs trouvés: {len(user_ids)}")
        
        # Envoyer le message à chaque utilisateur
        for user_id in user_ids:
            success = send_message(user_id, maintenance_message, contact_button)
            if success:
                success_count += 1
            else:
                error_count += 1
        
        # Si aucun utilisateur n'a été trouvé, proposer une solution alternative
        if len(user_ids) == 0:
            return jsonify({
                "success": False,
                "message": "Aucun utilisateur récent trouvé. Pour envoyer des messages en dehors de la fenêtre de 24h, vous devez utiliser les Sponsored Messages ou les Message Tags approuvés par Facebook."
            }), 200
        
        return jsonify({
            "success": True,
            "message": f"Message de maintenance envoyé à {success_count} utilisateurs sur {len(user_ids)} tentatives. {error_count} erreurs."
        }), 200
    
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi du broadcast: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/status', methods=['GET'])
def status():
    """
    Endpoint pour vérifier le statut du bot
    """
    return jsonify({
        "status": "online",
        "verify_token": VERIFY_TOKEN[:3] + "***" if VERIFY_TOKEN else "Non configuré",
        "page_token": PAGE_ACCESS_TOKEN[:5] + "***" if PAGE_ACCESS_TOKEN else "Non configuré"
    }), 200

if __name__ == "__main__":
    # Obtenir le port depuis les variables d'environnement pour Render
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
