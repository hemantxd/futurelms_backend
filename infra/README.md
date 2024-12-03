
### Push Docker Image to ECR

```
aws ecr create-repository --repository-name crysta --region ap-south-1

aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin 314346757401.dkr.ecr.ap-south-1.amazonaws.com

IMAGE_REPO=$(aws ecr describe-repositories --repository-names crysta --region ap-south-1 --query 'repositories[0].repositoryUri' --output text)

docker build -t crysta .

docker tag crysta:latest $IMAGE_REPO:$(git rev-parse --short HEAD)

docker push $IMAGE_REPO:$(git rev-parse --short HEAD)
```

### Create CloudFormation Stacks

```
aws cloudformation create-stack --region ap-south-1 --template-body file://$PWD/vpc.yml --stack-name crystaprodvpc

aws cloudformation create-stack --region ap-south-1 --template-body file://$PWD/iam.yml --stack-name crystaiam --capabilities CAPABILITY_NAMED_IAM

aws cloudformation create-stack --region ap-south-1 --template-body file://$PWD/app-cluster.yml --stack-name crysta

# Edit the frontend.yml to update Image tag/URL under Task > ContainerDefinitions and,
aws cloudformation create-stack --region ap-south-1 --template-body file://$PWD/backend.yml --stack-name crystabackend
```

## Need to deploy app changes?

There isn't a cleaner way to deploy application changes (container) with CloudFormation, especially if you prefer the same image tag (eg: latest, green, prod etc). There are a few different options,

- Use new image tag and pass that as parameter to CF stack (api.yml) to update-stack or deploy. Many don't prefer using new revision number for as tag.
- With CloudFormation, some prefer create-stack & delete-stack to manage zero-downtime blue-green deployments, not specifically for ECS. ECS does part of this but this is an option
- Use ECS-CLI if you like Docker Compose structure to define container services. This is interesting but I am not sure this is really useful.
- A little hack to register a new task definition revision and update the service using CLI. Refer the `./deploy_app.sh` script.

```
# ./deploy_app.sh <CLUSTER NAME> <SERVICE NAME> <TASK FAMILY> <REPOSETORY_NAME>
./deploy_app.sh crysta frontend-service frontend crysta
# One executed, ECS Service update will take a few minutes for the new task / container go live
```