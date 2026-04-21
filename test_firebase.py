import os
import sys

print("🔍 Testing Firebase setup...\n")

# 1. Check credentials file
if os.path.exists('firebase-credentials.json'):
    print("✅ firebase-credentials.json found at project root")
else:
    print("❌ firebase-credentials.json NOT found!")
    print("   Make sure it's in the project root, not in a subfolder")
    sys.exit(1)

# 2. Check imports
try:
    import firebase_admin
    print("✅ firebase_admin imported")
except ImportError:
    print("❌ firebase_admin not installed. Run: pip install firebase-admin")
    sys.exit(1)

# 3. Initialize Firebase
try:
    from firebase_admin import credentials, messaging
    
    cred = credentials.Certificate('firebase-credentials.json')
    firebase_admin.initialize_app(cred)
    print("✅ Firebase initialized successfully!")
    
except Exception as e:
    print(f"❌ Firebase initialization failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 4. Test sending a message
try:
    message = messaging.Message(
        notification=messaging.Notification(
            title="🧪 Firebase Test",
            body="Your Firebase setup is working!",
        ),
        data={
            "test": "true",
            "severity": "info"
        },
        topic="test-topic",
    )
    
    response = messaging.send(message)
    print(f"✅ Test message sent! Message ID: {response}")
    print("\n🎉 Firebase is ready to use!\n")
    
except Exception as e:
    print(f"❌ Error sending test message: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)