# Level02 - Snow Crash

## Tipo de ejercicio

Fuga de credenciales mediante un archivo temporal persistente y legible que
deja un servicio después de procesar una entrega.

## Objetivo

Encontrar la credencial que permite conectarse al usuario `level03`.

El nivel utiliza el servicio `kourier` y un archivo temporal de entrega.

## 1. Inspeccionar el nivel

Desde la sesión SSH de `level02`:

```bash
whoami
hostname
pwd
ls -la
cat README
```

Estos comandos confirman la identidad y la ubicación de la sesión. `whoami`
muestra el usuario actual, `hostname` el nombre de la máquina, `pwd` el
directorio de trabajo y `ls -la` todos los archivos, incluidos los ocultos.
`cat README` lee la pista proporcionada por el nivel.

El README contiene la pista:

```text
A Kourier never loses a package. Even after delivery.
```

El directorio personal no contiene archivos adicionales. La palabra
`Kourier` sugiere que debemos buscar un componente con ese nombre, pero todavía
no demuestra que sea un servicio. Primero se localiza el ejecutable:

```bash
find /opt/snowcrash/level02 -maxdepth 2 -ls 2>/dev/null
```

La orden examina `/opt/snowcrash/level02`, que es el directorio donde se
instalan los componentes de este nivel. `-maxdepth 2` limita la búsqueda al
directorio indicado y a un nivel de subdirectorios, evitando recorrer zonas
innecesarias. `-ls` muestra cada entrada con sus permisos, propietario, tamaño
y ruta. `2>/dev/null` oculta los errores de permisos que puedan aparecer.

Después se comprueba si está ejecutándose y si existe una unidad `systemd`:

```bash
ps aux | grep '[k]ourier'
systemctl list-units --type=service --all | grep -i kourier
systemctl status kourier.service --no-pager
```

`ps aux` lista los procesos activos. Si se escribiera:

```bash
ps aux | grep kourier
```

el propio proceso `grep kourier` también aparecería, porque contiene la palabra
que estamos buscando. Para evitarlo se escribe `[k]ourier`: en una expresión
regular, `[k]` coincide con la letra `k`, pero la orden del proceso contiene
literalmente los corchetes y no la cadena `kourier`; por eso el propio `grep`
no coincide consigo mismo.

`systemctl list-units` busca unidades de servicio conocidas por `systemd`, y
`systemctl status` muestra el estado, el usuario y el proceso asociado a
`kourier`. Estas comprobaciones permiten confirmar que
`/opt/snowcrash/level02/kourier` no es solo un archivo, sino el proceso
gestionado por el servicio `kourier`.

## 2. Buscar archivos relacionados

Como el README habla de paquetes y entregas, se buscan archivos cuyos nombres
estén relacionados con esos conceptos:

```bash
find /tmp /var/tmp /var/spool /opt/snowcrash -xdev \
	\( -iname '*kourier*' -o -iname '*package*' -o -iname '*delivery*' \) \
	-ls 2>/dev/null
```

La orden busca en las ubicaciones donde suelen quedar archivos temporales o
datos de servicios. `-xdev` evita atravesar otros sistemas de archivos
montados, `-iname` busca nombres sin distinguir mayúsculas y minúsculas, y
`-o` combina las tres alternativas de nombre. `-ls` muestra los permisos, el
propietario y la ruta. Finalmente, `2>/dev/null` oculta los errores de acceso.

El resultado reveló un archivo temporal legible:

```text
/tmp/kourier_delivery.tmp
```

Sus permisos y propietario eran:

```text
-rw-r--r-- 1 flag02 flag02 27 ... /tmp/kourier_delivery.tmp
```

En `-rw-r--r--`, los permisos se dividen en tres grupos de tres caracteres:

```text
-   rw-   r--   r--
	|     |     |
	|     |     └── otros usuarios: lectura
	|     └──────── grupo: lectura
	└────────────── propietario: lectura y escritura
```

El propietario es `flag02` y el grupo también es `flag02`. Como `level02` no
es ni el propietario ni miembro de ese grupo, se aplican los permisos del
último bloque, el de otros usuarios (`r--`). Por eso `level02` puede leer el
archivo aunque pertenezca a `flag02`, pero no puede modificarlo. Además,
`/tmp` permite acceder a sus entradas, por lo que la ruta completa también es
recorrible. El tamaño de 27 bytes indica que contiene una cadena corta,
compatible con una credencial.

