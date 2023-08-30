import csv
import boto3
import time
from botocore.exceptions import NoCredentialsError
import pandas as pd
import logging
import os
import json
from view_classifier import ViewClassifier
import scipy.io
import os

VIEW_LUT_PYTORCH = {
    0: 'AP2',
    1: 'AP3',
    2: 'AP4',
    3: 'AP5',
    4: 'PLAX',
    5: 'RVIF',
    6: 'SUBC4',
    7: 'SUBIVC',
    8: 'PSAXAo',
    9: 'PSAXM',
    10: 'PSAXPM',
    11: 'PSAXAp',
    12: 'SUPRA'
}

# Set up logging for this script
logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', level=logging.DEBUG)
logger = logging.getLogger()

# Set up the SQS client in your code
sqsEndpoint = "https://" + os.getenv('sqsEndpoint').split(":")[1]
queue_url = sqsEndpoint + "/" + os.getenv('queueName')


logger.debug("sqsEndpoint :: {}".format(sqsEndpoint))
logger.debug("queueURL :: {}".format(queue_url))

s3_client = boto3.client('s3')
session = boto3.session.Session()

sqs = session.client(
        service_name="sqs",
        endpoint_url=sqsEndpoint,
        )

vc = ViewClassifier(backend='pytorch', 
                    model_name='dense_evidential', 
                    frame_drop_rate=0.5, 
                    display=False)

# This remove method is to make sure that the files from s3 are not stored
# on the EC2 after processing
def removeTempfiles(file_path):
    if isinstance(file_path, list):
        for file in file_path:
            removeTempfiles(file)
    else:
        if os.path.isfile(file_path):
            os.remove(file_path)



if __name__== "__main__":
    while True:
        try:
            # Receive message from SQS queue
            response = sqs.receive_message(
                QueueUrl=queue_url,
                AttributeNames=[
                    'All'
                ],
                MaxNumberOfMessages=1,
                MessageAttributeNames=[
                    'All'
                ],
                VisibilityTimeout=0,
                WaitTimeSeconds=0
            )

            logger.debug("reposnse is ::: {}".format(response))


            # Only raise an exception or something for it to get printed in the terminal
            if 'Messages' in response:
                messages = response["Messages"]
                for message in messages:

                    # Get the receipt handle to delete the message
                    receipt_handle = message["ReceiptHandle"]
                    body = json.loads(message["Body"])

                    s3Key = body["Records"][0]["s3"]["object"]["key"]
                    bucket = body["Records"][0]["s3"]["bucket"]["name"]
                    userDir='/mnt/tmp/downloads/'
                    mat_file = os.path.join(userDir, s3Key)

                    logger.debug("s3Key    :: {}".format(s3Key))
                    logger.debug("bucket   :: {}".format(bucket))
                    logger.debug("zipFile  :: {}".format(mat_file))

                    if not os.path.isdir(userDir):
                        logger.debug("userDir directory does not exist, creating")
                        try:
                            os.makedirs(userDir)
                            logger.debug("Directory created successfully.")
                        except OSError as e:
                            logger.error(f"Failed to create directory: {e}")
                    result_dict = {}

                    # Download file from S3
                    logger.debug("attempting s3 file download into docker container")
                    s3_client.download_file(bucket, s3Key, mat_file)  # replace with your bucket name

                    mat_data = scipy.io.loadmat(userDir + s3Key)
                    # Inference
                    try:
                        cine = mat_data['Patient'][0][0]['DicomImage']
                    except KeyError:
                        cine = mat_data['resized']

                    view_ave, conf_ave, qual_ave, qual_std = vc.classify_case(cine)
                    logger.debug("{}s -> view = {} with conf = {}".format(mat_file, 
                                                                          VIEW_LUT_PYTORCH[view_ave], 
                                                                          conf_ave))
                    logger.debug("quality_ave :: {}, quality_std {}".format(qual_ave, qual_std))
                    # view_counts[view_ave] += 1

                    # open csv for writing the output 
                    directory = '/mnt/tmp/outputs'
                    os.makedirs(directory, exist_ok=True)

                    filename = os.path.splitext(s3Key)[0] + ".csv"
                    out_csv = os.path.join(directory, filename)
                    fields = ['filename', 'predicted view', 'predicted quality', 'prediction std']
                    # open a csv file and wwrite the fields and resutls in it
                    with open(out_csv, 'w') as csvfile:
                        writer = csv.DictWriter(csvfile, fieldnames=fields)
                        writer.writeheader()
                        writer.writerow({'filename': mat_file,
                                         'predicted view': VIEW_LUT_PYTORCH[view_ave],
                                         'predicted quality': qual_ave,
                                         'prediction std': qual_std})

                    logger.debug("uploading the following file {}".format(filename))
                    s3_client.upload_file(out_csv, bucket, 'outputs/' + filename)

                    # Delete the temporary file that was generated
                    removeTempfiles([out_csv, mat_file])

                    # Delete received message from queue
                    sqs.delete_message(
                        QueueUrl=queue_url,
                        ReceiptHandle=receipt_handle
                    )
            else:
                print('No messages in queue. Sleeping for 3 seconds...')
                time.sleep(3)

        except Exception as e:
            print('Exception: ', e)
            time.sleep(10)
