# SnowCrash - Level 00

## Tipo de ejercicio

Escalada de privilegios mediante un binario con permisos **setuid** y
extracción de una credencial expuesta dentro del ejecutable.

## Objetivo

Encontrar una forma de ejecutar el programa perteneciente a `flag00` y obtener la credencial necesaria para continuar con el nivel siguiente.

## 1. Revisar el directorio inicial

Una vez dentro, se puede comprobar el contenido del directorio personal:

```bash
ls -la
cat README
```

El archivo `README` solo contiene una referencia a **Hiro Protagonist**, por lo que el siguiente paso es localizar archivos relacionados con el usuario objetivo `flag00`.

## 2. Buscar archivos propiedad de `flag00`

El comando correcto para buscar en todo el sistema los archivos cuyo propietario es `flag00` es:

```bash
find / -user flag00 2>/dev/null
```

La redirección `2>/dev/null` oculta los mensajes de permisos denegados durante la búsqueda. Entre los resultados aparece el ejecutable:

```text
/opt/snowcrash/level00/hiro
```

## 3. Comprobar los permisos del ejecutable

Antes de ejecutarlo, se revisan sus permisos:

```bash
ls -l /opt/snowcrash/level00/hiro
```

El resultado relevante es similar a:

```text
-r-sr-x--- 1 flag00 level00 ... /opt/snowcrash/level00/hiro
```

La `s` en los permisos del propietario indica que el ejecutable tiene el bit **setuid**. Por tanto, al ejecutarlo, el programa puede funcionar con los privilegios de `flag00`.

## 4. Inspeccionar las cadenas del binario

El binario contiene información legible internamente. Se puede extraer con:

```bash
strings /opt/snowcrash/level00/hiro
```

`strings` extrae las secuencias de caracteres imprimibles que encuentra en el
binario. La salida completa no es una lista limpia: contiene nombres de
símbolos, rutas de librerías y fragmentos de código máquina interpretados
como texto, por lo que es habitual que líneas cercanas a la credencial
incluyan caracteres que no forman parte de ella. Es posible que la línea
buscada aparezca junto a otros caracteres pegados, por ejemplo:

```text
>@f2av5il02puano7naaf6adaf3a
```

El prefijo `>@` no es parte de la credencial: son bytes contiguos en el
binario que `strings` interpreta como caracteres imprimibles porque
preceden sin separador a la cadena real, pero no forman una palabra con
sentido ni tienen la longitud ni el formato alfanumérico homogéneo del resto
de la cadena. La credencial es solo la parte alfanumérica continua:

```text
f2av5il02puano7naaf6adaf3a
```

## 5. Ejecutar el programa

Se inicia el ejecutable usando su ruta absoluta:

```bash
/opt/snowcrash/level00/hiro
```

El programa valida la credencial y muestra un acceso concedido para `flag00`. Esto confirma que el binario es el mecanismo previsto para superar el nivel.

## 6. Continuar con el siguiente nivel

La OVA puede permanecer en la pantalla de login. No es necesario iniciar sesión
en la consola de la máquina virtual para cambiar de nivel. Desde el equipo
anfitrión se abre una nueva conexión SSH con el usuario del siguiente nivel:

```bash
ssh level01@localhost -p 2424
```

Cuando SSH solicite la contraseña, se introduce la misma clave descubierta en `level00`:

```text
f2av5il02puano7naaf6adaf3a
```

Si la autenticación es correcta, se accederá al entorno de `level01` y se podrá comenzar el siguiente ejercicio.

## Resumen de comandos válidos

```bash
ls -la
cat README
find / -user flag00 2>/dev/null
ls -l /opt/snowcrash/level00/hiro
strings /opt/snowcrash/level00/hiro
/opt/snowcrash/level00/hiro
exit
ssh level01@localhost -p 2424
```

## Conceptos importantes

- `find / -user flag00`: localiza archivos propiedad del usuario `flag00`.
- `2>/dev/null`: oculta errores de permisos durante la búsqueda.
- `ls -l`: permite revisar propietario, grupo y permisos.
- `setuid`: hace que un ejecutable se ejecute con los privilegios de su propietario.
- `strings`: extrae cadenas de texto legibles de un binario.
