#!/bin/bash
if [[ ! -n "$1" ]]; then
    GITBRANCH="master"
else
    GITBRANCH=$1
fi

echo "Using GIT BRANCH: $GITBRANCH"

cd ../layers
./createLayer.sh

cd ../lambdas

BUCKET=$(aws ssm get-parameter  --name "/covid19l3/${GITBRANCH}/s3Bucket" --query Parameter.Value --output text --profile cic_nima --region ca-central-1)
echo "Bucket: ${BUCKET}"

# Git bash on windows does not resolve sam. Using sam.cmd is a workaround for that
# Another workaround for this is to create an alias for sam.cmd
# alias sam="/c/Program\ Files/Amazon/AWSSAMCLI/bin/sam.cmd"
sam.cmd package --profile cic_nima --s3-bucket $BUCKET --output-template-file out.yaml
sam.cmd deploy --profile cic_nima --template-file out.yaml --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND --stack-name covid-19-app-lambda --parameter-overrides ParameterKey=gitHubBranch,ParameterValue=$GITBRANCH

LAMBDAARN=$(aws ssm get-parameter --profile cic_nima --name "/covid19l3/${GITBRANCH}/lambdaArn" --query Parameter.Value --output text)
echo "Lambda: ${LAMBDAARN}"

cp notification.json notification.s3 
sed "s|%LambdaArn%|$LAMBDAARN|g" notification.json > notification.s3

echo "Configuring s3Event"
aws  s3api put-bucket-notification-configuration --bucket ${BUCKET} --notification-configuration file://notification.s3 --profile cic_nima 
rm notification.s3
rm ../layers/*.zip
rm out.yaml