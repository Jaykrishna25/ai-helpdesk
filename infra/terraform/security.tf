# Security groups, IAM roles, ALB, WAF, SES, CloudWatch alarms.
resource "aws_security_group" "alb" {
  name = "alb-sg"; vpc_id = module.vpc.vpc_id
  ingress { from_port = 443 to_port = 443 protocol = "tcp" cidr_blocks = ["0.0.0.0/0"] }
  egress  { from_port = 0 to_port = 0 protocol = "-1" cidr_blocks = ["0.0.0.0/0"] }
}
resource "aws_security_group" "api" {
  name = "api-sg"; vpc_id = module.vpc.vpc_id
  ingress { from_port = 8000 to_port = 8000 protocol = "tcp" security_groups = [aws_security_group.alb.id] }
  egress  { from_port = 0 to_port = 0 protocol = "-1" cidr_blocks = ["0.0.0.0/0"] }
}
resource "aws_security_group" "db" {
  name = "db-sg"; vpc_id = module.vpc.vpc_id
  ingress { from_port = 5432 to_port = 5432 protocol = "tcp" security_groups = [aws_security_group.api.id] }
}
resource "aws_lb" "main" {
  name = "ai-helpdesk-alb"; load_balancer_type = "application"
  subnets = module.vpc.public_subnets; security_groups = [aws_security_group.alb.id]
}
resource "aws_lb_target_group" "api" {
  name = "api-tg"; port = 8000; protocol = "HTTP"; vpc_id = module.vpc.vpc_id
  target_type = "ip"
  health_check { path = "/api/health"; matcher = "200" }
}
resource "aws_wafv2_web_acl" "main" {
  name = "helpdesk-waf"; scope = "REGIONAL"
  default_action { allow {} }
  rule {
    name = "rate-limit"; priority = 1
    action { block {} }
    statement { rate_based_statement { limit = 2000 aggregate_key_type = "IP" } }
    visibility_config { cloudwatch_metrics_enabled = true metric_name = "rate" sampled_requests_enabled = true }
  }
  visibility_config { cloudwatch_metrics_enabled = true metric_name = "waf" sampled_requests_enabled = true }
}
# IAM: least-privilege task role (S3 KB, SES, SQS, Secrets, Bedrock)
resource "aws_iam_role" "ecs_task" {
  name = "ecs-task-role"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{
    Effect = "Allow", Principal = { Service = "ecs-tasks.amazonaws.com" }, Action = "sts:AssumeRole" }] })
}
resource "aws_iam_role_policy" "task_policy" {
  role = aws_iam_role.ecs_task.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    { Effect = "Allow", Action = ["s3:GetObject","s3:PutObject"], Resource = "${aws_s3_bucket.kb.arn}/*" },
    { Effect = "Allow", Action = ["ses:SendEmail"], Resource = "*" },
    { Effect = "Allow", Action = ["sqs:SendMessage","sqs:ReceiveMessage","sqs:DeleteMessage"], Resource = aws_sqs_queue.notifications.arn },
    { Effect = "Allow", Action = ["secretsmanager:GetSecretValue"], Resource = aws_secretsmanager_secret.db_url.arn },
    { Effect = "Allow", Action = ["bedrock:InvokeModel"], Resource = "*" }
  ]})
}
resource "aws_iam_role" "ecs_exec" {
  name = "ecs-exec-role"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{
    Effect = "Allow", Principal = { Service = "ecs-tasks.amazonaws.com" }, Action = "sts:AssumeRole" }] })
}
resource "aws_iam_role_policy_attachment" "exec" {
  role = aws_iam_role.ecs_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}
resource "aws_secretsmanager_secret" "db_url" { name = "helpdesk/database-url" }
resource "aws_ses_email_identity" "sender" { email = "helpdesk@univ.edu" }
# CloudWatch alarm: high 5xx or latency -> SNS to on-call
resource "aws_cloudwatch_metric_alarm" "api_5xx" {
  alarm_name = "api-5xx-high"; namespace = "AWS/ApplicationELB"
  metric_name = "HTTPCode_Target_5XX_Count"; statistic = "Sum"
  period = 60; evaluation_periods = 3; threshold = 20
  comparison_operator = "GreaterThanThreshold"
}
output "alb_dns" { value = aws_lb.main.dns_name }
