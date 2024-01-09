from flask import Flask, render_template, request, jsonify, redirect, url_for
import json
import requests
import random
import string
from kafka import KafkaProducer
from kafka import KafkaConsumer
import threading
import time

app = Flask(__name__)

test_details = {}
metrics_details = {}

def generate_random_string(length):
    return ''.join(random.choice(string.ascii_letters) for _ in range(length))

# Producer
kafka_producer = KafkaProducer(bootstrap_servers='192.168.68.116:9092', value_serializer=lambda v: json.dumps(v).encode('utf-8'))

# Consumer
consumer_1 = KafkaConsumer("metrics", bootstrap_servers="192.168.68.116:9092", value_deserializer=lambda x: json.loads(x.decode('utf-8')))
consumer_heartbeat = KafkaConsumer("heartbeat", bootstrap_servers="192.168.68.116:9092", value_deserializer=lambda x: json.loads(x.decode('utf-8')))


@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        # Creating a unique test ID
        test_id = generate_random_string(10)
        test_config = {
            "test_id": test_id,
            "test_type": request.form['test_type'],
            "test_message_delay": request.form['test_message_delay'],
            "message_count_per_driver": request.form['message_count_per_driver']
        }

        # Send test configuration to Kafka after serializing to JSON
        kafka_producer.send("test_config", value=test_config)
        time.sleep(5) #sleep for  seconds
        kafka_producer.send("test_config", value='END')

        test_details[test_id] = test_config

    return render_template('Home.html', test_details=test_details)

@app.route('/trigger/<test_id>', methods=['POST'])
def trigger_test(test_id):
    trigger_message = {
        "test_id": test_id,
        "trigger": "YES"
    }

    # Send trigger message to Kafka after serializing to JSON
    kafka_producer.send("trigger", value=trigger_message)
    kafka_producer.send("trigger", value='END')    

    return redirect(url_for('get_metrics', test_id=test_id))

@app.route('/get_metrics/<test_id>', methods=['POST', 'GET'])
def get_metrics(test_id):
    # Initialize the metrics to an empty dictionary
    metrics = {}

    for msg in consumer_1:
        if msg.value == 'END':
            break
        # Update metrics with received values
        metrics.update(msg.value)
    
    # Store the metrics in metrics_details
    metrics_details[test_id] = metrics

    return render_template('metrics.html', test_id=test_id, metrics=metrics)

    
   
@app.route('/metrics_from_server',methods=["POST","GET"])
def metrics_from_server():
    server_url = 'http://localhost:5001/metrics_from_server'
    response = requests.get(server_url)
    return render_template('server_metrics.html',response=response)


# Handle heartbeat requests
@app.route('/heartbeat', methods=['GET'])
def get_heartbeat():
    # Initialize the heartbeat status to an empty dictionary
    heartbeat_status = {}

    for msg in consumer_heartbeat:
        if msg.value == 'END':
            break
        # Update heartbeat_status with received values
        heartbeat_data = msg.value
        NODE_ID = heartbeat_data['NODE_ID']
        status = heartbeat_data['status']
        heartbeat_status[NODE_ID] = status
        print(heartbeat_status)
    return jsonify(heartbeat_status)

if __name__ == '__main__':
    app.run(debug=True, port=5015)
