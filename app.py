from flask import Flask, render_template, jsonify, request, redirect, session
from functools import wraps
import json

app = Flask(__name__)
ARCHIVO_DATOS = "data.json"

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

def conectar():
    conn = psycopg2.connect(os.environ["DATABASE_URL"], cursor_factory=RealDictCursor)
    return conn

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

def calcular_tabla_puntos(participantes, partidos):
    tabla_puntos = {p["nombre"]: 0 for p in participantes}

    for partido in partidos:
        if partido["goles_local_real"] is not None:
            real = (partido["goles_local_real"], partido["goles_visit_real"])
            for apuesta in partido["apuestas"]:
                ap = (apuesta["goles_local"], apuesta["goles_visit"])
                pts = calcular_puntos(ap, real)
                tabla_puntos[apuesta["nombre"]] += pts

    tabla_ordenada = sorted(tabla_puntos.items(), key=lambda x: x[1], reverse=True)
    return tabla_ordenada


@app.route("/")
def inicio():
    conn = conectar()
    cur = conn.cursor()

    cur.execute("SELECT * FROM participantes ORDER BY id")
    participantes = cur.fetchall()

    cur.execute("SELECT * FROM partidos ORDER BY id")
    partidos = cur.fetchall()

    for partido in partidos:
        cur.execute("""
            SELECT apuestas.goles_local, apuestas.goles_visit, participantes.nombre
            FROM apuestas
            JOIN participantes ON apuestas.participante_id = participantes.id
            WHERE apuestas.partido_id = %s
        """, (partido["id"],))
        partido["apuestas"] = cur.fetchall()

    cur.close()
    conn.close()

    tabla_puntos = calcular_tabla_puntos(participantes, partidos)

    return render_template("index.html", participantes=participantes, partidos=partidos, tabla_puntos=tabla_puntos)

@app.route("/admin")
@requiere_login
def admin():
    conn = conectar()
    cur = conn.cursor()

    cur.execute("SELECT * FROM participantes ORDER BY id")
    participantes = cur.fetchall()

    cur.execute("SELECT * FROM partidos ORDER BY id")
    partidos = cur.fetchall()

    for partido in partidos:
        cur.execute("""
            SELECT apuestas.goles_local, apuestas.goles_visit, participantes.nombre
            FROM apuestas
            JOIN participantes ON apuestas.participante_id = participantes.id
            WHERE apuestas.partido_id = %s
        """, (partido["id"],))
        partido["apuestas"] = cur.fetchall()

    cur.close()
    conn.close()

    tabla_puntos = calcular_tabla_puntos(participantes, partidos)

    return render_template("admin.html", participantes=participantes, partidos=partidos, tabla_puntos=tabla_puntos)

@app.route("/agregar-participante", methods=["POST"])
@requiere_login
def agregar_participante():
    nombre = request.form["nombre"]

    conn = conectar()
    cur = conn.cursor()
    cur.execute("INSERT INTO participantes (nombre) VALUES (%s)", (nombre,))
    conn.commit()
    cur.close()
    conn.close()

    return redirect("/admin")

@app.route("/agregar-partido", methods=["POST"])
@requiere_login
def agregar_partido():
    local = request.form["local"]
    visitante = request.form["visitante"]

    conn = conectar()
    cur = conn.cursor()

    cur.execute("SELECT * FROM participantes ORDER BY id")
    participantes = cur.fetchall()

    cur.execute(
        "INSERT INTO partidos (local, visitante) VALUES (%s, %s) RETURNING id",
        (local, visitante)
    )
    partido_id = cur.fetchone()["id"]

    for p in participantes:
        gl = int(request.form[f"goles_local_{p['nombre']}"])
        gv = int(request.form[f"goles_visit_{p['nombre']}"])
        cur.execute(
            "INSERT INTO apuestas (partido_id, participante_id, goles_local, goles_visit) VALUES (%s, %s, %s, %s)",
            (partido_id, p["id"], gl, gv)
        )

    conn.commit()
    cur.close()
    conn.close()

    return redirect("/admin")


@app.route("/resultado/<int:partido_id>", methods=["POST"])
@requiere_login
def guardar_resultado(partido_id):
    gl_real = int(request.form["goles_local_real"])
    gv_real = int(request.form["goles_visit_real"])

    conn = conectar()
    cur = conn.cursor()
    cur.execute(
        "UPDATE partidos SET goles_local_real = %s, goles_visit_real = %s WHERE id = %s",
        (gl_real, gv_real, partido_id)
    )
    conn.commit()
    cur.close()
    conn.close()

    return redirect("/admin")


if __name__ == "__main__":
    app.run(debug=True, port=5000)



