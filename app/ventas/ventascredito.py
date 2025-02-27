from flask import session,jsonify,render_template

def ventacredito():
    # Verificar si el usuario está autenticado
    if not session.get('idusuario'):
        return redirect(url_for('auth.login'))
    return render_template('ventas/ventas_realizadas_credito.html')