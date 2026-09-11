from flask import Flask, jsonify, render_template_string
import os
import socket
import boto3
import urllib.request
from datetime import datetime, timedelta

app = Flask(__name__)

VERSION = os.getenv("APP_VERSION", "1.0")
PROJECT_NAME = "devops-ha-web-app"
AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")

def get_instance_id():
    try:
        req = urllib.request.Request("http://169.254.169.254/latest/api/token", method="PUT")
        req.add_header("X-aws-ec2-metadata-token-ttl-seconds", "21600")
        token = urllib.request.urlopen(req, timeout=1).read().decode()
        
        req2 = urllib.request.Request("http://169.254.169.254/latest/meta-data/instance-id")
        req2.add_header("X-aws-ec2-metadata-token", token)
        return urllib.request.urlopen(req2, timeout=1).read().decode()
    except Exception:
        return "local-dev"

def get_ec2_instances():
    try:
        ec2 = boto3.client('ec2', region_name=AWS_REGION)
        # Fetch instances by tag
        response = ec2.describe_instances(
            Filters=[{'Name': 'tag:Name', 'Values': [f'{PROJECT_NAME}-server-*']}]
        )
        servers = []
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                name = next((tag['Value'] for tag in instance.get('Tags', []) if tag['Key'] == 'Name'), 'Unknown')
                servers.append({
                    'id': instance['InstanceId'],
                    'name': name,
                    'state': instance['State']['Name'],
                    'az': instance['Placement']['AvailabilityZone'],
                    'private_ip': instance.get('PrivateIpAddress', 'N/A'),
                    'public_ip': instance.get('PublicIpAddress', 'N/A')
                })
        return sorted(servers, key=lambda x: x['name'])
    except Exception as e:
        print(f"Error fetching EC2 instances: {e}")
        return []

def get_cloudwatch_metric(namespace, metric_name, dimensions, stat='Average'):
    try:
        cw = boto3.client('cloudwatch', region_name=AWS_REGION)
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=5)
        
        response = cw.get_metric_statistics(
            Namespace=namespace,
            MetricName=metric_name,
            Dimensions=dimensions,
            StartTime=start_time,
            EndTime=end_time,
            Period=60,
            Statistics=[stat]
        )
        datapoints = response.get('Datapoints', [])
        if not datapoints:
            return 0
        
        # Sort by timestamp and get the latest
        latest = sorted(datapoints, key=lambda x: x['Timestamp'], reverse=True)[0]
        return round(latest[stat], 2)
    except Exception as e:
        print(f"Error fetching metric {metric_name}: {e}")
        return 0

