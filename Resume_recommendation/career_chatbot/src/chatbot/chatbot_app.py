"""Compatibility entrypoint that delegates to the shared chatbot router."""

try:
    from .chat_router import main
except ImportError:
    from chat_router import main


if __name__ == "__main__":
    main()
