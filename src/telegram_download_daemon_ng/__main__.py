from . import cli, TelegramDownloadDaemon

__version__ = "1.0.0-beta.6"


def main():
    daemon = TelegramDownloadDaemon(args=cli.cli().parse_args())
    daemon.start(version=__version__)


if __name__ == "__main__":
    main()
