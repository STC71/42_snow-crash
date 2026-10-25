# SnowCrash

<br><br>

<img width="1536" height="1024" alt="snowcrash42" src="https://github.com/user-attachments/assets/b37a6ea2-af3a-4c33-80c3-55ff9507dd42" />

<br><br>

## Descripción

SnowCrash es un proyecto de tipo CTF (Capture The Flag) centrado en la seguridad informática. Se proporciona una OVA de Linux (x64, Ubuntu) y el objetivo es encontrar las distintas banderas.

El repositorio actual contiene 11 niveles, del `level00` al `level10`:

- Los niveles `level00` a `level10` son obligatorios.
- `level10` es el boss fight final del recorrido mandatory.
- La parte bonus está formada por `bonus01` a `bonus05` y se investiga después
	del mandatory.

El proyecto permite estudiar problemas de seguridad de diferentes tipos, como:

- Código mal escrito o sin protección.
- Comunicaciones de red sin protección.
- Trabajos automatizados mal gestionados en las máquinas.

La tabla de credenciales recuperadas está disponible en
[flags.md](flags.md).

## Encontrar y validar las banderas

En el sistema hay dos tipos principales de cuentas de usuario:

- `levelXX`: cuenta correspondiente a los niveles mandatory. `XX` representa el
	número del nivel, por ejemplo `level00`, `level01` o `level10`.
- `flagXX`: cuenta asociada a cada nivel mandatory, por ejemplo `flag00`,
	`flag01` o `flag10`. En la parte bonus, las cuentas usan nombres como
	`flagbonus01`.

El objetivo de cada nivel mandatory es obtener la flag protegida del usuario
asociado. En esta OVA, cada flag permite conectarse por SSH al siguiente nivel;
la de `level10` cierra el recorrido mandatory y no tiene un nivel mandatory
siguiente. El método cambia en cada ejercicio: puede ser un binario `setuid`,
un servicio, una plantilla, un protocolo o un sandbox.

Las guías de `resources/` documentan el recorrido real de cada nivel. Los
archivos `flag` de los niveles mandatory contienen las credenciales
recuperadas; los bonus siguen pendientes de resolución y sus flags se
completarán cuando se obtengan.

## Recursos

Los recursos del proyecto incluyen:

- El tema en inglés y en francés.
- La imagen OVA de Linux.
- El vídeo del proyecto disponible en Intra y en formato RAW, sin necesidad de iniciar sesión.

## Comenzar el proyecto

Para iniciar el proyecto, hay que abrir la OVA en una máquina virtual, como VMware o VirtualBox.

Si se utiliza VirtualBox, no es necesario configurar la red en modo puente, con el modo NAT por defecto es suficiente.

Tras haber importado la OVA, la dejamos arrancada en su pantalla de login. No
es necesario iniciar sesión en la consola de la máquina virtual: todos los
niveles se resuelven desde el equipo anfitrión mediante SSH.

En nuestro caso, observamos que la IP está configurada:

```text
enp0s3: 10.0.2.15
```
<br><br>

<img width="864" height="620" alt="image0" src="https://github.com/user-attachments/assets/35958d45-bae7-4822-9f2a-810313ff377f" />

<br><br>

Seguidamente en la sección Display / Screen, configuramos la Memoria de Video en 16 MB

<br><br>

<img width="1228" height="887" alt="image1" src="https://github.com/user-attachments/assets/dbdad8a1-8bf2-4fc6-be78-55a8e8701b7c" />

<br><br>

Ahora accedemos en la configuración de la OVA en la zona Red / Adaptador 1

<br><br>

<img width="1766" height="1326" alt="image2" src="https://github.com/user-attachments/assets/c34457e4-1019-4972-98e1-6a5e665d7dd3" />

<br><br>

hacemos click en Reenvío de puertos y dejamos esta configuración:

<br><br>

<img width="1596" height="1076" alt="image3" src="https://github.com/user-attachments/assets/67ec0fa3-3506-4bc2-a43d-83d523bd1d1f" />

<br><br>

Notar que hemos configurado en el Host Anfitrión el puerto 2424, ya que el 4242 (recomendado) en 42 Málaga se haya ocupado por otros servicios.

Según el subject del proyecto Snow-Crash de 42, se debe acceder a la máquina mediante SSH usando el puerto `4242` (nosotros gestionaremos el 2424). 

Ahora nos conectaremos vía SSH desde una terminal del equipo anfitrión con:

```bash
ssh level00@127.0.0.1 -p 2424

o

ssh level00@localhost -p 2424

```

<img width="1030" height="710" alt="image4" src="https://github.com/user-attachments/assets/7b918ef7-3999-4c6e-88c0-ad96945002fd" />




<br><br>
<br><br>
<br><br>


## Estructura del proyecto

El repositorio contiene un directorio para cada nivel, con el formato
`levelXX`. En esta versión del proyecto están disponibles los niveles
`level00` a `level10`, además de las carpetas reservadas para los bonus:

