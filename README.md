# Echo Cloud Application
Echo Cloud is an automated application for the storage and processing of echocardiogram videos. When new data is passed to the application, it is passed to the deployed model (at this time the view-classifier) and the resulting output is securely stored. Substituting the deployed model can be done by following the deployment guide.

# Usage

Once the [Deployment Guide](./docs/deployment_guide.md) has been followed, one can use the application simply by uploading a file to S3 that is readable by your model (as for Aug 29, 2023 with the view-classifier mounted, this would be a .mat file). The application automatically passes the data to the mounted model, runs inference on it, and uploads the result to the ```/outputs``` folder of the project's S3 bucket.

Find the name of the bucket by going to S3 Management Console page and copying the name of the associated bucket which will be of the following form: ```rcl-echo-cloud-imagebuilder-imagebuilderlogbucket-[unique identifier]```

## Stack

* **Data** - All data is saved in Amazon S3 
* **Model** - The models were containerized and deployed to Amazon ECR public repositories. 
* **Image** - As part of the infrastructure build, a custom AMI is created with model deployed in it to improve efficiency. 
* **Model Processing** - In the back-end, it was essential to create a cost-effective solution as it uses GPU machines to run the model. It is inspired by an [AWS blog post](https://aws.amazon.com/blogs/compute/running-cost-effective-queue-workers-with-amazon-sqs-and-amazon-ec2-spot-instances/), which describes how to dynamically run EC2 Spot instances in response to the SQS messages, pulling the model docker image from Amazon Elastic Container Repository.
* **Model Visualization** - Javascript plug-in displays the CT Scan image slices with the model results overlaid on top. 

## High level architecture

<img src="./images/Architecture.png"  width="800"/>

# Deployment
To deploy this solution into your AWS Account please follow our [Deployment Guide](./docs/deployment_guide.md)

# Authors
The key contributors to this repository are Artur Rodrigues a Senior Solutions Architect from the AWS, Tim Esler and Brian Lee of Sapien ML.

# Changelog
* Aug 29, 2023: Initial release.

# License
This project is distributed under the Apache License 2.0 license.

