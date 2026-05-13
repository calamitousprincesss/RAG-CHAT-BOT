import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.Config.app import create_app
from app.Config.settings import settings

app = create_app()


def main():
    print(f"\n  RAGChatbot running at http://{settings.app_host}:{settings.app_port}\n")
    app.run(host=settings.app_host, port=settings.app_port,
            debug=bool(settings.flask_debug))


if __name__ == "__main__":
    main()
