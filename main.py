from app import create_app
# Punto de entrada para la aplicación
app = create_app()

if __name__ == "__main__":
    app.run(debug=True)