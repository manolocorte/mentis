output "public_ip" {
  description = "Elastic IP of the instance."
  value       = aws_eip.mentis.public_ip
}

output "url" {
  description = "Where the app is served."
  value       = var.domain == "" ? "https://${aws_eip.mentis.public_ip}.sslip.io" : "https://${var.domain}"
}

output "instance_id" {
  description = "EC2 instance id (for SSM Session Manager)."
  value       = aws_instance.mentis.id
}

output "ssm_connect" {
  description = "Open a shell on the box (no SSH port needed)."
  value       = "aws ssm start-session --region ${var.region} --target ${aws_instance.mentis.id}"
}