```text
level00/
level01/
level02/
level03/
level04/
level05/
level06/
level07/
level08/
level09/
level10/
bonus01/
bonus02/
bonus03/
bonus04/
bonus05/
```

Cada nivel mandatory y cada bonus contiene:

```text
levelXX/ o bonusNN/
├── flag
└── resources/
```

El archivo `flag` contiene la credencial o el token obtenido al resolver el
nivel. La explicación del proceso no se guarda dentro de `flag`, sino en el
Markdown correspondiente de `resources`, cuando esa documentación ya está
disponible:

```text
level00/resources/level00.md
level01/resources/level01.md
level02/resources/level02.md
level03/resources/level03.md
level04/resources/level04.md
level05/resources/level05.md
level06/resources/level06.md
level07/resources/level07.md
level08/resources/level08.md
level09/resources/level09.md
level10/resources/level10.md
bonus01/resources/bonus01.md
bonus02/resources/bonus02.md
bonus03/resources/bonus03.md
bonus04/resources/bonus04.md
bonus05/resources/bonus05.md
```

El directorio `resources` también puede incluir archivos auxiliares necesarios
para reproducir el ejercicio. Todos ellos deben estar descritos en su guía
correspondiente. Por ejemplo:

```text
level01/resources/
└── level01.md

level02/resources/
└── level02.md

level03/resources/
├── build-extract.cmake
├── build-recon.cmake
└── level03.md

level04/resources/
└── level04.md

level05/resources/
├── level05.md
└── metaverse-exploit.wat

level06/resources/
├── level06.md
└── raven-payload.conf

level07/resources/
├── level07.md
└── sandbox-escape.expr

level08/resources/
├── blacksun_client.py
└── level08.md

level09/resources/
└── level09.md

level10/resources/
├── enzo-injection.wat
├── find_injection_token.py
└── level10.md

bonus01/resources/
└── bonus01.md

bonus02/resources/
└── bonus02.md

bonus03/resources/
└── bonus03.md

bonus04/resources/
└── bonus04.md

bonus05/resources/
└── bonus05.md
```

Los archivos auxiliares tienen estas funciones:

- `build-recon.cmake` realiza el reconocimiento inicial del directorio de
	`flag03`.
- `build-extract.cmake` extrae la credencial de `level03` mediante el runner
	de CMake ejecutado como `flag03`.
- `metaverse-exploit.wat` contiene el módulo WebAssembly textual utilizado para
	leer temporalmente `/home/flag05/.flag`.
- `raven-payload.conf` contiene la configuración temporal utilizada para
	explotar la evaluación de expresiones regulares Perl en `level06`.
- `sandbox-escape.expr` contiene la expresión Python utilizada para escapar del
	validador restringido de `level07`.
- `blacksun_client.py` implementa el cliente del protocolo Unix utilizado para
	saltar la autenticación de `level08`.
- `find_injection_token.py` calcula un campo con firma válida para seleccionar
	el handler vulnerable de `level10`.
- `enzo-injection.wat` emite el token manipulado que consume `validate.js`.

## Resumen de los ejercicios

- **level00:** escalada de privilegios mediante un binario con permisos
	`setuid` y extracción de una credencial expuesta dentro del ejecutable.
- **level01:** exposición de credenciales en los argumentos de un servicio
	`systemd` ejecutado con los privilegios de `flag01`.
- **level02:** fuga de una credencial mediante un archivo temporal persistente
	dejado por un servicio de entrega.
- **level03:** escalada de privilegios mediante un servicio `systemd` que
	ejecuta un archivo CMake escribible por el grupo del usuario.
- **level04:** inyección de comandos en una plantilla `m4` procesada con los
	privilegios de `flag04`.
- **level05:** reemplazo temporal de un módulo WebAssembly escribible y
	ejecución privilegiada mediante un servicio periódico.
- **level06:** ejecución de código Perl dentro de una expresión regular
	controlada mediante `use re 'eval'`.
- **level07:** escape de un sandbox Python mediante introspección de objetos y
	acceso a módulos ya cargados.
- **level08:** bypass de autenticación en un protocolo binario por un fallo de
	control de estados en un socket Unix.
- **level09:** validación de un token mediante un binario `setuid` y una cadena
	válida expuesta en sus datos legibles.
- **level10:** boss fight que combina la reconstrucción de un token WebAssembly
	con una inyección de comandos en un handler JavaScript.


- **bonus01:** lectura de una flag mediante un protocolo de memoria compartida expuesto por un daemon ejecutado como `flagbonus01`.
- **bonus02:** lectura de un fichero protegido mediante un binario con la
	capability Linux `cap_dac_read_search`.
- **bonus03:** abuso de un daemon `inotify` que procesa manifiestos en un
	directorio spool escribible por el grupo del usuario.
- **bonus04:** inyección de comandos a través de una configuración YAML
	escribible por grupo y procesada periódicamente por un servicio privilegiado.
- **bonus05:** carga de un módulo de kernel controlado por el atacante
	mediante un binario con la capability Linux `cap_sys_module`.