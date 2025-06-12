from flask import Flask, render_template, request, jsonify
import json
from fuzzywuzzy import process # Importamos fuzzywuzzy
from fuzzywuzzy import fuzz

app = Flask(__name__)

# Ruta del archivo de base de conocimiento
KNOWLEDGE_BASE_PATH = "base_conocimiento.json" # Cambiado a ruta relativa

# Cargar la base de conocimiento
def load_knowledge_base():
    try:
        with open(KNOWLEDGE_BASE_PATH, "r", encoding="utf-8") as file:
            # Asegúrate de que siempre sea una lista
            data = json.load(file)
            if not isinstance(data, list):
                print(f"Advertencia: El archivo {KNOWLEDGE_BASE_PATH} no es una lista. Inicializando como lista vacía.")
                return []
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        # Si el archivo no existe o está corrupto, inicializa una lista vacía
        print(f"Archivo {KNOWLEDGE_BASE_PATH} no encontrado o formato JSON inválido. Inicializando base de conocimiento vacía.")
        return []

# Guardar la base de conocimiento
def save_knowledge_base(data):
    with open(KNOWLEDGE_BASE_PATH, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

base_conocimiento = load_knowledge_base()

@app.route("/")
def home():
    # Renderiza la plantilla principal del chatbot
    return render_template("index.html")

@app.route("/consulta", methods=["POST"])
def consulta():
    # Obtiene la pregunta del usuario del cuerpo de la solicitud JSON
    pregunta_usuario = request.json.get("pregunta", "").lower().strip()

    # Si la pregunta del usuario está vacía, devuelve un mensaje
    if not pregunta_usuario:
        return jsonify({"respuesta": "Por favor, ingresa una pregunta."})

    # Obtener todas las preguntas de la base de conocimiento para la búsqueda fuzzy
    # Creamos una lista de tuplas (pregunta_original, índice) para asociar la pregunta con su objeto original
    preguntas_con_indices = []
    for i, entry in enumerate(base_conocimiento):
        if "pregunta" in entry:
            preguntas_con_indices.append((entry["pregunta"].lower(), i))

    if not preguntas_con_indices:
        return jsonify({
            "respuesta": "No tengo esa respuesta en mi base de conocimiento. Por favor, contacta al soporte técnico."
        })

    # Extraer solo las preguntas para fuzzywuzzy
    solo_preguntas = [item[0] for item in preguntas_con_indices]

    # Buscar la coincidencia más cercana
    # process.extractOne devuelve (coincidencia_encontrada, score, indice_en_solo_preguntas)
    mejor_coincidencia_info = process.extractOne(pregunta_usuario, solo_preguntas, scorer=fuzz.token_set_ratio)

    pregunta_coincidencia = None
    similitud = 0

    if mejor_coincidencia_info:
        pregunta_coincidencia_str, similitud, index_en_solo_preguntas = mejor_coincidencia_info
        # Recuperar la pregunta original (con su capitalización, si es necesario)
        pregunta_coincidencia = preguntas_con_indices[index_en_solo_preguntas][0]
        print(f"Pregunta ingresada: {pregunta_usuario}")
        print(f"Mejor coincidencia: '{pregunta_coincidencia}' con similitud: {similitud}")

    # Si la coincidencia es suficientemente alta, responde directamente
    if similitud >= 90:
        # Encontrar la entrada original en base_conocimiento
        respuesta_encontrada = next((entry["respuesta"] for entry in base_conocimiento if entry.get("pregunta", "").lower() == pregunta_coincidencia.lower()), None)
        if respuesta_encontrada:
            return jsonify({"respuesta": respuesta_encontrada})

    # Si no hay coincidencia exacta, buscar recomendaciones
    recomendaciones = process.extract(pregunta_usuario, solo_preguntas, limit=5, scorer=fuzz.token_set_ratio)
    print(f"Resultados de fuzzywuzzy para recomendaciones: {recomendaciones}")

    recomendaciones_filtradas = []
    for pregunta_rec_str, score, index_rec_en_solo_preguntas in recomendaciones:
        if score >= 50:
            # Asegurarse de obtener la pregunta original, no la que fue tokenizada por fuzzywuzzy
            pregunta_original_rec = preguntas_con_indices[index_rec_en_solo_preguntas][0]
            recomendaciones_filtradas.append(pregunta_original_rec)

    # Eliminar duplicados si los hay (aunque fuzzywuzzy debería evitarlo si las preguntas son distintas)
    recomendaciones_filtradas = list(dict.fromkeys(recomendaciones_filtradas))
    print(f"Recomendaciones filtradas (score >= 50): {recomendaciones_filtradas}")

    if recomendaciones_filtradas: # Si hay recomendaciones
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
    # Renderiza la plantilla de administración y pasa la base de conocimiento
    return render_template("admin.html", base_conocimiento=base_conocimiento)

@app.route("/update", methods=["POST"])
def update():
    # Obtiene los datos de la solicitud del formulario
    accion = request.form.get("accion")
    pregunta = request.form.get("pregunta", "").strip()
    respuesta = request.form.get("respuesta", "").strip()
    pregunta_original = request.form.get("pregunta_original", "").strip() # Para editar

    if not pregunta and accion != "delete": # La pregunta es obligatoria para añadir y editar
        return jsonify({"message": "La pregunta no puede estar vacía."})
    if not respuesta and accion == "add": # La respuesta es obligatoria para añadir
        return jsonify({"message": "La respuesta no puede estar vacía al añadir."})

    global base_conocimiento # Para modificar la variable global

    if accion == "add":
        # Verifica si la pregunta ya existe
        if any(entry.get("pregunta", "").lower() == pregunta.lower() for entry in base_conocimiento):
            return jsonify({"message": "Esta pregunta ya existe en la base de conocimiento."})
        
        # Añade una nueva entrada a la base de conocimiento
        new_entry = {
            "pregunta": pregunta,
            "respuesta": respuesta,
            "intencion": "", # Puedes añadir lógica para inferir intención/entidad si es necesario
            "entidad": []
        }
        base_conocimiento.append(new_entry)
        save_knowledge_base(base_conocimiento)
        return jsonify({"message": "Pregunta añadida exitosamente."})

    elif accion == "edit":
        if not pregunta_original:
            return jsonify({"message": "Se requiere la pregunta original para editar."})

        found = False
        for entry in base_conocimiento:
            if entry.get("pregunta", "").lower() == pregunta_original.lower():
                entry["pregunta"] = pregunta # Actualiza la pregunta
                entry["respuesta"] = respuesta # Actualiza la respuesta
                found = True
                break
        
        if found:
            save_knowledge_base(base_conocimiento)
            return jsonify({"message": "Pregunta editada correctamente."})
        else:
            return jsonify({"message": "La pregunta original no fue encontrada."})

    elif accion == "delete":
        initial_len = len(base_conocimiento)
        # Filtra la base de conocimiento para eliminar la entrada que coincide con la pregunta
        base_conocimiento = [entry for entry in base_conocimiento if entry.get("pregunta", "").lower() != pregunta.lower()]
        
        if len(base_conocimiento) < initial_len:
            save_knowledge_base(base_conocimiento)
            return jsonify({"message": "Pregunta eliminada exitosamente."})
        else:
            return jsonify({"message": "La pregunta no existe."})

    else:
        return jsonify({"message": "Acción no válida."})

if __name__ == "__main__":
    # Asegúrate de que el archivo base_conocimiento.json exista con una lista vacía si no existe
    # o si está en un formato incorrecto.
    if not base_conocimiento:
        save_knowledge_base([]) # Crea un archivo JSON con una lista vacía si está vacío

    app.run(debug=True)