El nombre coincide con la pista del README: Kourier conserva información de
la entrega incluso después de haberla completado.

## 3. Inspeccionar el binario Kourier

Ahora se identifica el ejecutable de Kourier y se comprueba que existe un
proceso activo que lo está ejecutando. El archivo es el programa almacenado en
disco; el proceso es la instancia que está funcionando en ese momento:

```bash
ls -la /opt/snowcrash/level02
ls -l /opt/snowcrash/level02/kourier
file /opt/snowcrash/level02/kourier
ps aux | grep '[k]ourier'
```

`ls -la` muestra el contenido del directorio y sus permisos. `ls -l` muestra
los permisos y el propietario del ejecutable. `file` identifica el formato del
archivo sin ejecutarlo. La segunda comprobación de `ps` confirma el proceso
que corresponde al ejecutable.

Resultados relevantes:

```text
/opt/snowcrash/level02/kourier: ELF 64-bit LSB pie executable, x86-64
flag02 ... /opt/snowcrash/level02/kourier
```

La salida de `ps` muestra que el proceso `kourier` se ejecuta con el usuario
`flag02`. Esto es importante porque ese usuario es el propietario del archivo
temporal que encontramos antes. A continuación se inspeccionan las cadenas
legibles del propio binario para descubrir qué rutas utiliza:

```bash
strings -a /opt/snowcrash/level02/kourier
```

`strings -a` extrae las cadenas de texto legibles del binario. No ejecuta el
programa ni muestra su código completo; solo recupera textos almacenados dentro
del archivo. Si aparecen rutas como `/tmp/kourier_delivery.tmp`,
`/etc/kourier/routing.conf` o `/var/run/kourier_manifest.db`, podemos
comprobarlas una por una para ver cuáles son accesibles.

Entre ellas aparecen:

```text
/tmp/kourier_delivery.tmp
/etc/kourier/routing.conf
/var/run/kourier_manifest.db
```

Los dos últimos archivos no aportaron información legible para `level02`:

```bash
cat /etc/kourier/routing.conf 2>/dev/null
cat /var/run/kourier_manifest.db 2>/dev/null
```

`cat` intenta leer ambos archivos y `2>/dev/null` oculta los posibles errores
de permisos. Si no producen salida, no contienen una credencial legible para
el usuario actual. El archivo temporal de `/tmp` sí es accesible y es la pista
relevante.

## 4. Leer el paquete entregado

La pista indicaba que el paquete no desaparecía después de la entrega. Al leer
el archivo temporal:

```bash
cat /tmp/kourier_delivery.tmp
```

`cat` escribe el contenido del archivo en la salida de la terminal. No se
ejecuta el contenido ni se modifica el archivo: solo se lee la información que
Kourier dejó después de procesar la entrega.

se obtuvo:

```text
qi0mauch9ahksha8b6dfe3p0kq
```

Este valor es la credencial del siguiente nivel.

## 5. Conectarse a level03

Si la sesión actual sigue abierta, se sale de ella:

```bash
exit
```

Después, desde la misma terminal del equipo anfitrión desde la que se abrió
SSH, se inicia una nueva conexión:

```bash
ssh level03@localhost -p 2424
```

`exit` cierra la sesión SSH actual. Después, el comando `ssh` se ejecuta en
la terminal del equipo anfitrión, no en la consola de la OVA. `level03` es el
usuario del siguiente nivel, `localhost` apunta al equipo anfitrión y `-p 2424`
usa el puerto reenviado hacia la OVA.

Cuando SSH solicite la contraseña, introducir:

```text
qi0mauch9ahksha8b6dfe3p0kq
```

La conexión correcta muestra un prompt similar a:

```text
level03@snowcrash:~$
```

## Conclusión

La pista de Kourier conduce al proceso
`/opt/snowcrash/level02/kourier` y al archivo temporal
`/tmp/kourier_delivery.tmp`. El archivo permanece después de la entrega y es
legible, por lo que contiene directamente la credencial de `level03`:

```text
qi0mauch9ahksha8b6dfe3p0kq
```
