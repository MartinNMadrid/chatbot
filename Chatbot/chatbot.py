from flask import Flask, render_template, request, jsonify
import json
from fuzzywuzzy import process  # Importamos fuzzywuzzy

app = Flask(__name__)

# Cargar la base de conocimiento
with open("/var/www/html/chatbot/base_conocimiento.json", "r", encoding="utf-8") as file:
    base_conocimiento = json.load(file)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/consulta", methods=["POST"])
def consulta():
    pregunta_usuario = request.json.get("pregunta", "").lower()

    # Obtener todas las preguntas de la base de conocimiento
    preguntas = list(base_conocimiento.keys())

    # Buscar la coincidencia más cercana
    pregunta_coincidencia, similitud = process.extractOne(pregunta_usuario, preguntas)
    print(f"Pregunta ingresada: {pregunta_usuario}")
    print(f"Mejor coincidencia: {pregunta_coincidencia} con similitud: {similitud}")

    # Si la coincidencia es suficientemente alta, responde directamente
    if similitud >= 90:
        respuesta = base_conocimiento[pregunta_coincidencia]
        return jsonify({"respuesta": respuesta})

    # Si no hay coincidencia exacta, buscar recomendaciones
    recomendaciones = process.extract(pregunta_usuario, preguntas, limit=3)
    print(f"Resultados de fuzzywuzzy para recomendaciones: {recomendaciones}")

    recomendaciones_filtradas = [
        pregunta for pregunta, score in recomendaciones if score >= 50
    ]
    print(f"Recomendaciones filtradas (score >= 50): {recomendaciones_filtradas}")

    if recomendaciones_filtradas:  # Si hay recomendaciones
        return jsonify({
            "respuesta": "No encontré una respuesta exacta, pero quizás quisiste preguntar algo de esto:",
            "recomendaciones": recomendaciones_filtradas
        })

    # Si no hay recomendaciones, responde genéricamente
    return jsonify({
        "respuesta": "No tengo esa respuesta en mi base de conocimiento. Por favor, contacta al soporte técnico."
    })

@app.route("/adminBot")
def admin():
    return render_template("admin.html", base_conocimiento=base_conocimiento)

@app.route("/update", methods=["POST"])
def update():
    accion = request.form.get("accion")
    pregunta = request.form.get("pregunta")
    respuesta = request.form.get("respuesta")
    
    if accion == "add":
        base_conocimiento[pregunta] = respuesta
        return jsonify({"message": "Pregunta añadida exitosamente"})
    elif accion == "edit":
         base_conocimiento[pregunta_original] = respuesta
         with open("base_conocimiento.json", "w", encoding="utf-8") as file:
            json.dump(base_conocimiento, file, ensure_ascii=False, indent=4)
         return jsonify({"message": "Pregunta editada correctamente"})
    elif accion == "delete":
        if pregunta in base_conocimiento:
            del base_conocimiento[pregunta]
            return jsonify({"message": "Pregunta eliminada exitosamente"})
        else:
            return jsonify({"message": "La pregunta no existe"})
    else:
        return jsonify({"message": "Acción no válida"})


if __name__ == "__main__":
    app.run(debug=True)
