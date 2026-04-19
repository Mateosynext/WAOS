# WAOS Vertical Marketplace

## Qué agrega

Esta capa convierte verticales, playbooks, packs de onboarding, prompts y automatizaciones en **paquetes instalables** con:

- versión y release notes
- compatibilidad y dependencias
- checklist de despliegue
- manifest instalable
- instalación por organización / bot
- upgrades controlados
- metadata de monetización

## Componentes

- `vertical_marketplace_packages`
- `vertical_marketplace_package_versions`
- `vertical_marketplace_installs`
- `vertical_marketplace_install_items`
- `vertical_marketplace_upgrade_runs`

## Flujo

1. Publicar paquete vía `/api/v1/vertical-marketplace/packages`
2. Resolver paquete y versión
3. Instalar sobre organización / bot
4. Aplicar manifest sobre runtime existente:
   - bot behavior
   - templates
   - knowledge docs
   - catálogo
   - integraciones
   - playbooks
   - automation rules
5. Guardar trazabilidad de instalación
6. Detectar nuevas versiones y ejecutar upgrade controlado

## Resultado

Cada vertical exitosa deja de ser sólo conocimiento interno y pasa a ser un **activo replicable, instalable y actualizable** dentro del mismo runtime.
