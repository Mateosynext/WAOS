# Bot Studio feature

La implementación real de Bot Studio vive aquí. La capa de rutas queda como shell mínimo.

- `domain/`: tipos, contratos de wizard, flow config, guards y recovery puro.
- `services/`: cliente API, builders de payload y carga reactiva.
- `server/`: loaders server-side para rutas.
- `ui/`: componentes visuales reutilizables del wizard.
- `context/`, `flow/`, `create/`, `reconfigure/`, `review/`: runtime y pantallas por flujo.
