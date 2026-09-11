from flask import Flask, jsonify, render_template
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
        return socket.gethostname()

def get_ec2_instances():
    try:
        ec2 = boto3.client('ec2', region_name=AWS_REGION)
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
        return [
            {
                'id': 'i-0ac2d228b9d004805',
                'name': f'{PROJECT_NAME}-server-1',
                'state': 'running',
                'az': 'ap-south-1a',
                'private_ip': '10.0.1.10',
                'public_ip': '13.233.10.1'
            },
            {
                'id': 'i-00733f91f574fc1ac',
                'name': f'{PROJECT_NAME}-server-2',
                'state': 'running',
                'az': 'ap-south-1b',
                'private_ip': '10.0.2.10',
                'public_ip': '13.233.10.2'
            }
        ]

def get_cloudwatch_metric_latest(namespace, metric_name, dimensions, stat='Average'):
    try:
        cw = boto3.client('cloudwatch', region_name=AWS_REGION)
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=10)
        
        response = cw.get_metric_statistics(
            Namespace=namespace,
            MetricName=metric_name,
            Dimensions=dimensions,
            StartTime=start_time,
            EndTime=end_time,
            Period=300,
            Statistics=[stat]
        )
        datapoints = response.get('Datapoints', [])
        if not datapoints:
            return 0.0
        
        latest = sorted(datapoints, key=lambda x: x['Timestamp'], reverse=True)[0]
        return round(latest[stat], 2)
    except Exception as e:
        print(f"Error fetching latest metric {metric_name}: {e}")
        return 0.0

def get_cloudwatch_timeseries(namespace, metric_name, dimensions, stat='Average', minutes=30):
    try:
        cw = boto3.client('cloudwatch', region_name=AWS_REGION)
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=minutes)
        
        response = cw.get_metric_statistics(
            Namespace=namespace,
            MetricName=metric_name,
            Dimensions=dimensions,
            StartTime=start_time,
            EndTime=end_time,
            Period=300,
            Statistics=[stat]
        )
        datapoints = sorted(response.get('Datapoints', []), key=lambda x: x['Timestamp'])
        
        labels = [dp['Timestamp'].strftime('%H:%M') for dp in datapoints]
        values = [round(dp[stat], 2) for dp in datapoints]
        return labels, values
    except Exception as e:
        print(f"Error fetching timeseries metric {metric_name}: {e}")
        return [], []

@app.route("/")
@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html", version=VERSION, hostname=get_instance_id())

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
    for server in servers:
        if server['state'] == 'running':
            cpu = get_cloudwatch_metric_latest('AWS/EC2', 'CPUUtilization', [{'Name': 'InstanceId', 'Value': server['id']}])
            server['cpu'] = cpu
        else:
            server['cpu'] = 0.0
            
    return jsonify({"servers": servers})

@app.route("/api/metrics")
def api_metrics():
    servers = get_ec2_instances()
    
    time_labels = []
    cpu_s1 = []
    cpu_s2 = []
    net_in = []
    net_out = []
    alb_reqs = []
    alb_resp_time = []
    
    # 1. Fetch CPU & Network for servers
    if len(servers) >= 1 and servers[0]['state'] == 'running':
        lbls, cpu_s1 = get_cloudwatch_timeseries('AWS/EC2', 'CPUUtilization', [{'Name': 'InstanceId', 'Value': servers[0]['id']}])
        if lbls:
            time_labels = lbls
            _, net_in = get_cloudwatch_timeseries('AWS/EC2', 'NetworkIn', [{'Name': 'InstanceId', 'Value': servers[0]['id']}])
            _, net_out = get_cloudwatch_timeseries('AWS/EC2', 'NetworkOut', [{'Name': 'InstanceId', 'Value': servers[0]['id']}])

    if len(servers) >= 2 and servers[1]['state'] == 'running':
        _, cpu_s2 = get_cloudwatch_timeseries('AWS/EC2', 'CPUUtilization', [{'Name': 'InstanceId', 'Value': servers[1]['id']}])

    # Fallback labels if no metrics yet
    if not time_labels:
        now = datetime.utcnow()
        time_labels = [(now - timedelta(minutes=5 * i)).strftime('%H:%M') for i in range(5, -1, -1)]
        cpu_s1 = [0.0] * 6
        cpu_s2 = [0.0] * 6
        net_in = [0.0] * 6
        net_out = [0.0] * 6
        alb_reqs = [0.0] * 6
        alb_resp_time = [0.0] * 6
    else:
        # Pad s2 if length mismatch
        if len(cpu_s2) < len(time_labels):
            cpu_s2.extend([0.0] * (len(time_labels) - len(cpu_s2)))

        # 2. Try fetching ALB metrics dynamically using CloudWatch list_metrics
        try:
            cw = boto3.client('cloudwatch', region_name=AWS_REGION)
            alb_metrics = cw.list_metrics(Namespace='AWS/ApplicationELB', MetricName='RequestCount')
            if alb_metrics.get('Metrics'):
                dims = alb_metrics['Metrics'][0]['Dimensions']
                _, alb_reqs = get_cloudwatch_timeseries('AWS/ApplicationELB', 'RequestCount', dims, stat='Sum')
                _, alb_resp_time = get_cloudwatch_timeseries('AWS/ApplicationELB', 'TargetResponseTime', dims, stat='Average')
        except Exception as e:
            print(f"Error fetching ALB metrics: {e}")

        if not alb_reqs or len(alb_reqs) < len(time_labels):
            alb_reqs = [0.0] * len(time_labels)
        if not alb_resp_time or len(alb_resp_time) < len(time_labels):
            alb_resp_time = [0.0] * len(time_labels)

    return jsonify({
        "labels": time_labels,
        "cpu": {
            "server1": cpu_s1,
            "server2": cpu_s2
        },
        "network": {
            "in": net_in,
            "out": net_out
        },
        "alb_requests": alb_reqs,
        "alb_response_time": alb_resp_time
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
