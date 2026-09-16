# Conversor de AFN a AFD

Convierte un autómata finito no determinista (AFN), escrito en un archivo JSON, a un autómata finito determinista (AFD). El resultado se guarda en otro archivo JSON.

## Cómo ejecutarlo

Poner AUTOMATA.py y el archivo JSON en la misma carpeta, abrir una terminal ahí y escribir:

```bash
python AUTOMATA.py prueba.json
```

Se crea el archivo prueba_afd.json con el AFD y el paso a paso, y en pantalla aparece:

```
AFN de entrada: prueba ejemplo
  estados: 3 | no determinista: si | usa epsilon: no
AFD resultante: 3 estados -> escrito en prueba_afd.json
```


## Cómo llenar el JSON

```json
{
  "nombre": "prueba ejemplo",
  "alfabeto": ["0", "1"],
  "estados": ["q0", "q1", "q2"],
  "estado_inicial": "q0",
  "estados_finales": ["q2"],
  "transiciones": {
    "q0": {
      "0": ["q1"],
      "1": ["q1"]
    },
    "q1": {
      "0": ["q1", "q2"],
      "1": ["q1"]
    }
  }
}
```

Reglas:

- Todo va entre comillas, incluidos los símbolos del alfabeto (`"0"`, no `0`).
- En `transiciones`, cada estado tiene los símbolos que lee y, para cada uno, la lista de estados a los que puede ir.
- Los destinos siempre son una lista, aunque sea uno solo: `["q1"]`.
- Si un estado no tiene transiciones de salida (como `q2`), no hace falta escribirlo.
- Si un símbolo no lleva a ningún lado desde cierto estado, simplemente no se escribe.
- Para una transición épsilon se usa `"epsilon"` como símbolo, y no se incluye en el alfabeto:

```json
"q0": { "a": ["q0"], "epsilon": ["q1"] }
```

## El resultado

En el archivo de salida, `afd_final` tiene el autómata terminado y `pasos` muestra cómo se llegó a él. Los estados del AFD se llaman según los estados del AFN que agrupan, por ejemplo `{q0}` o `{q1,q2}`.
