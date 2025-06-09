from datetime import timedelta
from flask import request, jsonify, Blueprint
from flask_jwt_extended import create_access_token, jwt_required
from sqlalchemy import select
from api.models import db, User
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

api = Blueprint('api', __name__)

CORS(api)

@api.route('/signup', methods=['POST'])
def create_usuario():
    data = request.get_json()
    required_fields = ["email", "user_name", "password", "ranking_user", "avatar", "experiencia"]

    if not all(field in data for field in required_fields):
        return jsonify({"msg": "Faltan campos obligatorios"}), 400
    
    nuevo_usuario = User(
        email = data["email"],
        user_name = data["user_name"],
        ranking_user = 0,
        password= generate_password_hash(data["password"]),  
        avatar = data["avatar"],  #Predefinir una o obligar al usuario a seleccionar una ?
        experiencia = 0
    )
    db.session.add(nuevo_usuario)
    db.session.commit()
    return jsonify(nuevo_usuario.serialize()), 201

@api.route('/usuarios', methods=['GET'])
def get_usuarios():
    usuarios = User.query.all()

    if not usuarios:
        return jsonify({"msg": "No hay usuarios registrados"}), 404
    
    return jsonify([user.serialize() for user in usuarios]), 200

@api.route('/token', methods=['POST'])
def login_user():
    body = request.get_json(silent=True)

    if body is None:
        return {"message": "Debes enviarme el body"}, 400

    if 'user_name' not in body or 'password' not in body:
        return {"message": "Datos incompletos"}, 404
    
    user = db.session.execute(select(User).where(User.user_name == body['user_name'])).scalar_one_or_none()

    if user is None or not check_password_hash(user.password, body['password']):
        return {"message": "Credenciales incorrectas"}, 401

    access_token = create_access_token(identity = str (user.id))
    return jsonify({ "token": access_token, "user_id": user.id })

@api.route('/usuarios/<int:user_id>', methods=['GET'])
def get_usuario(user_id):
    usuario = User.query.get(user_id)
    if not usuario:
        return jsonify({"msg": "Usuario no encontrado"}), 404
    return jsonify(usuario.serialize()), 200

@api.route('/usuarios/<int:user_id>', methods=['PUT'])
def update_usuario(user_id):
    usuario = User.query.get(user_id)
    if not usuario:
        return jsonify({"msg": "Usuario no encontrado"}), 404

    data = request.get_json()
    # if 'email' in data:
    #     usuario.email = data['email']
    if 'user_name' in data:
        usuario.user_name = data['user_name']
    if 'password' in data:
        usuario.password = generate_password_hash(data['password'])
    # if 'ranking_user' in data:
    #     usuario.ranking_user = data['ranking_user']
    if 'avatar' in data:
        usuario.avatar = data['avatar']
    # if 'experiencia' in data:
    #     usuario.experiencia = data['experiencia']

    db.session.commit()
    return jsonify(usuario.serialize()), 200

@api.route('/usuarios/<int:user_id>', methods=['DELETE'])
def delete_usuario(user_id):
    usuario = User.query.get(user_id)
    if not usuario:
        return jsonify({"msg": "Usuario no encontrado"}), 404

    db.session.delete(usuario)
    db.session.commit()
    return jsonify({"msg": "Usuario eliminado"}), 200

@api.route('/private', methods=['GET'])
@jwt_required
def private_route():
    return jsonify({"msg": "Esta es una ruta privada"}), 200

@api.route('/recover_password', methods=['POST'])
def recover_password():
    data = request.get_json()
    if not data or 'email' not in data:
        return jsonify({"msg": "Email es requerido"}), 400

    user = User.query.filter_by(email=data['email']).first()
    if not user:
        return jsonify({"msg": "Usuario no encontrado"}), 404

    reset_token = create_access_token(
        identity= User.id,
        expires_delta=timedelta(minutes=15),
        additional_claims={"pw_reset": True}
        )

    # Crear enlace de recuperación
    reset_link = f"http://localhost:3000/reset-password?token={reset_token}"

    # Enviar el enlace por correo o imprimirlo (simulación)
    print(f"Enlace de recuperación enviado a {User.email}: {reset_link}")

    return jsonify({"msg": "Correo de recuperación enviado"}), 200
















