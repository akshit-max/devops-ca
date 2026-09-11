from flask import Flask, jsonify
import os
import socket

app = Flask(__name__)

VERSION = os.getenv("APP_VERSION", "1.0")


@app.route("/")
def home():
    hostname = socket.gethostname()

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>DevOps HA Web Application</title>

        <style>
            body {{
                font-family: Arial, sans-serif;
                background-color: #f4f6f8;
                text-align: center;
                padding-top: 80px;
            }}

            .container {{
                background: white;
                width: 600px;
                margin: auto;
                padding: 40px;
                border-radius: 10px;
                box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            }}

            h1 {{
                color: #222;
            }}

            .status {{
                color: green;
                font-weight: bold;
            }}

            .info {{
                margin-top: 20px;
                font-size: 18px;
            }}
        </style>
    </head>

    <body>

        <div class="container">

            <h1>DevOps Highly Available Web Application</h1>

            <h2 class="status">Application Status: Running</h2>

            <div class="info">
                <p><strong>Version:</strong> {VERSION}</p>
                <p><strong>Server:</strong> {hostname}</p>
            </div>

            <p>
                Deployed using Docker, Terraform, AWS EC2,
                Application Load Balancer and GitHub Actions.
            </p>

        </div>

    </body>
    </html>
    """


@app.route("/health")
def health():

    return jsonify({
        "status": "healthy",
        "version": VERSION,
        "hostname": socket.gethostname()
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
