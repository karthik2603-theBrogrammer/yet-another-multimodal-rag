import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import dotenv

cred = credentials.Certificate("medico-rag-firebase-adminsdk-5f7j4-cbd3868a6f.json")
app = firebase_admin.initialize_app(cred)
db = firestore.client()

