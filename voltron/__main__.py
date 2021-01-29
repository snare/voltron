try:
    # for some reason the relative import doesn't work in VSCode's
    # interactive debugger, but this does but I'm not sure if there's a
    # chance a different voltron could be somewhere in sys.path, so
    # let's try the relative import first
    from .main import main
except ImportError:
    from voltron.main import main

main()
