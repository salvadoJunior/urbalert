import os
import time
from flask import Flask, request, jsonify, send_from_directory
from flask_mysqldb import MySQL
from flask_cors import CORS
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Ativar o CORS para permitir a comunicação com o vosso Frontend (HTML)
CORS(app)

# Configuração da Base de Dados MySQL (XAMPP)
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'urbalert'

mysql = MySQL(app)

# Configuração da pasta de uploads no Disco D
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


# --- ROTA PARA SERVIR AS IMAGENS PARA O FRONTEND ---
@app.route('/uploads/<filename>')
def serve_image(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# --- ROTA DE TESTE ---
@app.route('/')
def home():
    return jsonify({"mensagem": "API do UrbAlert a funcionar com sucesso!"})


# --- ROTA DE REGISTO DE UTILIZADOR (RF7) ---
@app.route('/api/registar', methods=['POST'])
def registar_utilizador():
    dados = request.get_json()
    nome = dados.get('nome')
    email = dados.get('email')
    password = dados.get('password')
    tipo = dados.get('tipo_utilizador', 'cidadao')

    if not nome or not email or not password:
        return jsonify({"erro": "Todos os campos são obrigatórios"}), 400

    senha_cripto = generate_password_hash(password)

    try:
        cursor = mysql.connection.cursor()
        cursor.execute(
            "INSERT INTO utilizador (nome, email, password, tipo_utilizador) VALUES (%s, %s, %s, %s)",
            (nome, email, senha_cripto, tipo)
        )
        mysql.connection.commit()
        cursor.close()
        return jsonify({"mensagem": "Utilizador registado com sucesso!"}), 201
    except Exception as e:
        return jsonify({"erro": "Erro ao registar utilizador", "detalhe": str(e)}), 400


# --- ROTA PARA CRIAR UMA DENÚNCIA (RF1, RF5, RF6) ---
@app.route('/api/denuncia', methods=['POST'])
def criar_denuncia():
    if 'imagem' not in request.files:
        return jsonify({"erro": "É obrigatório anexar uma imagem da ocorrência"}), 400

    file = request.files['imagem']
    titulo = request.form.get('titulo')
    descricao = request.form.get('descricao')
    localizacao = request.form.get('localizacao')

    if not titulo or not descricao or not localizacao:
        return jsonify({"erro": "Título, descrição e localização são obrigatórios"}), 400

    if file.filename == '':
        return jsonify({"erro": "Nenhum ficheiro de imagem selecionado"}), 400

    try:
        filename = secure_filename(file.filename)
        filename_unico = f"{int(time.time())}_{filename}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename_unico))

        cursor = mysql.connection.cursor()
        cursor.execute(
            "INSERT INTO denuncia (titulo, descricao, localizacao, imagem) VALUES (%s, %s, %s, %s)",
            (titulo, descricao, localizacao, filename_unico)
        )
        mysql.connection.commit()
        cursor.close()

        return jsonify({"mensagem": "Denúncia submetida com sucesso!", "foto_salva": filename_unico}), 201

    except Exception as e:
        print("\n❌ [ERRO REAL DO MYSQL]:", str(e), "\n")
        return jsonify({"erro": "Erro ao registar denúncia", "detalhe": str(e)}), 500


# --- ROTA PARA LISTAR TODAS AS DENÚNCIAS ---
@app.route('/api/denuncias', methods=['GET'])
def listar_denuncias():
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT id, titulo, descricao, localizacao, imagem, estado FROM denuncia ORDER BY id DESC")
        linhas = cursor.fetchall()  # <-- Guardado em português: linhas
        cursor.close()

        lista_denuncias = []
        for linha in linhas:  # <-- Lido em português: linhas (Corrigido!)
            lista_denuncias.append({
                "id": linha[0],
                "titulo": linha[1],
                "descricao": linha[2],
                "localizacao": inline_fix if False else linha[3],
                "imagem": linha[4],
                "estado": linha[5]
            })

        return jsonify(lista_denuncias), 200
    except Exception as e:
        print("\n❌ [ERRO AO LISTAR]:", str(e), "\n")
        return jsonify({"erro": "Erro ao carregar denúncias", "detalhe": str(e)}), 500


# --- ROTA PARA ATUALIZAR O ESTADO DA DENÚNCIA (RF2) ---
@app.route('/api/denuncia/<int:id_denuncia>/estado', methods=['PUT'])
def atualizar_estado(id_denuncia):
    dados = request.get_json()
    novo_estado = dados.get('estado')

    if novo_estado not in ['Pendente', 'Em Resolução', 'Resolvido']:
        return jsonify({"erro": "Estado inválido"}), 400

    try:
        cursor = mysql.connection.cursor()
        cursor.execute(
            "UPDATE denuncia SET estado = %s WHERE id = %s",
            (novo_estado, id_denuncia)
        )
        mysql.connection.commit()
        cursor.close()
        return jsonify(
            {"mensagem": f"Estado da denúncia #{id_denuncia} alterado para '{novo_estado}' com sucesso!"}), 200
    except Exception as e:
        return jsonify({"erro": "Erro ao atualizar estado no banco", "detalhe": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)