#!/bin/bash

# Usage: ./deploy_app.sh <CLUSTER NAME> <SERVICE NAME> <TASK FAMILY> <REPOSETORY_NAME>

#Script to get current task definition, and based on that add new ecr image address to old template and remove attributes that are not needed, then we send new task definition, get new revision number from output and update service
CLUSTER=$1
SERVICE=$2
TASK_FAMILY=$3
REPOSETORY_NAME=$4

IMAGE_REPO=$(aws ecr describe-repositories --repository-names "$REPOSETORY_NAME" --region "$AWS_DEFAULT_REGION" --query 'repositories[0].repositoryUri' --output text)
ECR_IMAGE=${IMAGE_REPO}:$(git rev-parse --short HEAD)
TASK_DEFINITION=$(aws ecs describe-task-definition --task-definition "$TASK_FAMILY" --region "$AWS_DEFAULT_REGION")
NEW_TASK_DEFINTIION=$(echo $TASK_DEFINITION | jq --arg IMAGE "$ECR_IMAGE" '.taskDefinition | .containerDefinitions[0].image = $IMAGE | del(.taskDefinitionArn) | del(.revision) | del(.status) | del(.requiresAttributes) | del(.registeredAt) | del(.registeredBy) | del(.compatibilities)')
NEW_TASK_INFO=$(aws ecs register-task-definition --region "$AWS_DEFAULT_REGION" --cli-input-json "$NEW_TASK_DEFINTIION")
NEW_REVISION=$(echo $NEW_TASK_INFO | jq '.taskDefinition.revision')
aws ecs update-service --cluster ${CLUSTER} --service ${SERVICE} --task-definition ${TASK_FAMILY}:${NEW_REVISION}
