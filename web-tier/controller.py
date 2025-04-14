import boto3
import time

# AWS configurations
ASU_ID = "1230469840"
AMI_ID = "ami-06cf091226ec7928e"
INSTANCE_TYPE = "t2.micro"
MAX_INSTANCES = 15
MIN_INSTANCES = 0
REGION = 'us-east-1'
INSTANCE_PREFIX = "app-tier-instance-"

# List of 15 pre-created EC2 instances (stopped)
pre_created_instances = [
    "i-057788d2808f0bf37", "i-02bbc02876f0430cf", "i-0fcd847f5732a87e4", "i-0dcafc12c702cb69b",
    "i-02591dadc5e46fb48", "i-0530600dfaf6074a6", "i-0735d7a177ee8b3aa", "i-06b193e123ec9e891",
    "i-05e15786e5ee0c271", "i-038c7e8cb15215530", "i-0d8a8bdc0179091c3", "i-01f6d31b2e31f51fc",
    "i-07247d1d58351bee9", "i-01680bbd499eaef4d", "i-038466f8c4974d629"
]

# Initialize AWS Clients
ec2 = boto3.client('ec2', region_name=REGION)
sqs = boto3.client('sqs', region_name=REGION)

REQ_QUEUE_URL = f"https://sqs.us-east-1.amazonaws.com/861276114572/{ASU_ID}-req-queue"
RESP_QUEUE_URL = f"https://sqs.us-east-1.amazonaws.com/861276114572/{ASU_ID}-resp-queue"

def get_queue_length():
    response = sqs.get_queue_attributes(
        QueueUrl=REQ_QUEUE_URL,
        AttributeNames=[
            'ApproximateNumberOfMessages',
            'ApproximateNumberOfMessagesNotVisible',
        ]
    )
    messages_waiting = int(response['Attributes']['ApproximateNumberOfMessages'])
    messages_not_visible = int(response['Attributes']['ApproximateNumberOfMessagesNotVisible'])
    return messages_waiting + messages_not_visible

def get_running_instances():
    response = ec2.describe_instances(
        Filters=[{'Name': 'tag:Name', 'Values': [f"{INSTANCE_PREFIX}*"]}]
    )
    running_instances = []
    stopped_instances = []
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            state = instance['State']['Name']
            if state == 'running':
                running_instances.append(instance['InstanceId'])
            elif state == 'stopped':
                stopped_instances.append(instance['InstanceId'])
    return running_instances, stopped_instances

def auto_scale():
    queue_length = get_queue_length()
    running_instances, stopped_instances = get_running_instances()
    active_instance_count = len(running_instances)

    #print(f"Queue length: {queue_length}, Active instances: {active_instance_count}")

    # ✅ SCALE OUT
    if queue_length > active_instance_count and active_instance_count < MAX_INSTANCES:
        scale_out_count = min(queue_length - active_instance_count, MAX_INSTANCES - active_instance_count)
        instances_to_start = stopped_instances[:scale_out_count]

        if instances_to_start:
            print(f"Starting instances: {instances_to_start}")
            ec2.start_instances(InstanceIds=instances_to_start)
            ec2.get_waiter('instance_running').wait(InstanceIds=instances_to_start)
            print("Instances started and running.")
        else:
            print("No stopped instances available to scale out.")
    
    # ✅ SCALE IN (after double-check)
    elif queue_length == 0 and active_instance_count > 0:
        flag = True
        for _ in range(2):
            if get_queue_length() != 0:
                flag = False
                break
            time.sleep(0.15)

        if flag:
            #print(f"Queue remained empty. Stopping instances: {running_instances}")
            ec2.stop_instances(InstanceIds=running_instances)
            ec2.get_waiter('instance_stopped').wait(InstanceIds=running_instances)
            print("Instances stopped.")
        else:
            print("Queue not empty on repeated check. Skipping scale-in.")

def manage_instances():
    while True:
        auto_scale()
        # You can uncomment this to add a loop delay
        # time.sleep(1)

if __name__ == "__main__":
    manage_instances()