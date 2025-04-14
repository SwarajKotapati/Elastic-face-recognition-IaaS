import boto3
import json
import torch
from PIL import Image
from io import BytesIO
import sys
import os
import subprocess
import socket
#from face_recognition import face_match

# AWS configurations
ASU_ID = "1230469840"
S3_INPUT_BUCKET = f"{ASU_ID}-in-bucket"
S3_OUTPUT_BUCKET = f"{ASU_ID}-out-bucket"
REQ_QUEUE_URL = f"https://sqs.us-east-1.amazonaws.com/861276114572/{ASU_ID}-req-queue"
RESP_QUEUE_URL = f"https://sqs.us-east-1.amazonaws.com/861276114572/{ASU_ID}-resp-queue"

# Initialize AWS Clients
sqs = boto3.client('sqs', region_name='us-east-1')
s3 = boto3.client('s3')

# Get the instance ID from the metadata or hostname
def get_instance_id():
    try:
        with open('/var/lib/cloud/data/instance-id') as f:
            return f.read().strip()
    except Exception:
        return socket.gethostname()
    
INSTANCE_ID = get_instance_id()

def get_request_from_sqs():
    response = sqs.receive_message(
        QueueUrl=REQ_QUEUE_URL,
        MaxNumberOfMessages=1,
        WaitTimeSeconds=10,
        VisibilityTimeout=60
    )
    
    if 'Messages' in response:
        message = response['Messages'][0]
        print("Message",message)
        receipt_handle = message['ReceiptHandle']
        return json.loads(message['Body']), receipt_handle
    
    return None, None

def fetch_image_from_s3(filename):
    #print(f"Attempting to fetch image from S3 with filename: {filename}")
    
    local_path = f"./{filename}"
    
    # Use boto3's download_file method to download the image
    s3.download_file(S3_INPUT_BUCKET, filename, local_path)
    return local_path

def perform_inference(image_path):
    
    #print("Enter perform inferance for",image_path)
    # Run face_recognition.py as a subprocess with the local image path
    result = subprocess.run(
        ["python3", "face_recognition.py", image_path], 
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    print("Prediction found for", image_path,result)

    if result.returncode == 0:
        os.remove(image_path)
        return result.stdout.strip()
    else:
        print(f"Error: {result.stderr}")
        return None

def store_result_in_s3(filename, result):
    key = filename.rsplit('.', 1)[0]  # Strip off the extension
    s3.put_object(Bucket=S3_OUTPUT_BUCKET, Key=key, Body=result)

def send_response_to_sqs(filename, result):
    #print(f"Sending to response queue: {filename}, {result}")
    message = {
        'fileName': filename,
        'prediction': result
    }
    sqs.send_message(
        QueueUrl=RESP_QUEUE_URL,
        MessageBody=json.dumps(message)
    )

def process_request():
    request, receipt_handle = get_request_from_sqs()
    if request:
        filename = request['fileName']

        try:
            # Fetch image from S3
            image_path = fetch_image_from_s3(filename)

            # Perform model inference
            result = perform_inference(image_path)

            if result:
                # Store result in S3
                store_result_in_s3(filename, result)

                # Send the result to the response queue
                send_response_to_sqs(filename, result)
                #print("Processed message successfully by instance", result, INSTANCE_ID)

                # ✅ Delete message **after** successful processing
                if receipt_handle:
                    sqs.delete_message(
                        QueueUrl=REQ_QUEUE_URL,
                        ReceiptHandle=receipt_handle
                    )
                    #print(f"Deleted message from queue: {filename}")

        except Exception as e:
            print(f"Error processing request: {e}")

if __name__ == "__main__":
    print("New EC2 Main called", INSTANCE_ID)
    while True:
        process_request()