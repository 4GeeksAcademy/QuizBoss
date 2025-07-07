from datetime import timedelta
import os
from flask import request, jsonify, Blueprint
from flask_jwt_extended import create_access_token, decode_token, jwt_required
from flask_mail import Message
from sqlalchemy import select
from api.models import db, User
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from api.extensions import mail
from sqlalchemy import cast, Integer
import re


api = Blueprint('api', __name__)

CORS(api)


@api.route('/signup', methods=['POST'])
def create_usuario():
    data = request.get_json()
    required_fields = ["email", "user_name", "password",
                       "ranking_user", "avatar", "experiencia"]

    if not all(field in data for field in required_fields):
        return jsonify({"msg": "Faltan campos obligatorios"}), 400

    user = db.session.execute(select(User).where(
        User.email == data["email"])).scalar_one_or_none()
    if user:
        return jsonify({"msg": "El email ya está registrado"}), 400

    user = db.session.execute(select(User).where(
        User.user_name == data["user_name"])).scalar_one_or_none()
    if user:
        return jsonify({"msg": "El nombre de usuario ya está registrado"}), 400

    # Validaciones de formato para email, user_name y password
    if not isinstance(data["email"], str) or not data["email"].strip():
        return jsonify({"msg": "Email inválido"}), 400
    email_regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    if not re.match(email_regex, data["email"]):
        return jsonify({"msg": "Formato de email inválido"}), 400

    if not isinstance(data["user_name"], str) or not data["user_name"].strip():
        return jsonify({"msg": "Nombre de usuario inválido"}), 400
    # Solo letras, números y guiones bajos, sin espacios ni símbolos especiales ni emojis
    if not re.match(r"^[A-Za-z0-9_]+$", data["user_name"]):
        return jsonify({"msg": "El nombre de usuario solo puede contener letras, números y guiones bajos"}), 400

    if not isinstance(data["password"], str) or not data["password"].strip():
        return jsonify({"msg": "Contraseña inválida"}), 400
    # Solo permite letras, números y algunos símbolos seguros, sin emojis ni caracteres extraños
    if not re.match(r"^[A-Za-z0-9!@#$%^&*()_\-+=\[\]{};:,.<>?/|\\]+$", data["password"]):
        return jsonify({"msg": "La contraseña contiene caracteres no permitidos"}), 400

    # Validaciones de longitud
    if len(data["user_name"]) > 20:
        return jsonify({"msg": "El nombre de usuario no puede tener más de 20 caracteres"}), 400
    if len(data["password"]) > 32:
        return jsonify({"msg": "La contraseña no puede tener más de 32 caracteres"}), 400
    if len(data["password"]) < 6:
        return jsonify({"msg": "La contraseña debe tener al menos 6 caracteres"}), 400

    nuevo_usuario = User(
        email=data["email"],
        user_name=data["user_name"],
        ranking_user=0,
        password=generate_password_hash(data["password"]),
        avatar=data["avatar"],
        experiencia=0
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

    if 'user_name_or_email' not in body or 'password' not in body:
        return {"message": "Datos incompletos"}, 400

    user = db.session.execute(
        select(User).where(
            (User.user_name == body['user_name_or_email']) | (
                User.email == body['user_name_or_email'])
        )
    ).scalar_one_or_none()

    if user is None or not check_password_hash(user.password, body['password']):
        return {"message": "Credenciales incorrectas"}, 401

    access_token = create_access_token(identity=str(user.id))
    return jsonify({"token": access_token, "user_id": user.id})


@api.route('/usuarios/<int:user_id>', methods=['GET'])
def get_usuario(user_id):
    usuario = db.session.execute(select(User).where(
        User.id == user_id)).scalar_one_or_none()
    if not usuario:
        return jsonify({"msg": "Usuario no encontrado"}), 404
    return jsonify(usuario.serialize()), 200


@api.route('/usuarios/<int:user_id>', methods=['PUT'])
def update_usuario(user_id):
    usuario = User.query.get(user_id)
    if not usuario:
        return jsonify({"msg": "Usuario no encontrado"}), 404

    data = request.get_json()
    if 'user_name' in data:
        existing_user = db.session.execute(
            select(User).where(User.user_name ==
                               data['user_name'], User.id != user_id)
        ).scalar_one_or_none()
        if existing_user:
            return jsonify({"msg": "Ese nombre de usuario ya está en uso"}), 400
        usuario.user_name = data['user_name']
    if 'password' in data:
        usuario.password = generate_password_hash(data['password'])
    if 'avatar' in data:
        usuario.avatar = data['avatar']
    if 'experiencia' in data:
        usuario.experiencia = data['experiencia']
    if 'ranking_user' in data:
        usuario.ranking_user = data['ranking_user']

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


@api.route('/usuarios/ranking', methods=['GET'])
def get_usuarios_ranking():
    usuarios = db.session.execute(
        select(User).order_by(cast(User.ranking_user, Integer).desc())
    ).scalars().all()

    if not usuarios:
        return jsonify({"msg": "No hay usuarios registrados"}), 404

    return jsonify([user.serialize() for user in usuarios]), 200


@api.route('/recover_password', methods=['POST'])
def recover_password():
    data = request.get_json()
    if not data or 'email' not in data:
        return jsonify({"msg": "Email es requerido"}), 400

    user = db.session.execute(select(User).where(
        User.email == data['email'])).scalar_one_or_none()
    if user is None:
        return jsonify({"msg": "Usuario no encontrado"}), 404

    reset_token = create_access_token(
        identity=str(user.id),
        expires_delta=timedelta(minutes=15),
        additional_claims={"pw_reset": True}
    )

    frontend_url = os.getenv("VITE_BASENAME")
    reset_link = f"{frontend_url}/reset?token={reset_token}"

    if not isinstance(user.email, str) or not user.email.strip():
        return jsonify({"msg": "Email inválido del usuario"}), 400

    print("DEBUG user.email:", user.email, "type:", type(user.email))

    msg = Message(
        subject="Recuperación de password",
        recipients=[user.email]
    )
    msg.body = "Hola Jefe 🧠,\n\nPara recuperar tu password, haz clic en el siguiente enlace:\n\n{}\n\nEste enlace exp. en 15 minutos.".format(
        reset_link)
    msg.html = f"""
    <html>
        <body>
            <p>Hola Jefe 🧠,</p>
            <p>Para recuperar tu password, haz clic en el siguiente enlace:</p>
            <p><a href="{reset_link}">Recuperar password</a></p>
            <p>Este enlace exp. en 15 minutos.</p>
        </body>
    </html>
    """
    msg.charset = "utf-8"

    mail.send(msg)

    return jsonify({"msg": "Correo de recuperación enviado"}), 200


@api.route('/reset_password', methods=['POST'])
def reset_password():
    data = request.get_json()

    if not data or 'token' not in data or 'new_password' not in data:
        return jsonify({"msg": "Token y nueva contraseña son requeridos"}), 400
    if not isinstance(data['new_password'], str) or not data['new_password'].strip():
        return jsonify({"msg": "Nueva contraseña inválida"}), 400
    if len(data['new_password']) < 6 or len(data['new_password']) > 32:
        return jsonify({"msg": "La nueva contraseña debe tener entre 6 y 32 caracteres"}), 400
    if not re.match(r"^[A-Za-z0-9!@#$%^&*()_\-+=\[\]{};:,.<>?/|\\]+$", data['new_password']):
        return jsonify({"msg": "La nueva contraseña contiene caracteres no permitidos"}), 400

    try:
        decoded = decode_token(data['token'])

        if not decoded.get('pw_reset', False):
            return jsonify({"msg": "Token inválido para este propósito"}), 400

        user_id = int(decoded['sub'])  # ID del usuario (identity en el token)

        print(User)
        user = db.session.execute(select(User).where(
            User.id == user_id)).scalar_one_or_none()

        if user is None:
            return jsonify({"msg": "Usuario no encontrado"}), 404

        hashed_pw = generate_password_hash(data['new_password'])

        user.password = hashed_pw
        db.session.commit()

        return jsonify({"msg": "Contraseña actualizada con éxito"}), 200

    except Exception as e:
        print("ERROR BACKEND:", e)
        return jsonify({"msg": "Token inválido o expirado"}), 400
