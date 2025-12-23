import logging

logging.basicConfig(
    level=logging.INFO,  # INFO 级别就够了
    format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
)

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
