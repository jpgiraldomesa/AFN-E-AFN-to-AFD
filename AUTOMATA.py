# -*- coding: utf-8 -*-
"""
Created on Wed Sep  9 17:31:17 2026

@author: Michel
"""
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

"""

import json
import sys
import argparse

EPS = "ε"                                   
ALIAS_EPS = {"epsilon", "eps", "lambda", "λ", "@", "e", "-", "", EPS}


def cargar_afn(ruta):
    with open(ruta, encoding="utf-8") as f:
        datos = json.load(f)

    estados = list(datos["estados"])
    alfabeto = list(datos["alfabeto"])          
    inicial = datos["estado_inicial"]
    finales = set(datos["estados_finales"])

    delta = {q: {} for q in estados}   #
    tiene_epsilon = False
    for origen, fila in datos.get("transiciones", {}).items():
        for simbolo, destinos in fila.items():
           
            es_alias = simbolo.strip().lower() in ALIAS_EPS and simbolo not in alfabeto #
            simbolo_norm = EPS if es_alias else simbolo                                 #
            if simbolo_norm == EPS:
                tiene_epsilon = True
            delta.setdefault(origen, {})
            delta[origen].setdefault(simbolo_norm, set())
            delta[origen][simbolo_norm].update(destinos)

    es_no_determinista = tiene_epsilon or any(                                    #
        len(delta.get(q, {}).get(s, ())) > 1 for q in estados for s in alfabeto   #
    )

    return {
        "nombre": datos.get("nombre", "AFN sin nombre"),
        "estados": estados,
        "alfabeto": alfabeto,
        "inicial": inicial,
        "finales": finales,
        "delta": delta,
        "tiene_epsilon": tiene_epsilon,
        "es_no_determinista": es_no_determinista,
    }



def clausura_epsilon(conjunto, delta): #
#Estados alcanzables desde 'conjunto' con epsilon (o el mismo conjunto, si no hay transiciones epsilon)
    pila = list(conjunto)
    vistos = set(conjunto)
    while pila:
        q = pila.pop()
        for destino in delta.get(q, {}).get(EPS, ()):
            if destino not in vistos:
                vistos.add(destino)
                pila.append(destino)
    return frozenset(vistos) #


def mover(conjunto, simbolo, delta):
#Union de los posibles destinos del estado al leer simbolo/flecha (sin epsilon)
    destinos = set()
    for q in conjunto:
        destinos.update(delta.get(q, {}).get(simbolo, ()))
    return destinos


def etiqueta(conjunto, orden_estados):
#orden de menor a mayor de estados (q0,q1) en lugar de (q1,q0)
    ordenado = [q for q in orden_estados if q in conjunto]
    return "{" + ",".join(ordenado) + "}"



def construir_afd(afn):
#Construccion de subconjuntos incluyendo cerradura
    delta, alfabeto, orden = afn["delta"], afn["alfabeto"], afn["estados"]

    inicial_afd = clausura_epsilon({afn["inicial"]}, delta)     #

    tabla = {}                 
    orden_descubrimiento = [inicial_afd]      
    detalle_uniones = []  
                    
    pendientes = [inicial_afd]                                  #
    while pendientes:
        actual = pendientes.pop(0)
        
        if actual in tabla:
            continue
        tabla[actual] = {}

        for simbolo in alfabeto:                                                #
            componentes = {q: sorted(delta.get(q, {}).get(simbolo, ()))
                           for q in orden if q in actual}
            bruto = mover(actual, simbolo, delta)
            destino = clausura_epsilon(bruto, delta) if bruto else frozenset()  #

            detalle_uniones.append({
                "subconjunto": etiqueta(actual, orden),
                "simbolo": simbolo,
                "componentes": {q: d for q, d in componentes.items() if d},
                "resultado": etiqueta(destino, orden) if destino else None,
            })

            tabla[actual][simbolo] = destino if destino else None               #
            if destino and destino not in tabla and destino not in pendientes:
                pendientes.append(destino)
                orden_descubrimiento.append(destino)                            #

    finales_afd = {c for c in tabla if c & afn["finales"]}                     #
    return tabla, inicial_afd, finales_afd, orden_descubrimiento, detalle_uniones
#Devuelve tabla AFD por conjuntos de estados del AFN con paso a paso



def podar_muertos(tabla, inicial_afd, finales_afd, alfabeto):
#Eliminar estados que nunca pueden llegar a un final excluyendo el inicial(se conserva)
    vivos = set(finales_afd)                                        #
    cambio = True
    while cambio:
        cambio = False
        for estado, fila in tabla.items():
            if estado in vivos:
                continue
            if any(destino in vivos for destino in fila.values()):
                vivos.add(estado)
                cambio = True
    vivos.add(inicial_afd)                                          #

    muertos = [e for e in tabla if e not in vivos]
    tabla_podada = {e: {s: (d if d in vivos else None) for s, d in fila.items()}
                     for e, fila in tabla.items() if e in vivos}
    return tabla_podada, muertos


def minimizar(tabla, inicial_afd, finales_afd, alfabeto, orden):
#Agrupar estados muertos del paso anterior en estado 'trampa' implicito para definir todas las transiciones
    TRAMPA = "trampa"                            #
    estados = list(tabla.keys()) + [TRAMPA]

    def destino_de(e, s):
        if e == TRAMPA:
            return TRAMPA
        d = tabla[e].get(s)
        return d if d is not None else TRAMPA   #

    grupo = {e: (1 if e in finales_afd else 0) for e in estados}  #  finales y no finales
    while True:
        firma = {}                                                #
        
        for e in estados:
            firma[e] = (grupo[e], tuple(grupo[destino_de(e, s)] for s in alfabeto))

        firmas_unicas = sorted(set(firma.values()))
        nuevo_grupo = {e: firmas_unicas.index(firma[e]) for e in estados}

        if len(set(nuevo_grupo.values())) == len(set(grupo.values())):  #
            break
        grupo = nuevo_grupo                                             #

    
    clases = {}
    for e in estados:
        clases.setdefault(grupo[e], []).append(e)
        
    clase_trampa = grupo[TRAMPA]           # construccion estado minimizado
    fusiones = []
    representante = {}                       #el primero en orden alfabetico 
    for g, miembros in clases.items():
        if g == clase_trampa:
            continue                       #
            
        miembros_reales = [m for m in miembros if m != TRAMPA]
        rep = sorted(miembros_reales, key=lambda e: etiqueta(e, orden))[0]
        for m in miembros_reales:
            representante[m] = rep
        if len(miembros_reales) > 1:
            fusiones.append({
                "clase_resultante": etiqueta(rep, orden),
                "estados_fusionados": [etiqueta(m, orden) for m in miembros_reales],
            })

    tabla_min = {}
    for e, rep in representante.items():
        if rep in tabla_min:
            continue
        fila = {}
        for s in alfabeto:
            d = destino_de(e, s)
            fila[s] = representante.get(d)   # None si cae en la trampa
        tabla_min[rep] = fila

    nuevo_inicial = representante[inicial_afd]
    nuevos_finales = {representante[e] for e in finales_afd}
    return tabla_min, nuevo_inicial, nuevos_finales, fusiones


# salida

def tabla_a_json(tabla, orden):
#Convierte tabla de llaves frozenset a estados q0,q1.. listo para json.dump
    salida = {}
    for estado, fila in tabla.items():
        clave = etiqueta(estado, orden) if isinstance(estado, frozenset) else estado
        salida[clave] = {s: (etiqueta(d, orden) if isinstance(d, frozenset) else d)
                          for s, d in fila.items()}
    return salida


def procesar(ruta_entrada, ruta_salida, minimizar_afd=True):
    afn = cargar_afn(ruta_entrada)
    orden = afn["estados"]

    tabla, inicial_afd, finales_afd, orden_desc, uniones = construir_afd(afn)
    tabla_podada, muertos = podar_muertos(tabla, inicial_afd, finales_afd, afn["alfabeto"])

    resultado = {
        "nombre": afn["nombre"],
        "pasos": {
            "1_afn_original": {
                "estados": afn["estados"],
                "alfabeto": afn["alfabeto"],
                "estado_inicial": afn["inicial"],
                "estados_finales": sorted(afn["finales"]),
                "tiene_epsilon": afn["tiene_epsilon"],
                "es_no_determinista": afn["es_no_determinista"],
                "transiciones": {q: {s: sorted(d) for s, d in fila.items()}
                                 for q, fila in afn["delta"].items()},
            },
            "2_subconjuntos_nuevos_en_orden_de_aparicion": [
                etiqueta(c, orden) for c in orden_desc
            ],
            "3_uniones_por_cada_transicion_nueva": uniones,
            "4_tabla_completa_afd": {
                "estado_inicial": etiqueta(inicial_afd, orden),
                "estados_finales": sorted(etiqueta(c, orden) for c in finales_afd),
                "transiciones": tabla_a_json(tabla, orden),
            },
            "5_poda_y_minimizacion": {
                "estados_podados_por_no_llevar_a_ningun_final":
                    [etiqueta(m, orden) for m in muertos],
                "minimizacion_aplicada": minimizar_afd,
            },
        },
    }

    if minimizar_afd:
        tabla_min, inicial_min, finales_min, fusiones = minimizar(
            tabla_podada, inicial_afd, finales_afd, afn["alfabeto"], orden)
        resultado["pasos"]["5_poda_y_minimizacion"]["estados_fusionados_por_equivalentes"] = fusiones
        resultado["afd_final"] = {
            "estados": sorted(tabla_min.keys(), key=lambda e: etiqueta(e, orden)),
            "alfabeto": afn["alfabeto"],
            "estado_inicial": etiqueta(inicial_min, orden),
            "estados_finales": sorted(etiqueta(c, orden) for c in finales_min),
            "transiciones": tabla_a_json(tabla_min, orden),
        }
        # los nombres de estado en "estados" tambien deben verse como texto
        resultado["afd_final"]["estados"] = [etiqueta(e, orden) for e in tabla_min.keys()]
    else:
        resultado["afd_final"] = {
            "estados": [etiqueta(c, orden) for c in tabla_podada],
            "alfabeto": afn["alfabeto"],
            "estado_inicial": etiqueta(inicial_afd, orden),
            "estados_finales": sorted(etiqueta(c, orden) for c in finales_afd if c in tabla_podada),
            "transiciones": tabla_a_json(tabla_podada, orden),
        }

    with open(ruta_salida, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)

    print("AFN de entrada: %s" % afn["nombre"])
    print("  estados: %d | no determinista: %s | usa epsilon: %s" %
          (len(afn["estados"]), "si" if afn["es_no_determinista"] else "no",
           "si" if afn["tiene_epsilon"] else "no"))
    print("AFD resultante: %d estados -> escrito en %s" %
          (len(resultado["afd_final"]["estados"]), ruta_salida))


def main():
    ap = argparse.ArgumentParser(
        description="Convierte un AFN (JSON) en un AFD (JSON), paso a paso.")
    ap.add_argument("entrada", help="archivo .json con el AFN")
    ap.add_argument("-o", "--salida", help="archivo .json de salida "
                                            "(por omision <entrada>_afd.json)")
    ap.add_argument("--sin-minimizar", action="store_true",
                     help="no fusionar estados equivalentes")
    args = ap.parse_args()

    salida = args.salida or (args.entrada.rsplit(".", 1)[0] + "_afd.json")
    procesar(args.entrada, salida, minimizar_afd=not args.sin_minimizar)


if __name__ == "__main__":
    main()