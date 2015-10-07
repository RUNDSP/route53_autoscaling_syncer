#!/bin/bash

# Usage: provision-example.sh [create|update]
# (defaults to create)
# dependencies: AWS CLI (`aws`, which comes from `pip install awscli>=1.8.8`)
# Assumes you have your ~/.aws/credentials set up with AWS keys
# or have set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY.

# This is for testing purposes -- normally route53_autoscaling_syncer would be
# included as a child stack in another CloudFormation template.

REGION=us-east-1
STACK_NAME=r53-test
CFTEMPLATE=./route53_autoscaling_syncer.json

read -r -d '' TEMPLATEPARAMS << EOM
[
    {"ParameterKey": "VpcId", "ParameterValue": "vpc-xxxxxx"},
    {"ParameterKey": "Subnets", "ParameterValue": "subnet-xxxxxx,subnet-xxxxxx"},
    {"ParameterKey": "ClusterSize", "ParameterValue": "2"},
    {"ParameterKey": "AutoScalingGroupName", "ParameterValue": "my-autoscaling-group-name"},
    {"ParameterKey": "Route53Zone", "ParameterValue": "example.com"},
    {"ParameterKey": "Route53RecordName", "ParameterValue": "kinesauce.example.com"}
]
EOM

mode=${1:-create}

if [ $mode = 'update' ]; then
    echo "Updating stack $STACK_NAME"
    aws --region $REGION \
        cloudformation update-stack \
        --stack-name $STACK_NAME \
        --template-body file://$CFTEMPLATE \
        --parameters "$TEMPLATEPARAMS" \
        --capabilities CAPABILITY_IAM
else
    echo "Creating stack $STACK_NAME"
    aws --region $REGION \
        cloudformation create-stack \
        --stack-name $STACK_NAME \
        --on-failure DO_NOTHING \
        --template-body file://$CFTEMPLATE \
        --parameters "$TEMPLATEPARAMS" \
        --tags \
            Key=Stack,Value=$STACK_NAME \
        --capabilities CAPABILITY_IAM
fi
