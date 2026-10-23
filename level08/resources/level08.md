# Level08 - Snow Crash

## Tipo de ejercicio

Explotación de un protocolo binario mediante un fallo de control de estados
en un daemon accesible por socket Unix.

## Objetivo

Encontrar la credencial que permite conectarse al usuario `level09`.

El daemon `blacksun` expone un protocolo de  sesiones `HELLO -> AUTH -> ADMIN`.

## 1. Localizar el daemon

Desde la sesión SSH de `level08`:

```bash
whoami
hostname
pwd
ls -la
cat README
find /home/level08 -maxdepth 2 -ls
```

`find /home/level08 -maxdepth 2 -ls` hace una primera inspección del
directorio personal: muestra los archivos y directorios que hay hasta dos
niveles de profundidad, junto con sus permisos y propietarios. Sirve para
comprobar si hay alguna pista local antes de buscar el componente del nivel en
`/opt`.

El componente del nivel se localiza así:

```bash
find /opt/snowcrash/level08 -maxdepth 2 -ls 2>/dev/null
find / -xdev -user flag08 -ls 2>/dev/null
```

El primer `find` inspecciona directamente los archivos del nivel hasta dos
niveles de profundidad. El segundo busca en el sistema de archivos principal
(`-xdev`) todos los archivos propiedad de `flag08`; `2>/dev/null` oculta los
mensajes de permisos denegados que aparecen al recorrer otras carpetas.

Los archivos relevantes son:

```text
/opt/snowcrash/level08/blacksun
/opt/snowcrash/level08/blacksun.c
```

`blacksun` es el ejecutable del daemon y `blacksun.c` es su código fuente.
Comprobamos los permisos y el tipo del ejecutable:

```bash
ls -l /opt/snowcrash/level08/blacksun
file /opt/snowcrash/level08/blacksun
```

`ls -l` muestra los permisos, el propietario y el grupo del ejecutable.
`file` identifica el formato del archivo sin ejecutarlo.

En la salida de `ls -l`, la primera columna representa los permisos; el
propietario y el grupo aparecen después del número de enlaces. Si aparece una
`s` en los permisos del propietario, el bit `setuid` está activo y el daemon
se ejecuta con los privilegios de su propietario, `flag08`. La salida de
`file` confirma que `blacksun` es un ejecutable binario, normalmente en formato
ELF, y no un script de texto.

```text
-rwxr-x--- 1 flag08 blacksun 17392 Jun  9 19:03 /opt/snowcrash/level08/blacksun
```

```text
/opt/snowcrash/level08/blacksun: ELF 64-bit LSB pie executable, x86-64, version 1 (SYSV), dynamically linked, interpreter /lib64/ld-linux-x86-64.so.2, BuildID[sha1]=bae56d7953072d3bb116589813a7dabf18e623c8, for GNU/Linux 3.2.0, not stripped
```

## 2. Analizar el protocolo

Para leer el código fuente del daemon sin ejecutarlo:

```bash
sed -n '1,320p' /opt/snowcrash/level08/blacksun.c
```

`sed -n '1,320p'` muestra las primeras 320 líneas de `blacksun.c`, lo que
permite analizar cómo funciona el protocolo antes de preparar el cliente.

La fuente revela las constantes principales:

```c
#define SOCK_PATH       "/run/blacksun/blacksun.sock"
#define FLAG_PATH       "/home/flag08/.flag"
#define PROTOCOL_VER    1
#define MAGIC_HELLO     0xDEADU
#define AUTH_KEY_PATH   "/etc/blacksun/auth.key"
#define AUTH_PASS_LEN   32
#define MAX_PAYLOAD     4096
#define READ_TIMEOUT_S  30
...
#define CMD_HELLO       0
#define CMD_AUTH        1
#define CMD_ADMIN       2
#define CMD_QUIT        3
```

Para entender el formato de los mensajes, hay que localizar en la fuente el
código que recibe y valida cada paquete:

```bash
grep -nE 'read|recv|header|version|state|cmd|checksum|acc' \
	/opt/snowcrash/level08/blacksun.c
```

`grep` busca texto dentro de `blacksun.c`; `-n` muestra el número de línea y
`-E` permite buscar varias palabras alternativas separadas por `|`. En la
salida buscamos las llamadas `read` o `recv` para localizar dónde se recibe la
cabecera y comprobar cuántos bytes se leen. También revisamos las líneas con
`version`, `state` y `cmd` para ver cómo se separan los campos del primer byte,
y las líneas con `checksum` o `acc` para localizar cómo se calcula y valida el
checksum del payload.

La salida de `grep` permite comprobarlo directamente:

- Las líneas 53–55 muestran que el primer byte se divide en `version` (3
	bits), `state` (2 bits) y `cmd` (3 bits). Esos campos suman 8 bits, es decir,
	un byte; no representan por sí solos toda la cabecera. La declaración de
	`raw[8]` es la que indica que la cabecera completa ocupa 8 bytes, y el campo
	`checksum` aparece en la misma estructura.

