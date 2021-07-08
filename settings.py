import os

SQLALCHEMY_DATABASE_URI = os.environ['DATABASE_URL_SQL'] #can't use the original one, because support for postgres:// in URI got removed (now: postgresql)
SECRET_KEY = os.environ.get('SECRET_KEY')
SQLALCHEMY_TRACK_MODIFICATIONS = False
# NETWORK_FOLDER = './Networks'

