variable "location" {
  type        = string
  description = "Azure region where all resources will be deployed"
  default     = "polandcentral"
}

variable "rg_name" {
  type        = string
  description = "Name of the Resource Group"
  default     = "latex-shared-clone"
}

variable "vm_size" {
  type        = string
  description = "Size / SKU of the Virtual Machine"
  default     = "Standard_B2ats_v2"
}

variable "dns_label" {
  type        = string
  description = "Globally unique DNS label for the public IP"
  default     = "mc-leaf-clone"
}

variable "disk_size_gb" {
  type        = number
  description = "OS Disk size in GB"
  default     = 64
}

variable "admin_username" {
  type        = string
  description = "Admin username for the VM"
  default     = "mc-leaf-clone"
}

variable "vm_name" {
  type        = string
  description = "Name of the Virtual Machine"
  default     = "latex-vm-clone"
}

variable "zone" {
  type = string
  description = "Availability Zone for the VM"
  default = "3"
}

variable "subscription_id" {
  type = string
  description = "Azure's Subscription ID where resources are provisioned"
  default = null
}