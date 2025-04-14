import os
import boto3
import json
from flask import Flask, request
import asyncio

# Initialize Flask app
app = Flask(__name__)

# AWS configurations
ASU_ID = "1230469840"
S3_BUCKET = f"{ASU_ID}-in-bucket"
S3_OUTPUT_BUCKET = f"{ASU_ID}-out-bucket"
SIMPLEDB_DOMAIN = f"{ASU_ID}-simpleDB"
REGION = "us-east-1"

# AWS Clients
sqs = boto3.client("sqs", region_name=REGION)
s3 = boto3.client("s3", region_name=REGION)

REQ_QUEUE_URL = "https://sqs.us-east-1.amazonaws.com/861276114572/1230469840-req-queue"
RESPONSE_QUEUE_URL = "https://sqs.us-east-1.amazonaws.com/861276114572/1230469840-resp-queue"

# ✅ Cache to store responses temporarily
response_cache = {}

@app.route("/", methods=["GET"])
def handle_get():
    return "GET request received", 200

@app.route("/", methods=["POST"])
async def handle_request():
    if "inputFile" not in request.files:
        return "No file provided", 400
    
    file = request.files["inputFile"]
    filename = file.filename

    if not filename:
        return "Invalid filename", 400
    
    try:
        # ✅ Upload file to S3
        #print(f"📤 Uploading {filename} to S3 bucket {S3_BUCKET}")
        await asyncio.to_thread(s3.upload_fileobj, file, S3_BUCKET, filename)

        # ✅ Prepare and send message to SQS
        message = {
            "fileName": filename,
            "status": "pending"
        }
        response = await asyncio.to_thread(
            sqs.send_message,
            QueueUrl=REQ_QUEUE_URL,
            MessageBody=json.dumps(message)
        )
        #print(f"✅ Request sent to SQS with message ID: {response['MessageId']}")

        # ✅ Wait for response directly from the response queue
        result = await wait_for_response(filename)

        if result:
            clean_filename = filename.replace('.jpg', '')
            #print(f"Returning to user request, {clean_filename}:{result}")
            return f"{clean_filename}:{result}", 200
    
    except boto3.exceptions.Boto3Error as e:
        print(f"🚨 AWS error: {e}")
        return "AWS service failure", 500
    except Exception as e:
        print(f"⚠️ Unexpected error: {e}")
        return "Server error", 500
    # ✅ Wait for the response, with caching

async def wait_for_response(filename):
    #print(f"🔎 Waiting for response for file: {filename}")
    
    while True:
        # ✅ First check the cache for the result
        if filename in response_cache:
            result, receipt_handle = response_cache.pop(filename)
            #print(f"✅ Found cached response for file: {filename}")
            #await delete_message(receipt_handle)  # ✅ Delete from SQS after processing
            return result.get("prediction")

        # ✅ Poll SQS if not found in cache
        result, receipt_handle = await get_response_from_sqs()
        if result:
            file_in_message = result.get("fileName")
            if file_in_message == filename:
                #print(f"✅ Found matching response for file: {filename}")
                await delete_message(receipt_handle)  # ✅ Delete from SQS after processing
                return result.get("prediction")
            else:
                #print(f"📥 Caching response for file: {file_in_message}")
                response_cache[file_in_message] = (result, receipt_handle)
                await delete_message(receipt_handle)  # ✅ Delete the message from the queue after caching

        # ✅ Wait before polling again
        await asyncio.sleep(1) 

# ✅ Poll response queue from SQS
async def get_response_from_sqs():
    try:
        response = await asyncio.to_thread(
            sqs.receive_message,
            QueueUrl=RESPONSE_QUEUE_URL,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=10,
            VisibilityTimeout=60
        )
        if 'Messages' in response:
            message = response['Messages'][0]
            body = json.loads(message['Body'])
            receipt_handle = message['ReceiptHandle']
            #print(f"📩 Received response from SQS: {body}")
            return body, receipt_handle
        return None, None
    except Exception as e:
        print(f"⚠️ Error receiving message from SQS: {e}")
        return None, None

# ✅ Delete message from SQS after successful processing
async def delete_message(receipt_handle):
    try:
        await asyncio.to_thread(
            sqs.delete_message,
            QueueUrl=RESPONSE_QUEUE_URL,
            ReceiptHandle=receipt_handle
            )
        #print(f"🗑️ Deleted message from SQS")
    except Exception as e:
        print(f"⚠️ Error deleting message from SQS: {e}")

# ✅ Start Flask server using asyncio
def start_flask():
    app.run(host="0.0.0.0", port=8000, debug=True, use_reloader=False)

if __name__ == "__main__":
    #loop = asyncio.get_event_loop()
    #loop.create_task(asyncio.to_thread(start_flask))
    #loop.run_forever()
    start_flask()