"""Research CLI uses the same bounded source adapter as the application."""

from bible.youversion_source import main as main
from bible.youversion_source import *  # noqa: F403 -- retain the historical research-module reexport API

if __name__ == "__main__":
    main()
