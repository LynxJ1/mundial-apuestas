from flask import Flask, render_template, jsonify, request, redirect, session
from functools import wraps
import json

app = Flask(__name__)
ARCHIVO_DATOS = "data.json"

app.secret_key = "CorralejasyAnolaima"
CONTRASENA_ADMIN = "Corralejas1909."

def requiere_login(f):
    @wraps(f)
    def decorada(*args, **kwargs):
        if not session.get("logueado"):
            return redirect("/login")
        return f(*args, **kwargs)
    return decorada


def cargar_datos():
    with open(ARCHIVO_DATOS, "r", encoding="utf-8") as f:
        return json.load(f)


def guardar_datos(datos):
    with open(ARCHIVO_DATOS, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=2, ensure_ascii=False)

def calcular_puntos(apuesta, real):
    gl_ap, gv_ap = apuesta
    gl_re, gv_re = real

    if gl_ap == gl_re and gv_ap == gv_re:
        return 5

    puntos = 0

    if gl_ap == gl_re:
        puntos += 1

    if gv_ap == gv_re:
        puntos += 1

    ganador_ap = (gl_ap > gv_ap) - (gl_ap < gv_ap)
    ganador_re = (gl_re > gv_re) - (gl_re < gv_re)
    if ganador_ap == ganador_re:
        puntos += 2

    return puntos

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        clave =request.form["clave"]
        if clave == CONTRASENA_ADMIN:
            session["logueado"] = True
            return redirect("/admin")
        return render_template("login.html", error="Contraseña Incorrecta")
    return render_template("login.html", error=None)

@app.route("/logout")
def logout():
    session.pop("logueado", None)
    return redirect("/")

def calcular_tabla_puntos(datos):
    tabla_puntos = {p: 0 for p in datos["participantes"]}
    for partido in datos["partidos"]:
        if partido["resultado_real"] is not None:
            for participante, apuesta in partido["apuestas"].items():
                pts = calcular_puntos(apuesta, partido["resultado_real"])
                tabla_puntos[participante] += pts
    
    tabla_ordenada = sorted(tabla_puntos.items(), key=lambda x: x[1], reverse=True)
    return tabla_ordenada


@app.route("/")
def inicio():
    datos = cargar_datos()

    tabla_puntos = calcular_tabla_puntos(datos)
    
    return render_template("index.html", datos=datos, tabla_puntos=tabla_puntos)

@app.route("/admin")
@requiere_login
def admin():
    datos = cargar_datos()
    tabla_puntos = calcular_tabla_puntos(datos)
    return render_template("admin.html", datos=datos, tabla_puntos=tabla_puntos)

@app.route("/agregar-participante", methods=["POST"])
@requiere_login
def agregar_participante():
    nombre = request.form["nombre"]
    datos = cargar_datos()
    datos["participantes"].append(nombre)
    guardar_datos(datos)
    return redirect("/")


@app.route("/agregar-partido", methods=["POST"])
@requiere_login
def agregar_partido():
    datos = cargar_datos()

    local = request.form["local"]
    visitante = request.form["visitante"]

    apuestas = {}
    for p in datos["participantes"]:
        gl = int(request.form[f"goles_local_{p}"])
        gv = int(request.form[f"goles_visit_{p}"])
        apuestas[p] = [gl, gv]

    nuevo_partido = {
        "id": len(datos["partidos"]) + 1,
        "local": local,
        "visitante": visitante,
        "resultado_real": None,
        "apuestas": apuestas,
    }

    datos["partidos"].append(nuevo_partido)
    guardar_datos(datos)
    return redirect("/")


@app.route("/resultado/<int:partido_id>", methods=["POST"])
@requiere_login
def guardar_resultado(partido_id):
    datos = cargar_datos()

    gl_real = int(request.form["goles_local_real"])
    gv_real = int(request.form["goles_visit_real"])

    for partido in datos["partidos"]:
        if partido["id"] == partido_id:
            partido["resultado_real"] = [gl_real, gv_real]

    guardar_datos(datos)
    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True, port=5000)



