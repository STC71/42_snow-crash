# Level01 - Snow Crash

## Tipo de ejercicio

Análisis de credenciales expuestas en la configuración y en los argumentos de
un servicio `systemd`.

## Objetivo

Encontrar la credencial que permite conectarse al usuario `level02`.

La cuenta `flag01` está configurada con `/usr/sbin/nologin`. El acceso se
obtiene analizando el servicio que se ejecuta como ese usuario.

## 1. Identificar el entorno

Desde la sesión SSH de `level01`:

```bash
whoami
hostname
pwd
grep '^flag01:' /etc/passwd
```

Resultado relevante:

```text
level01
snowcrash
/home/level01
flag01:x:2001:2001::/home/flag01:/usr/sbin/nologin
```

La línea de `/etc/passwd` está formada por campos separados por `:`. El
segundo campo corresponde a la contraseña o a una referencia a ella:

```text
usuario:contraseña_o_referencia:UID:GID:comentario:directorio:shell
```

En esta entrada, la `x` significa que la contraseña no está escrita en
`/etc/passwd`. El sistema la buscaría en `/etc/shadow`, un archivo protegido
que no podemos leer como `level01`. Por tanto, la `x` no es la contraseña ni
la flag.

El último campo indica que el shell de `flag01` es `/usr/sbin/nologin`. Esto
bloquea el inicio de una sesión interactiva normal con ese usuario, por
ejemplo mediante `su` o SSH. Por eso no intentamos entrar como `flag01`:
debemos analizar el servicio que se ejecuta con sus privilegios y localizar
allí la credencial del siguiente nivel.

## 2. Revisar los archivos del nivel

La primera pista aparece al listar el directorio personal:

```bash
ls -la
cat README
```

El contenido del `README` es:

```text
Gargoyles never stop collecting.
```

La referencia a `gargoyles` indica qué componente buscar en el siguiente paso.

## 3. Localizar el componente propio de la OVA

Buscar archivos propiedad de `flag01` y binarios SUID muestra el programa
específico del nivel:

```bash
find / -xdev -user flag01 -ls 2>/dev/null
find / -xdev -type f -perm -4000 -ls 2>/dev/null
find / -xdev -type f -readable 2>/dev/null | grep -E 'level01|flag01|snowcrash'
```

La opción `-xdev` indica a `find` que permanezca en el mismo sistema de
archivos desde el que comenzó la búsqueda. Así evita atravesar otros sistemas
de archivos montados, como `/proc`, `/sys` o dispositivos externos. Esto hace
la búsqueda más rápida, reduce el ruido de resultados y evita recorrer zonas
que no forman parte del sistema de archivos principal. No concede permisos
adicionales ni oculta archivos del sistema principal.

Resumen de cada búsqueda:

- `find / -xdev -user flag01 -ls`: busca archivos propiedad de `flag01` y
	muestra sus detalles.
- `find / -xdev -type f -perm -4000 -ls`: busca archivos normales con el bit
	`setuid` activado y muestra sus permisos.
- `find / -xdev -type f -readable ... | grep -E '...'`: busca archivos
	legibles y filtra las rutas relacionadas con este nivel.

En las tres órdenes, `2>/dev/null` oculta los errores de permisos.

El archivo relevante es:

```text
/opt/snowcrash/level01/gargoyle
```

El `README` daba la pista `Gargoyles never stop collecting`. Como el archivo
es un daemon, el siguiente paso es buscar referencias a `gargoyle` en la
configuración de `systemd`:

```bash
grep -R -n 'gargoyle' /etc/systemd/system 2>/dev/null
systemctl list-units --type=service --all | grep -i gargoyle
systemctl status gargoyle.service --no-pager
```

`grep -R -n 'gargoyle' /etc/systemd/system` busca recursivamente (`-R`) la
palabra `gargoyle` en las unidades de `systemd` definidas por el administrador,
mostrando el archivo y el número de línea (`-n`). Con `2>/dev/null` se ocultan
los errores de permisos.

`systemctl list-units --type=service --all` lista todos los servicios que
conoce `systemd`, incluidos los inactivos o fallidos (`--all`). El filtro
`grep -i gargoyle` conserva solo las líneas que contienen `gargoyle`, sin
distinguir mayúsculas de minúsculas.

`systemctl status gargoyle.service --no-pager` muestra el estado, el usuario,
el PID y los últimos registros del servicio. `--no-pager` imprime todo
directamente, sin abrir `less`.

Estas comprobaciones permiten confirmar que `/opt/snowcrash/level01/gargoyle`
no es solo un archivo, sino el proceso gestionado por el servicio `gargoyle`.

Después se inspecciona su definición:

```bash
cat /etc/systemd/system/gargoyle.service
```

Su contenido relevante es:

```ini
[Service]
Type=forking
User=flag01
ExecStart=/opt/snowcrash/level01/gargoyle kooda7puivaav1idi4f57q8iq0
Restart=always
RestartSec=5
```

## 4. Obtener la credencial del siguiente nivel

El proceso confirma que el servicio sigue ejecutándose con este argumento:

```bash
ps aux | grep '[g]argoyle'
```

Resultado:

```text
flag01 ... /opt/snowcrash/level01/gargoyle kooda7puivaav1idi4f57q8iq0
```

El valor encontrado es:

```text
kooda7puivaav1idi4f57q8iq0
```

El argumento no se utiliza para iniciar sesión como `flag01`. En este nivel,
ese valor es directamente la credencial SSH para acceder a `level02`.

## 5. Conectarse a level02

Si la sesión actual sigue abierta, se sale de ella:

```bash
exit
```

Después, desde la misma terminal del equipo anfitrión desde la que se abrió
SSH, se inicia una nueva conexión:

```bash
ssh level02@localhost -p 2424
```

Cuando SSH solicite la contraseña, introducir:

```text
kooda7puivaav1idi4f57q8iq0
```

La conexión correcta muestra:

```text
level02@snowcrash:~$
```

## Conclusión

La solución consiste en leer la configuración del servicio `gargoyle`,
observar el argumento del proceso que se ejecuta como
`flag01` y reutilizar ese valor como credencial de `level02`.
