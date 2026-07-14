variable "name" { type = string }
variable "vpc_id" { type = string }
variable "public_subnet_ids" { type = list(string) }
variable "private_subnet_ids" { type = list(string) }
variable "tags" { type = map(string) }

# ECS / ALB / CloudFront の骨格。イメージ URI・証明書・ドメインは環境ごとに設定する。
resource "aws_ecs_cluster" "main" {
  name = "${var.name}-cluster"
  tags = var.tags
}

resource "aws_cloudfront_distribution" "web" {
  enabled             = true
  comment             = "${var.name} web CDN (placeholder origin)"
  default_root_object = "index.html"

  origin {
    domain_name = "example.com"
    origin_id   = "placeholder-origin"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  default_cache_behavior {
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "placeholder-origin"
    viewer_protocol_policy = "redirect-to-https"

    forwarded_values {
      query_string = false
      cookies { forward = "none" }
    }
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }

  tags = var.tags
}

output "ecs_cluster_name" { value = aws_ecs_cluster.main.name }
output "cloudfront_domain" { value = aws_cloudfront_distribution.web.domain_name }
