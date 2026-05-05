import os

class Config:
    """Flask应用配置"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-mdvrp-2026'
    DEBUG = os.environ.get('FLASK_DEBUG', 'True') == 'True'
    HOST = os.environ.get('FLASK_HOST', '0.0.0.0')
    PORT = int(os.environ.get('FLASK_PORT', '5000'))
