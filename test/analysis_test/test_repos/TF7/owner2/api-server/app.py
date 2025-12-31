"""Web application."""
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/api/data', methods=['GET'])
def get_data():
    return jsonify({'status': 'ok', 'data': []})

if __name__ == "__main__":
    app.run(port=5000)
