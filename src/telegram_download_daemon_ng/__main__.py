from . import cli, TelegramDownloadDaemon

def main():
    daemon = TelegramDownloadDaemon(args=cli.cli().parse_args())
    daemon.start()


if __name__ == "__main__":
    main()