```c
49:/* ── binary protocol header ───────────────────────────────────── */
51:    uint8_t raw[8];
53:        uint8_t  version : 3;
54:        uint8_t  state   : 2;
55:        uint8_t  cmd     : 3;
57:        uint16_t checksum;        /* simple XOR-16 over payload      */
59:} msg_header_t;
```

- Las líneas 183–184 muestran `read_exact(cfd, hdr.raw, sizeof(hdr.raw))`.
  Como `hdr.raw` está declarado como un array de 8 bytes, `sizeof(hdr.raw)`
  vale 8 y esa llamada lee la cabecera completa antes del payload.

```c
183:        /* read fixed-size header */
184:        if (read_exact(cfd, hdr.raw, sizeof(hdr.raw)) < 0)
```

- Las líneas 208–209 comparan el checksum recibido (`got`) con el checksum
	calculado (`expected`).

```c
208:            uint16_t got      = hdr.fields.checksum;
209:            uint16_t expected = compute_checksum(payload, plen);
```

Por eso sabemos qué formato tiene el mensaje: primero se leen esos 8 bytes,
después el payload, y el daemon verifica que su checksum calculado coincida
con el valor incluido en la cabecera.

En otra parte de la fuente aparece el cálculo del checksum del payload:

```c
90:compute_checksum(const uint8_t * restrict buf, uint32_t len)
92:    uint16_t acc = 0;
94:        acc ^= (uint16_t)buf[i] ^ (uint16_t)(i & 0xFFu);
```

`acc` acumula un valor de comprobación. En cada byte del payload, el operador
`^` combina el acumulado con el byte actual y con su posición. El daemon usa
el resultado para comprobar que los datos recibidos tienen el checksum
esperado; no es una operación que lea la flag ni una parte del estado de la
sesión. Aunque un comentario cercano en la fuente lo llama “Fletcher-16
variant”, la fórmula mostrada aquí es un acumulador XOR con el índice, no el
algoritmo Fletcher-16 estándar.

La autenticación exige una clave de 32 bytes, pero no necesitamos conocerla
debido al fallo de validación de estados.

## 3. Identificar el fallo lógico

Buscamos solo las líneas necesarias para seguir el flujo y revisar la
comprobación de `CMD_ADMIN`:

```bash
grep -nE 'STATE_(INIT|AUTH|ADMIN)|CHECK_STATE|ctx\.state = STATE_(AUTH|ADMIN)|cmd == CMD_ADMIN' \
	/opt/snowcrash/level08/blacksun.c
```

`grep` busca esas expresiones en `blacksun.c`; `-n` añade el número de línea
y `-E` permite combinar alternativas con `|`. Buscamos las definiciones de
los estados, los lugares donde cambia el estado, la macro `CHECK_STATE` y la
rama que atiende `CMD_ADMIN`. Así podemos seguir qué estado tiene la conexión
en cada paso y qué comprobación se aplica al comando administrativo.

La salida relevante es:

```text
38:    STATE_INIT  = 0,
39:    STATE_AUTH  = 1,
40:    STATE_ADMIN = 2,
83:#define CHECK_STATE(ctx, required)                                      \
84:    ( ((required) == STATE_ADMIN)                                       \
85:        ? ((ctx)->state >= STATE_AUTH)                                  \
86:        : ((ctx)->state == (required)) )
236:            ctx.state = STATE_AUTH;
251:                ctx.state = STATE_ADMIN;
259:        else if (cmd == CMD_ADMIN) {
260:            if (UNLIKELY(!CHECK_STATE(&ctx, STATE_ADMIN))) {
```

Antes de seguir el flujo, miramos qué hace la macro `CHECK_STATE` en sí misma
(líneas 83-86). Es un operador ternario con una condición de entrada:

```text
CHECK_STATE(ctx, required) =
    si required == STATE_ADMIN:
        devuelve (ctx->state >= STATE_AUTH)   // línea 85
    si no:
        devuelve (ctx->state == required)     // línea 86
```

Es decir, la macro no compara siempre igualdad de estados. Cuando a quien la
llama le interesa proteger una acción con `required = STATE_ADMIN`, la macro
decide ignorar `required` y, en su lugar, comprueba `ctx->state >=
STATE_AUTH`. Como `STATE_AUTH` vale `1` y `STATE_ADMIN` vale `2` (línea 38-40),
esa condición es cierta tanto en `STATE_AUTH` como en `STATE_ADMIN`: basta con
haber superado `STATE_INIT` para que la macro devuelva "verdadero", aunque se
le haya pedido comprobar el nivel más alto. Esto parece pensado para
simplificar el caso `STATE_ADMIN` (todo lo que sea igual o superior a `AUTH`
vale), pero en la práctica anula la protección: nunca exige llegar realmente a
`STATE_ADMIN`.

