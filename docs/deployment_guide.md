# Requirements
Before you deploy, you must have the following in place:
*  [AWS Account](https://aws.amazon.com/account/) 
*  [GitHub Account](https://github.com/) 
*  [Node 10 or greater](https://nodejs.org/en/download/) 
*  [AWS CLI installed](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
    * [Configure default profile](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html#cli-configure-files-methods)

For prototyping, you need the following:
*  [Python 3.7 or greater](https://realpython.com/installing-python/) 
*  [SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html) 
*  [Docker](https://docs.docker.com/install/) 

# Step 1: Back-end deployment

In this step we will execute three Cloudformation scripts:
* [cfn-vpc](../cfn/cfn-vpc.yaml) - This Cloudformation create the networking for the image creation EC2 instance, Lambda functions and EC2 instances that processes the model.
* [cfn-imageBuilder](../cfn/cfn-imageBuilder.yaml) - It creates the EC2 Image Builder infrastructure that embeds the model into our custom AMI. 
* [cfn-backend](../cfn/cfn-backend.yaml) - Responsible for the creation of the underlying infrastructure of the solution. It includes the EC2 Auto Scaling configuration, SQS, VPC Endpoints, EFS, and CloudFront


## Step 1.1: VPC Deployment

1. Log into the CloudFormation Management Console.
2. Select 'Create Stack' with the 'With new resources (standard)' option.
3. Click 'Upload a template file', and then 'Choose file' and select the **cfn-vpc.yaml** located in the /cfn directory of the repo
4. Click Next.
5. Give the Stack name a name (e.g. rcl-echo-cloud-vpc).

## Step 1.2: Upload Model To ECR And Update Image Builder
Use a Docker Container with your model on it and a script for inference (As of Aug 29, 2023, use view-classifier by running `docker run -it -d nimakondori/aws:latest` locally).

- For example, on `nimakondori/aws:latest`, the script `run.py` is what sets up a continuous process that monitors an SQS queue and performs inference on view-classifier model on any .mat data loaded to the S3 bucket, and uploads output to the same bucket.

To upload your Docker Container to ECR we follow [this AWS tutorial](https://docs.aws.amazon.com/AmazonECR/latest/userguide/docker-push-ecr-image.html):

1. Go to Elastic Container Registry Management Console. On the Repositories page, choose the Private tab, and then choose Create repository. For Visibility settings, verify that Private is selected. Name it as you wish.
2. Authenticate your docker client by doing
```aws ecr get-login-password --region [your region] | docker login --username AWS --password-stdin [you aws_account_id].dkr.ecr.[your region].amazonaws.com```
3. Identify the local image to push. Run the docker images command to list the container images on your system.
```docker images```
4. Tag your image with the Amazon ECR registry, repository, and optional image tag name combination to use. The registry format is ```[your aws_account_id].dkr.ecr.[your region].amazonaws.com```. The repository name should match the repository that you created for your image. If you omit the image tag, we assume that the tag is latest.

The following example tags a local image with the ID 'localImage' as 'aws_account_id.dkr.ecr.[your region].amazonaws.com/[my-repository:tag]'.

```docker tag localImage aws_account_id.dkr.ecr.us-west-2.amazonaws.com/[my-repository:tag]```
5. Push the image ```docker push [your aws_account_id].dkr.ecr.[your region].amazonaws.com/[my-repository:tag]```
6. In your cloned repository for this project, go to ~/cfn/cfn-imageBuilder.yaml, and look for the ContainerBuildComponent resource, under `dockerpull` step. Replace the two lines of code with the link to your new ECR repository. Save this file before proceeding.

## Step 1.3: EC2 Image Builder Deployment

1.  You also need the latest Deep Learning Amazon Machine Image (AMI) Id in the step. Please, run the command below to obtain it. **Make sure you run this command on the region you are executing the solution, and also make sure your default profile is configured.**
```bash
aws ec2 describe-images \
    --owners amazon \
    --filters 'Name=name,Values=Deep Learning Base AMI (Amazon Linux 2)*' 'Name=state,Values=available' \
    --query 'reverse(sort_by(Images, &CreationDate))[:1].ImageId' \
    --output text
```

2. Log into the CloudFormation Management Console.
3. Select 'Create Stack' with the 'With new resources (standard)' option.
4. Click 'Upload a template file', and then 'Choose File' and select the **cfn-ImageBuilder.yaml** located in the /cfn directory of the repo
5. Click Next.
6. Give the Stack name a name (e.g. rcl-echo-cloud-ImageBuilder).
7. Select a key-pair. If you don’t have any Amazon EC2 key-pair available [create-your-key-pair](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-key-pairs.html#having-ec2-create-your-key-pair), and repeat this step.
8. On the AmazonLinuxAMI paste the AMI ID from the command listed at beginning of this step.

:warning: **Important Note**: This step takes approximately 40min-60min as it spins up an instance and runs all the steps to create the AMI. **Make sure it finishes successfully to move to the next step**

## Step 1.4: Backend Deployment

1. Log into the CloudFormation Management Console.
2. Select 'Create Stack' with the 'With new resources (standard)' option.
3. Click 'Upload a template file', and then 'Choose File' and select the **cfn-backend.yaml** located in the /cfn directory of the repo
4. Click Next.
5. Give the Stack name a name (e.g. rcl-echo-cloud-ImageBuilder).
6. Select a key-pair that you have defined on Step 2.1 item 7.
7. On the S3Bucket field, find the name of the bucket by going to S3 Management Console page and copying the name of the associated bucket which will be of the following form:
   - ```rcl-echo-cloud-imagebuilder-imagebuilderlogbucket-[unique identifier]```

## Step 1.5: Inference Script Initialization
**Make sure your default profile is configured.**:
1. Start a session inside the EC2 instance associated with the prior deployment
```aws ssm start-session --target [ec2 instance id]`
This can also be done on the web interface by going to the EC2 Management Console, selecting the instance associated with the above deployment, clicking the "Actions" button, and selecting "connect"
2. Download the repository from ECR manually by authenticating
```aws ecr get-login-password --region [your region] | docker login --username AWS --password-stdin [you aws_account_id].dkr.ecr.[your region].amazonaws.com```
    - If your account lacks it, you will need to give yourself the `ecr:GetAuthorizationToken` permission for your IAM User.
And pull the docker container using the ECR URI, which you can find on the ECR Management Console under the listing for your model's docker container:
```docker run -it [ECR URI]```
3. Use ```docker ps -a``` to locate the present containers and their IDs. If the container with your model is stopped, start it ```docker start [container ID]```.
4. Open a shell inside the container using ```docker exec -it [container id] /bin/bash``.
5. Start the inference script.

For example, using the view-classifier docker container, the inferencing can be initialized by doing `python3 run.py` from the root directory.

# Step 2: Lambda Function

## 2.1: Creating the Lambda Layer
When an echo ultrasound is submitted to be processed, a Lambda function is triggered to perform inference on the view-classifier model on any .mat data loaded to S3 bucket, and uploads output to the same bucket. **Make sure your default profile is configured.**

1. Go to the directory <strong>/backend/lambda</strong> and execute:
```bash
deploy.sh 
```

# Resource: Front-end deployment

* This front-end exists from a previous app ([here](https://github.com/UBC-CIC/COVID19-L3-Net-APP)) and has not been modified to fit our needs. However, feel free to use this deployment guide as a baseline.
* Download [Amplify CLI installed and configured](https://aws-amplify.github.io/docs/cli-toolchain/quickstart#quickstart)

1.  Clone and Fork this solution repository.
    If you haven't configured Amplify before, configure the Amplify CLI in your terminal as follows:
```bash
amplify configure
```

2.  In a terminal from the project root directory, enter the following command selecting the IAM user of the AWS Account you will deploy this application from. (accept all defaults):

```bash
amplify init
```

3.  Deploy the resource to your AWS Account using the command:
```bash
amplify push
```

4.  After the Amplify deployment finishes, run the command below to obtain the Amazon S3 Bucket Amplify created. This information will be used later as a parameter in a CloudFormation
```bash
aws resourcegroupstaggingapi get-resources --tag-filters Key=user:Application,Values="rcl-echo-cloud" Key=user:Stack,Values="dev" --resource-type-filters s3 --query 'ResourceTagMappingList[*].[ResourceARN]' --output text | grep -v deployment | awk -F':::' '{print $2}'
```

5. Log into the AWS Management Console.
6. Select AWS Amplify and select the 'rcl-echo-cloud'
7. At the *Frontend environments* tab connect to your GitHub account pointing to the forked repo. More information at https://docs.aws.amazon.com/amplify/latest/userguide/deploy-backend.html
