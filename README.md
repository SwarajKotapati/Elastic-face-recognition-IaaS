# Elastic-face-recognition-IaaS
This project is a dynamic, scalable face recognition application built using AWS Infrastructure-as-a-Service (IaaS) resources as part of CSE546 - Cloud Computing @ ASU.

# Elastic Face Recognition Application on AWS (IaaS)

This project implements a scalable face recognition system using Infrastructure-as-a-Service (IaaS) resources on AWS. It was developed as part of CSE546 - Cloud Computing at Arizona State University.

## Overview

The system is a multi-tier cloud-native application that uses EC2 instances, S3 buckets, and SQS queues to handle asynchronous requests and perform machine learning inference for face recognition. A custom autoscaling controller was developed to manage EC2 instances dynamically based on queue depth and request volume.

## Architecture

![image](https://github.com/user-attachments/assets/53f53fba-6765-400a-8103-f3768a842c93)

- **Web Tier (`server.py`)**: Receives HTTP POST requests containing images, uploads them to S3, and sends metadata to an SQS request queue.
- **Application Tier (`backend.py`)**: EC2 instances perform inference using a pre-trained deep learning model and respond via an SQS response queue.
- **Autoscaling Controller (`controller.py`)**: Monitors request queue depth and scales EC2 instances manually based on load. AWS Auto Scaling services were not used.
  
## Machine Learning Model

- Framework: PyTorch
- Inference-only model provided
- Achieved 100% classification accuracy on a benchmark dataset of 1,000 facial images

## Technologies Used

- Python 3.10
- Flask (web tier)
- Boto3 (AWS SDK)
- PyTorch (model inference)
- AWS EC2, S3, and SQS

## Key Metrics

| Metric                            | Result        |
|-----------------------------------|---------------|
| Average latency per request       | 0.96 seconds  |
| Inference accuracy                | 100%          |
| Total requests handled            | 100           |
| Time to process full workload     | 96 seconds    |
| Max number of EC2 instances       | 15            |
| Autoscaling scale-in time         | 0.24 seconds  |

## How It Works

1. A user uploads an image to the web tier via an HTTP POST request.
2. The image is stored in an S3 input bucket.
3. The image filename is sent as a message to an SQS request queue.
4. EC2 instances in the app tier fetch the image, run inference, and store the result in an output S3 bucket.
5. The recognition result is sent via an SQS response queue and returned to the user.