Con esto en mente, seguimos el flujo de la conexión:

1. `HELLO` deja la conexión en `STATE_AUTH` (línea 236). Un `AUTH` válido la
	cambiaría a `STATE_ADMIN` (línea 251), pero no es obligatorio pasar por
	ahí para seguir enviando comandos.
2. La rama que atiende `CMD_ADMIN` (línea 259) llama a
	`CHECK_STATE(&ctx, STATE_ADMIN)` (línea 260): sustituye `required` por
	`STATE_ADMIN`, así que entra en la primera rama de la macro explicada
	arriba.
3. Esa rama evalúa `ctx->state >= STATE_AUTH`, no `ctx->state ==
	STATE_ADMIN`. Como el estado tras `HELLO` ya es `STATE_AUTH` (que cumple
	`>= STATE_AUTH`), la comprobación se satisface sin haber ejecutado nunca
	`AUTH`. El resultado es que `CMD_ADMIN` queda accesible solo con `HELLO`,
	sin necesidad de conocer la clave de 32 bytes.

El daemon está activo:

```bash
ps aux | grep '[b]lacksun'
systemctl status blacksun.service --no-pager
```

`ps aux` muestra los procesos en ejecución. El patrón `'[b]lacksun'` encuentra
el daemon sin que el propio comando `grep` aparezca en los resultados.
`systemctl status` muestra el estado del servicio y sus errores recientes.

Y el socket es accesible para el grupo `blacksun`:

```bash
ls -ld /run/blacksun
ls -l /run/blacksun/blacksun.sock
id
```

`ls -ld` muestra los permisos del directorio que contiene el socket; el permiso
`x` permite atravesarlo.
`ls -l` confirma que `blacksun.sock` es un socket Unix y muestra sus permisos,
propietario y grupo.
`id` confirma que `level08` pertenece al grupo `blacksun`; el permiso de escritura `w` del grupo sobre el socket le permite conectarse al daemon.

Resultado relevante:

```text
srw-rw---- 1 flag08 blacksun ... /run/blacksun/blacksun.sock
groups=...,4007(blacksun)
```

La `s` inicial indica que `blacksun.sock` es un socket Unix: un punto de
comunicación local, parecido a un archivo por su ruta, pero usado para que un
cliente intercambie datos con el daemon. Aquí el cliente se conecta a este
socket para enviarle los mensajes del protocolo.

## 4. Usar el cliente del protocolo

El cliente [blacksun_client.py](blacksun_client.py) se creó para esta
resolución; no forma parte de la OVA. Se conecta al socket Unix, calcula el
checksum requerido y envía `HELLO` seguido de `ADMIN` sin enviar `AUTH`, para
comprobar y aprovechar el fallo de estados descrito antes. No modifica la OVA.

Si estás dentro de la sesión SSH de `level08`, vuelve primero al terminal del
equipo anfitrión:

```bash
exit
```

Desde la raíz del repositorio en el anfitrión, copia el cliente a `/tmp` de la
OVA:

```bash
scp -P 2424 level08/resources/blacksun_client.py \
	level08@localhost:/tmp/blacksun_client.py
```

`scp` pide la contraseña de `level08` para autenticar la transferencia. Al
terminar, vuelve al prompt del anfitrión; no abre una sesión SSH interactiva.
Después hay que conectarse a la OVA por SSH, autenticándose de nuevo:

```bash
ssh level08@localhost -p 2424
```

El archivo ya quedó copiado en `/tmp`; no hay que volver a escribirlo ni
transferirlo. Dentro de `level08@snowcrash`, ejecútalo así:

```bash
python3 /tmp/blacksun_client.py
```

El cliente realiza estas operaciones:

1. Conecta a `/run/blacksun/blacksun.sock`.
2. Envía `HELLO` con versión `1` y magic `0xDEAD`.
3. Recibe `HELLO OK` y la sesión pasa a `STATE_AUTH`.
4. Envía `CMD_ADMIN` sin enviar `CMD_AUTH`.
5. El fallo `state >= STATE_AUTH` permite la operación administrativa.
6. El daemon lee `/home/flag08/.flag` como `flag08` y devuelve su contenido.

Resultado obtenido:

```text
HELLO OK
ACCESS GRANTED
FLAG=s5cAhoAfNT9GrgqykhZavyBg9
```

## 5. Conectarse a level09

Desde el equipo anfitrión:

```bash
exit
ssh level09@localhost -p 2424
```

Cuando SSH solicite la contraseña, introducir:

```text
s5cAhoAfNT9GrgqykhZavyBg9
```

## Conclusión

No se modificó ningún archivo de la OVA. La solución aprovecha únicamente el
socket Unix ya expuesto por el daemon y un error en la comprobación de estados:
`ADMIN` se acepta después de `HELLO`, aunque nunca se haya completado la
autenticación. El daemon devuelve entonces la credencial de `level09`.