@app.route("/")
@app.route("/dashboard")
def dashboard():
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>DevOps HA Monitor</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body { background-color: #121212; color: #e0e0e0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
            .card { background-color: #1e1e1e; border: 1px solid #333; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
            .card-header { background-color: #252525; border-bottom: 1px solid #333; font-weight: 600; color: #fff; }
            .text-success { color: #4caf50 !important; }
            .text-danger { color: #f44336 !important; }
            .text-warning { color: #ff9800 !important; }
            .badge-success { background-color: #4caf50; }
            .badge-danger { background-color: #f44336; }
            .stat-value { font-size: 2rem; font-weight: bold; }
            .stat-label { font-size: 0.9rem; color: #aaa; text-transform: uppercase; letter-spacing: 1px; }
            .server-card { transition: transform 0.2s; }
            .serving-indicator { border: 2px solid #4caf50; position: relative; }
            .serving-indicator::after { content: 'CURRENTLY SERVING'; position: absolute; top: -10px; right: 10px; background: #4caf50; color: #000; font-size: 0.7rem; font-weight: bold; padding: 2px 8px; border-radius: 10px; }
            h1, h2, h3 { color: #ffffff; }
            .header-bar { background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%); padding: 20px 0; border-bottom: 3px solid #4caf50; margin-bottom: 30px; }
        </style>
    </head>
    <body>
        <div class="header-bar text-center">
            <h1>DEVOPS HA MONITOR</h1>
            <p class="mb-0 text-light">Highly Available Auto-Failover Architecture</p>
        </div>

        <div class="container">
            <div class="row mb-4">
                <div class="col-md-3">
                    <div class="card text-center p-3">
                        <div class="stat-label">Overall Status</div>
                        <div class="stat-value" id="overall-status"><span class="text-success">🟢 HEALTHY</span></div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card text-center p-3">
                        <div class="stat-label">App Version</div>
                        <div class="stat-value text-info">{{ version }}</div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card text-center p-3">
                        <div class="stat-label">Failover Status</div>
                        <div class="stat-value" id="failover-status">🟢 Normal</div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card text-center p-3">
                        <div class="stat-label">Current Serving ID</div>
                        <div class="stat-value text-warning" style="font-size: 1.5rem; margin-top: 5px;">{{ hostname }}</div>
                    </div>
                </div>
            </div>

            <h3 class="mb-3 border-bottom border-secondary pb-2">SERVER HEALTH</h3>
            <div class="row" id="servers-container">
                <div class="col-12 text-center py-5">
                    <div class="spinner-border text-light" role="status"></div>
                    <p class="mt-2">Loading Server Data from AWS...</p>
                </div>
            </div>

        </div>

        <script>
            const CURRENT_HOSTNAME = "{{ hostname }}";

            async function fetchMetrics() {
                try {
                    const res = await fetch('/api/servers');
                    const data = await res.json();
                    
                    let html = '';
                    let healthyCount = 0;
                    
                    data.servers.forEach(server => {
                        const isServing = (server.id === CURRENT_HOSTNAME || server.name === CURRENT_HOSTNAME) || CURRENT_HOSTNAME.includes(server.id.replace('i-', ''));
                        const isHealthy = server.state === 'running';
                        if (isHealthy) healthyCount++;
                        
                        const statusIcon = isHealthy ? '🟢 HEALTHY' : '🔴 UNHEALTHY';
                        const statusClass = isHealthy ? 'text-success' : 'text-danger';
                        const servingClass = isServing ? 'serving-indicator' : '';
                        
                        html += `
                        <div class="col-md-6 mb-4">
                            <div class="card server-card ${servingClass}">
                                <div class="card-header d-flex justify-content-between align-items-center">
                                    <span>${server.name.toUpperCase()}</span>
                                    <span class="${statusClass} fw-bold">${statusIcon}</span>
                                </div>
                                <div class="card-body">
                                    <div class="row">
                                        <div class="col-6">
                                            <p class="mb-1"><span class="text-muted">Instance ID:</span> ${server.id}</p>
                                            <p class="mb-1"><span class="text-muted">AZ:</span> ${server.az}</p>
                                            <p class="mb-1"><span class="text-muted">State:</span> ${server.state}</p>
                                        </div>
                                        <div class="col-6">
                                            <p class="mb-1"><span class="text-muted">Private IP:</span> ${server.private_ip}</p>
                                            <p class="mb-1"><span class="text-muted">Public IP:</span> ${server.public_ip}</p>
                                            <p class="mb-1"><span class="text-muted">CPU (5m avg):</span> ${server.cpu}%</p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>`;
                    });
                    
                    document.getElementById('servers-container').innerHTML = html;
                    
                    if (healthyCount === 2) {
                        document.getElementById('overall-status').innerHTML = '<span class="text-success">🟢 HEALTHY</span>';
                        document.getElementById('failover-status').innerHTML = '<span class="text-success">🟢 Normal</span>';
                    } else if (healthyCount === 1) {
                        document.getElementById('overall-status').innerHTML = '<span class="text-warning">🟡 DEGRADED</span>';
                        document.getElementById('failover-status').innerHTML = '<span class="text-warning">⚠️ Failover Active</span>';
                    } else {
                        document.getElementById('overall-status').innerHTML = '<span class="text-danger">🔴 FAILED</span>';
                        document.getElementById('failover-status').innerHTML = '<span class="text-danger">🔴 Complete Outage</span>';
                    }
                    
                } catch (err) {
                    console.error('Failed to fetch metrics', err);
                }
            }

            // Fetch immediately and poll every 10 seconds
            fetchMetrics();
            setInterval(fetchMetrics, 10000);
            
            // Auto refresh page every 15 seconds to demonstrate load balancing
            setTimeout(() => { window.location.reload(); }, 15000);
        </script>
    </body>
    </html>
    """
    return render_template_string(html, version=VERSION, hostname=get_instance_id())

@app.route("/health")
def health():
    return jsonify({
        "status": "healthy",
        "version": VERSION,
        "hostname": get_instance_id()
    })

@app.route("/api/servers")
def api_servers():
    servers = get_ec2_instances()
    
    # Enhance with CPU metrics
    for server in servers:
        if server['state'] == 'running':
            cpu = get_cloudwatch_metric('AWS/EC2', 'CPUUtilization', [{'Name': 'InstanceId', 'Value': server['id']}])
            server['cpu'] = cpu
        else:
            server['cpu'] = 0
            
    return jsonify({"servers": servers})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
