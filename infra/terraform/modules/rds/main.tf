variable "name" { type = string }
variable "vpc_id" { type = string }
variable "subnet_ids" { type = list(string) }
variable "tags" { type = map(string) }

# NOTE: 本番適用前にシークレット管理・パラメータグループ・バックアップ等を拡充すること
resource "aws_db_subnet_group" "main" {
  name       = "${var.name}-db-subnet"
  subnet_ids = var.subnet_ids
  tags       = var.tags
}

resource "aws_db_instance" "main" {
  identifier                 = "${var.name}-postgres"
  engine                     = "postgres"
  engine_version             = "16"
  instance_class             = "db.t4g.micro"
  allocated_storage          = 20
  db_name                    = "elearning"
  username                   = "elearning"
  manage_master_user_password = true
  db_subnet_group_name       = aws_db_subnet_group.main.name
  skip_final_snapshot        = true
  publicly_accessible        = false
  tags                       = var.tags
}

output "endpoint" { value = aws_db_instance.main.endpoint }
