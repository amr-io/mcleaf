output "public_ip_address" {
  description = "The public IP address of the LaTeX VM"
  value       = azurerm_public_ip.pubip.ip_address
}

output "public_dns_fqdn" {
  description = "The fully-qualified domain name (DNS) of the VM"
  value       = azurerm_public_ip.pubip.fqdn
}

output "vm_id" {
  description = "The Azure Resource ID of the VM"
  value       = azurerm_linux_virtual_machine.vm.id
}

output "vm_principal_id" {
  description = "The Principal ID of the VM's Managed Identity"
  value       = azurerm_linux_virtual_machine.vm.identity[0].principal_id
}

output "ssh_command" {
  description = "Command to SSH directly into the VM"
  value       = "ssh -i id_rsa_${terraform.workspace}.pem ${var.admin_username}@${azurerm_public_ip.pubip.ip_address}"
}

output "ssh_private_key_pem" {
  description = "The generated private SSH key (Sensitive)"
  value       = tls_private_key.ssh.private_key_pem
  sensitive   = true
}

# Credentials for the Cloudflare Wakeup Worker
output "subscription_id" {
  description = "Subscription ID for Cloudflare Worker"
  value       = data.azurerm_client_config.current.subscription_id
}

output "tenant_id" {
  description = "Tenant ID for Cloudflare Worker"
  value       = data.azurerm_client_config.current.tenant_id
}

output "cf_worker_client_id" {
  description = "Application (Client) ID for Cloudflare Worker"
  value       = azuread_application.cf_worker.client_id
}

output "cf_worker_client_secret" {
  description = "Client Secret password for Cloudflare Worker"
  value       = azuread_service_principal_password.cf_worker_secret.value
  sensitive   = true
}
