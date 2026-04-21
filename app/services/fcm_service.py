import firebase_admin
from firebase_admin import credentials, messaging
import os

# Initialize Firebase app only once
_firebase_initialized = False

def initialize_firebase():
    global _firebase_initialized
    if not _firebase_initialized:
        try:
            cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "firebase_credentials.json")
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            _firebase_initialized = True
            print("✅ Firebase initialized successfully")
        except Exception as e:
            print(f"❌ Firebase initialization error: {e}")

def send_alert_notification(
    token: str,
    title: str,
    body: str,
    data: dict = None
) -> dict:
    """Send push notification to a specific device token."""
    try:
        initialize_firebase()
        
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body
            ),
            data=data or {},
            token=token,
            android=messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    sound="default",
                    priority="high",
                    channel_id="wildlife_alerts"
                )
            )
        )
        
        response = messaging.send(message)
        return {
            "success": True,
            "message_id": response,
            "message": "Notification sent successfully"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to send notification: {str(e)}"
        }

def send_alert_to_topic(
    topic: str,
    title: str,
    body: str,
    data: dict = None
) -> dict:
    """
    Send push notification to a topic.
    All users subscribed to topic will receive it.
    e.g topic = "chitwan_alerts" for all users near Chitwan
    """
    try:
        initialize_firebase()
        
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body
            ),
            data=data or {},
            topic=topic,
            android=messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    sound="default",
                    priority="high",
                    channel_id="wildlife_alerts"
                )
            )
        )
        
        response = messaging.send(message)
        return {
            "success": True,
            "message_id": response,
            "message": f"Notification sent to topic: {topic}"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to send to topic: {str(e)}"
        }

def send_bulk_notifications(
    tokens: list,
    title: str,
    body: str,
    data: dict = None
) -> dict:
    """Send push notification to multiple device tokens at once."""
    try:
        initialize_firebase()
        
        message = messaging.MulticastMessage(
            notification=messaging.Notification(
                title=title,
                body=body
            ),
            data=data or {},
            tokens=tokens,
            android=messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    sound="default",
                    channel_id="wildlife_alerts"
                )
            )
        )
        
        response = messaging.send_each_for_multicast(message)
        return {
            "success": True,
            "success_count": response.success_count,
            "failure_count": response.failure_count,
            "message": f"Sent to {response.success_count} devices"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Bulk send failed: {str(e)}"
        }