data "azurerm_client_config" "current" {}

# 1. CREATE the Cloudflare Worker Application in Azure AD (Entra ID)
resource "azuread_application" "cf_worker" {
  display_name = "cloudflare-${var.vm_name}-wake-worker"
}

# 2. CREATE the Service Principal for that Application
resource "azuread_service_principal" "cf_worker" {
  client_id = azuread_application.cf_worker.client_id
}

# 3. GENERATE a fresh, secure Client Secret password
resource "azuread_service_principal_password" "cf_worker_secret" {
  service_principal_id = azuread_service_principal.cf_worker.id
}

# 4. ASSIGN the Cloudflare Worker permission to start this VM
resource "azurerm_role_assignment" "cf_wake" {
  principal_id         = azuread_service_principal.cf_worker.object_id
  role_definition_name = "Virtual Machine Contributor"
  scope                = azurerm_linux_virtual_machine.vm.id
}

# 5. ASSIGN the VM's Managed Identity permission to auto-deallocate itself
resource "azurerm_role_assignment" "identity" {
  description          = "Access Permission for auto deallocate."
  principal_id         = azurerm_linux_virtual_machine.vm.identity[0].principal_id
  role_definition_name = "Virtual Machine Contributor"
  scope                = azurerm_linux_virtual_machine.vm.id
}
