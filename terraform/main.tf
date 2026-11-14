resource "azurerm_resource_group" "rg" {
  name     = var.rg_name
  location = var.location
}

resource "azurerm_virtual_network" "vnet" {
  name                = "vnet-${var.location}-clone"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  address_space       = ["172.16.0.0/16"]
}

resource "azurerm_subnet" "snet" {
  name                 = "snet-${var.location}-clone"
  resource_group_name  = azurerm_resource_group.rg.name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = ["172.16.0.0/24"]
}

resource "azurerm_public_ip" "pubip" {
  name                    = "${var.vm_name}-ip"
  location                = azurerm_resource_group.rg.location
  resource_group_name     = azurerm_resource_group.rg.name
  allocation_method       = "Static"
  sku                     = "Standard"
  domain_name_label       = var.dns_label
  idle_timeout_in_minutes = 30
  zones                   = [var.zone]
}

# Firewall / NSG Rules
resource "azurerm_network_security_group" "nsg" {
  name                = "${var.vm_name}-nsg"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name

  security_rule {
    name                       = "SSH"
    priority                   = 340
    protocol                   = "Tcp"
    destination_port_range     = "22"
    direction                  = "Inbound"
    access                     = "Allow"
    source_address_prefix      = "*"
    source_port_range          = "*"
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "HTTPS"
    priority                   = 320
    protocol                   = "Tcp"
    destination_port_range     = "443"
    direction                  = "Inbound"
    access                     = "Allow"
    source_address_prefix      = "*"
    source_port_range          = "*"
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "HTTP"
    priority                   = 300
    protocol                   = "Tcp"
    destination_port_range     = "80"
    direction                  = "Inbound"
    access                     = "Allow"
    source_address_prefix      = "*"
    source_port_range          = "*"
    destination_address_prefix = "*"
  }
}

resource "azurerm_network_interface" "nic" {
  name                = "${var.vm_name}-nic"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name

  ip_configuration {
    name                          = "ipconfig1"
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.pubip.id
    subnet_id                     = azurerm_subnet.snet.id
  }
}

resource "azurerm_network_interface_security_group_association" "nic_nsg" {
  network_interface_id      = azurerm_network_interface.nic.id
  network_security_group_id = azurerm_network_security_group.nsg.id
}

resource "azurerm_linux_virtual_machine" "vm" {
  name                  = var.vm_name
  admin_username        = var.admin_username
  location              = azurerm_resource_group.rg.location
  network_interface_ids = [azurerm_network_interface.nic.id]
  resource_group_name   = azurerm_resource_group.rg.name
  size                  = var.vm_size
  zone                  = var.zone
  secure_boot_enabled   = true
  vtpm_enabled          = true

  identity {
    type = "SystemAssigned"
  }

  admin_ssh_key {
    public_key = tls_private_key.ssh.public_key_openssh
    username   = var.admin_username
  }

  os_disk {
    disk_size_gb         = var.disk_size_gb
    storage_account_type = "Premium_LRS"
    caching              = "ReadWrite"
  }

  additional_capabilities {
    ultra_ssd_enabled = true
  }

  source_image_reference {
    offer     = "ubuntu-24_04-lts"
    version   = "latest"
    publisher = "canonical"
    sku       = "server"
  }
}

resource "azurerm_managed_disk" "datadisk" {
  name                 = "${var.vm_name}_datadisk"
  location             = azurerm_resource_group.rg.location
  resource_group_name  = azurerm_resource_group.rg.name
  storage_account_type = "Premium_LRS"
  create_option        = "Empty"
  disk_size_gb         = var.disk_size_gb
  zone                 = var.zone
}

resource "azurerm_virtual_machine_data_disk_attachment" "datadisk" {
  managed_disk_id    = azurerm_managed_disk.datadisk.id
  virtual_machine_id = azurerm_linux_virtual_machine.vm.id
  lun                = 0
  caching            = "ReadWrite"
}
