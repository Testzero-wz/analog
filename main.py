from analog.bin.controller.controller import Controller
import os,sys


if sys.version_info < (3, 5):
    sys.stdout.write("Requires Python 3.5 or higher ")
    sys.exit(1)


def main():
    try:
        path = os.path.dirname(os.path.realpath(__file__))
        controller = Controller(path)
        controller.mainloop()

    except KeyboardInterrupt:
        print("User abort")
    except Exception as e:
        print(e)


if __name__ == "__main__":
    main()
