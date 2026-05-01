"""
Menú textual para armar un modelo en memoria y lanzar la misma visualización que ``supertesteo``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def _default_spec() -> Dict[str, Any]:
    return {
        "materials": {
            "default": {
                "E": 20000.0,
                "A": 100.0,
                "I_y": 833.0,
                "I_z": 833.0,
                "G": 7720.0,
                "J": 1408.0,
            }
        },
        "default_material": "default",
        "nodes": [],
        "bars": [],
        "loads_point": [],
    }


def _prompt(msg: str, default: Optional[str] = None) -> str:
    if default is not None:
        s = input(f"{msg} [{default}]: ").strip()
        return s if s else default
    return input(f"{msg}: ").strip()


def _prompt_float(msg: str, default: float) -> float:
    s = _prompt(msg, str(default))
    return float(s)


def _print_spec(spec: Dict[str, Any]) -> None:
    print("\n--- Modelo actual ---")
    print("Nodos:", len(spec["nodes"]))
    for n in spec["nodes"]:
        print(f"  id={n['id']} ({n['x']}, {n['y']}, {n['z']}) fix={n.get('fix')}")
    print("Barras:", len(spec["bars"]))
    for b in spec["bars"]:
        print(f"  id={b['id']} nodo {b['i']} -> {b['j']}")
    print("Cargas puntuales:", len(spec.get("loads_point") or []))
    for c in spec.get("loads_point") or []:
        print(f"  barra {c.get('bar_id')} en ({c['x']}, {c['y']}, {c['z']})")
    print("----------------------\n")


def run_interactive_menu() -> None:
    from .loader import build_estructura_from_spec
    from .pipeline import run_pipeline

    spec = _default_spec()
    print(
        "Cliente interactivo — mismos pasos que supertesteo (ensamble, cargas, resolver, diagramas).\n"
        "Comandos: 1 nodo | 2 barra | 3 carga | 4 listar | 5 guardar json | 6 cargar json | 7 resolver y graficar | 0 salir\n"
    )

    while True:
        op = _prompt("Opción [1-7 / 0]", "7").lower()
        if op in ("0", "q", "salir"):
            print("Chau.")
            return
        if op == "1":
            nid = int(_prompt("ID nodo (único)", "1"))
            x = _prompt_float("x (cm)", 0.0)
            y = _prompt_float("y (cm)", 0.0)
            z = _prompt_float("z (cm)", 0.0)
            print("Restricciones [Ux,Uy,Uz,Rx,Ry,Rz]: true=fijo, false=libre. Ej: true,true,true,false,false,false")
            fs = _prompt("Lista separada por coma", "false,false,false,false,false,false").replace(" ", "")
            parts = fs.split(",")
            if len(parts) != 6:
                print("Necesito 6 valores.")
                continue
            def _pb(s: str) -> bool:
                s = s.lower()
                if s in ("1", "true", "t", "si", "sí"):
                    return True
                if s in ("0", "false", "f", "no", "n", "none", ""):
                    return False
                return bool(s)
            fix = [_pb(p) for p in parts]
            spec["nodes"] = [n for n in spec["nodes"] if n["id"] != nid]
            spec["nodes"].append({"id": nid, "x": x, "y": y, "z": z, "fix": fix})
            spec["nodes"].sort(key=lambda d: d["id"])
            print("Nodo agregado.")
        elif op == "2":
            bid = int(_prompt("ID barra", "1"))
            ni = int(_prompt("Nodo inicial (id)", "1"))
            nj = int(_prompt("Nodo final (id)", "2"))
            spec["bars"] = [b for b in spec["bars"] if b["id"] != bid]
            spec["bars"].append({"id": bid, "i": ni, "j": nj, "material": "default"})
            spec["bars"].sort(key=lambda d: d["id"])
            print("Barra agregada (material 'default').")
        elif op == "3":
            bid = int(_prompt("ID barra donde actúa la carga", "1"))
            x = _prompt_float("x global carga (cm)", 0.0)
            y = _prompt_float("y global carga (cm)", 0.0)
            z = _prompt_float("z global carga (cm)", 0.0)
            print("Fuerza: podés dar Fx,Fy,Fz en una línea (3 números) o dejar 0 y usar componentes sueltas.")
            tri = _prompt("Fx, Fy, Fz (kN aprox. en global)", "0,0,0")
            parts = [p.strip() for p in tri.split(",") if p.strip() != ""]
            if len(parts) == 3:
                spec.setdefault("loads_point", []).append(
                    {
                        "id": len(spec.get("loads_point") or []) + 1,
                        "bar_id": bid,
                        "x": x,
                        "y": y,
                        "z": z,
                        "force_global": [float(parts[0]), float(parts[1]), float(parts[2])],
                    }
                )
            else:
                print("Usá exactamente 3 números separados por coma.")
            print("Carga añadida (se recalcula al resolver).")
        elif op == "4":
            _print_spec(spec)
        elif op == "5":
            out = Path(_prompt("Ruta .json", str(_ROOT / "modelo_cli.json")))
            out.write_text(json.dumps(spec, indent=2), encoding="utf-8")
            print(f"Guardado: {out}")
        elif op == "6":
            p = Path(_prompt("Ruta .json a cargar", ""))
            if not p.is_file():
                print("Archivo no encontrado.")
                continue
            spec = json.loads(p.read_text(encoding="utf-8"))
            if "materials" not in spec:
                spec["materials"] = _default_spec()["materials"]
            spec.setdefault("nodes", [])
            spec.setdefault("bars", [])
            spec.setdefault("loads_point", [])
            print("Modelo cargado.")
        elif op == "7":
            if not spec["nodes"] or not spec["bars"]:
                print("Falta al menos un nodo y una barra.")
                continue
            try:
                est = build_estructura_from_spec(spec)
            except Exception as e:
                print(f"Error al armar estructura: {e}")
                continue
            print("Resolviendo y abriendo ventana (pestañas: estructura, fuerzas, V, N, M)...")
            try:
                run_pipeline(est, show_matplotlib=True, titulo="Hyperstatic CLI (interactivo)")
            except Exception as e:
                print(f"Error: {e}")
        else:
            print("Opción no reconocida.")


if __name__ == "__main__":
    run_interactive_menu()
