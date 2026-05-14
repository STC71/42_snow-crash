# ❄️ Snow Crash - Cyber Security Project

**Versión**: 3.2  
**Tipo de Proyecto**: Introducción a Ciberseguridad  
**Entorno**: Máquina Virtual de 64-bits (ISO proporcionada)  

> Una modesta pero profunda introducción al amplio mundo de la ciberseguridad. Un entorno donde no hay margen de error y deberás descubrir diversas vulnerabilidades del sistema.

---

## 📋 Tabla de Contenidos

1. [Descripción General](#-descripción-general)
2. [Objetivos del Proyecto](#-objetivos-del-proyecto)
3. [Instrucciones Generales](#-instrucciones-generales)
4. [Dinámica de Juego (CTF)](#-dinámica-de-juego-ctf)
5. [Parte Obligatoria](#-parte-obligatoria)
6. [Estructura de Carpetas](#-estructura-de-carpetas)
7. [Parte Bonus](#-parte-bonus)

---

## 🎯 Descripción General

Como desarrollador, el software creado será utilizado por muchas personas y cualquier debilidad las expondrá al peligro. Es un deber entender las diferentes técnicas de explotación de estas debilidades para poder detectarlas y evitarlas. 

**Snow Crash** es una serie de desafíos prácticos que buscan iniciar al estudiante en la ciberseguridad a través de varios campos, proporcionando nuevas perspectivas sobre la informática general a través de un formato *Capture The Flag* (CTF).

---

## 💡 Objetivos del Proyecto

- ✅ Descubrir problemas de seguridad y vulnerabilidades en sistemas Linux (escalada de privilegios, inyecciones, etc.).
- ✅ Desarrollar pensamiento lógico avanzado e independiente; superar callejones sin salida buscando la solución por iniciativa propia.
- ✅ Ganar una perspectiva crítica sobre cómo escribir y estructurar código de manera segura.

> *Nota: "Tú debes ser la única llave de las puertas cerradas que encuentres."*

---

## ⚙️ Instrucciones Generales

Para realizar el proyecto se necesita una máquina virtual de **64 bits** y la **ISO** oficial provista.
Una vez iniciada la VM y con la configuración correcta de red, el sistema mostrará un prompt presentando un *ASCII Art* ("Good luck & Have fun") seguido por la dirección IP de la máquina:

```
192.168.16.128
SnowCrash login: _
```
*(Si no se ve la IP, se puede usar el comando `ifconfig` tras el inicio de sesión).*

### Acceso Inicial

El primer acceso al entorno se realiza con las siguientes credenciales:
- **Usuario**: `level00`
- **Contraseña**: `level00`

Se recomienda altamente acceder a través de una conexión remota **SSH** en el **puerto 4242**:
```bash
ssh level00@<ip_de_la_vm> -p 4242
```

---

## 🎮 Dinámica de Juego (CTF)

La progresión se basa en un esquema de niveles (`levelXX`). 

1. **El Objetivo Principal:** Estando logueado en un nivel dado, el objetivo es conseguir la contraseña de la cuenta del usuario "objetivo" (`flagXX`), el cual corresponde al número del nivel actual.
2. **Conseguir el Token:** Una vez se ha logrado iniciar sesión o ejecutar un comando como la cuenta `flagXX`, se debe ejecutar el binario `getflag`. Al hacerlo, proporcionará el **token/password** para poder entrar al **siguiente** nivel (ej. `level01`).
3. **Escalada indirecta:** Si no se puede acceder de forma directa con `su flagXX`, habrá que buscar un método alternativo como una inyección de comandos en un binario o script vulnerable que dependa de los permisos locales del sistema.

### Ejemplo de sesión

```bash
level00@SnowCrash:~$ su flag00
Password:
Don't forget to launch getflag!
flag00@SnowCrash:~$ getflag
Check flag.Here is your token: ?????????????????
flag00@SnowCrash:~$ su level01
Password:
level01@SnowCrash:~$
```

⚠️ **Advertencias importantes:**
- Utilizar *fuerza bruta* sobre las contraseñas SSH o tokens está **prohibido**. No servirá, pues se exige explicar detalladamente todas las soluciones durante la evaluación.
- Los directorios `/tmp/` y `/var/tmp/` tienen derechos limitados y se vaciarán de vez en cuando. Se recomienda no trabajar directamente en la máquina o llevar el control local.
- Sugerencia útil: familiarizarse con utilidades como `scp` para enviar y recibir archivos de la máquina virtual.

---

## ⭐ Parte Obligatoria

En la parte obligatoria se deben resolver y superar un total de **10** niveles consecutivos, comenzando por el 0 y llegando hasta el 9:

- `level00`, `level01`, `level02`, `level03`, `level04`, `level05`, `level06`, `level07`, `level08`, `level09`

Todo debe estar preparado para ser demostrado ante la corrección de pares, siendo capaz de justificar detalladamente cómo cada técnica fue descubierta y explotada.

---

## 📁 Estructura de Carpetas

Todo el material utilizado para resolver el proyecto debe entregarse subido en el repositorio con un esquema muy estricto por cada nivel.
No se debe incluir **ningún** archivo binario o material nativo extraído de la ISO en el repositorio, pero en la evaluación se pueden volver a descargar si fueran necesarios.

Ejemplo general de la estructura obligatoria:
```text
.
├── level00/
│   ├── flag                    # El token (puede estar vacío pero requiere explicación si lo está)
│   └── resources/              # Todo material externo/scripts necesarios para probar la solución
│       └── scripts_extras.py
├── level01/
│   ├── flag
│   └── resources/
...
```

---

## 🚀 Parte Bonus

> ⚠️ Los niveles bonus **sólo** se tendrán en consideración si la parte obligatoria está valorada como **PERFECTA**. (Significa que está 100% acabada y su comportamiento no tiene fallos, malentendidos ni dudas técnicas).

Los desafíos adicionales para subir la nota son los subiguientes niveles:

- `level10`
- `level11`
- `level12`
- `level13`
- `level14`

---

<div align="center">

[⬅️ Volver al repositorio principal](../../README.md)

</div>