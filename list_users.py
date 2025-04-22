from main import app
from app.models.database import User, db

with app.app_context():
      users = User.query.all()
      for user in users:
          print(f'{user.id}: {user.username} ({user.email})')
