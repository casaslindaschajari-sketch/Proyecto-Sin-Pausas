# Cómo descargar el paquete a tu computador

El archivo descargable está en la VM aquí:

```text
/home/Sabrina/Proyecto-Sin-Pausas-GitHub-Copy-Package.tar.gz
```

Nombre del archivo:

```text
Proyecto-Sin-Pausas-GitHub-Copy-Package.tar.gz
```

## Opción 1: Descargar desde VS Code Remote SSH

Si estás conectada a la VM con VS Code Remote SSH:

1. En VS Code, abre el explorador de archivos.
2. Busca el archivo:

   ```text
   /home/Sabrina/Proyecto-Sin-Pausas-GitHub-Copy-Package.tar.gz
   ```

3. Click derecho sobre el archivo.
4. Selecciona:

   ```text
   Download...
   ```

5. Elige una carpeta de tu computador.

Esta es la opción más simple.

---

## Opción 2: Descargar con `scp` desde tu computador

Ejecuta este comando en la terminal de tu computador, no dentro de la VM.

### macOS / Linux

```bash
scp -i /ruta/a/tu_clave.pem ubuntu@20.115.208.7:/home/Sabrina/Proyecto-Sin-Pausas-GitHub-Copy-Package.tar.gz .
```

Eso descargará el archivo a la carpeta actual de tu computador.

Ejemplo si quieres guardarlo en Descargas:

```bash
scp -i /ruta/a/tu_clave.pem ubuntu@20.115.208.7:/home/Sabrina/Proyecto-Sin-Pausas-GitHub-Copy-Package.tar.gz ~/Downloads/
```

### Windows PowerShell

```powershell
scp -i "C:\Ruta\Hacia\tu_clave.pem" ubuntu@20.115.208.7:/home/Sabrina/Proyecto-Sin-Pausas-GitHub-Copy-Package.tar.gz "$env:USERPROFILE\Downloads\"
```

Cambia:

```text
C:\Ruta\Hacia\tu_clave.pem
```

por la ruta real de tu llave `.pem`.

---

## Opción 3: Copiarlo a tu carpeta local usando VS Code terminal

Si tienes abierta la terminal local de tu computador, usa el mismo comando `scp`.

Importante: si la terminal dice algo como:

```text
ubuntu@Sabrina
```

o estás dentro de `/home/Sabrina`, entonces estás en la VM. El comando `scp` de descarga debe ejecutarse desde tu computador local.

---

## Opción 4: Servirlo temporalmente por navegador

Solo usa esta opción si entiendes el riesgo de exponer temporalmente un archivo por HTTP.

En la VM:

```bash
cd /home/Sabrina
python3 -m http.server 9000
```

Luego en tu navegador local abre:

```text
http://20.115.208.7:9000/Proyecto-Sin-Pausas-GitHub-Copy-Package.tar.gz
```

Después de descargarlo, detén el servidor con:

```text
Ctrl+C
```

Nota: esta opción requiere que el puerto 9000 esté abierto en Azure/Firewall. Si no funciona, usa VS Code Download o `scp`.

---

## Cómo descomprimirlo en tu computador

### macOS / Linux

```bash
tar -xzf Proyecto-Sin-Pausas-GitHub-Copy-Package.tar.gz
```

### Windows PowerShell

```powershell
tar -xzf .\Proyecto-Sin-Pausas-GitHub-Copy-Package.tar.gz
```

Después tendrás una carpeta:

```text
github_copy_package/
```

Dentro está:

```text
github_copy_package/project/
```

Esa carpeta `project/` es la que contiene la estructura lista para subir a GitHub.

---

## Contenido importante del paquete

```text
github_copy_package/
├── README_DESCARGA.md
├── COPY_MANIFEST_FOR_GITHUB.md
├── COPY_PASTE_TO_GITHUB.md
├── GITHUB_UPLOAD_INSTRUCTIONS_FOR_COPILOT.md
├── copy_chunks/
└── project/
    ├── README.md
    ├── .gitignore
    └── proyectos/
        └── sabrina_ai_lab/
            ├── README.md
            └── app.py