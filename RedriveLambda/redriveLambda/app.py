import boto3
import logging
import os
import time

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):

    logger.info(f"Lambda Triggered from a {event["detail-type"]}")
    # Read source and dl queue URLs from environment variables
    deadLetter_queue_url = os.environ.get('SourceQueue')
    source_queue_url = os.environ.get('DestinationQueue')

    if not source_queue_url or not deadLetter_queue_url:
        logger.error("No Source or Destination queue found")
        return {
            'statusCode': 400,
            'body': 'Invalid Source or Destination queue.'
        }

    # Create SQS client
    sqs = boto3.client('sqs')

    start_time = time.time()
    duration_limit = 240  # 4 minutes in seconds

    try:
        while True:
            # Check elapsed time
            elapsed_time = time.time() - start_time
            if elapsed_time >= duration_limit:
                # Log when the specified duration is reached
                logger.info(f"Duration limit ({duration_limit} seconds) reached.")
                break

            # Receive up to 10 messages from the DL queue
            response = sqs.receive_message(
                QueueUrl = deadLetter_queue_url,
                AttributeNames = ['All'],
                MaxNumberOfMessages = 10,
                MessageAttributeNames = ['All']
            )

            if 'Messages' in response:
                # Iterate through received messages and send them to the source queue
                for message in response['Messages']:
                    # Send the message to the source queue
                    sqs.send_message(
                        QueueUrl = source_queue_url,
                        MessageBody = message['Body']
                    )

                    # Delete the message from the DL queue
                    sqs.delete_message(
                        QueueUrl = deadLetter_queue_url,
                        ReceiptHandle = message['ReceiptHandle']
                    )

                    logger.info(f"Moved message(s) from DL queue to Source Queue: {message['MessageId']}")
            else:
                # Log when the DL queue is empty
                logger.info("DL queue is empty.")
                break

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")

    return {
        'statusCode': 200,
        'body': 'Messages moved successfully'
    }