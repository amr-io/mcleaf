resource "local_file" "ansible_inv" {
  filename = "${path.module}/../ansible/inventory/hosts.ini"
  content  = <<EOF
[webservers]
latex-vm ansible_host=${azurerm_public_ip.pubip.fqdn} ansible_user=${var.admin_username} ansible_ssh_private_key_file=~/.ssh/mcleaf_clone.pem ansible_python_interpreter=/usr/bin/python3
EOF
}
