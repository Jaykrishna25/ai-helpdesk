# ============================================================================
# AWS production infrastructure for the AI Student Help Desk (ap-south-1).
# Multi-AZ, auto-scaling ECS Fargate + RDS PostgreSQL + OpenSearch + Cognito.
# NOTE: illustrative/reference IaC — review CIDRs, sizing & IAM before applying.
# ============================================================================
terraform {
  required_version = ">= 1.5"
  required_providers { aws = { source = "hashicorp/aws", version = "~> 5.40" } }
  backend "s3" { bucket = "univ-helpdesk-tfstate" key = "prod/terraform.tfstate" region = "ap-south-1" }
}
provider "aws" { region = var.region }

variable "region"       { default = "ap-south-1" }
variable "project"      { default = "ai-helpdesk" }
variable "db_password"  { sensitive = true }
variable "desired_count"{ default = 3 }

# ---------- Networking: VPC across 3 AZs ----------
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"
  name = "${var.project}-vpc"
  cidr = "10.20.0.0/16"
  azs             = ["${var.region}a", "${var.region}b", "${var.region}c"]
  private_subnets = ["10.20.1.0/24", "10.20.2.0/24", "10.20.3.0/24"]
  public_subnets  = ["10.20.101.0/24", "10.20.102.0/24", "10.20.103.0/24"]
  enable_nat_gateway = true
  single_nat_gateway = false          # one NAT/AZ for HA
}

# ---------- S3: knowledge-base documents + audit archive ----------
resource "aws_s3_bucket" "kb" { bucket = "${var.project}-kb-docs" }
resource "aws_s3_bucket_versioning" "kb" {
  bucket = aws_s3_bucket.kb.id
  versioning_configuration { status = "Enabled" }
}
resource "aws_s3_bucket_server_side_encryption_configuration" "kb" {
  bucket = aws_s3_bucket.kb.id
  rule { apply_server_side_encryption_by_default { sse_algorithm = "aws:kms" } }
}

# ---------- RDS PostgreSQL (Multi-AZ) ----------
resource "aws_db_subnet_group" "db" {
  name = "${var.project}-db"; subnet_ids = module.vpc.private_subnets
}
resource "aws_db_instance" "postgres" {
  identifier            = "${var.project}-pg"
  engine                = "postgres"
  engine_version        = "15.5"
  instance_class        = "db.r6g.large"
  allocated_storage     = 100
  max_allocated_storage = 1000
  multi_az              = true                # synchronous standby in 2nd AZ
  storage_encrypted     = true
  db_name               = "helpdesk"
  username              = "helpdesk"
  password              = var.db_password
  db_subnet_group_name  = aws_db_subnet_group.db.name
  vpc_security_group_ids = [aws_security_group.db.id]
  backup_retention_period = 14                # point-in-time recovery
  deletion_protection   = true
  performance_insights_enabled = true
}

# ---------- OpenSearch (vector/k-NN search, 3 data nodes) ----------
resource "aws_opensearch_domain" "search" {
  domain_name    = "${var.project}-search"
  engine_version = "OpenSearch_2.13"
  cluster_config {
    instance_type = "r6g.large.search"
    instance_count = 3
    zone_awareness_enabled = true
    zone_awareness_config { availability_zone_count = 3 }
  }
  ebs_options { ebs_enabled = true; volume_size = 100 }
  encrypt_at_rest { enabled = true }
  node_to_node_encryption { enabled = true }
}

# ---------- ElastiCache Redis (session + response cache) ----------
resource "aws_elasticache_replication_group" "redis" {
  replication_group_id = "${var.project}-redis"
  description          = "session & RAG response cache"
  engine              = "redis"
  node_type           = "cache.r6g.large"
  num_node_groups     = 1
  replicas_per_node_group = 2
  automatic_failover_enabled = true
  multi_az_enabled    = true
  subnet_group_name   = aws_elasticache_subnet_group.redis.name
}
resource "aws_elasticache_subnet_group" "redis" {
  name = "${var.project}-redis"; subnet_ids = module.vpc.private_subnets
}

# ---------- Cognito (student/faculty auth + MFA) ----------
resource "aws_cognito_user_pool" "users" {
  name = "${var.project}-users"
  mfa_configuration = "OPTIONAL"
  software_token_mfa_configuration { enabled = true }
  password_policy {
    minimum_length = 12; require_uppercase = true
    require_numbers = true; require_symbols = true
  }
}

# ---------- SQS (async ticket/notification workers) ----------
resource "aws_sqs_queue" "notifications_dlq" { name = "${var.project}-notif-dlq" }
resource "aws_sqs_queue" "notifications" {
  name = "${var.project}-notifications"
  visibility_timeout_seconds = 60
  redrive_policy = jsonencode({ deadLetterTargetArn = aws_sqs_queue.notifications_dlq.arn, maxReceiveCount = 5 })
}

# ---------- ECS Fargate service + Application Load Balancer ----------
resource "aws_ecs_cluster" "main" { name = "${var.project}-cluster" }
resource "aws_ecs_service" "api" {
  name            = "${var.project}-api"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"
  network_configuration {
    subnets         = module.vpc.private_subnets
    security_groups = [aws_security_group.api.id]
  }
  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api"; container_port = 8000
  }
}
resource "aws_ecs_task_definition" "api" {
  family                   = "${var.project}-api"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu    = "1024"
  memory = "2048"
  execution_role_arn = aws_iam_role.ecs_exec.arn
  task_role_arn      = aws_iam_role.ecs_task.arn
  container_definitions = jsonencode([{
    name  = "api"
    image = "${aws_ecr_repository.api.repository_url}:latest"
    portMappings = [{ containerPort = 8000 }]
    environment = [
      { name = "CONFIDENCE_THRESHOLD", value = "0.85" },
      { name = "NOTIFY_BACKEND", value = "ses" }
    ]
    secrets = [{ name = "DATABASE_URL", valueFrom = aws_secretsmanager_secret.db_url.arn }]
    logConfiguration = { logDriver = "awslogs", options = {
      "awslogs-group" = "/ecs/${var.project}", "awslogs-region" = var.region,
      "awslogs-stream-prefix" = "api" } }
  }])
}
resource "aws_ecr_repository" "api" { name = "${var.project}-api" }

# ---------- Auto Scaling: target-tracking on CPU + request count ----------
resource "aws_appautoscaling_target" "api" {
  max_capacity       = 20
  min_capacity       = 3
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.api.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}
resource "aws_appautoscaling_policy" "cpu" {
  name               = "${var.project}-cpu-scale"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.api.resource_id
  scalable_dimension = aws_appautoscaling_target.api.scalable_dimension
  service_namespace  = aws_appautoscaling_target.api.service_namespace
  target_tracking_scaling_policy_configuration {
    predefined_metric_specification { predefined_metric_type = "ECSServiceAverageCPUUtilization" }
    target_value = 60.0
  }
}
