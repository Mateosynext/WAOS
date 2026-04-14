# WAOS Release Reproducibility

## Objetivo
Generar exactamente los tres perfiles de release de WAOS desde un checkout limpio:
- source
- runtime
- audit docs

## Precondiciones
- Python 3.12+
- Dependencias de backend disponibles para smoke de artifact (`pip install -r backend/requirements.txt`)
- Node solo es necesario para validaciones frontend fuera del build de artifact

## Procedimiento
1. Extraer o clonar el source actualizado en un directorio cuyo nombre coincida con la versión, por ejemplo:
   - `waos_source_0.16.7-real-browser-e2e`
2. Entrar a la raíz del proyecto.
3. Ejecutar:

```bash
python scripts/release_build.py --output-dir dist
```

## Artefactos esperados
- `dist/waos_runtime_<version>-clean-release.zip`
- `dist/waos_audit_docs_<version>-clean-release.zip`
- `dist/waos_source_<version>-clean-release.zip`
- `dist/RELEASE_MANIFEST.json`
- `dist/RELEASE_MANIFEST.sha256`
- `dist/RELEASE_CHECKSUMS.sha256`
- `dist/reports/*.json`

## Validación reproducible
Ejecutar:

```bash
bash scripts/validate_release_in_ci.sh
```

Esto fuerza:
- build de los tres artefactos
- gate del runtime
- scan duro de secretos/placeholders/local domains sobre el runtime
- generación de SBOM e inventario de licencias
- smoke real del runtime descomprimido
- verificación de hashes contra manifest y checksums

## Nota de naming
Si la carpeta raíz extraída tiene una versión vieja, `scripts/release_build.py` falla. Esto evita publicar artefactos con nombres visibles inconsistentes.
