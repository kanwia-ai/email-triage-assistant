"""
Flask app for Cloud Run entry point.
"""
from flask import Flask
from main import main

app = Flask(__name__)


@app.route('/', methods=['GET', 'POST'])
def index():
    """Handle Cloud Scheduler trigger."""
    try:
        main()
        return 'OK', 200
    except Exception as e:
        print(f'Error in main: {e}')
        return str(e), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return 'OK', 200


if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
